#!/usr/bin/env python3

import os
import sys
import argparse
import stat
import shutil
from pathlib import Path
from datetime import datetime
import platform

# Windows-specific imports (only if on Windows)
if platform.system() == 'Windows':
    try:
        import ctypes
        from ctypes import wintypes
        HAS_WINDOWS_API = True
    except ImportError:
        HAS_WINDOWS_API = False
else:
    HAS_WINDOWS_API = False

class HiddenFileFinder:
    def __init__(self):
        self.system = platform.system()
        self.hidden_files = []
        self.total_files = 0
        self.total_size = 0
        self.errors = 0
        
    def format_size(self, size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.2f} {size_names[i]}"
    
    def is_hidden_windows(self, filepath):
        """Check if file is hidden on Windows using API"""
        if not HAS_WINDOWS_API:
            # Fallback: check for dot prefix or common Windows hidden files
            filename = os.path.basename(filepath)
            return (filename.startswith('.') or 
                   filename.lower() in ['thumbs.db', 'desktop.ini', '$recycle.bin'])
        
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
            return bool(attrs != -1 and attrs & 2)  # FILE_ATTRIBUTE_HIDDEN = 2
        except:
            return False
    
    def is_hidden_unix(self, filepath):
        """Check if file is hidden on Unix-like systems"""
        filename = os.path.basename(filepath)
        return filename.startswith('.')
    
    def is_hidden(self, filepath):
        """Cross-platform hidden file detection"""
        if self.system == 'Windows':
            return self.is_hidden_windows(filepath)
        else:
            return self.is_hidden_unix(filepath)
    
    def get_file_attributes(self, filepath):
        """Get detailed file attributes"""
        try:
            stat_info = os.stat(filepath)
            return {
                'size': stat_info.st_size,
                'modified': datetime.fromtimestamp(stat_info.st_mtime),
                'accessed': datetime.fromtimestamp(stat_info.st_atime),
                'created': datetime.fromtimestamp(stat_info.st_ctime),
                'permissions': stat.filemode(stat_info.st_mode),
                'is_dir': stat.S_ISDIR(stat_info.st_mode),
                'is_file': stat.S_ISREG(stat_info.st_mode),
                'is_link': stat.S_ISLNK(stat_info.st_mode)
            }
        except (OSError, IOError):
            return None
    
    def scan_directory(self, directory, recursive=True, include_system=False):
        """Scan directory for hidden files"""
        print(f"Scanning for hidden files in: {directory}")
        print(f"Platform: {self.system}")
        print("Please wait...\n")
        
        self.hidden_files = []
        self.total_files = 0
        self.total_size = 0
        self.errors = 0
        
        try:
            if recursive:
                for root, dirs, files in os.walk(directory):
                    # Process directories
                    for dirname in dirs[:]:  # Use slice to avoid modification during iteration
                        dir_path = os.path.join(root, dirname)
                        self.total_files += 1
                        
                        try:
                            if self.is_hidden(dir_path):
                                attrs = self.get_file_attributes(dir_path)
                                if attrs:
                                    self.hidden_files.append({
                                        'path': dir_path,
                                        'type': 'directory',
                                        'name': dirname,
                                        'size': 0,  # Directories don't have size
                                        'attributes': attrs
                                    })
                                
                                # Skip scanning inside hidden directories unless include_system is True
                                if not include_system:
                                    dirs.remove(dirname)
                        
                        except (OSError, IOError, PermissionError):
                            self.errors += 1
                            continue
                    
                    # Process files
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        self.total_files += 1
                        
                        try:
                            if self.is_hidden(file_path):
                                attrs = self.get_file_attributes(file_path)
                                if attrs:
                                    self.hidden_files.append({
                                        'path': file_path,
                                        'type': 'file',
                                        'name': filename,
                                        'size': attrs['size'],
                                        'attributes': attrs
                                    })
                                    self.total_size += attrs['size']
                        
                        except (OSError, IOError, PermissionError):
                            self.errors += 1
                            continue
                        
                        # Progress indicator
                        if self.total_files % 1000 == 0:
                            print(f"Scanned {self.total_files} items, found {len(self.hidden_files)} hidden...", end='\r')
            
            else:
                # Non-recursive scan
                try:
                    for item in os.listdir(directory):
                        item_path = os.path.join(directory, item)
                        self.total_files += 1
                        
                        if self.is_hidden(item_path):
                            attrs = self.get_file_attributes(item_path)
                            if attrs:
                                item_type = 'directory' if attrs['is_dir'] else 'file'
                                size = attrs['size'] if attrs['is_file'] else 0
                                
                                self.hidden_files.append({
                                    'path': item_path,
                                    'type': item_type,
                                    'name': item,
                                    'size': size,
                                    'attributes': attrs
                                })
                                
                                if attrs['is_file']:
                                    self.total_size += size
                
                except (OSError, IOError, PermissionError):
                    print(f"Error: Cannot access directory {directory}")
                    return False
        
        except KeyboardInterrupt:
            print("\nScan interrupted by user")
            return False
        
        print(f"\nScan complete! Found {len(self.hidden_files)} hidden items")
        return True
    
    def display_results(self, sort_by='size', show_details=False):
        """Display scan results"""
        if not self.hidden_files:
            print("No hidden files found.")
            return
        
        # Sort results
        if sort_by == 'size':
            self.hidden_files.sort(key=lambda x: x['size'], reverse=True)
        elif sort_by == 'name':
            self.hidden_files.sort(key=lambda x: x['name'].lower())
        elif sort_by == 'date':
            self.hidden_files.sort(key=lambda x: x['attributes']['modified'], reverse=True)
        elif sort_by == 'type':
            self.hidden_files.sort(key=lambda x: (x['type'], x['name'].lower()))
        
        print("\n" + "="*100)
        print("HIDDEN FILES AND DIRECTORIES FOUND")
        print("="*100)
        
        # Summary
        files_count = sum(1 for item in self.hidden_files if item['type'] == 'file')
        dirs_count = sum(1 for item in self.hidden_files if item['type'] == 'directory')
        
        print(f"Files: {files_count} | Directories: {dirs_count} | Total Size: {self.format_size(self.total_size)}")
        print("-" * 100)
        
        if show_details:
            print(f"{'Type':<4} {'Size':<10} {'Modified':<20} {'Permissions':<12} {'Path'}")
            print("-" * 100)
            
            for item in self.hidden_files:
                type_indicator = "DIR" if item['type'] == 'directory' else "FILE"
                size_str = self.format_size(item['size']) if item['type'] == 'file' else "-"
                mod_time = item['attributes']['modified'].strftime('%Y-%m-%d %H:%M')
                permissions = item['attributes']['permissions']
                
                print(f"{type_indicator:<4} {size_str:<10} {mod_time:<20} {permissions:<12} {item['path']}")
        else:
            print(f"{'Type':<4} {'Size':<10} {'Name':<30} {'Path'}")
            print("-" * 100)
            
            for item in self.hidden_files[:50]:  # Limit to first 50 for readability
                type_indicator = "DIR" if item['type'] == 'directory' else "FILE"
                size_str = self.format_size(item['size']) if item['type'] == 'file' else "-"
                name = item['name'][:27] + "..." if len(item['name']) > 30 else item['name']
                path = item['path']
                
                print(f"{type_indicator:<4} {size_str:<10} {name:<30} {path}")
            
            if len(self.hidden_files) > 50:
                print(f"\n... and {len(self.hidden_files) - 50} more items (use --details to see all)")
        
        print("\n" + "="*100)
        print(f"SUMMARY: Scanned {self.total_files} items total")
        if self.errors > 0:
            print(f"Access errors: {self.errors}")
        print("="*100)
    
    def unhide_file(self, filepath):
        """Unhide a file (platform-specific)"""
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        try:
            if self.system == 'Windows' and HAS_WINDOWS_API:
                # Remove hidden attribute on Windows
                attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)
                if attrs != -1:
                    new_attrs = attrs & ~2  # Remove FILE_ATTRIBUTE_HIDDEN
                    result = ctypes.windll.kernel32.SetFileAttributesW(filepath, new_attrs)
                    return bool(result), "Success" if result else "Failed to modify attributes"
            else:
                # On Unix-like systems, rename file to remove dot prefix
                if os.path.basename(filepath).startswith('.'):
                    directory = os.path.dirname(filepath)
                    old_name = os.path.basename(filepath)
                    new_name = old_name[1:]  # Remove the dot
                    new_path = os.path.join(directory, new_name)
                    
                    if os.path.exists(new_path):
                        return False, f"File {new_name} already exists"
                    
                    os.rename(filepath, new_path)
                    return True, f"Renamed to {new_path}"
                else:
                    return False, "File is not hidden by dot prefix"
        
        except Exception as e:
            return False, str(e)
    
    def delete_hidden_files(self, pattern=None, confirm=True):
        """Delete hidden files matching pattern"""
        if not self.hidden_files:
            print("No hidden files to delete.")
            return
        
        files_to_delete = []
        
        if pattern:
            # Filter by pattern
            for item in self.hidden_files:
                if pattern.lower() in item['name'].lower():
                    files_to_delete.append(item)
        else:
            files_to_delete = self.hidden_files[:]
        
        if not files_to_delete:
            print(f"No hidden files matching pattern '{pattern}' found.")
            return
        
        print(f"\nFiles to delete ({len(files_to_delete)} items):")
        for item in files_to_delete[:20]:  # Show first 20
            print(f"  {item['type'].upper()}: {item['path']}")
        
        if len(files_to_delete) > 20:
            print(f"  ... and {len(files_to_delete) - 20} more items")
        
        if confirm:
            response = input(f"\nDelete {len(files_to_delete)} hidden items? (yes/no): ").lower()
            if response not in ['yes', 'y']:
                print("Operation cancelled.")
                return
        
        deleted = 0
        errors = 0
        
        for item in files_to_delete:
            try:
                if item['type'] == 'directory':
                    shutil.rmtree(item['path'])
                else:
                    os.remove(item['path'])
                deleted += 1
            except Exception as e:
                print(f"Error deleting {item['path']}: {e}")
                errors += 1
        
        print(f"\nDeleted {deleted} items successfully.")
        if errors > 0:
            print(f"Failed to delete {errors} items.")

