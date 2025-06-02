import uuid
import json
import re
import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from sse_starlette.sse import EventSourceResponse
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from nexra.src.tools import response_tool
from runner import initialize_kg, query_kg
from pymongo import MongoClient
from typing import List
from fastapi import FastAPI, Query, Body


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

def get_session(session_id: str = None) -> tuple[str, ConversationBufferMemory]:
    """Create or retrieve session with isolated memory from MongoDB."""
    if session_id:
        doc = memory_collection.find_one({"_id": session_id})
        if doc:
            #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="query",      # only store inputs under 'query'
                output_key="text",      # only store outputs under 'text'
                return_messages=True
            )
            stored_history = doc.get("chat_history", [])
            for message in stored_history:
                role = message.get("role")
                content = message.get("content")
                if role == "human":
                    memory.chat_memory.add_user_message(content)
                elif role == "ai":
                    memory.chat_memory.add_ai_message(content)
            return session_id, memory
    # Create new session if not found or new
    #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="query",      # only store inputs under 'query'
            output_key="text",      # only store outputs under 'text'
            return_messages=True
        )
    memory_collection.insert_one({"_id": session_id, "chat_history": []})
    return session_id, memory

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

async def query_stream_generator(session_id, user_input, bot,top_k):
    sid, memory = get_session(session_id)
    chat_chain = LLMChain(llm=llm, prompt=chat_prompt, memory=memory)
    hist = format_chat_history(memory.load_memory_variables({})["chat_history"])
    response = query_kg(user_input)
#     if bot == "agni":
#         context = "hi agniiiiii"
#         print(context)
#     else:
#         context = None
#     # 1. Manager decision
#     print("++++++++++++++")
#     print(hist)
#     print("++++++++++++++")
#     raw = manager_agent_chain.invoke({"chat_history": hist, "context": context, "query": user_input})
#     manager_resp = raw["text"]
#     json_match = re.search(r'\{.*?\}', manager_resp, re.DOTALL)
#     if json_match:
#         json_str = json_match.group()
#         parsed_data = json.loads(json_str)
#         sig = parsed_data.get("signal")
#         reasoning = parsed_data.get("reasoning")
#         search_q = parsed_data.get("query")
#         loc = parsed_data.get("location")
#    # sig, search_q, reasoning, followups, loc = parse_manager_response(raw)
#     if sig in ("USE_KWD"):
#         # resp = chat_chain.invoke({"chat_history": hist, "context": None, "query": user_input})["text"].strip()
#         resp = chat_chain.invoke({
#                     "context": "",
#                     "query": user_input
#                 })["text"].strip()
#     if sig in ("USE_CONTEXT"):
#         # resp = chat_chain.invoke({"chat_history": hist, "context": context, "query": user_input})["text"].strip()
#         resp = chat_chain.invoke({
#                     "context": context,
#                     "query": user_input
#                 })["text"].strip()
#     elif sig == "INVOKE_SEARCH":
#         resp = await search_tool(search_q, top_k, loc)
#         resp = resp[0]
    #yield f"**Answer:**\n\n{resp}\n\n"
    message = format_sse(data=response)
    yield message
   # print(sig, search_q, reasoning, followups, loc)

    # # 2. Convert that parsed JSON → markdown
    # parsed = {
    #     "signal": sig,
    #     "reasoning": reasoning,
    #     "followups": followups,
    #     "location": loc,
    #     "query": search_q or user_input
    # }
    # md = markdown_chain.invoke({"json_data": json.dumps(parsed)})["text"]
    # yield f"{md}\n\n"

    # # 3. Get final answer
    # if sig in ("USE_CONTEXT", "GREETING"):
    #     resp = chat_chain.invoke({"chat_history": hist, "query": user_input})["text"].strip()
    # elif sig == "INVOKE_SEARCH":
    #     resp = await search_tool(parsed["query"], top_k, loc)
    # else:
    #     resp = raw

    # yield f"**Answer:**\n\n{resp}\n\n"

    # # 4. Persist
    chat_memory = memory.chat_memory.messages
    history_to_store = []
    for msg in chat_memory:
        if isinstance(msg, HumanMessage):
            #print("chat_message",{"role": "human", "content": msg.content} )
            history_to_store.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            history_to_store.append({"role": "ai", "content": msg.content}) 

    memory_collection.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "_id": session_id,
                        "chat_history": history_to_store
                    }
                },
                upsert=True
            )


# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()

@app.get("/stream")
async def sse_query(
    query: str = Query(...),
    bot: str = Query(...),
    top_k:    int = Query(5),
    session_id: str = Query(None)
):
    return EventSourceResponse(query_stream_generator(session_id, query, bot,top_k))


@app.get("/initialize")
async def initialize_system():
    """
    Initialize KG system with data files
    """
    file_paths = [
            "/app/SarposhFoods/instagram.json",
            "/app/SarposhFoods/videos.json",
            "/app/SarposhFoods/crawl_output.txt",
            "/app/SarposhFoods/2307.09288.pdf",
            "/app/SarposhFoods/1687-6180-2014-45.pdf"
    ]
    result = initialize_kg(file_paths)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("clost_web_server_markdown:app", host="0.0.0.0", port=8000, loop="asyncio")