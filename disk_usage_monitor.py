import os
import sys
import time
import json
import smtplib
import platform
import subprocess
import psutil
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import argparse
import logging
from pathlib import Path

class DiskUsageMonitor:
    def __init__(self, config_file='disk_monitor_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.last_alerts = {}  # Track when alerts were last sent
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        

        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / 'disk_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "thresholds": {
                "warning": 80,
                "critical": 90
            },
            "monitored_paths": ["/", "C:\\"] if platform.system() == "Windows" else ["/"],
            "check_interval": 300,  # 5 minutes
            "alert_methods": {
                "console": True,
                "email": False,
                "log": True,
                "system_notification": True
            },
            "email_config": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipient_emails": []
            },
            "alert_cooldown": 3600,  # 1 hour between similar alerts
            "log_level": "INFO",
            "exclude_filesystems": ["tmpfs", "devtmpfs", "squashfs"]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)

                for key, value in default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                return loaded_config
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return default_config
        else:

            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Save configuration to file"""
        config_to_save = config or self.config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def format_bytes(self, bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def get_disk_usage(self, path):
        """Get disk usage statistics for a path"""
        try:
            if platform.system() == "Windows":

                usage = psutil.disk_usage(path)
                return {
                    'path': path,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
            else:

                statvfs = os.statvfs(path)
                total = statvfs.f_blocks * statvfs.f_frsize
                free = statvfs.f_available * statvfs.f_frsize
                used = total - free
                percent = (used / total) * 100 if total > 0 else 0
                
                return {
                    'path': path,
                    'total': total,
                    'used': used,
                    'free': free,
                    'percent': percent
                }
        except Exception as e:
            self.logger.error(f"Error getting disk usage for {path}: {e}")
            return None
    
    def get_all_disks(self):
        """Get all available disks/partitions"""
        disks = []
        
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:

                if partition.fstype.lower() in [fs.lower() for fs in self.config.get('exclude_filesystems', [])]:
                    continue
                
                try:
                    usage = self.get_disk_usage(partition.mountpoint)
                    if usage:
                        usage['device'] = partition.device
                        usage['fstype'] = partition.fstype
                        usage['mountpoint'] = partition.mountpoint
                        disks.append(usage)
                except PermissionError:

                    continue
                except Exception as e:
                    self.logger.warning(f"Could not get usage for {partition.mountpoint}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error getting disk list: {e}")
        
        return disks
    
    def should_send_alert(self, path, alert_type):
        """Check if enough time has passed since last alert"""
        cooldown = self.config.get('alert_cooldown', 3600)
        alert_key = f"{path}_{alert_type}"
        
        if alert_key in self.last_alerts:
            time_since_last = time.time() - self.last_alerts[alert_key]
            return time_since_last >= cooldown
        
        return True
    
    def mark_alert_sent(self, path, alert_type):
        """Mark that an alert was sent"""
        alert_key = f"{path}_{alert_type}"
        self.last_alerts[alert_key] = time.time()
    
    def send_console_alert(self, disk_info, alert_level):
        """Send alert to console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*60}")
        print(f"🚨 DISK USAGE ALERT - {alert_level.upper()}")
        print(f"{'='*60}")
        print(f"Timestamp: {timestamp}")
        print(f"Path: {disk_info['path']}")
        print(f"Device: {disk_info.get('device', 'Unknown')}")
        print(f"Usage: {disk_info['percent']:.1f}%")
        print(f"Used: {self.format_bytes(disk_info['used'])}")
        print(f"Free: {self.format_bytes(disk_info['free'])}")
        print(f"Total: {self.format_bytes(disk_info['total'])}")
        print(f"{'='*60}\n")
    
    def send_email_alert(self, disk_info, alert_level):
        """Send email alert"""
        if not self.config['alert_methods'].get('email', False):
            return False
        
        email_config = self.config['email_config']
        if not email_config.get('sender_email') or not email_config.get('recipient_emails'):
            self.logger.warning("Email configuration incomplete")
            return False
        
        try:
            msg = MimeMultipart()
            msg['From'] = email_config['sender_email']
            msg['To'] = ', '.join(email_config['recipient_emails'])
            msg['Subject'] = f"Disk Usage Alert - {alert_level.upper()} - {platform.node()}"
            
            body = f"""
            Disk Usage Alert - {alert_level.upper()}
            
            Server: {platform.node()}
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Disk Information:
            - Path: {disk_info['path']}
            - Device: {disk_info.get('device', 'Unknown')}
            - Usage: {disk_info['percent']:.1f}%
            - Used Space: {self.format_bytes(disk_info['used'])}
            - Free Space: {self.format_bytes(disk_info['free'])}
            - Total Space: {self.format_bytes(disk_info['total'])}
            
            Please take action to free up disk space.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email alert sent for {disk_info['path']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
    
    def send_system_notification(self, disk_info, alert_level):
        """Send system notification"""
        if not self.config['alert_methods'].get('system_notification', False):
            return False
        
        title = f"Disk Usage Alert - {alert_level.upper()}"
        message = f"Disk {disk_info['path']} is {disk_info['percent']:.1f}% full"
        
        try:
            system = platform.system()
            if system == "Windows":
                # Windows notification
                subprocess.run([
                    'powershell', '-Command',
                    f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show("{message}", "{title}")'
                ], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{message}" with title "{title}"'
                ], check=True)
            elif system == "Linux":
                # Try different notification methods
                try:
                    subprocess.run(['notify-send', title, message], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        subprocess.run(['zenity', '--info', f'--text={title}\n{message}'], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        self.logger.warning("No notification system found on Linux")
                        return False
            
            self.logger.info(f"System notification sent for {disk_info['path']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send system notification: {e}")
            return False
    
    def check_disk_usage(self):
        """Check disk usage and send alerts if necessary"""
        self.logger.info("Starting disk usage check...")
        
        # Get monitored paths or all disks
        if self.config.get('monitored_paths'):
            disks_to_check = []
            for path in self.config['monitored_paths']:
                if os.path.exists(path):
                    usage = self.get_disk_usage(path)
                    if usage:
                        disks_to_check.append(usage)
        else:
            disks_to_check = self.get_all_disks()
        
        alerts_sent = 0
        
        for disk in disks_to_check:
            usage_percent = disk['percent']
            path = disk['path']
            
            # Determine alert level
            alert_level = None
            if usage_percent >= self.config['thresholds']['critical']:
                alert_level = 'critical'
            elif usage_percent >= self.config['thresholds']['warning']:
                alert_level = 'warning'
            
            if alert_level and self.should_send_alert(path, alert_level):
                self.logger.warning(f"Disk usage alert: {path} is {usage_percent:.1f}% full")
                
                # Send alerts based on configuration
                if self.config['alert_methods'].get('console', True):
                    self.send_console_alert(disk, alert_level)
                
                if self.config['alert_methods'].get('email', False):
                    self.send_email_alert(disk, alert_level)
                
                if self.config['alert_methods'].get('system_notification', False):
                    self.send_system_notification(disk, alert_level)
                
                self.mark_alert_sent(path, alert_level)
                alerts_sent += 1
        
        if alerts_sent == 0:
            self.logger.info("All monitored disks are within normal usage limits")
        
        return alerts_sent > 0
    
    def display_current_usage(self):
        """Display current disk usage"""
        print(f"\nDisk Usage Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        disks = self.get_all_disks()
        
        if not disks:
            print("No disk information available")
            return
        
        print(f"{'Device':<15} {'Path':<20} {'Usage':<8} {'Used':<12} {'Free':<12} {'Total':<12}")
        print("-"*80)
        
        for disk in disks:
            device = disk.get('device', 'Unknown')[:14]
            path = disk['path'][:19]
            usage = f"{disk['percent']:.1f}%"
            used = self.format_bytes(disk['used'])
            free = self.format_bytes(disk['free'])
            total = self.format_bytes(disk['total'])
            
            # Color coding for usage levels
            if disk['percent'] >= self.config['thresholds']['critical']:
                status = "🔴"
            elif disk['percent'] >= self.config['thresholds']['warning']:
                status = "🟡"
            else:
                status = "🟢"
            
            print(f"{device:<15} {path:<20} {usage:<8} {used:<12} {free:<12} {total:<12} {status}")
        
        print("="*80)
        print("🟢 Normal  🟡 Warning  🔴 Critical")
    
    def run_monitor(self, daemon=False):
        """Run the monitor continuously or once"""
        if daemon:
            self.logger.info("Starting disk usage monitor in daemon mode...")
            self.logger.info(f"Check interval: {self.config['check_interval']} seconds")
            
            try:
                while True:
                    self.check_disk_usage()
                    time.sleep(self.config['check_interval'])
            except KeyboardInterrupt:
                self.logger.info("Monitor stopped by user")
        else:
            self.check_disk_usage()

def main():
    parser = argparse.ArgumentParser(
        description="Monitor disk usage and send alerts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python disk_usage_monitor.py                    # Check once and exit
  python disk_usage_monitor.py --daemon           # Run continuously
  python disk_usage_monitor.py --status           # Show current disk usage
  python disk_usage_monitor.py --config           # Create/edit configuration
  python disk_usage_monitor.py --test-alert       # Test alert system
        """
    )
    
    parser.add_argument('--daemon', action='store_true',
                       help='Run continuously as a daemon')
    parser.add_argument('--status', action='store_true',
                       help='Display current disk usage status')
    parser.add_argument('--config', action='store_true',
                       help='Create or edit configuration file')
    parser.add_argument('--test-alert', action='store_true',
                       help='Test alert system with fake data')
    parser.add_argument('--config-file', default='disk_monitor_config.json',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    monitor = DiskUsageMonitor(args.config_file)
    
    if args.config:
        print(f"Configuration file: {args.config_file}")
        print("Edit the configuration file to customize monitoring settings.")
        monitor.save_config()
        
        print("\nCurrent configuration:")
        print(json.dumps(monitor.config, indent=2))
        return
    
    if args.status:
        monitor.display_current_usage()
        return
    
    if args.test_alert:
        # Create fake disk info for testing
        fake_disk = {
            'path': '/test',
            'device': '/dev/test',
            'percent': 95.0,
            'used': 950 * 1024**3,  # 950 GB
            'free': 50 * 1024**3,   # 50 GB
            'total': 1000 * 1024**3  # 1 TB
        }
        
        print("Testing alert system...")
        monitor.send_console_alert(fake_disk, 'critical')
        
        if monitor.config['alert_methods'].get('email'):
            monitor.send_email_alert(fake_disk, 'critical')
        
        if monitor.config['alert_methods'].get('system_notification'):
            monitor.send_system_notification(fake_disk, 'critical')
        
        print("Test complete!")
        return
    
    # Default: run monitor
    try:
        monitor.run_monitor(daemon=args.daemon)
    except Exception as e:
        monitor.logger.error(f"Monitor error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
