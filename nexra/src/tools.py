import requests
import googlemaps
import json 
import re
import os
import yaml
import asyncio
from urllib.parse import urlparse
from langchain_community.utilities import SearxSearchWrapper
import difflib
from googleapiclient.discovery import build
# from utils_agni import scrape_content_agni
from nexra.src.search_utils import content_tool
from nexra.src.utils import generate_search_urls,fetch_social_links,classify_zomato_url,classify_swiggy_url,extract_video_id,fetch_video_details,fetch_transcript,fetch_youtube_data,crawl_google_and_reels
from crawl4ai import AsyncWebCrawler
from crawl4ai import AsyncWebCrawler,CrawlerRunConfig
from dotenv import load_dotenv
import logging
import urllib
import nest_asyncio


logging.basicConfig( level=logging.ERROR)
logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

async def youtube_tool(query):
    loop = asyncio.get_running_loop()
    final_data = await loop.run_in_executor(None, fetch_youtube_data, query)
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/youtube_tool.json')
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    return final_data

async def instagram_tool(query):
    query = '+'.join(query.strip().split())
    query = f"site:youtube.com OR site:instagram.com intext:{query}"
    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://www.google.com/search?q={encoded_query}"
   #final_data = await crawl_google_and_reels(search_url, query)
    final_data = await crawl_google_and_reels(search_url, query)
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/instagram_tool.json')
    with open(file_path , "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    return final_data


async def extract_social_link():
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_response_places.json')
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Error reading JSON file (%s): %s", file_path, e)
        return None
    for place in data.get("response", []):
        try:
            name = place.get('name', 'Unknown')
            google_places = place.get("google_places")
            if google_places:
                address = google_places.get("formatted_address", "Address not available")
                params_path = os.path.join(os.getcwd(), 'nexra/src/configs/params.yaml')
                try:
                    with open(params_path, 'r') as file:
                        params = yaml.safe_load(file)
                except Exception as e:
                    logger.error("Error reading params YAML file (%s): %s", params_path, e)
                    continue
                try:
                    search_url, shorts_url = generate_search_urls(name, address)
                except Exception as e:
                    logger.error("Error generating search URLs for %s: %s", name, e)
                    continue
                try:
                    search_task = fetch_social_links(search_url, name)
                    shorts_task = fetch_social_links(shorts_url, name)
                    search_links, shorts_links = await asyncio.gather(search_task, shorts_task)
                except Exception as e:
                    logger.error("Error fetching social links for %s: %s", name, e)
                    continue
                try:
                    combined_links = {}
                    for platform in search_links.keys():
                        combined_list = list(set(search_links.get(platform, []) + shorts_links.get(platform, [])))
                        combined_links[platform] = combined_list
                    place["social_links"] = combined_links
                  #  print(place["social_links"])
                except Exception as e:
                    logger.error("Error combining social links for %s: %s", name, e)
            else:
               # print(f"{name}: No Google Places data available")
                continue

        except Exception as e:
            logger.error("Error processing place: %s", e)
            continue
    output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_response_socials.json')
    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error("Error writing JSON to file (%s): %s", output_path, e)

    return data


def socials_tool():
    """
        fetch social links of the places fetched by places api
    """
    nest_asyncio.apply()  
    return asyncio.run(extract_social_link())


async def extract_food_details():
    combined_data = {}

    # Load the original JSON data.
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_response_socials.json')
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Error reading JSON file (%s): %s", file_path, e)
        return None

    for place in data.get("response", []):
        name = name = place.get("name", "Unknown")
        try:
            social_link = place.get("social_links")
            zomato_links = None
            swiggy_links = None
            if social_link:
                zomato_links = social_link.get("Zomato")
                swiggy_links = social_link.get("Swiggy")
            
            if zomato_links or swiggy_links:
                # print("INFO: fetching Zomato and Swiggy website for the place:", name)
                summaries = []
                z_url_list = []
                s_url_list = []
                z_result = ""
                s_result = ""

                # Classify Zomato links.
                if zomato_links:
                    for link in zomato_links:
                        try:
                            if classify_zomato_url(link) == "main":
                                z_url_list.append(link)
                        except Exception as e:
                            logger.error("Error classifying Zomato link for %s: %s", name, e)
                            continue
                if swiggy_links:
                    for link in swiggy_links:
                        try:
                            classification = classify_swiggy_url(link)
                            # Check if classification is either "book/place_order" or "main"
                            if classification in ["book/place_order", "main"]:
                                s_url_list.append(link)
                        except Exception as e:
                            logger.error("Error classifying Swiggy link for %s: %s", name, e)
                            continue
                if z_url_list or s_url_list:
                    if z_url_list:
                        z_url = z_url_list[0]
                        crawl_config = CrawlerRunConfig(wait_until="networkidle")
                        async with AsyncWebCrawler() as crawler:
                            try:
                                result = await crawler.arun(url=z_url, config=crawl_config)
                            except Exception as e:
                                logger.error("Error crawling Zomato URL for %s (networkidle): %s", name, e)
                                try:
                                    crawl_config = CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=120000)
                                    result = await crawler.arun(url=z_url, config=crawl_config)
                                except Exception as e2:
                                    logger.error("Error crawling Zomato URL for %s (domcontentloaded): %s", name, e2)
                                    result = None
                            if result:
                                z_result = result.markdown
                    else:
                        z_url = ""

                    if s_url_list:
                        s_url = s_url_list[0]
                        crawl_config = CrawlerRunConfig(wait_until="networkidle")
                        async with AsyncWebCrawler() as crawler:
                            try:
                                result_s = await crawler.arun(url=s_url, config=crawl_config)
                            except Exception as e:
                                logger.error("Error crawling Swiggy URL for %s (networkidle): %s", name, e)
                                try:
                                    crawl_config = CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=120000)
                                    result_s = await crawler.arun(url=s_url, config=crawl_config)
                                except Exception as e2:
                                    logger.error("Error crawling Swiggy URL for %s (domcontentloaded): %s", name, e2)
                                    result_s = None
                            if result_s:
                                s_result = result_s.markdown
                    else:
                        s_url = ""

                    summaries.append({
                        "name": name,
                        "zomato": z_result if z_result else "",
                        "swiggy": s_result if s_result else "",
                        "z_url": z_url if z_url else "",
                        "s_url": s_url if s_url else "",
                    })
                    combined_data[name] = summaries
            else:
                #print("skipping the append for the place", name)
                combined_data[name] = []
                continue

        except Exception as e:
            logger.error("Error processing place entry: %s", e)
            continue

    prompt_yaml_path = os.path.join(os.getcwd(), 'nexra/src/configs/prompts.yaml')
    try:
        with open(prompt_yaml_path, 'r') as file:
            prompt_yaml = yaml.safe_load(file)
        prompt_template = prompt_yaml.get("extract_food_details_prompt")
        if not prompt_template:
            raise ValueError("Key 'extract_food_details_prompt' not found in prompts.yaml")
    except Exception as e:
        logger.error("Error loading prompt from %s: %s", prompt_yaml_path, e)
        return None

    # Format the prompt using the combined_data.
   # print(combined_data)
    try:
        prompt = prompt_template.format(combined_data=json.dumps(combined_data))
    except Exception as e:
        logger.error("Error formatting prompt: %s", e)
        return None
    try:
        llm = LLM(
            model='gemini/gemini-2.0-flash',
            api_key=GEMINI_API_KEY  # GEMINI_API_KEY should be defined elsewhere.
        )
        response = llm.call(prompt)
    except Exception as e:
        logger.error("Error during LLM call: %s", e)
        return None

    try:
        cleaned_response = re.sub(r"```json|\n```", "", response).strip()
        response_json = json.loads(cleaned_response)
    except Exception as e:
        logger.error("Error processing LLM response: %s", e)
        response_json = None
    output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/food.json')
    try:
        with open(output_path, "w") as f:
            json.dump(response_json, f, indent=4)
    except Exception as e:
        logger.error("Error writing output JSON to file (%s): %s", output_path, e)

    return response_json

