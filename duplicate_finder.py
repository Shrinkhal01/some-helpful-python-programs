"""
Duplicate File Finder
A tool to find and manage duplicate files across directories.
"""
import os
import hashlib
import argparse
from collections import defaultdict
from pathlib import Path
import shutil
import sys
from datetime import datetime

class DuplicateFileFinder:
    def __init__(self, directories, ignore_patterns=None):
        self.directories = [Path(d) for d in directories]
        self.ignore_patterns = ignore_patterns or []
        self.file_hashes = defaultdict(list)
        self.duplicates = {}
        
    def calculate_file_hash(self, filepath, chunk_size=8192):
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            print(f"Error reading file {filepath}: {e}")
            return None
    
    def should_ignore_file(self, filepath):
        filename = filepath.name
        for pattern in self.ignore_patterns:
            if pattern in filename or filename.startswith(pattern):
                return True
        return False
    
    def scan_directories(self):
        print("Scanning directories for files...")
        total_files = 0
        
        for directory in self.directories:
            if not directory.exists():
                print(f"Warning: Directory {directory} does not exist")
                continue
                
            print(f"Scanning: {directory}")
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = Path(root) / filename
                    
                    if self.should_ignore_file(filepath):
                        continue
                    
                    try:
                        file_size = filepath.stat().st_size
                        if file_size == 0:  # Skip empty files
                            continue
                            
                        file_hash = self.calculate_file_hash(filepath)
                        if file_hash:
                            # Store file info: (path, size, modification_time)
                            file_info = (
                                filepath,
                                file_size,
                                filepath.stat().st_mtime
                            )
                            self.file_hashes[file_hash].append(file_info)
                            total_files += 1
                            
                            if total_files % 100 == 0:
                                print(f"Processed {total_files} files...", end='\r')
                                
                    except (OSError, IOError) as e:
                        print(f"Error processing {filepath}: {e}")
        
        print(f"\nCompleted scanning. Processed {total_files} files.")
    
    def find_duplicates(self):
        print("Identifying duplicates...")
        
        for file_hash, file_list in self.file_hashes.items():
            if len(file_list) > 1:
                # Sort by modification time (oldest first)
                file_list.sort(key=lambda x: x[2])
                self.duplicates[file_hash] = file_list
        
        print(f"Found {len(self.duplicates)} sets of duplicate files.")
    
    def display_duplicates(self):
        if not self.duplicates:
            print("No duplicate files found.")
            return
        
        total_duplicates = sum(len(files) - 1 for files in self.duplicates.values())
        total_wasted_space = sum(
            sum(info[1] for info in files[1:])  # Size of all but the first file
            for files in self.duplicates.values()
        )
        
        print(f"\n{'='*60}")
        print(f"DUPLICATE FILES REPORT")
        print(f"{'='*60}")
        print(f"Total duplicate sets: {len(self.duplicates)}")
        print(f"Total duplicate files: {total_duplicates}")
        print(f"Total wasted space: {self.format_size(total_wasted_space)}")
        print(f"{'='*60}\n")
        
        for i, (file_hash, files) in enumerate(self.duplicates.items(), 1):
            print(f"Duplicate Set #{i} (Hash: {file_hash[:12]}...)")
            print(f"File size: {self.format_size(files[0][1])}")
            
            for j, (filepath, size, mtime) in enumerate(files):
                mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                marker = " [ORIGINAL]" if j == 0 else " [DUPLICATE]"
                print(f"  {j+1}. {filepath}{marker}")
                print(f"     Modified: {mod_time}")
            print()
    
    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def remove_duplicates(self, interactive=True, dry_run=False):
        if not self.duplicates:
            print("No duplicates to remove.")
            return
        
        removed_count = 0
        space_freed = 0
        
        if dry_run:
            print("\n--- DRY RUN MODE (No files will be deleted) ---")
        
        for file_hash, files in self.duplicates.items():
            print(f"\nProcessing duplicate set (Hash: {file_hash[:12]}...):")
            
            # Keep the first file (oldest), remove the rest
            original = files[0]
            duplicates_to_remove = files[1:]
            
            print(f"  Keeping: {original[0]}")
            
            for filepath, size, mtime in duplicates_to_remove:
                if interactive and not dry_run:
                    response = input(f"  Delete {filepath}? (y/n/q): ").lower()
                    if response == 'q':
                        print("Operation cancelled by user.")
                        return
                    elif response != 'y':
                        print(f"  Skipping: {filepath}")
                        continue
                
                try:
                    if not dry_run:
                        filepath.unlink()
                        print(f"  Deleted: {filepath}")
                    else:
                        print(f"  Would delete: {filepath}")
                    
                    removed_count += 1
                    space_freed += size
                    
                except OSError as e:
                    print(f"  Error deleting {filepath}: {e}")
        
        action = "Would free" if dry_run else "Freed"
        print(f"\n{action} {self.format_size(space_freed)} by removing {removed_count} duplicate files.")
    
    def move_duplicates_to_folder(self, target_folder, dry_run=False):
        if not self.duplicates:
            print("No duplicates to move.")
            return
        
        target_path = Path(target_folder)
        
        if not dry_run:
            target_path.mkdir(parents=True, exist_ok=True)
        
        moved_count = 0
        
        if dry_run:
            print(f"\n--- DRY RUN MODE (No files will be moved) ---")
        
        for file_hash, files in self.duplicates.items():
            duplicates_to_move = files[1:]  # Skip the first (original) file
            
            for filepath, size, mtime in duplicates_to_move:
                # Create unique name to avoid conflicts
                counter = 1
                new_name = filepath.name
                while (target_path / new_name).exists():
                    name_parts = filepath.stem, counter, filepath.suffix
                    new_name = f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                    counter += 1
                
                new_path = target_path / new_name
                
                try:
                    if not dry_run:
                        shutil.move(str(filepath), str(new_path))
                        print(f"Moved: {filepath} -> {new_path}")
                    else:
                        print(f"Would move: {filepath} -> {new_path}")
                    
                    moved_count += 1
                    
                except OSError as e:
                    print(f"Error moving {filepath}: {e}")
        
        action = "Would move" if dry_run else "Moved"
        print(f"\n{action} {moved_count} duplicate files to {target_folder}")

