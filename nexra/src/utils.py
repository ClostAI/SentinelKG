import os
import re
import urllib.parse
import yaml
import time
import asyncio
import urllib
import logging
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from crawl4ai import AsyncWebCrawler,CrawlerRunConfig
load_dotenv()
logging.basicConfig( level=logging.ERROR)
logger = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def is_valid_social_link(url: str) -> bool:
    return "instagram.com" in url or "youtube.com" in url

def is_instagram_reel(url: str) -> bool:
    return "instagram.com" in url and "/reel/" in url
async def crawl_single_url(crawler, url: str):
    result = await crawler.arun(url)
    if not result.success:
        print(f"❌ Failed: {url}")
        return None

    if not result:
        print(f"⚠️ No results returned for {url}")
        return None

    html = result.html or ""
    meta = result.metadata or {}

    return {
        "href": url,
        "title": meta.get("title") or "",
        "summary": meta.get("description") or ""
    }


async def crawl_google_and_reels(search_url: str, query: str):
    async with AsyncWebCrawler() as crawler:
        print(f"🌐 Crawling Google search page: {search_url}")
        initial_links = await crawl_single_url(crawler, search_url)
        if not initial_links:
            return {"query": query, "number_of_results": 0, "results": []}

        # Get links from first level (Google search)
        result = await crawler.arun(search_url)
        links = result.links.get("internal", []) + result.links.get("external", [])
        filtered_links = [link.get("href") for link in links if is_valid_social_link(link.get("href", ""))]

        # Filter only Instagram reels (can expand for YouTube later)
        reel_links = [url for url in filtered_links if is_instagram_reel(url)]

        print(f"🎯 Found {len(reel_links)} Instagram Reels to crawl")

        # Crawl all Reels concurrently
        tasks = [crawl_single_url(crawler, url) for url in reel_links]
        crawled_reels = await asyncio.gather(*tasks)

        # Filter out any failed crawls
        valid_reels = [r for r in crawled_reels if r]

        return {
            "query": query,
            "number_of_results": len(valid_reels),
            "results": valid_reels
        }


def search_youtube_videos(query,max_results):
    # Initialize YouTube API
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(
            q=query,
            part='id,snippet',
            type='video',
            maxResults=max_results
        )
    response = request.execute()
    return response['items']

def get_video_statistics(video_id):
    request = youtube.videos().list(
        part='statistics',
        id=video_id
    )
    response = request.execute()
    stats = response['items'][0]['statistics']
    return stats.get('viewCount', '0')

def get_transcript_summary(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript)
        # Basic summary: return first 2-3 lines
        return ' '.join(text.split('\n')) + '...'
    except:
        return 'Transcript not available.'

def fetch_youtube_data(query, max_results=10):
    videos = search_youtube_videos(query, max_results)
    results = []

    for video in videos:
        video_id = video['id']['videoId']
        title = video['snippet']['title']
        views = get_video_statistics(video_id)
        summary = get_transcript_summary(video_id)

        results.append({
            'video_id': video_id,
            'title': title,
            'views': views,
            'transcript_summary': summary
        })
        time.sleep(1)  

    return results


def extract_video_id(video_url):
    """Extracts video ID from various YouTube URL formats (shorts, regular videos, embed)."""
    try:
        if not video_url or not isinstance(video_url, str):
            raise ValueError("Invalid video_url provided.")
        match = re.search(r"(?:v=|\/shorts\/|\/embed\/|\/watch\?v=)([\w-]+)", video_url)
        if match:
            return match.group(1)
        else:
            raise ValueError("No valid video ID found in the provided URL.")
    except Exception as e:
        logger.error("Error extracting video ID: %s", e)
        return None

def fetch_video_details(video_id):
    """Fetches title, description, channel name, and views of the YouTube video."""
    try:
        if not video_id:
            raise ValueError("Invalid video_id provided.")
        request = youtube.videos().list(part="snippet,statistics", id=video_id)
        response = request.execute()
        if "items" in response and response["items"]:
            snippet = response["items"][0]["snippet"]
            return {
                "title": snippet["title"],
                "description": snippet["description"],
                "channel": snippet["channelTitle"],
                "views": response["items"][0]["statistics"].get("viewCount", "N/A")
            }
        else:
            raise ValueError("No video details found for the provided video_id.")
    except Exception as e:
        logger.error("Error fetching video details: %s", e)
        return None

