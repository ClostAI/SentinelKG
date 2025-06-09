import uuid
import json
import re
import asyncio
import os
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import FastAPI, Query, HTTPException
from sse_starlette.sse import EventSourceResponse
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from typing import List
from nexra.src.tools import response_tool
from runner import initialize_kg, query_kg
from pymongo import MongoClient
from router_llm import route_query
from typing import List
from fastapi import FastAPI, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse
import subprocess
import threading
import time
import httpx

load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.getenv("GEMINI_API_KEY")

# -----------------------------
# MongoDB Setup
# -----------------------------
# Make sure to configure the MongoDB URI in your environment
MONGO_URI = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["conversation_db"]  # change the db name as needed
memory_collection = db["conversation_memory"]

# Global dictionary for in-memory session caching (optional)
session_data = {}

# -----------------------------
# Utility Functions and Setup
# -----------------------------
whatsapp_process = None
qr_generated = False
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GO_BINARY_PATH = BASE_DIR / "whatsapp-mcp-server" / "whatsapp-bridge"
def run_whatsapp_client():
    global whatsapp_process, qr_generated
    if not GO_BINARY_PATH.exists():
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "WhatsApp binary not found"}
        )
    try:
        # Run the Go WhatsApp client
        process = subprocess.Popen(
            [str(GO_BINARY_PATH)],  # Use absolute path
            cwd=str(BASE_DIR / "whatsapp-bridge"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        whatsapp_process = process
        
        # Monitor output for QR generation
        while True:
            output = process.stdout.readline().decode()
            if not output and process.poll() is not None:
                break
            if "QR code is available at" in output:
                qr_generated = True
                break
                
    except Exception as e:
        print(f"Error running WhatsApp client: {e}")


def get_session(session_id: str = None) -> tuple[str, ConversationSummaryBufferMemory]:
    """Create or retrieve session with summary buffer memory."""
    if session_id:
        doc = memory_collection.find_one({"_id": session_id})
        if doc:
            memory = ConversationSummaryBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1),
                max_token_limit=1000
            )
            # Load stored messages
            stored_history = doc.get("chat_history", [])
            for message in stored_history:
                if message["role"] == "human":
                    memory.chat_memory.add_user_message(message["content"])
                elif message["role"] == "ai":
                    memory.chat_memory.add_ai_message(message["content"])
            
            # Load summary if exists
            if "summary" in doc:
                memory.moving_summary_buffer = doc["summary"]
                
            return session_id, memory
    
    # Create new session
    memory = ConversationSummaryBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1),
        max_token_limit=1000
    )
    memory_collection.insert_one({
        "_id": session_id, 
        "chat_history": [], 
        "summary": ""
    })
    return session_id, memory

# def get_session(session_id: str = None) -> tuple[str, ConversationBufferMemory]:
#     """Create or retrieve session with isolated memory from MongoDB."""
#     if session_id:
#         doc = memory_collection.find_one({"_id": session_id})
#         if doc:
#             #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
#             memory = ConversationBufferMemory(
#                 memory_key="chat_history",
#                 input_key="query",      # only store inputs under 'query'
#                 output_key="text",      # only store outputs under 'text'
#                 return_messages=True
#             )
#             stored_history = doc.get("chat_history", [])
#             for message in stored_history:
#                 role = message.get("role")
#                 content = message.get("content")
#                 if role == "human":
#                     memory.chat_memory.add_user_message(content)
#                 elif role == "ai":
#                     memory.chat_memory.add_ai_message(content)
#             return session_id, memory
#     # Create new session if not found or new
#     #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
#     memory = ConversationBufferMemory(
#             memory_key="chat_history",
#             input_key="query",      # only store inputs under 'query'
#             output_key="text",      # only store outputs under 'text'
#             return_messages=True
#         )
#     memory_collection.insert_one({"_id": session_id, "chat_history": []})
#     return session_id, memory

def format_chat_history(chat_history):
    """Convert list of messages to a formatted string."""
    formatted = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Bot: {msg.content}")
    return "\n".join(formatted)


def parse_manager_response(text):
    try:
        m = re.search(r'\{.*?\}', text, re.DOTALL)
        j = m.group().replace("'", '"') if m else text
        if isinstance(j, str):
            try:
                obj = json.loads(j)
                print("obj", obj)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string: {e}") from e
        elif isinstance(j, dict):
            obj = obj
        return (
            obj.get("signal", "USE_CONTEXT").upper(),
            obj.get("query", "").strip(),
            obj.get("reasoning", ""),
            obj.get("followups", []),
            obj.get("location", "").strip()
        )
    except:
        sig = re.search(r'(INVOKE_SEARCH|USE_CONTEXT)', text.upper())
        return (sig.group(0) if sig else "USE_CONTEXT", "", "", [], "NA")