def main():
    parser = argparse.ArgumentParser(description='Find and manage duplicate files')
    parser.add_argument('directories', nargs='*', help='Directories to scan (default: script location)')
    parser.add_argument('--ignore', nargs='*', default=['.DS_Store', 'Thumbs.db'],
                       help='File patterns to ignore')
    parser.add_argument('--remove', action='store_true',
                       help='Remove duplicate files (keeps oldest)')
    parser.add_argument('--move-to', metavar='FOLDER',
                       help='Move duplicates to specified folder')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run without prompting for confirmation')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    
    args = parser.parse_args()
    script_dir = Path(__file__).parent.absolute()
    
    if not args.directories:
        directories = [str(script_dir)]
        print(f"{'='*60}")
        print(f"DUPLICATE FILE FINDER")
        print(f"{'='*60}")
        print(f"No directory specified. Using script location:")
        print(f"Checking directory: {script_dir}")
        print(f"{'='*60}\n")
    else:
        directories = args.directories
        print(f"{'='*60}")
        print(f"DUPLICATE FILE FINDER")
        print(f"{'='*60}")
        print(f"Checking specified directories:")
        for i, directory in enumerate(directories, 1):
            print(f"  {i}. {os.path.abspath(directory)}")
        print(f"{'='*60}\n")
    for directory in directories:
        if not os.path.exists(directory):
            print(f"Error: Directory '{directory}' does not exist.")
            sys.exit(1)
    finder = DuplicateFileFinder(directories, args.ignore)
    finder.scan_directories()
    finder.find_duplicates()
    finder.display_duplicates()
    if args.remove:
        interactive = not args.non_interactive
        finder.remove_duplicates(interactive=interactive, dry_run=args.dry_run)
    elif args.move_to:
        finder.move_duplicates_to_folder(args.move_to, dry_run=args.dry_run)
    
    print("\nOperation completed.")

if __name__ == "__main__":
    main()
