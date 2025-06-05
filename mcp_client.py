import asyncio
import json
from openai import AsyncOpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client
import os

# 1) Configure MCP and OpenAI
MCP_SSE_URL = "http://localhost:3000/sse"
OPENAI_MODEL = "gpt-4o-mini"  # Or "gpt-4"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Set in environment

# 2) Initialize OpenAI client
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# 3) Define tool schemas
TOOL_SCHEMAS = {
    "create_workbook": {
        "description": "Creates a new Excel workbook",
        "parameters": {
            "filepath": {"type": "string", "description": "Path to save the workbook (e.g., 'my_file.xlsx')"}
        }
    },
    "create_worksheet": {
        "description": "Adds a new worksheet to an existing workbook",
        "parameters": {
            "filepath": {"type": "string", "description": "Path to the workbook"},
            "sheet_name": {"type": "string", "description": "Name of the new sheet"}
        }
    },
    "write_data_to_excel": {
        "description": "Writes data to a worksheet",
        "parameters": {
            "filepath": {"type": "string", "description": "Path to the workbook"},
            "sheet_name": {"type": "string", "description": "Target worksheet name"},
            "data": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]}
                },
                "description": "2D data array (e.g., [['Name','Age'],['Alice',30]])"
            },
            "start_cell": {"type": "string", "description": "Starting cell (e.g., 'A1')"}
        }
    },
    # Add more tools as needed based on your available tools
}

async def natural_language_to_tool_call(user_query: str, available_tools: list) -> tuple:
    """Use OpenAI to convert natural language to tool call"""
    # Prepare tools list for OpenAI
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": schema["description"],
                "parameters": {
                    "type": "object",
                    "properties": schema["parameters"],
                    "required": list(schema["parameters"].keys())
                }
            }
        }
        for tool_name, schema in TOOL_SCHEMAS.items() 
        if tool_name in available_tools
    ]

    # Call OpenAI with new API
    response = await ai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": user_query}],
        tools=openai_tools,
        tool_choice="auto"
    )
    
    # Parse new response format
    tool_calls = response.choices[0].message.tool_calls
    print(tool_calls)
    if not tool_calls:
        return None, None
    
    main_tool = tool_calls[0]
    return (
        main_tool.function.name,
        json.loads(main_tool.function.arguments)
    )

