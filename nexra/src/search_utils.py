import json
import os
import re
import praw
import aiofiles
import logging
import asyncio
from bs4 import BeautifulSoup
import nest_asyncio
from langchain_core.messages import HumanMessage 
import networkx as nx
from pyvis.network import Network
from dotenv import load_dotenv
import yaml
from google.generativeai import GenerativeModel
import google.generativeai as genai
from crawl4ai import AsyncWebCrawler
from crawl4ai import AsyncWebCrawler,CrawlerRunConfig
from nexra.src.utils import extract_video_id, fetch_video_details, fetch_transcript
#from nexra.src.db_utils import store_db_utils, find_record
from nexra.src.places_utils import get_place_details
from sentence_transformers import SentenceTransformer, util
from playwright.async_api import async_playwright
from readability import Document
logging.basicConfig( level=logging.ERROR)
logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
SEARCH_ENGINE_ID= os.getenv("SEARCH_ENGINE_ID")
os.environ["TOKENIZERS_PARALLELISM"] = "true"
API_KEY=os.getenv("API_KEY")




def filter_summary_embeddings(text, query, threshold=0.35):
    """
    Splits the input text into sentences and filters sentences based on 
    their semantic similarity to the query using sentence embeddings.

    Parameters:
      text (str): The full text summary.
      query (str): The query to measure relevance.
      threshold (float): The minimum cosine similarity score to consider a sentence relevant.
    
    Returns:
      str: A filtered summary containing only the sentences that pass the similarity threshold.
    """
    # Split the text into sentences using a regular expression.
    text = str(text)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    # Load the pre-trained sentence transformer model.
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Generate the embedding for the query.
    query_embedding = model.encode(query, convert_to_tensor=True)

    # Generate embeddings for each sentence.
    sentence_embeddings = model.encode(sentences, convert_to_tensor=True)

    # Compute cosine similarity scores between the query and each sentence.
    cosine_scores = util.cos_sim(query_embedding, sentence_embeddings)[0]

    # Filter out sentences with a similarity score above the threshold.
    relevant_sentences = [
        sentence 
        for sentence, score in zip(sentences, cosine_scores) 
        if float(score) >= threshold
    ]
    # Return the joined relevant sentences.
    return " ".join(relevant_sentences)