def fetch_transcript(video_id):
    """Fetches transcript of the video, if available."""
    try:
        if not video_id:
            raise ValueError("Invalid video_id provided.")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        logger.error("Error fetching transcript: %s", e)
        return "Transcript unavailable (e.g., auto-generated, disabled, or private video)."

def model_loader():
    try:
        file_path = os.path.join(os.getcwd(), 'nexra/src/configs/params.yaml')
        with open(file_path, 'r') as file:
            param = yaml.safe_load(file)
        model_name = param["model"]["name"]
        temperature = param["model"]["temperature"]
        return LLM(model=model_name, temperature=temperature)
    
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {file_path}.")
    except yaml.YAMLError as e:
        logger.error("Error parsing YAML file: %s", e)
    except KeyError as e:
        logger.error("Missing configuration key: %s", e)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
    return None

def parse_instagram_metadata(description: str) -> dict:
    """
    Parses the metadata description from an Instagram post to extract:
      - likes (as a string, e.g. "2,865")
      - comments (as a string, e.g. "83")
      - username (e.g. "slurp_till_u_burp")
      - date (e.g. "July 12, 2024")
      - post content (the text within quotes)
    
    Expected format:
      "<likes> likes, <comments> comments - <username> on <date>: "<post content>""
    
    Returns a dictionary with keys: likes, comments, username, date, content.
    """
    try:
        if not isinstance(description, str) or not description.strip():
            logger.error("Invalid or empty description provided.")
            return {}
        
        # Regex may need adjustment based on variations in the metadata format.
        pattern = r"([\d,]+)\s+likes,\s+([\d,]+)\s+comments\s*-\s*(\S+)\s+on\s+([^:]+):\s*\"(.*)\""
        match = re.search(pattern, description)
        if match:
            return {
                "likes": match.group(1),
                "comments": match.group(2),
                "username": match.group(3),
                "date": match.group(4).strip(),
                "content": match.group(5).strip(),
            }
        else:
            logger.error("Regex did not match the provided description: %s", description)
            return {}
    except Exception as e:
        logger.error("Exception occurred while parsing Instagram metadata: %s", e)
        return {}

async def extract_instagram_links(url: str) -> list:
    """
    Crawls the Google search results page and extracts all Instagram links.
    """
    instagram_links = []
    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            try:
                result = await crawler.arun(url=url, bypass_cache=True)
            except Exception as e:
                logger.error("Error during crawler.arun for URL %s: %s", url, e)
                return []
            
            if result and hasattr(result, 'cleaned_html') and result.cleaned_html:
                try:
                    soup = BeautifulSoup(result.cleaned_html, "html.parser")
                    href_links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
                    pattern = re.compile(r"https?://(www\.)?instagram\.com/.*")
                    instagram_links = [link for link in href_links if pattern.search(link)]
                except Exception as e:
                    logger.error("Error parsing HTML for URL %s: %s", url, e)
            else:
                logger.error("No cleaned HTML content available for extracting links for URL %s", url)
    except Exception as e:
        logger.error("Exception occurred in extract_instagram_links for URL %s: %s", url, e)
    
    return instagram_links

async def extract_youtube_links(url: str) -> list:
    """
    Crawls the Google search results page and extracts all Youtube links.
    """
    youtube_links = []
    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            try:
                result = await crawler.arun(url=url, bypass_cache=True)
            except Exception as e:
                logger.error("Error during crawler.arun for Youtube links: %s", e)
                return []
            if result and hasattr(result, 'cleaned_html') and result.cleaned_html:
                try:
                    soup = BeautifulSoup(result.cleaned_html, "html.parser")
                    href_links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
                    pattern = re.compile(r"https?://(www\.)?youtube\.com/.*")
                    youtube_links = [link for link in href_links if pattern.search(link)]
                except Exception as e:
                    logger.error("Error parsing HTML for Youtube links: %s", e)
            else:
                logger.error("No cleaned HTML content available for extracting Youtube links.")
    except Exception as e:
        logger.error("Exception in extract_youtube_links: %s", e)
    return youtube_links


def generate_search_urls(cafe_name, address):
    """
    Generate URLs for a Google search and a Google short videos search for a cafe based on its name, address, and additional keywords.
    
    Parameters:
      - cafe_name: The name of the cafe.
      - address: The full address of the cafe.
      - keywords: Additional keywords to include in the search query.
    
    Returns:
      - A tuple containing:
          1. Google search URL (general search results)
          2. Google short videos URL (video search filtered for short videos)
    """
    try:
        query = f"{cafe_name} {address}"
        encoded_query = urllib.parse.quote_plus(query)
        google_search_url = f"https://www.google.com/search?q={encoded_query}"
        google_short_videos_url = f"https://www.google.com/search?q={encoded_query}&tbm=vid&tbs=dur:1"
        return google_search_url, google_short_videos_url
    except Exception as e:
        logger.error("Error generating search URLs: %s", e)
        return None, None


