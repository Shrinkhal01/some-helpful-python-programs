import os
import shutil
from pathlib import Path
from PIL import Image
import subprocess
IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
VIDEO_TYPES = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']

def get_image_resolution(file_path):

    try:
        with Image.open(file_path) as img:
            return img.width, img.height
    except:
        return 0, 0

def get_video_duration(file_path):

    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 
            'format=duration', '-of', 'csv=p=0', str(file_path)
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0

def categorize_image(width, height):
    """Categorize image by resolution"""
    pixels = width * height
    if pixels >= 8000000:  # 8MP+
        return "high_res"
    elif pixels >= 2000000:  # 2MP+
        return "medium_res"
    else:
        return "low_res"

def categorize_video(duration):
    """Categorize video by duration"""
    if duration >= 3600:  # 1 hour+
        return "long_videos"
    elif duration >= 300:  # 5 minutes+
        return "medium_videos"
    else:
        return "short_videos"

def organize_media():
    """Organize media files in current directory"""
    current_dir = Path('.')
    organized = 0
    
    for file_path in current_dir.iterdir():
        if not file_path.is_file():
            continue
            
        ext = file_path.suffix.lower()
        folder = None
        
        if ext in IMAGE_TYPES:
            width, height = get_image_resolution(file_path)
            if width > 0 and height > 0:
                folder = categorize_image(width, height)
                print(f"📸 {file_path.name} -> {folder} ({width}x{height})")
        
        elif ext in VIDEO_TYPES:
            duration = get_video_duration(file_path)
            if duration > 0:
                folder = categorize_video(duration)
                mins = int(duration // 60)
                secs = int(duration % 60)
                print(f"🎬 {file_path.name} -> {folder} ({mins}m {secs}s)")
        
        if folder:
            folder_path = Path(folder)
            folder_path.mkdir(exist_ok=True)
            
            try:
                shutil.move(str(file_path), str(folder_path / file_path.name))
                organized += 1
            except Exception as e:
                print(f"❌ Failed to move {file_path.name}: {e}")
    
    if organized == 0:
        print("✅ No media files found to organize")
    else:
        print(f"✅ Organized {organized} files")

if __name__ == '__main__':
    print("🗂️  Media Organizer - Sorting by resolution/duration...")
    organize_media()