async def get_rendered_html(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        html = await page.content()
        await browser.close()
        return html

def extract_main_content(html):
    doc = Document(html)
    main_content = doc.summary()
    title = doc.title()
    return main_content, title

def heuristic_filter(html):
    soup = BeautifulSoup(html, 'lxml')
    
    # Remove non-content tags (e.g., ads, scripts)
    for tag in soup(['script', 'style', 'nav', 'footer', 'aside']):
        tag.decompose()

    # Score elements by text/link density
    elements = soup.find_all(['p', 'div', 'article', 'section'])
    scored = []
    for el in elements:
        text = el.get_text(strip=True)
        links = len(el.find_all('a'))
        words = len(text.split())
        score = words - (links * 10)  # Penalize elements with many links
        if words > 50 and score > 20:  # Adjust thresholds as needed
            scored.append(el)
    
    return ' '.join([str(el) for el in scored])

def html_to_clean_text(html):
    soup = BeautifulSoup(html, 'lxml')
    # Remove remaining inline styles/attributes
    for tag in soup.find_all(True):
        tag.attrs = {}
    # Convert to Markdown-like structure
    text = "\n\n".join([p.get_text().strip() for p in soup.find_all(['p', 'h1', 'h2', 'h3'])])
    return text


import requests
from readability import Document
from bs4 import BeautifulSoup

async def extract_content_readability(url):
    response = requests.get(url)
    doc = Document(response.text)
    content_html = doc.summary()  # contains the main article as HTML
    soup = BeautifulSoup(content_html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    return text

async def intelligent_scraper(url):
    # Step 1: Get rendered HTML
    html = await get_rendered_html(url)
    
    # Step 2: Initial content extraction
    main_content, title = extract_main_content(html)
    
    # Step 3: Heuristic refinement
    filtered_content = heuristic_filter(main_content)
    
    # Step 4: Final cleaning
    clean_text = html_to_clean_text(filtered_content)
    if clean_text == "":
        clean_text = await extract_content_readability(url)

    return {
        "title": title,
        "content": clean_text
    }


async def process_link(url: str):
    crawl_config = CrawlerRunConfig(wait_until="networkidle")
    # Process the URL using an asynchronous crawler.
    try:
        async with AsyncWebCrawler() as crawler:
            try:
                result = await crawler.arun(url=url, config=crawl_config)
            except Exception as e:
                logger.error("Error during crawler.arun (first attempt) for URL %s: %s", url, e)
                return None
            html_content = getattr(result, 'html', None)
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                paragraphs = soup.find_all('p')
                paragraphs_html = ''.join(str(p) for p in paragraphs)
                return {
                     "summary": paragraphs_html.strip(),
                 }
            else:
                logger.error("No HTML content returned for URL %s", url)
                return None
    except Exception as e:
        logger.error("Error processing link %s: %s", url, e)
        return None


async def process_instagram_link(insta_url:str):
    crawl_config = CrawlerRunConfig(wait_until="networkidle")
    async with AsyncWebCrawler() as crawler:
        try:
            result = await crawler.arun(url=insta_url, config=crawl_config)
        except Exception as e:
            # Optional: wait and retry once if necessary
            await asyncio.sleep(2)
            result = await crawler.arun(url=insta_url, config=crawl_config)
       # await asyncio.sleep(2)
        meta = result.metadata or {}
        if meta is None:
            return None
        title = meta.get("og:title") or meta.get("title", "")
        # Prefer og:description if available, otherwise use description
        description = meta.get("og:description") or meta.get("description", "")
        account = meta.get("twitter:creator") or meta.get("author") or meta.get("og:site_name", "")
        if title and description and account:
            return {
                "title": title.strip(),
                "summary": description.strip(),
                "account": account.strip()
            }  
        else:
            return None

async def process_youtube_link(url):
    video_id = extract_video_id(url)
    if video_id:
        details = fetch_video_details(video_id)
        if details:
            transcript = fetch_transcript(video_id)
        else:
            return None
    else:
        return None
    return {
                "details": details,
                "transcript": transcript
            }
def extract_reddit_comments(url):
    """
    Extracts comments from a Reddit post given its URL.
    Returns a list of dictionaries containing comment author, text, and score.
    """
    try:
        reddit = praw.Reddit(
            client_id=APP_ID,
            client_secret=APP_SECRET,
            user_agent="REDDIT_AGENT"
        )
    except Exception as e:
        logger.error("Error initializing Reddit instance: %s", e)
        reddit = None
    try:
        if not reddit:
            raise RuntimeError("Reddit instance not initialized properly.")
        if not url or not isinstance(url, str):
            raise ValueError("A valid URL must be provided.")
        post_id = url.split("/comments/")[-1].split("/")[0]
        if not post_id:
            raise ValueError("Unable to extract post ID from URL.")

        submission = reddit.submission(id=post_id)
        comments = []
        submission.comments.replace_more(limit=0)

        for comment in submission.comments.list():
            comments.append({
                "author": comment.author.name if comment.author else "Deleted",
                "text": comment.body,
                "score": comment.score
            })

        return comments
    except Exception as e:
        logger.error("Error extracting reddit comments: %s", e)
        return []



def run(url):
    """
    Runs the extraction process for a given Reddit post URL.
    Returns the list of extracted comments.
    """
    try:
        comments = extract_reddit_comments(url)
        return comments
    except Exception as e:
        logger.error("Error running comment extraction: %s", e)
        return []

async def process_result(result):
        try:
            if "url" in result or "link" in result:
                link = result.get("url", result.get("link", "")).lower()
                content_summary = {}
                if "instagram.com" in link:
                    content_summary = await process_instagram_link(link)
                elif "youtube.com" in link:
                    content_summary = await process_youtube_link(link)
                elif "reddit.com" in link:
                    try:
                        content_summary = run(link)
                    except Exception as e:
                        logger.error("Error processing reddit link (%s): %s", link, e)
                        content_summary = {}
                elif not ("zomato.com" in link or "swiggy.com" in link):
                    content_summary =  await intelligent_scraper(link)   #await process_link(link)
                else:
                    return
                # summary = filter_summary_embeddings(content_summary,category, threshold=0.35)
                # result["content_summary"] = summary
                # async with aiofiles.open('tmp.txt', mode='a', encoding='utf-8') as f:
                #     await f.write(summary)

                # summary = filter_summary_embeddings(content_summary,  threshold=0.35)
                result = {
                    "document": {
                        "url": link,
                        "summary": content_summary
                    }
                }
                json_result = json.dumps(result, indent=2)
                async with aiofiles.open('tmp.txt', mode='a', encoding='utf-8') as f:
                    await f.write(json_result + '\n')
                                
        except Exception as e:
            logger.error("Error processing result for URL %s: %s", result.get("url", "N/A"), e)

async def fetch_content_tool(query,  top_k, location):
    file_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_reponse.json')
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Error reading JSON file (%s): %s", file_path, e)
        return None
    results = data.get("results", [])
    top_k_results = [r for r in results if ("url" in r or "link" in r)][:top_k]
    remainder_results = [r for r in results if ("url" in r or "link" in r)][top_k:]
    try:
        tasks = [asyncio.create_task(process_result(result)) for result in top_k_results]
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error("Error processing results concurrently: %s", e)
    data["results"] = top_k_results + remainder_results
    output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/search_reponse_updated.json')
    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error("Error writing updated JSON to file (%s): %s", output_path, e)
    #return data
    txt_path = os.path.join(os.getcwd(), "tmp.txt")
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        raise RuntimeError(f"Could not read {txt_path}: {e}")
    prompt_yaml_path = os.path.join(os.getcwd(), 'nexra/src/configs/prompts.yaml')
    try:
        with open(prompt_yaml_path, 'r') as file:
            prompt_yaml = yaml.safe_load(file)
        prompt_template = prompt_yaml.get("summarisation_prompt")
        if not prompt_template:
            raise ValueError("Key 'summarisation_prompt' not found in prompts.yaml")
    except Exception as e:
        logger.error("Error loading prompt from YAML file (%s): %s", prompt_yaml_path, e)
        return None
    try:
        formatted_prompt = prompt_template.format(text=text, query=query)
    except Exception as e:
        logger.error("Error formatting prompt: %s", e)
        return None
    
    # client = genai.Client(api_key=GEMINI_API_KEY)
    # response = client.models.generate_content(
    #             model="gemini-2.0-flash", 
    #             contents=formatted_prompt)
    # return response.text
    model = GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(formatted_prompt)
    return response.text

   
    # if isinstance(json_string, list):
    #     json_string = json_string[0]
    # else:
    #     json_string = json_string

    # # Match the block inside ```json ... ```
    # match = re.search(r'```json\s*(\{.*?\})\s*```', json_string, re.DOTALL)
    # if not match:
    #     raise ValueError("No JSON block found.")

    # json_data = json.loads(match.group(1))
    # if os.path.exists(txt_path):
    #     os.remove(txt_path)
    # else:
    #     print("Error deleating file tmp.txt: File does not exist.")
    # if location != "NA":
    #     json_data = get_place_details(json_data, query, location)  
    #store_db_utils(json_data)      ###store the data in wevaite database
    # extractions = json_data["extractions"]
    # G = nx.DiGraph()
    # for item in extractions:
    #     entity = item["entity"]
    #     relationship = item["relationship"]
    #     attributes = item.get("attributes", {})

    #     # Add entity node with highlighting (e.g., a yellow fill)
    #     G.add_node(entity, title=entity, color="lightgreen", style="filled")
        
    #     # Only add attribute edges if the attributes dictionary is non-empty
    #     if attributes:
    #         for attr, value in attributes.items():
    #             attr_node = f"{attr}: {value}"
    #             G.add_node(attr_node, title=attr_node, color="red")
    #             G.add_edge(entity, attr_node, label=relationship, color="lightgray")

    # # Step 5: Visualize using Pyvis
    # net = Network(height="800px", width="100%", notebook=True, directed=True)
    # net.from_nx(G)
    # net.show("graph.html")
    # return json_data
   
def content_tool(query: str,  top_k:int, location:str):
    """
    Tool to crawl links and generate summary relevant to query
    """
    nest_asyncio.apply()
    return asyncio.run(fetch_content_tool(query, top_k, location))