async def fetch_social_links(url, cafe_name):
    """
    Uses AsyncWebCrawler to fetch social links for the provided URL and cafe name.
    Returns a dictionary containing lists of links for various platforms.
    """
    try:
        # Create a CrawlerRunConfig that waits until network is idle.
        crawl_config = CrawlerRunConfig(wait_until="networkidle")
        async with AsyncWebCrawler() as crawler:
            try:
                result = await crawler.arun(url=url, config=crawl_config)
            except Exception as e:
                logger.error("Initial extraction error for %s: %s", cafe_name, e)
                # Fallback configuration
                crawl_config = CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=120000)
                result = await crawler.arun(url=url, config=crawl_config)
            
            try:
                soup = BeautifulSoup(result.html, 'html.parser')
                all_links = [a['href'] for a in soup.find_all('a', href=True)]
            except Exception as e:
                logger.error("Error parsing HTML for %s: %s", cafe_name, e)
                return {}
            
            return {
                "Zomato": [link for link in all_links if 'zomato' in link.lower()],
                "Swiggy": [link for link in all_links if 'swiggy.com' in link.lower()],
                "Instagram": [link for link in all_links if 'instagram.com' in link.lower()],
                "YouTube": [link for link in all_links if 'youtube.com' in link.lower()],
            }
    except Exception as e:
        logger.error("Error in fetch_social_links for %s: %s", cafe_name, e)
        return {}

def classify_zomato_url(url: str) -> str:
    """
    Classify a Zomato URL into one of these categories:
      - "main": The homepage URL for a restaurant.
      - "book": A URL used for booking/reservation.
      - "menu": A URL pointing to the restaurant's menu.
      - "other": Any other URL (e.g. translated or share links).
    """
    try:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("Invalid URL provided.")
        
        # URLs starting with link.zomato.com are usually share links.
        if re.search(r"^https:\/\/link\.zomato\.com", url):
            return "other"
        
        # Look for /book in the path.
        if re.search(r"/book\b", url):
            return "book"
        
        # Look for /menu in the path.
        if re.search(r"/menu\b", url):
            return "menu"
        
        # A "main" Zomato URL typically looks like: https://www.zomato.com/<city>/<restaurant>
        main_pattern = r"^https:\/\/www\.zomato\.com\/[a-zA-Z0-9\-]+\/[a-zA-Z0-9\-]+\/?$"
        if re.match(main_pattern, url):
            return "main"
        
        # Also, sometimes a main URL may appear with a language code, e.g. /vi/
        alt_main_pattern = r"^https:\/\/www\.zomato\.com\/[a-z]{2}\/[a-zA-Z0-9\-]+\/[a-zA-Z0-9\-]+\/?$"
        if re.match(alt_main_pattern, url):
            return "main"
        
        return "other"
    except Exception as e:
        logger.error("Error classifying Zomato URL '%s': %s", url, e)
        return "other"


def classify_swiggy_url(url: str) -> str:
    """
    Classify a Swiggy URL into one of these categories:
      - "main": The primary restaurant page.
      - "dineout": A URL directing to dineout or similar experiences.
      - "book/place_order": URLs related to booking or placing orders.
      - "other": Any other URL.
    """
    try:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("Invalid URL provided.")
        
        # Check for dineout in the URL first.
        if re.search(r"/dineout\b", url):
            return "dineout"
        
        # Check for booking/order keywords in query parameters (e.g. utm_source).
        if re.search(r"utm_source=.*placeorder", url, re.IGNORECASE):
            return "book/place_order"
        
        # General check for booking/order keywords anywhere in the URL.
        if re.search(r"(book|placeorder)", url, re.IGNORECASE):
            return "book/place_order"
        
        # Check for a "main" URL pattern (typically under /restaurants/).
        main_pattern = r"^https:\/\/www\.swiggy\.com\/restaurants\/[a-zA-Z0-9\-\_]+\/[a-zA-Z0-9\-\_]+\/?$"
        if re.match(main_pattern, url):
            return "main"
        
        return "other"
    except Exception as e:
        logger.error("Error classifying Swiggy URL '%s': %s", url, e)
        return "other"