# -----------------------------
# LangChain and Prompt Setup
# -----------------------------

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.1,
    convert_system_message_to_human=True
)

chat_prompt = PromptTemplate(
    input_variables=["chat_history", "context", "query"],
    template=(
        "You are a smart assistant build by clost, that understands follow-up queries.\n"
        "Conversation history:\n{chat_history}\n"
        "Context: {context}\n"
        "User: {query}\n"
        "Provide a helpful and relevant response based on the conversation history.\n"
        " Instructions:"
            "- Respond in a cordial manner, acknowledging the user's request."
            "- if {context} is None then use your internal knowledge to answer, else use {context} to respond accordingly"
            "- Do not mention According to provided content/According to the information I have sound as if you know all, context is provided for your accuracy"
            "- Format your response using markdown with appropriate headings, bullet points, numbered lists, and tables where they enhance clarity."
            "- Emphasize key terms and concepts using bold text."
    )
)

manager_agent_prompt = PromptTemplate(
    input_variables=["chat_history", "context", "query"],
    template=(
        "You are a cordial, general-purpose AI assistant, dedicated to helping users efficiently.\n"
        "Step 1 - Query Category Identification:\n"
        "Identify if the user's query falls into one of these categories:\n"
        "  - GREETING: a greeting or introduction (e.g., 'Hi', 'Hello', 'My name is...').\n"
        "  - NO: none of the above.\n\n"
        "Step 2 - Action & Tool Selection:\n"
        "  - If GREETING or the question can be answered from existing context, set \"signal\" to USE_KWD.\n"
        "  - For querues that can be answered using the context {context} provided, set  \"signal\" to USE_CONTEXT.\n"
        "  - For queries outside the assistant's current knowledge or requiring external data, set \"signal\" to INVOKE_SEARCH.\n\n"
        "Return a JSON object with exactly these keys:\n"
        "  \"signal\": one of [\"INVOKE_SEARCH\",\"USE_CONTEXT\",\"USE_KWD\"],\n"
        "  \"location\": the place mentioned in the query or \"NA\",\n"
        "  \"reasoning\": your step-by-step thought process,\n"
        "  \"followups\": a list of five follow-up questions to clarify the user's needs,\n"
        "  \"query\": a refined search query if applicable.\n\n"
        "History: {chat_history}\n"
        "Context: {context}\n"
        "Query: {query}\n"
    )
)

# chains
manager_agent_chain = LLMChain(llm=llm, prompt=manager_agent_prompt)

# -----------------------------
# Tool Integration
# -----------------------------
async def run_all_tools(query,  top_k, location):
    response_task = asyncio.create_task(response_tool(query, top_k, location))
    results = await asyncio.gather(response_task)
    return {"search": results}

async def search_tool(query, top_k, location):
    try:
        res = await run_all_tools(query, top_k, location)
        return res["search"]
    except:
        return "Search failed."

# -----------------------------
# SSE Generator
# -----------------------------

def format_sse(data: dict, event: str = "new_message", id: str = None):
    """
    Format the data as a JSON string for SSE.
    """
    return {
        "event": event,
        "data": json.dumps(data),
        "id": id
    }

# async def query_stream_generator(session_id, user_input, bot,top_k):
#     sid, memory = get_session(session_id)
#     chat_chain = LLMChain(llm=llm, prompt=chat_prompt, memory=memory)
#     hist = format_chat_history(memory.load_memory_variables({})["chat_history"])
#     response = await route_query(user_input)
#     message = format_sse(data=response)
#     yield message
#     chat_memory = memory.chat_memory.messages
#     history_to_store = []
#     for msg in chat_memory:
#         if isinstance(msg, HumanMessage):
#             history_to_store.append({"role": "human", "content": msg.content})
#         elif isinstance(msg, AIMessage):
#             history_to_store.append({"role": "ai", "content": msg.content}) 

#     memory_collection.update_one(
#                 {"_id": session_id},
#                 {
#                     "$set": {
#                         "_id": session_id,
#                         "chat_history": history_to_store
#                     }
#                 },
#                 upsert=True
#             )

async def query_stream_generator(session_id, user_input, bot, top_k):
    sid, memory = get_session(session_id)
    print("**&&Memory", memory)
    # Add current message to memory
    memory.chat_memory.add_user_message(user_input)
    
    # Get formatted history
    history = memory.load_memory_variables({})["chat_history"]
    
    # Pass conversation history to route_query
    response = await route_query(user_input, conversation_history=history)
    
    # Add AI response to memory
    memory.chat_memory.add_ai_message(response)
    
    # Prepare SSE response
    message = format_sse(data=response)
    yield message
    
    # Save updated memory to MongoDB
    stored_messages = []
    for msg in memory.chat_memory.messages:
        if isinstance(msg, HumanMessage):
            stored_messages.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            stored_messages.append({"role": "ai", "content": msg.content})
    memory_collection.update_one(
        {"_id": session_id},
        {
            "$set": {
                "chat_history": stored_messages,
                "summary": memory.moving_summary_buffer  # Use correct attribute
            }
        },
        upsert=True
    )

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()
from fastapi.responses import PlainTextResponse

