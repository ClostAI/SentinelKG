import os
import json
from apify_client import ApifyClient
import traceback
from dotenv import load_dotenv
from src.utils import extract_instagram_username, video_downloader,image_downloader
# from apollo.runner import run_apollo_video_qa
load_dotenv()

def scrape_Instagram(url, category):
    name = extract_instagram_username(url)
    APIFY_TOKEN = os.getenv("APIFY_TOKEN")
    client = ApifyClient(APIFY_TOKEN)

    # use the full input schema so we can get every post
    run_input = {
        "usernames": [name],
        "resultsType": "posts,reels",   # or "reels", or "posts, reels"
        "resultsLimit": 2000         # 0 == crawl until exhaustion
    }
    run = client.actor("dSCLg0C3YEZ83HzYX").call(run_input=run_input)

    # collect all items from the dataset
    items = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        items.append(item)

    # save to file as before
    output_path = os.path.join(os.getcwd(), category, f"instagram.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(items)} items to {output_path}")


# def fetch_content(json_path, save_dir):
#     with open(json_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)

#     for profile in data:
#         if "latestIgtvVideos" in profile:
#             for item in profile["latestIgtvVideos"]:
#                 content_type = item.get("type")
#                 url = item.get("url")
#                 if url:
#                     if content_type == "Video":
#                         video_downloader(url, save_dir)
#                     elif content_type == "Image":
#                         image_downloader(url, save_dir)

# fetch_content('/home/drovco/detection/restaurant/sarposhfoods/sarposhfoods.json', '/home/drovco/detection/restaurant/sarposhfoods/tmp')
# def process_all_videos(video_dir):
#     for filename in os.listdir(video_dir):
#         if not filename.endswith('.mp4'):
#             continue

#         video_path = os.path.join(video_dir, filename)
#         print(f"Processing: {video_path}")

#         try:
#             answer = run_apollo_video_qa(video_path, "Summarise this video?")
#         except Exception as e:
#             print(f"Error processing {filename}: {e}")
#             traceback.print_exc()   # optional: prints full stack trace
#             continue
#         print(f"Answer for {filename}: {answer}\n")

# process_all_videos('/home/drovco/detection/restaurant/sarposhfoods/tmp')
