import os
import shutil
from pathlib import Path

UNWANTED = [
    "*.pyc", "*.pyo", "*.pyd",           # Python cache
    "__pycache__", ".pytest_cache",      # Python folders
    ".DS_Store", "Thumbs.db",            # OS files
    "*.tmp", "*.log", "*~",              # Temp files
    ".mypy_cache", ".coverage"           # Dev tools
]

def clean_repo():
    """Clean unwanted files from current directory"""
    if not Path('.git').exists():
        print("❌ Not a git repository!")
        return
    
    removed = 0
    
    for pattern in UNWANTED:
        matches = list(Path('.').glob(f'**/{pattern}'))
        
        for item in matches:
            try:
                if item.is_file():
                    item.unlink()
                    print(f"🗑️  Removed file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"🗑️  Removed folder: {item}")
                removed += 1
            except Exception as e:
                print(f"❌ Failed to remove {item}: {e}")
    
    if removed == 0:
        print("✅ Repository is already clean!")
    else:
        print(f"✅ Cleaned {removed} items")

if __name__ == '__main__':
    clean_repo()
