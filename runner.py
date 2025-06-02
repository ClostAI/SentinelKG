from src.instascrapper import scrape_Instagram
from src.youtubescrapper import get_video_details
from src.webpagescrapper import scrape_webpage
import asyncio
from src.kgraph import KnowledgeGraphSystem


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
#     "/home/drovco/SentinelKG/SarposhFoods/instagram.json",
#     "/home/drovco/SentinelKG/SarposhFoods/videos.json",
#     "/home/drovco/SentinelKG/SarposhFoods/crawl_output.txt",
#     "/home/drovco/kg-data/ColPali-demo/2307.09288.pdf"

# ]

file_paths = [
    "/app/SarposhFoods/instagram.json",
    "/app/SarposhFoods/videos.json",
    "/app/SarposhFoods/crawl_output.txt",
    "/app/SarposhFoods/2307.09288.pdf",
    "/app/SarposhFoods/1687-6180-2014-45.pdf"
]

kg_system = KnowledgeGraphSystem()
def initialize_kg(filepaths):
    if kg_system.initialize(filepaths):
        return {"status": "already_initialized"}
    else:
        return {"status": "not_initialized", "message": "System initialized with hardcoded paths on startup"}

def query_kg(query):
    response = kg_system.query(query)
    return response


# docker compose up --build
# docker compose up -d --build
# curl -N "http://localhost:8000/stream?query=hello&bot=agni&top_k=5&session_id=test123"
#docker image prune --all -f
#sudo docker rm -f $(sudo docker ps -aq)
# sudo docker ps -a
###CORRECT ONE= sudo docker compose down --rmi all --volumes --remove-orphans



#### MCP SERVER ############################
# export EXCEL_FILES_PATH=/home/drovco/SentinelKG/SarposhFoods
# export FASTMCP_PORT=8000  # Optional, defaults to 8000
# uv run excel-mcp-server sse
