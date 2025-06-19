import os
import argparse

def delete_empty_dirs(root_dir):
    deleted_count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                print(f"Deleted empty directory: {dirpath}")
                deleted_count += 1
            except OSError as e:
                print(f"Could not delete {dirpath}: {e}")
    if deleted_count == 0:
        print("No empty directories found.")
    else:
        print(f"\nTotal empty directories deleted: {deleted_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Empty Folder Cleaner - Deletes empty directories recursively.")
    parser.add_argument("path", help="Path to start scanning (e.g., /home/user/folder or C:\\Users\\Name\\folder)")

    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print("Invalid directory path!")
    else:
        delete_empty_dirs(os.path.abspath(args.path))
