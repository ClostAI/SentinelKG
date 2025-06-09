from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
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

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

import re
from typing import Dict, Any,Union

def format_single_booking(booking: dict) -> str:
    """Format individual booking dictionary"""
    if not isinstance(booking, dict):
        return str(booking)
    
    lines = []
    for key, value in booking.items():
        display_value = "N/A" if value is None else str(value)
        lines.append(f"• *{key}*: {display_value}")
    
    return "\n".join(lines)

def format_booking_list(bookings: list) -> str:
    """Format list of bookings with numbering"""
    if not bookings:
        return "No bookings found"
    
    # Single booking - no numbering needed
    if len(bookings) == 1:
        return format_single_booking(bookings[0])
    
    # Multiple bookings
    results = []
    for i, booking in enumerate(bookings, 1):
        results.append(f"*Booking #{i}*")
        results.append(format_single_booking(booking))
        results.append("")  # Spacer between bookings
    
    return "\n".join(results)

def format_booking_data(data: Union[list, dict]) -> str:
    """Convert booking data into WhatsApp-friendly format"""
    if isinstance(data, list):
        return format_booking_list(data)
    elif isinstance(data, dict):
        return format_single_booking(data)
    return str(data)  # Fallback for other types

def parse_and_format_message(input_str: str) -> str:
    """Detect and format JSON booking data or return plain text"""
    # Handle plain text messages immediately
    if not input_str.startswith(("[", "{")) or not input_str.endswith(("]", "}")):
        return input_str

    try:
        data = json.loads(input_str)
        return format_booking_data(data)
    except json.JSONDecodeError:
        return input_str  # Return original if invalid JSON


@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    try:
        # Convert markdown to WhatsApp formatting
        formatted_message = parse_and_format_message(message)
    except Exception as e:
        formatted_message = message  # Fallback to original on error
    success, status_message = whatsapp_send_message(recipient, formatted_message)
    return {"success": success, "message": status_message}
    
    # # Call the whatsapp_send_message function with the unified recipient parameter
    # success, status_message = whatsapp_send_message(recipient, message)
    # return {
    #     "success": success,
    #     "message": status_message
    # }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

from flask import Flask, Response
import time
import json
from flask import jsonify
from mcp.server.fastmcp import FastMCP
from flask import Flask, render_template

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


@app.route('/sse')
def sse_stream():
    """SSE stream for sending data in real-time."""
    
    def generate():
        while True:
            # Call the list_messages method directly
            data = mcp.list_messages(limit=5)  # Adjust based on your tool
            # Convert the data to JSON and yield it
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)  # Delay between each message for real-time updates
    
    return Response(generate(), content_type='text/event-stream')


import asyncio
from typing import AsyncIterator, Dict, Any

@mcp.resource("whatsapp://new_messages")
async def stream_new_messages() -> AsyncIterator[Dict[str, Any]]:
    last_seen: Optional[str] = None
    while True:
        # fetch messages after last_seen
        msgs = whatsapp_list_messages(after=last_seen, limit=10)
        for msg in msgs:
            yield {
                "id":       msg.id,
                "chat_jid": msg.chat_jid,
                "content":  msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "from_me":  msg.is_from_me,
            }
            last_seen = msg.timestamp.isoformat()
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Run the Flask app to handle SSE
    app.run(debug=True, threaded=True, host="0.0.0.0", port=3000)

# if __name__ == "__main__":
#     # Initialize and run the server
#     mcp.run(transport='stdio')