def food_orders_tool():
    """
        fetch swiggy and zomato details by place name
    """
    nest_asyncio.apply() 
    return asyncio.run(extract_food_details())


# A mapping of priority patterns with lower numbers indicating higher priority.
PRIORITY_PATTERNS = {
    re.compile(r'(.*\.)?reddit\.com$'): 0,
    re.compile(r'(.*\.)?instagram\.com$'): 0,
    re.compile(r'(.*\.)?youtube\.com$'): 0,
    # For blogs, you might adjust the regex to suit your definition:
    re.compile(r'.*blog.*'): 1
}

# A default priority for results that don't match any special hostname.
DEFAULT_PRIORITY = 5

def get_priority(hostname: str) -> int:
    """Returns a priority score based on matched patterns.
       Lower score => higher priority.
    """
    for pattern, score in PRIORITY_PATTERNS.items():
        if pattern.search(hostname):
            return score
    return DEFAULT_PRIORITY

async def response_tool(query: str, top_k: int, location: str):
    #url = "http://localhost:8080"
    url = os.getenv("SEARXNG_URL")
    search = SearxSearchWrapper(searx_host=url)
    
    try:
        raw_results = search.results(
            query=query,
            num_results=100,
            categories=["videos", "general"],
            engines=["brave", "google", "youtube", "bing"],
            time_range="year"
        )
        allowed_engines = {"brave", "google", "youtube", "bing"}
        name_map = {"youtube": "YouTube"}

        clean_results = []
        for item in raw_results:
            r = item if isinstance(item, dict) else item.__dict__
            # Filter results by engine
            engines = [e.lower() for e in r.get("engines", [])]
            engines = [name_map.get(e, e) for e in engines if e in allowed_engines]
            if not engines:
                continue

            link = r.get("link", "")
            parsed = urlparse(link)
            hostname = parsed.hostname.lower() if parsed.hostname else ""
            
            result_entry = {
                "title":    r.get("title"),
                "snippet":  r.get("snippet"),
                "link":     link,
                "category": r.get("category"),
                "engines":  engines,
                "priority": get_priority(hostname)  # Attach priority score
            }
            clean_results.append(result_entry)

        # Sort the results based on the assigned priority (lower values come first)
        sorted_results = sorted(clean_results, key=lambda x: x.get("priority", DEFAULT_PRIORITY))
        
        data = {
            "query": query,
            "number_of_results": len(sorted_results),
            "results": sorted_results
        }
        
        output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_reponse.json')
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return content_tool(query, top_k, location)

    except Exception as e:
        logger.error("Error during requests.get: %s", e)
        return None


