import google.generativeai as genai
import subprocess
from fastapi import FastAPI, Request
import importlib.util
import os
from pathlib import Path
from flask import Flask, Response
import time
import json
from flask import jsonify
from mcp.server.fastmcp import FastMCP
from flask import Flask, render_template
import sys
import httpx
from fastapi.responses import JSONResponse

# parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)

def load_send_message(path_to_main_py):
    # Construct a module spec
    spec = importlib.util.spec_from_file_location(
        "whatsapp_main", Path(path_to_main_py).resolve()
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send_message

app = Flask(__name__)

# Configure Gemini
# GEMINI_API_KEY="AIzaSyD8bwyn4220ZKL9biFi3_46tRlgKrZETbg"

# genai.configure(api_key= GEMINI_API_KEY)


send_message = load_send_message(os.path.join(os.getcwd(), "main.py"))

def generate_gemini_response(prompt: str) -> str:
    """Generate response using Gemini 1.5 Flash model"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "response_mime_type": "text/plain"
        }
    )
    return response.text



from flask import Flask, Response
import time
import json
from flask import jsonify
from mcp.server.fastmcp import FastMCP
from flask import Flask, render_template
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)
app = Flask(__name__)
@app.route('/tools', methods=['GET'])
def list_tools():
    """Endpoint to list all tools and their descriptions."""
    tools = {
        "search_contacts": whatsapp_search_contacts,
        "list_messages": whatsapp_list_messages,
        "list_chats": whatsapp_list_chats,
        "get_chat": whatsapp_get_chat,
        "get_direct_chat_by_contact": whatsapp_get_direct_chat_by_contact,
        "get_contact_chats": whatsapp_get_contact_chats,
        "get_last_interaction": whatsapp_get_last_interaction,
        "get_message_context": whatsapp_get_message_context,
        "send_message": whatsapp_send_message,
        "send_file": whatsapp_send_file,
        "send_audio_message": whatsapp_audio_voice_message,
        "download_media": whatsapp_download_media
    }

    # Prepare the tools data for rendering
    tools_info = [
        {"name": tool_name, "description": tool.__doc__}
        for tool_name, tool in tools.items()
    ]
    
    # Render the HTML template with tools data
    return render_template('tools.html', tools_info=tools_info)




from flask import Flask, request, jsonify
# @app.post("/incoming")
# async def handle_message():
#     data = request.get_json()
#     message = data.get("text")
#     sender  = data.get("from")

#     if not message or not sender:
#         return jsonify(error="Missing message or sender"), 400

#     try:
#         response = await route_query(message)
#         # gemini_response = generate_gemini_response(message)
#         send_message(sender, response)
#         return jsonify(status="Message processed successfully")
#     except Exception as e:
#         return jsonify(error=str(e)), 500


# @app.post("/incoming")
# async def handle_message():
#     data = await request.json()
#     message = data.get("text")
#     sender = data.get("from")

#     if not message or not sender:
#         return JSONResponse(content={"error": "Missing message or sender"}, status_code=400)

#     try:
#         url = "http://localhost:8000/stream"
#         params = {
#             "query": message,
#             "bot": "agni",
#             "top_k": 5,
#             "session_id": "test123"
#         }

#         markdown_response = ""
#         async with httpx.AsyncClient(timeout=None) as client:
#             async with client.stream("GET", url, params=params) as response:
#                 async for chunk in response.aiter_text():
#                     markdown_response += chunk

#         # Optionally sanitize/convert markdown here if needed

#         send_message(sender, markdown_response)
#         return JSONResponse(content={"status": "Message processed successfully"})

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)


import requests

@app.post("/incoming")
def handle_message():
    data = request.get_json()
    message = data.get("text")
    sender = data.get("from")

    if not message or not sender:
        return jsonify(error="Missing message or sender"), 400

    try:
        url = "http://fastapi:8000/stream"
        params = {
            "query": message,
            "bot": "agni",
            "top_k": 5,
            "session_id": "test123"
        }
        print("MESSAGE", message)

        resp = requests.get(url, params=params, stream=True, timeout=90)
        # If it fails to connect, requests will raise an exception here
        resp.raise_for_status()

        print("RESPONSE STATUS CODE:", resp.status_code)
        markdown_response = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                markdown_response += chunk

        send_message(sender, markdown_response)
        return jsonify(status="Message processed successfully")

    except Exception as e:
        # Log the full exception to stdout (so you see it in Docker logs)
        print("⛔ ERROR FETCHING STREAM:", repr(e))
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    # Run the Flask app to handle SSE
    app.run(debug=True, threaded=True, host="0.0.0.0", port=3000)