def main():
    parser = argparse.ArgumentParser(
        description="Find and manage hidden files across platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hidden_file_finder.py                          # Scan current directory
  python hidden_file_finder.py /home/user               # Scan specific directory
  python hidden_file_finder.py --no-recursive           # Scan only current level
  python hidden_file_finder.py --sort name              # Sort by name
  python hidden_file_finder.py --details                # Show detailed info
  python hidden_file_finder.py --unhide /path/to/file   # Unhide specific file
  python hidden_file_finder.py --delete-pattern .DS_Store  # Delete matching files
        """
    )
    
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to scan (default: current directory)')
    parser.add_argument('--no-recursive', action='store_true',
                       help='Do not scan subdirectories')
    parser.add_argument('--include-system', action='store_true',
                       help='Include system hidden directories in scan')
    parser.add_argument('--sort', choices=['size', 'name', 'date', 'type'], default='size',
                       help='Sort results by (default: size)')
    parser.add_argument('--details', action='store_true',
                       help='Show detailed information')
    parser.add_argument('--unhide', type=str, metavar='FILEPATH',
                       help='Unhide a specific file')
    parser.add_argument('--delete-pattern', type=str, metavar='PATTERN',
                       help='Delete hidden files matching pattern')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation for delete operations')
    
    args = parser.parse_args()
    
    finder = HiddenFileFinder()
    
    # Handle unhide operation
    if args.unhide:
        success, message = finder.unhide_file(args.unhide)
        print(f"Unhide result: {message}")
        sys.exit(0 if success else 1)
    
    # Validate directory
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory")
        sys.exit(1)
    
    # Scan directory
    success = finder.scan_directory(
        args.directory, 
        recursive=not args.no_recursive,
        include_system=args.include_system
    )
    
    if not success:
        sys.exit(1)
    
    # Display results
    finder.display_results(sort_by=args.sort, show_details=args.details)
    
    # Handle delete operation
    if args.delete_pattern:
        finder.delete_hidden_files(
            pattern=args.delete_pattern,
            confirm=not args.no_confirm
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
