from src.instascrapper import scrape_Instagram
from src.youtubescrapper import get_video_details
from src.webpagescrapper import scrape_webpage
import asyncio
from src.kgraph import KnowledgeGraphSystem
import os

# step1: scrape Instagram profile and save posts and reels to JSON
# scrape_Instagram("https://www.instagram.com/sarposhfoods/", "SarposhFoods")

# # step2: get video details from YouTube and save to JSON
# get_video_details(['WG1OONWUpMk', 'tX0L22-0xZk'], "SarposhFoods", "videos.json")

# # step3: scrape the main webpage and save markdown content
# asyncio.run(scrape_webpage("https://sarposhfoods.com", "SarposhFoods"))



"""
docker run -d \
  -p 8080:8080 \
  -v weaviate_text_data:/var/lib/weaviate \
  -e PERSISTENCE_DATA_PATH="/var/lib/weaviate" \
  -e MAX_VECTOR_DIMENSIONS=768 \
  --name weaviate-text \
  cr.weaviate.io/semitechnologies/weaviate:1.24.2

# For image vectors (1024 dimensions)
docker run -d \
  -p 8081:8080 \
  -v weaviate_image_data:/var/lib/weaviate \
  -e PERSISTENCE_DATA_PATH="/var/lib/weaviate" \
  -e MAX_VECTOR_DIMENSIONS=1024 \
  --name weaviate-image \
  cr.weaviate.io/semitechnologies/weaviate:1.24.2

"""

# file_paths = [
#     "/app/User/instagram.json",
#     "/app/User/videos.json",
#     "/app/User/crawl_output.txt",
#     "/app/User/2307.09288.pdf",
#     "/app/User/1687-6180-2014-45.pdf"
# ]

kg_system = KnowledgeGraphSystem()


from typing import List, Dict
from urllib.parse import urlparse

def segregate_urls(urls: List[str]) -> Dict[str, List[str]]:
    """
    Segregate a list of URLs into generic websites, YouTube links, and Instagram links.
    
    Args:
        urls: List of URL strings.
    
    Returns:
        A dict with keys:
          - "websites": List of URLs not matching YouTube or Instagram.
          - "youtube":  List of URLs whose domain contains youtube.com or youtu.be.
          - "instagram":List of URLs whose domain contains instagram.com.
    """
    websites: List[str] = []
    youtube:   List[str] = []
    instagram: List[str] = []

    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "youtube.com" in domain or "youtu.be" in domain:
            youtube.append(url)
        elif "instagram.com" in domain:
            instagram.append(url)
        else:
            websites.append(url)

    return {
        "websites":  websites,
        "youtube":   youtube,
        "instagram": instagram
    }

from typing import List
from urllib.parse import urlparse, parse_qs

def extract_youtube_ids(urls: List[str]) -> List[str]:
    """
    Given a list of YouTube URLs, return a list of their video IDs.

    Supports URLs like:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://youtube.com/v/VIDEO_ID

    Args:
        urls: List of YouTube URL strings.

    Returns:
        List of video ID strings (skips any URLs it can’t parse).
    """
    ids: List[str] = []
    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path

        # 1) Standard watch?v=VIDEO_ID
        if "youtube.com" in domain and parsed.query:
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            if vid:
                ids.append(vid)
                continue

        # 2) Short youtu.be/VIDEO_ID
        if "youtu.be" in domain:
            vid = path.lstrip("/")
            if vid:
                ids.append(vid)
                continue

        # 3) Embedded or /v/ URLs
        #    e.g. /embed/VIDEO_ID or /v/VIDEO_ID
        segments = path.split("/")
        if len(segments) >= 3 and segments[1] in {"embed", "v"}:
            vid = segments[2]
            if vid:
                ids.append(vid)
                continue

        # Could not parse, skip
    return ids



# file_paths = [
#     "/app/User/instagram.json",
#     "/app/User/videos.json",
#     "/app/User/crawl_output.txt",
#     "/app/User/2307.09288.pdf",
#     "/app/User/1687-6180-2014-45.pdf"
# ]

def get_txt_pdf_files(directory: str = "/app/User") -> List[str]:
    """
    Recursively scan the directory and return paths to all .txt and .pdf files.
    
    Args:
        directory (str): Path to the root directory to search.
        
    Returns:
        List[str]: List of full file paths ending with .txt or .pdf
    """
    print("*******************Getting TXT/PDF Files********************")
    txt_pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.txt', '.pdf')):
                full_path = os.path.join(root, file)
                txt_pdf_files.append(full_path)
    print("Fetched pdfs/text files:", txt_pdf_files)
    return txt_pdf_files

async def initialize_kg(urls):
    file_paths = []
    kg_system = KnowledgeGraphSystem()
    buckets = segregate_urls(urls)
    indx = 1
    inst = False
    ytb = False
    file_paths = file_paths + get_txt_pdf_files("/app/User")
    for web in buckets["websites"]:
      await scrape_webpage(web, "/app/User", f"crawl_output_{indx}.txt")
      file_paths.append("/app/User/crawl_output_{indx}.txt")
    if buckets["youtube"]:
      video_ids = extract_youtube_ids(urls)
      get_video_details(video_ids, "/app/User", "videos.json")
    for inst in buckets["instagram"]:
      scrape_Instagram(inst, "/app/User")
    if inst:
      file_paths.append("/app/User/instagram.json")
    if ytb:
      file_paths.append("/app/User/videos.json")

    print("Initializing the knowledgeGraph...")
    if kg_system.initialize(file_paths):
        return {"status": "already_initialized"}
    else:
        return {"status": "not_initialized", "message": "System initialized with hardcoded paths on startup"}

def query_kg(query):
    response = kg_system.query(query)
    return response


# docker compose up --build
# docker compose up -d --build
# curl -N "http://localhost:8000/stream?query=hello&bot=agni&top_k=5&session_id=test123"
#wget http://localhost:8000/initialize   ########NOTE THIS TO BE RUN BEFORE KG 
#wget http://localhost:8000/whatsapp/start
#ssh -i ~/.ssh/clost_infra clostinfra@34.123.179.207
#curl -i -H "Accept: application/json" http://localhost:8000/whatsapp/start #####Whatsapp start

#docker image prune --all -f
#sudo docker rm -f $(sudo docker ps -aq)
# sudo docker ps -a
###CORRECT ONE= sudo docker compose down --rmi all --volumes --remove-orphans
# curl -X POST http://localhost:8000/initialize      -H "Content-Type: application/json"      -d '{
#            "urls": [
#              "https://www.instagram.com/sarposhfoods",
#              "https://sarposhfoods.com"]
#          }'


#### MCP SERVER ############################
# export EXCEL_FILES_PATH=/home/drovco/SentinelKG/SarposhFoods
# export FASTMCP_PORT=3000  # Optional, defaults to 8000
# uv run excel-mcp-server sse
#http://drovco.eastus2.cloudapp.azure.com:8080/
#NEW CMD = python -m excel_mcp_server.src.excel_mcp sse