async def main():
    async with sse_client(url=MCP_SSE_URL) as (send_stream, recv_stream):
        async with ClientSession(send_stream, recv_stream) as session:
            await session.initialize()
            
            # Get available tools from server
            tools_response = await session.list_tools()
            available_tools = [tool.name for tool in tools_response.tools]
            print(f"✨ Available tools: {', '.join(available_tools)}")
            
            # Natural language interaction loop
            while True:
                try:
                    # Get user input
                    query = input("\n💬 Enter command (or 'exit'): ").strip()
                    if query.lower() in ["exit", "quit"]:
                        break
                    if not query:
                        continue
                    
                    # Convert to tool call
                    tool_name, params = await natural_language_to_tool_call(query, available_tools)
                    
                    if not tool_name:
                        print("❌ No valid tool identified for this command")
                        continue
                    
                    # Execute tool call
                    print(f"🔧 Calling {tool_name} with: {json.dumps(params, indent=2)}")
                    result = await session.call_tool(tool_name, params)
                    print(f"✅ Result: {result}")
                    
                except Exception as e:
                    print(f"🚨 Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

# import asyncio
# import json
# import re
# from mcp import ClientSession
# from mcp.client.sse import sse_client
# import os

# # Configure MCP
# MCP_SSE_URL = "http://localhost:3000/sse"

# # Regex patterns for tool calls
# TOOL_PATTERNS = {
#     "create_workbook": [
#         (r"create(?: a)? new workbook (?:named|called) ['\"]?(?P<filepath>[\w\s\.\-]+\.xlsx)['\"]?", 
#          lambda m: {"filepath": m.group("filepath")}),
#         (r"make (?:a )?workbook at ['\"]?(?P<filepath>[\w\s\.\-]+\.xlsx)['\"]?", 
#          lambda m: {"filepath": m.group("filepath")})
#     ],
#     "create_worksheet": [
#         (r"add (?:a )?new sheet (?:named|called) ['\"]?(?P<sheet_name>[\w\s]+)['\"]? to ['\"]?(?P<filepath>[\w\s\.\-]+\.xlsx)['\"]?", 
#          lambda m: {"filepath": m.group("filepath"), "sheet_name": m.group("sheet_name")}),
#         (r"create worksheet ['\"]?(?P<sheet_name>[\w\s]+)['\"]? in ['\"]?(?P<filepath>[\w\s\.\-]+\.xlsx)['\"]?", 
#          lambda m: {"filepath": m.group("filepath"), "sheet_name": m.group("sheet_name")})
#     ],
#     "write_data_to_excel": [
#         (r"write data to ['\"]?(?P<filepath>[\w\s\.\-]+\.xlsx)['\"]? sheet ['\"]?(?P<sheet_name>[\w\s]+)['\"]? starting at (?P<start_cell>[A-Z]+\d+)", 
#          lambda m: {"filepath": m.group("filepath"), "sheet_name": m.group("sheet_name"), "start_cell": m.group("start_cell")})
#     ]
# }

# def natural_language_to_tool_call(user_query: str) -> tuple:
#     """Convert natural language to tool call using regex"""
#     user_query = user_query.lower().strip()
    
#     for tool_name, patterns in TOOL_PATTERNS.items():
#         for pattern, param_extractor in patterns:
#             match = re.search(pattern, user_query, re.IGNORECASE)
#             if match:
#                 params = param_extractor(match)
#                 return tool_name, params
                
#     return None, None

# async def main():
#     async with sse_client(url=MCP_SSE_URL) as (send_stream, recv_stream):
#         async with ClientSession(send_stream, recv_stream) as session:
#             await session.initialize()
            
#             # Get available tools from server
#             tools_response = await session.list_tools()
#             available_tools = [tool.name for tool in tools_response.tools]
#             print(f"✨ Available tools: {', '.join(available_tools)}")
#             print("Try commands like:")
#             print("  - Create a new workbook named 'reports.xlsx'")
#             print("  - Add new sheet called 'Summary' to 'reports.xlsx'")
#             print("  - Write data to 'reports.xlsx' sheet 'Summary' starting at A1")
            
#             # Natural language interaction loop
#             while True:
#                 try:
#                     # Get user input
#                     query = input("\n💬 Enter command (or 'exit'): ").strip()
#                     if query.lower() in ["exit", "quit"]:
#                         break
#                     if not query:
#                         continue
                    
#                     # Convert to tool call
#                     tool_name, params = natural_language_to_tool_call(query)
                    
#                     if not tool_name:
#                         print("❌ No valid tool identified. Try something like:")
#                         print("  - 'Create a workbook named sales.xlsx'")
#                         print("  - 'Add sheet January to sales.xlsx'")
#                         continue
                    
#                     # Handle data input separately
#                     if tool_name == "write_data_to_excel":
#                         print("Enter your data as comma-separated rows (e.g., Name,Age,Department)")
#                         print("Press Enter twice when finished:")
#                         data = []
#                         while True:
#                             row = input("> ").strip()
#                             if not row:
#                                 break
#                             data.append([x.strip() for x in row.split(",")])
#                         params["data"] = data
                    
#                     # Execute tool call
#                     print(f"🔧 Calling {tool_name} with: {json.dumps(params, indent=2)}")
#                     result = await session.call_tool(tool_name, params)
#                     print(f"✅ Result: {result}")
                    
#                 except Exception as e:
#                     print(f"🚨 Error: {str(e)}")

# if __name__ == "__main__":
#     asyncio.run(main())