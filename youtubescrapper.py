
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