def places_tool(query: str, latitude: float, longitude: float, area: str, radius: int):
    """
    Tool to fetch details for each cafe and update the JSON data.
    """
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_response_summary.json')
    API_KEY = GOOGLE_API_KEY  # make sure this is defined
    
    # Load the original JSON data.
    try:
        with open(file_path, "r") as f:
            content = f.read()
            data = json.loads(content)  # Parse the JSON string into a dictionary
    except Exception as e:
        logger.error("Error reading or parsing JSON file (%s): %s", file_path, e)
        data = {"error": "Failed to load or parse summary JSON data."}
    
    # Initialize the Google Maps client.
    try:
        gmaps = googlemaps.Client(key=API_KEY)
    except Exception as e:
        logger.error("Error initializing Google Maps client: %s", e)
        return {"error": "Failed to initialize Google Maps client."}
    
    # Iterate over each cafe in the response.
    for cafe in data.get("response", {}).get("places", []):
        try:
            name = cafe.get('name')
            if not name:
                logger.error("Cafe entry missing name. Skipping entry.")
                continue

            # Use a space between the cafe name and area.
            input_text = f"{name} {area}"
            try:
                find_response = gmaps.find_place(
                    input=input_text,
                    input_type="textquery",
                    fields=["place_id"]
                )
            except Exception as e:
                logger.error("Error during find_place for %s: %s", name, e)
                continue

            if find_response.get('status') != "OK" or not find_response.get("candidates"):
                logger.error("No candidate found for %s (%s)", name, query)
                continue

            place_id = find_response["candidates"][0].get("place_id")
            try:
                details_response = gmaps.place(
                    place_id=place_id,
                    fields=[
                        "name",
                        "formatted_address",
                        "photo",
                        "opening_hours",
                        "price_level",
                        "rating",
                        "formatted_phone_number",
                        "geometry"
                    ]
                )
            except Exception as e:
                logger.error("Error during place details fetch for %s: %s", name, e)
                continue

            if details_response.get('status') != "OK":
                logger.error("Error fetching details for %s (%s): %s", name, query, details_response.get('status'))
                continue

            details = details_response.get("result", {})
            cutoff = 0.6

            # Check if the name in details roughly matches the cafe's name.
            if details.get("name") and difflib.SequenceMatcher(None, details.get("name").lower(), name.lower()).ratio() < cutoff:
                continue

            # Normalize opening hours if available.
            if "opening_hours" in details and "weekday_text" in details["opening_hours"]:
                details["opening_hours"] = details["opening_hours"]["weekday_text"]

            # Process photos.
            photos = details.get("photos", [])
            photo_urls = []
            for photo in photos:
                photo_ref = photo.get("photo_reference")
                if photo_ref:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={API_KEY}"
                    photo_urls.append(photo_url)
                else:
                    logger.error("Missing photo_reference in photo for %s", name)
            details["photo_urls"] = photo_urls
            details["photos"] = ""  # Clear original photos field if not needed.

            # Extract geometry information.
            geometry = details.get("geometry", {})
            if geometry:
                location = geometry.get("location", {})
                details["lat"] = location.get("lat")
                details["lon"] = location.get("lng")
            
            # Update the cafe's entry with the fetched details.
            cafe["google_places"] = details
        except Exception as e:
            logger.error("Error processing cafe %s: %s", cafe.get("name", "Unknown"), e)
            continue

    # Write the updated JSON to a new file.
    output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_response_places.json')
    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error("Error writing updated JSON to file (%s): %s", output_path, e)
        return {"error": "Failed to write updated data to file."}

    return data