@app.get("/stream")
async def sse_query(
    query: str = Query(...),
    bot: str = Query(...),
    top_k: int = Query(5),
    session_id: str = Query(None),
    raw: bool = Query(False, description="if true, return raw response without SSE framing")
):
    # Generate your LLM response just once, not as SSE
    print("=======================")
    print(session_id)
    sid, memory = get_session(session_id)
    memory.chat_memory.add_user_message(query)
    history = memory.load_memory_variables({})["chat_history"]
    response = await route_query(query, conversation_history=history)
    memory.chat_memory.add_ai_message(response)
    # persist memory back to MongoDB…
    # (same as in your SSE generator)
    stored_messages = []
    for msg in memory.chat_memory.messages:
        if isinstance(msg, HumanMessage):
            stored_messages.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            stored_messages.append({"role": "ai", "content": msg.content})

    memory_collection.update_one(
        {"_id": session_id},
        {
            "$set": {
                "chat_history": stored_messages,
                "summary": memory.moving_summary_buffer  # Use correct attribute
            }
        },
        upsert=True
    )
    return PlainTextResponse(response)

    # otherwise fall back to SSE
    #return EventSourceResponse(query_stream_generator(session_id, query, bot, top_k))



# @app.get("/stream")
# async def sse_query(
#     query: str = Query(...),
#     bot: str = Query(...),
#     top_k:    int = Query(5),
#     session_id: str = Query(None)
# ):
#     return EventSourceResponse(query_stream_generator(session_id, query, bot,top_k))

# @app.get("/whatsapp/start")
# async def start_whatsapp():
#     global whatsapp_process, qr_generated
    
#     # Start WhatsApp client in background thread if not already running
#     if whatsapp_process is None or whatsapp_process.poll() is not None:
#         qr_generated = False
#         thread = threading.Thread(target=run_whatsapp_client)
#         thread.daemon = True
#         thread.start()
        
#         # Wait for QR generation
#         start_time = time.time()
#         while not qr_generated and time.time() - start_time < 30:  # 30s timeout
#             time.sleep(0.5)
    
#     if qr_generated:
#         # Return QR code from Go server
#         return RedirectResponse(url="http://localhost:5000/qr")
#     else:
#         return {"status": "error", "message": "QR generation timed out"}


@app.get("/whatsapp/start")
async def start_whatsapp():
    global whatsapp_process, qr_ready
    
    # Check if process is already running
    if whatsapp_process and whatsapp_process.poll() is None:
        if qr_ready:
            return RedirectResponse(url="http://localhost:5000/qr")
        return JSONResponse(
            content={"status": "running", "message": "Client is running but QR not ready yet"},
            status_code=200
        )
    
    qr_ready = False
    threading.Thread(target=run_whatsapp_client, daemon=True).start()
    start = time.time()
    while not qr_ready and time.time() - start < 15:
        time.sleep(0.2)
    
    if qr_ready:
        return RedirectResponse(url="http://localhost:5000/qr")
    else:
        return JSONResponse(
            content={"status": "starting", "message": "Client started - QR may appear later at http://localhost:5000/qr"},
            status_code=202
        )


@app.get("/whatsapp/status")
async def whatsapp_status():
    # Check if WhatsApp client is running
    if whatsapp_process and whatsapp_process.poll() is None:
        return {"status": "running"}
    return {"status": "stopped"}

class InitializeRequest(BaseModel):
    urls: List[str]


@app.post("/initialize")
async def initialize(body: InitializeRequest):
    urls = body.urls
    if not urls:
            raise HTTPException(status_code=400, detail="`urls` list cannot be empty")
    else:
        result = await initialize_kg(urls)
        return result

    return {"status": "initialized", "received": urls}


# @app.get("/initialize")
# async def initialize_system():
#     """
#     Initialize KG system with data files
#     """
#     file_paths = [
#             "/app/SarposhFoods/instagram.json",
#             "/app/SarposhFoods/videos.json",
#             "/app/SarposhFoods/crawl_output.txt",
#             "/app/SarposhFoods/2307.09288.pdf",
#             "/app/SarposhFoods/1687-6180-2014-45.pdf"
#     ]
#     result = initialize_kg(file_paths)
#     return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("clost_web_server_markdown:app", host="0.0.0.0", port=8000, loop="asyncio")
