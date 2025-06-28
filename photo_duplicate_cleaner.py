from pathlib import Path
from PIL import Image
import imagehash

def find_duplicates():
    hashes = {}
    
    # Scan images
    for img_file in Path('.').glob('*.{jpg,jpeg,png,gif,bmp,webp}'):
        try:
            with Image.open(img_file) as img:
                img_hash = str(imagehash.dhash(img))
                
                if img_hash in hashes:
                    # Found duplicate - keep larger file
                    existing = hashes[img_hash]
                    current_size = img_file.stat().st_size
                    existing_size = existing.stat().st_size
                    
                    if current_size > existing_size:
                        # Current is larger, delete existing
                        print(f"🗑️  Removing {existing.name}")
                        existing.unlink()
                        hashes[img_hash] = img_file
                    else:
                        # Existing is larger, delete current
                        print(f"🗑️  Removing {img_file.name}")
                        img_file.unlink()
                else:
                    hashes[img_hash] = img_file
                    
        except Exception as e:
            print(f"❌ Error with {img_file.name}: {e}")
    
    print(f"✅ Scan complete - kept {len(hashes)} unique images")

if __name__ == '__main__':
    find_duplicates()
