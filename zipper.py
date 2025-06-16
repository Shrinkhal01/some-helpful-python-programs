import os
import zipfile
from pathlib import Path
def create_zip_archive(source_folder, zip_filename):
    source_path = Path(source_folder)
    if not os.path.dirname(zip_filename):
        zip_path = source_path / zip_filename
    else:
        zip_path = Path(zip_filename)
    if not source_path.exists():
        print(f"Error: Source folder '{source_folder}' does not exist.")
        return False
    if not source_path.is_dir():
        print(f"Error: '{source_folder}' is not a directory.")
        return False
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            print(f"Creating zip archive: {zip_path}")
            print(f"Archiving contents of: {source_path}")
            for root, dirs, files in os.walk(source_path):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    if file_path.resolve() == zip_path.resolve():
                        print(f"Skipping zip file itself: {file}")
                        continue
                    arcname = file_path.relative_to(source_path)
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")
                for dir_name in dirs:
                    dir_path = root_path / dir_name
                    if not any(dir_path.iterdir()):
                        arcname = dir_path.relative_to(source_path)
                        zipf.writestr(str(arcname) + "/", "")
                        print(f"Added empty directory: {arcname}/")
        
        print(f"\nZip archive created successfully: {zip_path}")
        file_size = zip_path.stat().st_size
        print(f"Archive size: {file_size:,} bytes ({file_size / 1048576:.2f} MB)")
        print(f"Archive location: {zip_path.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"Error creating zip archive: {e}")
        return False

def main():
    # Specify the folder to zip - your Downloads folder
    source_folder = "/Users/shrinkhals/Downloads"
    
    # Specify the output zip filename (will be created in the same folder)
    zip_filename = "Downloads_Archive.zip"
    
    print("=== Directory Zip Creator ===")
    print(f"Source folder: {source_folder}")
    print(f"Output zip file: {zip_filename}")
    print(f"Zip will be created at: {Path(source_folder) / zip_filename}")
    print("-" * 40)
    success = create_zip_archive(source_folder, zip_filename)
    
    if success:
        print("\n✓ Archive creation completed successfully!")
    else:
        print("\n✗ Archive creation failed!")
def list_zip_contents(zip_filename):
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zipf:
            print(f"\nContents of {zip_filename}:")
            print("-" * 40)
            for info in zipf.infolist():
                print(f"{info.filename:40} {info.file_size:>10} bytes")
            print("-" * 40)
            print(f"Total files: {len(zipf.infolist())}")
    except Exception as e:
        print(f"Error reading zip file: {e}")

if __name__ == "__main__":
    main()
    list_zip_contents(Path(source_folder) / zip_filename)
