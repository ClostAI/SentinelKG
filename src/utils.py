import os
import re
from yt_dlp import YoutubeDL
import requests


def extract_instagram_username(url):
    pattern = r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)"
    match = re.match(pattern, url)
    if match:
        return match.group(1)
    return None


def video_downloader(url, save_path):
    os.makedirs(save_path, exist_ok=True)
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(save_path, '%(uploader)s_%(id)s.%(ext)s'),
        'verbose': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def image_downloader(url, save_path):
    os.makedirs(save_path, exist_ok=True)
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filename = os.path.join(save_path, os.path.basename(url.split("?")[0]))
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded image: {filename}")
        else:
            print(f"Failed to download image: {url}")
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")