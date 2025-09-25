from pytube import YouTube
from moviepy.editor import AudioFileClip
import os

def download_youtube_as_mp3(url):
    try:
        yt = YouTube(url)
        print(f"Downloading: {yt.title}")
        
        # Download audio stream only
        stream = yt.streams.filter(only_audio=True).first()
        downloaded_file = stream.download()
        
        # Convert to MP3
        mp3_file = os.path.splitext(downloaded_file)[0] + ".mp3"
        audio = AudioFileClip(downloaded_file)
        audio.write_audiofile(mp3_file, logger=None)
        audio.close()
        
        # Clean up the original file
        os.remove(downloaded_file)
        print(f"Saved as: {mp3_file}")
        
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    video_url = input("Enter YouTube video URL: ")
    download_youtube_as_mp3(video_url)
