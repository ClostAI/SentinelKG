from instascrapper import scrape_Instagram
from youtubescrapper import get_video_details
from webpagescrapper import scrape_webpage
import asyncio
from kgraph import create_kg


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

file_paths = [
    "/home/drovco/kg-data/clost_kg/SarposhFoods/instagram.json",
    "/home/drovco/kg-data/clost_kg/SarposhFoods/videos.json",
    "/home/drovco/kg-data/clost_kg/SarposhFoods/crawl_output.txt",
    "/home/drovco/kg-data/ColPali-demo/2307.09288.pdf"

]

print(create_kg(file_paths))
