# With this module you can:
#     Get all videos from a Youtube channel.
#     Get all videos from a playlist.
#     Search youtube.

# import scrapetube
# videos = scrapetube.get_channel("UC9-y-6csu5WGm29I7JiwpnA") #channel ID

# for video in videos:
#     print(video['videoId'])

# import sys
# import logging
# from yt_dlp import YoutubeDL
# import whisper
# from youtube_transcript_api import (
#     YouTubeTranscriptApi,
#     NoTranscriptFound,
#     TranscriptsDisabled,
#     VideoUnavailable,
# )
# from googletrans import Translator

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# def transribe_audio(audio_path):
#     # 1. Load your chosen model
#     model = whisper.load_model("base")

#     # 2. First pass: just detect/transcribe
#     result = model.transcribe(
#         audio_path,
#         language=None,        # let it auto-detect
#         task="transcribe"     # default, explicit here
#     )

#     detected_lang = result["language"]
#     print(f"Detected language: {detected_lang}")

#     # 3. If not English, re-run in translate mode
#     if detected_lang != "en":
#         print("Non-English speech detected; translating to English…")
#         result = model.transcribe(
#             audio_path,
#             task="translate"   # auto-translates everything into English
#         )

#     # 4. Access the final English text
#     text = result["text"]
#     return text

# def download_audio(urls, output_path):
#     ydl_opts = {
#         'format': 'bestaudio/best',
#         'outtmpl': output_path,
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '192',
#         }],
#     }
#     with YoutubeDL(ydl_opts) as ydl:
#         ydl.download(urls)


# def fetch_or_translate_transcript(video_id: str) -> list:
#     """
#     Fetches an English transcript for the given YouTube video ID.
#     1. Attempt to fetch English transcript (manual or auto).
#     2. If that fails, fetch any generated transcript (e.g., Hindi auto-generated) and translate to English.
#     Returns:
#         List of {{'text': str, 'start': float, 'duration': float}}
#     Raises:
#         NoTranscriptFound: If no transcript is available.
#         VideoUnavailable: If the video is not accessible.
#     """
#     translator = Translator()

#     try:
#         logging.info(f"Fetching English transcript for video {video_id}")
#         # Try manual or auto-generated English
#         return YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])

#     except NoTranscriptFound:
#         logging.warning(f"No English transcript found; checking alternatives for {video_id}.")
#         try:
#             download_audio([f"https://www.youtube.com/watch?v={video_id}"], "output")
#             transribe_audio("output.mp3")

#         except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
#             logging.error(f"Transcript retrieval failed: {e}")
#             raise

#     except VideoUnavailable as e:
#         logging.error(f"Video unavailable: {e}")
#         raise

#     except Exception as e:
#         logging.error(f"Unexpected error for {video_id}: {e}", exc_info=True)
#         raise


# if __name__ == '__main__':
#     video_id =   "bfBvaIwkfeM" #"BPvMm0CF2fk"
#     try:
#         for snippet in fetch_or_translate_transcript(video_id):
#             print(f"[{snippet['start']:6.2f}s] {snippet['text']}")
#     except Exception as e:
#         logging.error(f"Failed to fetch transcript for {video_id}: {e}")
#         sys.exit(1)

from googleapiclient.discovery import build
import os
import json
from dotenv import load_dotenv


load_dotenv()
API_KEY = APIFY_TOKEN = os.getenv("YOUTUBE_API_KEY")  

def get_video_details(video_ids, output_dir, output_filename="videos.json"):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    youtube = build('youtube', 'v3', developerKey=API_KEY)
    request = youtube.videos().list(
        part='snippet,contentDetails,statistics',
        id=','.join(video_ids)
    )
    response = request.execute()

    videos = []
    for item in response.get('items', []):
        info = {
            'id': item['id'],
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'channelTitle': item['snippet']['channelTitle'],
            'publishedAt': item['snippet']['publishedAt'],
            'duration': item['contentDetails']['duration'],
            'viewCount': item['statistics'].get('viewCount'),
            'likeCount': item['statistics'].get('likeCount'),
            'commentCount': item['statistics'].get('commentCount'),
        }
        videos.append(info)

    # Save to JSON
    output_path = os.path.join(output_dir, output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f"Saved video details to {output_path}")
    return 
