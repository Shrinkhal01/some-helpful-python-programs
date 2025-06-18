#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
import heapq
from datetime import datetime

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f} {size_names[i]}"

def scan_directory(directory, num_files=20, min_size=0, extensions=None):
    print(f"Scanning directory: {directory}")
    print("Please wait, this may take a while for large directories...\n")
    largest_files = []
    total_files = 0
    total_size = 0
    errors = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    
                    if not os.path.exists(file_path):
                        continue
                    file_size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += file_size
                    
                    if file_size < min_size:
                        continue
                    
                    if extensions:
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext not in extensions:
                            continue
                    
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if len(largest_files) < num_files:
                        heapq.heappush(largest_files, (file_size, file_path, mod_time))
                    elif file_size > largest_files[0][0]:
                        heapq.heapreplace(largest_files, (file_size, file_path, mod_time))
                    
                    if total_files % 1000 == 0:
                        print(f"Scanned {total_files} files...", end='\r')
                
                except (OSError, IOError, PermissionError):
                    errors += 1
                    continue
    
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
        return [], 0, 0, 0
    
    print(f"Scan complete! Processed {total_files} files")
    if errors > 0:
        print(f"Encountered {errors} files that couldn't be accessed")
    
    largest_files.sort(reverse=True)
    
    return largest_files, total_files, total_size, errors

def main():
    parser = argparse.ArgumentParser(
        description="Find the largest files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=
    )
    
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to scan (default: current directory)')
    parser.add_argument('-n', '--number', type=int, default=20,
                       help='Number of largest files to show (default: 20)')
    parser.add_argument('-s', '--size', type=str,
                       help='Minimum file size (e.g., 10MB, 1GB)')
    parser.add_argument('-e', '--extensions', nargs='+',
                       help='File extensions to include (e.g., .jpg .mp4)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory")
        sys.exit(1)
    
    min_size = 0
    if args.size:
        size_str = args.size.upper()
        multiplier = 1
        
        if size_str.endswith('KB'):
            multiplier = 1024
            size_str = size_str[:-2]
        elif size_str.endswith('MB'):
            multiplier = 1024 * 1024
            size_str = size_str[:-2]
        elif size_str.endswith('GB'):
            multiplier = 1024 * 1024 * 1024
            size_str = size_str[:-2]
        elif size_str.endswith('TB'):
            multiplier = 1024 * 1024 * 1024 * 1024
            size_str = size_str[:-2]
        elif size_str.endswith('B'):
            size_str = size_str[:-1]
        
        try:
            min_size = int(float(size_str) * multiplier)
        except ValueError:
            print(f"Error: Invalid size format '{args.size}'")
            sys.exit(1)
    extensions = None
    if args.extensions:
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                     for ext in args.extensions]
    
    largest_files, total_files, total_size, errors = scan_directory(
        args.directory, args.number, min_size, extensions
    )
    
    print("\n" + "="*80)
    print(f"LARGEST FILES IN: {os.path.abspath(args.directory)}")
    print("="*80)
    
    if not largest_files:
        print("No files found matching the criteria.")
        return
    
    print(f"{'Rank':<4} {'Size':<12} {'Modified':<20} {'File Path'}")
    print("-" * 80)
    
    for i, (size, path, mod_time) in enumerate(largest_files, 1):
        print(f"{i:<4} {format_size(size):<12} {mod_time.strftime('%Y-%m-%d %H:%M'):<20} {path}")
    
    print("\n" + "="*80)
    print(f"SUMMARY:")
    print(f"Total files scanned: {total_files:,}")
    print(f"Total size of all files: {format_size(total_size)}")
    if errors > 0:
        print(f"Files with access errors: {errors}")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
