"""

# 1. Stop all containers
sudo docker stop $(sudo docker ps -q)

# 2. Remove all containers
sudo docker rm $(sudo docker ps -aq)

# 3. Remove all images
sudo docker rmi -f $(sudo docker images -q)

# 4. Clean up volumes, networks, cache
sudo docker system prune -a --volumes


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


import os
import sys
import base64
import gc
from io import BytesIO
import torch
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image, ImageChops
from torch.utils.data import DataLoader
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict, Any
import json
from openai import OpenAI
from transformers import AutoTokenizer, AutoModel
from colpali_engine.models import ColQwen2, ColQwen2Processor
import nltk
import weaviate
import numpy as np
from weaviate import Client
from dotenv import load_dotenv
load_dotenv()


# Constants
SUPPORTED_EXTENSIONS = ['.pdf', '.csv', '.xlsx', '.xls', '.json', '.txt']
TOP_K = 5
device = "cuda" if torch.cuda.is_available() else "cpu"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Global model references
colqwen_model = None
colqwen_processor = None
jina_tokenizer = None
jina_model = None

def initialize_weaviate() -> tuple[Client, Client]:
    """Initialize two Weaviate clients with proper schemas"""
    # text_client = weaviate.Client("http://localhost:8080")
    # image_client = weaviate.Client("http://localhost:8081")
    text_client = weaviate.Client("http://weaviate-text:8080")
    image_client = weaviate.Client("http://weaviate-image:8080")

    #THIS IS TO UNCOMMENTED IF THERE"S WEVIATE ERROR
    # Clear existing classes if needed
    # for client, class_name in [(text_client, "TextChunk"), (image_client, "ImageChunk")]:
    #     if client.schema.exists(class_name):
    #         client.schema.delete_class(class_name)

    # ⭐ MODIFIED: Optimized HNSW parameters for better recall
    if not image_client.schema.exists("ImageChunk"):
        image_class = {
            "class": "ImageChunk",
            "vectorizer": "none",
            "vectorIndexConfig": {
                "distance": "cosine",
                "dimensions": 1024,
                "efConstruction": 256,
                "maxConnections": 64,
                "ef": 128
            },
            "properties": [
                {"name": "source", "dataType": ["string"]},
                {"name": "chunk_id", "dataType": ["int"]},
                {"name": "content_base64", "dataType": ["text"]}
            ]
        }
        image_client.schema.create_class(image_class)

    # ⭐ MODIFIED: Tuned text index parameters
    if not text_client.schema.exists("TextChunk"):
        text_class = {
            "class": "TextChunk",
            "vectorizer": "none",
            "vectorIndexConfig": {
                "distance": "cosine",
                "dimensions": 768,
                "efConstruction": 512,
                "maxConnections": 128,
                "ef": 256
            },
            "properties": [
                {"name": "source", "dataType": ["string"]},
                {"name": "chunk_id", "dataType": ["int"]},
                {"name": "text", "dataType": ["text"]}
            ]
        }
        text_client.schema.create_class(text_class)

    return text_client, image_client


def initialize_models():
    """Load all models with consistent configurations"""
    global colqwen_model, colqwen_processor, jina_tokenizer, jina_model
    
    # Initialize with explicit processor config
    colqwen_processor = ColQwen2Processor.from_pretrained(
        "vidore/colqwen2-v1.0",
        use_fast=False  # Explicitly handle processor version
    )
    
    colqwen_model = ColQwen2.from_pretrained(
        "vidore/colqwen2-v1.0",
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    ).eval()

    # Initialize Jina with proper config
    jina_tokenizer = AutoTokenizer.from_pretrained(
        "jinaai/jina-embeddings-v2-base-en",
        use_fast=True,
        trust_remote_code=True
    )
    jina_model = AutoModel.from_pretrained(
        "jinaai/jina-embeddings-v2-base-en",
        trust_remote_code=True
    ).to(device).eval()

def trim_whitespace(img: Image.Image) -> Image.Image:
    """Remove borders from PDF images"""
    bg = Image.new(img.mode, img.size, img.getpixel((0,0)))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img

def encode_image_to_base64(img: Image.Image) -> str:
    """Convert PIL image to base64 string"""
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# Text extraction functions
def extract_text_from_csv(path: str) -> List[str]:
    df = pd.read_csv(path)
    return [json.dumps(row.to_dict(), default=str) for _, row in df.iterrows()]

def extract_text_from_excel(path: str) -> List[str]:
    df = pd.read_excel(path)
    return [json.dumps(row.to_dict(), default=str) for _, row in df.iterrows()]

def extract_text_from_json(path: str) -> List[str]:
    with open(path) as f:
        data = json.load(f)
    return [json.dumps(data, indent=2)]

def extract_text_from_txt(path: str, max_tokens: int = 256, overlap: int = 64) -> List[str]:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = start + max_tokens
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start += (max_tokens - overlap)
    
    return chunks


def process_file(file_path: str, text_client: Client, image_client: Client):
    """Process a single file and store in appropriate Weaviate instance"""
    if not os.path.exists(file_path):
        print(f"Skipping missing file: {file_path}")
        return

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        images = [trim_whitespace(img) for img in convert_from_path(file_path)]
        store_images_in_weaviate(images, file_path, image_client)
    
    elif ext in ['.txt', '.csv', '.xlsx', '.xls', '.json']:
        if ext == '.txt':
            chunks = extract_text_from_txt(file_path)
        elif ext == '.csv':
            chunks = extract_text_from_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            chunks = extract_text_from_excel(file_path)
        elif ext == '.json':
            chunks = extract_text_from_json(file_path)
        
        text_chunks = [{
            'text': chunk,
            'source': file_path,
            'chunk_id': i
        } for i, chunk in enumerate(chunks)]
        
        store_text_in_weaviate(text_chunks, text_client)


def store_images_in_weaviate(images: List[Image.Image], source: str, client: Client):
    """Store PDF images with ColQwen2 embeddings"""
    client.batch.configure(
        batch_size=8,
        dynamic=True,
        timeout_retries=3,
        callback=None
    )
    print("starting to store images.......")
    with client.batch as batch:
        for idx, img in enumerate(tqdm(images, desc="Storing images")):
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            processed = colqwen_processor.process_images([img]).to(device)
            
            with torch.no_grad():
                outputs = colqwen_model(**processed)
                # Handle different output formats
                if isinstance(outputs, tuple):
                    # Case 1: Tuple output (hidden_states, ...)
                    hidden_state = outputs[0]
                else:
                    # Case 2: Raw tensor output
                    hidden_state = outputs
                
                # Use average pooling of all tokens
                emb = hidden_state.mean(dim=1)  # [batch_size, hidden_size]
                emb = torch.nn.functional.normalize(emb, p=2, dim=1)
                emb = emb.float().cpu().numpy()[0]

            batch.add_data_object(
                {
                    "source": source,
                    "chunk_id": idx,
                    "content_base64": encode_image_to_base64(img)
                },
                "ImageChunk",
                vector=emb.tolist()
            )
            print(f"Stored image chunk {idx + 1}/{len(images)} from {source}")


def store_text_in_weaviate(text_chunks: List[dict], client: Client):
    """Store text chunks with Jina embeddings"""
    # ⭐ MODIFIED: Increased batch size for better GPU utilization
    client.batch.configure(
        batch_size=64,
        dynamic=True,
        timeout_retries=3,
        callback=None
    )
    
    with client.batch as batch:
        for chunk in tqdm(text_chunks, desc="Storing text"):
            inputs = jina_tokenizer(
                chunk['text'],
                padding=True,
                truncation=True,
                max_length=512,  # ⭐ NEW: Explicit length control
                return_tensors="pt"
            ).to(device)
            
            with torch.no_grad():
                outputs = jina_model(**inputs)
                # ⭐ MODIFIED: Use proper pooling and normalization
                emb = outputs.last_hidden_state[:, 0, :]  # CLS token pooling
                emb = torch.nn.functional.normalize(emb, p=2, dim=1)
                emb = emb.float().cpu().numpy()[0]

            batch.add_data_object(
                {
                    "source": chunk['source'],
                    "chunk_id": chunk['chunk_id'],
                    "text": chunk['text']
                },
                "TextChunk",
                vector=emb.tolist()
            )


def retrieve_image_top_k(query: str, client: Client, k: int = TOP_K) -> List[Image.Image]:
    """
    Retrieve images using ColQwen2 query embedding, with null‐safe handling.
    Returns an empty list if no matches or on error.
    """
    # 1) Build the query embedding
    q_batch = colqwen_processor.process_queries([query]).to(device)
    with torch.no_grad():
        outputs = colqwen_model(**q_batch)
        hidden_state = outputs[0] if isinstance(outputs, tuple) else outputs
        q_emb = hidden_state.mean(dim=1)                       # average‐pool
        q_emb = torch.nn.functional.normalize(q_emb, p=2, dim=1)
        q_emb = q_emb.float().cpu().numpy()[0]

    # 2) Fire the Weaviate query
    try:
        result = (
            client.query
                  .get("ImageChunk", ["content_base64", "_additional { distance }"])
                  .with_near_vector({"vector": q_emb.tolist()})
                  .with_limit(k * 2)
                  .do()
        )
    except Exception as e:
        print(f"[Warning] Weaviate image query failed: {e}")
        return []

    # 3) Null‐safe extraction
    image_list = (
        result.get("data", {})
              .get("Get", {})
              .get("ImageChunk")
    )
    if not isinstance(image_list, list):
        print(f"[Warning] No ImageChunk returned for query “{query}”.")
        return []

    # 4) Sort & decode top-k
    items = sorted(image_list, key=lambda x: x["_additional"]["distance"])[:k]
    images = []
    for obj in items:
        try:
            raw = base64.b64decode(obj["content_base64"])
            images.append(Image.open(BytesIO(raw)))
        except Exception as decode_err:
            print(f"[Error] failed to decode an image chunk: {decode_err}")
    return images


def retrieve_text_top_k(query: str, client: Client, k: int = TOP_K) -> List[dict]:
    """Retrieve text using Jina query embedding"""
    inputs = jina_tokenizer(
        query,
        padding=True,
        truncation=True,
        max_length=512,  # ⭐ NEW: Match storage length
        return_tensors="pt"
    ).to(device)
    
    with torch.no_grad():
        outputs = jina_model(**inputs)
        q_emb = outputs.last_hidden_state[:, 0, :]  # CLS token pooling
        q_emb = torch.nn.functional.normalize(q_emb, p=2, dim=1)
        q_emb = q_emb.cpu().numpy()[0]

    result = client.query.get(
        "TextChunk",
        ["text", "source", "chunk_id", "_additional { certainty distance }"]
    ).with_near_vector({
        "vector": q_emb.tolist()
    }).with_limit(k*2).with_additional(["explainScore"]).do()
    items = result["data"]["Get"]["TextChunk"]
    items = sorted(items, key=lambda x: x['_additional']['distance'])[:k]
    
    return [{
        "text": item["text"],
        "source": item["source"],
        "chunk_id": item["chunk_id"],
        "score": 1 - item["_additional"]["distance"]  # Convert to similarity score
    } for item in items]


def summarize_with_gpt(query: str, text_results: List[dict], image_results: List[Image.Image]) -> str:
    """Generate final answer using GPT-4 with retrieved content"""
    client = OpenAI(api_key=OPENAI_API_KEY.strip())

    # Prepare text context
    combined = "\n\n".join(
        f"Source: {os.path.basename(res['source'])} (chunk {res['chunk_id']})\n{res['text']}"
        for res in text_results
    )

    # Prepare images
    image_content = [{
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{encode_image_to_base64(img)}"}
    } for img in image_results]

    messages = [
        {
            "role": "system",
            "content": "You are a technical assistant. Use the provided document chunks and images to answer the query. Cite sources using chunk numbers."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Query: {query}\n\nRetrieved text chunks:\n{combined}"},
                *image_content
            ]
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1000,
    )
    return response.choices[0].message.content


def check_existing_data(client: Client, class_name: str) -> bool:
    """
    Check if any data exists in a Weaviate class, safely handling null/malformed responses.
    """
    try:
        result = (
            client.query
                  .aggregate(class_name)
                  .with_meta_count()
                  .do()
        )
    except Exception as e:
        print(f"[Warning] aggregate() call failed for {class_name}: {e}")
        return False

    # if the call itself returned None or something unexpected, bail out
    if not isinstance(result, dict):
        return False

    data = result.get("data")
    if not isinstance(data, dict):
        return False

    agg = data.get("Aggregate")
    if not isinstance(agg, dict):
        return False

    class_list = agg.get(class_name)
    if not (isinstance(class_list, list) and class_list):
        return False

    # Finally, extract count (default 0)
    meta = class_list[0].get("meta")
    if not isinstance(meta, dict):
        return False

    count = meta.get("count", 0)
    return bool(count)


def ingestion_pipeline(file_paths, text_client: Client, image_client: Client):
    """Run only when new data needs to be ingested"""
    print("Starting data ingestion...")
    for file_path in file_paths:
        process_file(file_path, text_client, image_client)
    print("Ingestion completed successfully")

def create_kg(file_paths: List[str]):
    # Initialize system
    nltk.download('punkt')
    print("Initializing models and Weaviate clients...")
    initialize_models()
    text_client, image_client = initialize_weaviate()

    # Check existing data
    text_data_exists = check_existing_data(text_client, "TextChunk")
    print(f"Text data exists: {text_data_exists}")
    image_data_exists = check_existing_data(image_client, "ImageChunk")
    print(f"Image data exists: {image_data_exists}")

    # Only ingest if no data exists
    if not text_data_exists or not image_data_exists:
        ingestion_pipeline(file_paths, text_client, image_client)
    else:
        print("Using existing data in Weaviate")
    # Example query
    query = "Awards won by  Sarposh Foods?"
    
    # Retrieve results
    top_images = retrieve_image_top_k(query, image_client)
    top_texts = retrieve_text_top_k(query, text_client)
    os.makedirs('saved_images', exist_ok=True)
    for i, img in enumerate(top_images):
        if isinstance(img, Image.Image):
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(f'saved_images/image_{i+1}.png')
        else:
            if isinstance(img, torch.Tensor):
                img = img.detach().cpu().numpy()
            if img.shape[0] in [1, 3]:  # [C, H, W]
                img = np.transpose(img, (1, 2, 0))
            img = (img * 255).clip(0, 255).astype(np.uint8)
            Image.fromarray(img).save(f'saved_images/image_{i+1}.png')
    
    summary = summarize_with_gpt(query, top_texts, top_images)
    return summary
