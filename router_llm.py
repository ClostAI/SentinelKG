# # Add these imports at the top
# import json
# from openai import AsyncOpenAI
# from typing import Dict, Any
# import uuid
# import json
# import re
# import asyncio
# import os
# from dotenv import load_dotenv
# from sse_starlette.sse import EventSourceResponse
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
# from langchain.memory import ConversationBufferMemory
# from langchain.schema import HumanMessage, AIMessage
# from nexra.src.tools import response_tool
# # from runner import initialize_kg, query_kg
# from pymongo import MongoClient
# from typing import List
# from runner import initialize_kg, query_kg
# # In your chatbot_router.py file
# from datetime import datetime, timedelta
# import re
# from excel_mcp_server.src.excel_mcp.server import (
#     apply_formula,
#     validate_formula_syntax,
#     format_range,
#     read_data_from_excel,
#     write_data_to_excel,
#     update_data_in_excel,
#     delete_data_in_excel,
#     create_workbook,
#     create_worksheet,
#     create_chart,
#     create_pivot_table,
#     copy_worksheet,
#     delete_worksheet,
#     rename_worksheet,
#     get_workbook_metadata,
#     merge_cells,
#     unmerge_cells,
#     copy_range,
#     delete_range,
#     validate_excel_range,
#     # Add other tools as needed
# )
# load_dotenv()
# current_date = datetime.now().strftime("%Y-%m-%d")
# current_time = datetime.now().strftime("%H:%M")
# tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
# # MONGO_URI = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
# TOP_K = 5
# LOCATION = "Bangalore"
# # mongo_client = MongoClient(MONGO_URI)
# # db = mongo_client["conversation_db"]  # change the db name as needed
# # memory_collection = db["conversation_memory"]
# OPENAI_MODEL = "gpt-4o-mini"
# session_data = {}
# OPENAI_API_KEY="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"
# ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# CAFE_DATA_PATH =  os.path.join(os.getcwd(), "SarposhFoods")
# RESERVATIONS_FILE = f"{CAFE_DATA_PATH}/reservations.xlsx"
# MENU_FILE = f"{CAFE_DATA_PATH}/menu.xlsx"
# STAFF_FILE = f"{CAFE_DATA_PATH}/staff_schedule.xlsx"
# SALES_FILE = f"{CAFE_DATA_PATH}/sales.xlsx"
# CAFE_NAME = "Sarpoosh Foods"

# RESERVATIONS_COLUMNS = {
#     "Bookings": [
#         ("Booking ID", "text"),
#         ("Customer Name", "text"),
#         ("Phone", "text"),
#         ("Date", "date (YYYY-MM-DD)"),
#         ("Time", "time (HH:MM)"),
#         ("Party Size", "number"),
#         ("Status", "text (Confirmed/Pending/Cancelled)"),
#         ("Notes", "text")
#     ],
#     "Customers": [
#         ("Customer ID", "text"),
#         ("Name", "text"),
#         ("Phone", "text"),
#         ("Email", "text"),
#         ("Loyalty Points", "number")
#     ]
# }

# SALES_COLUMNS = {
#     "Transactions": [
#         ("Transaction ID", "text"),
#         ("Date", "date (YYYY-MM-DD)"),
#         ("Time", "time (HH:MM)"),
#         ("Item ID", "text"),
#         ("Item Name", "text"),
#         ("Quantity", "number"),
#         ("Unit Price", "currency"),
#         ("Total Price", "currency"),
#         ("Payment Method", "text")
#     ],
#     "Inventory": [
#         ("Item ID", "text"),
#         ("Item Name", "text"),
#         ("Category", "text"),
#         ("Price", "currency"),
#         ("Stock", "number")
#     ]
# }


# SYSTEM_PROMPT = f"""
# You are a routing assistant for Sarpoosh Foods.
# Your job is to decide which “tool” (from the list below) to call, and then output exactly one JSON object with these two keys:
#   1. "tool_name"   (string, one of: perform_web_search, query_enterprise_kg, read_data_from_excel, write_data_to_excel, update_data_in_excel, delete_data_in_excel)
#   2. "arguments"   (an object matching that tool’s schema in TOOL_SCHEMAS)

# IMPORTANT:  
# - As soon as you see the word “booking” or “bookings” anywhere in the user’s query, you **must** pick one of the Excel tools with "context": "bookings".  
# - Always convert “today” or “tomorrow” into an exact YYYY-MM-DD string.  
#   (Today is {current_date}, so “tomorrow” → {tomorrow_date}.)  
# - Output **only** the JSON—no extra words, no markdown fences, no commentary.  

# Available tools:  
#   • perform_web_search  
#   • query_enterprise_kg  
#   • read_data_from_excel  
#   • write_data_to_excel  
#   • update_data_in_excel  
#   • delete_data_in_excel  

# RULES:

# 1) If the question is about general knowledge (geography, history, science), use:
#    "tool_name": "perform_web_search"
#    "arguments": {{ "query": "<the user’s full question>" }}

#    Example:
#    {{
#      "tool_name": "perform_web_search",
#      "arguments": {{
#        "query": "What is the capital of France?"
#      }}
#    }}

# 2) If the question is about Sarpoosh Foods (menu, hours, policies, vegan options, etc.), use:
#    "tool_name": "query_enterprise_kg"
#    "arguments": {{ "query": "<the user’s full question>" }}

#    Example:
#    {{
#      "tool_name": "query_enterprise_kg",
#      "arguments": {{
#        "query": "Do you have vegan options on the menu?"
#      }}
#    }}

# 3) If the question contains “booking” or “bookings,” you **must** choose one of these (all with "context": "bookings"):
#      • read_data_from_excel  
#      • write_data_to_excel  
#      • update_data_in_excel  
#      • delete_data_in_excel  

#    Always convert “today”/“tomorrow” to YYYY-MM-DD using the dates above.

#    a) Fetch bookings for tomorrow  
#    (Tomorrow is {tomorrow_date}.)  
#    {{
#      "tool_name": "read_data_from_excel",
#      "arguments": {{
#        "context": "bookings",
#        "filter_criteria": {{
#          "Date": "{tomorrow_date}"
#        }}
#      }}
#    }}

#    b) Fetch today’s bookings  
#    (Today is {current_date}.)  
#    {{
#      "tool_name": "read_data_from_excel",
#      "arguments": {{
#        "context": "bookings",
#        "filter_criteria": {{
#          "Date": "{current_date}"
#        }}
#      }}
#    }}

#    c) Book a table for 4 at 19:00 on {tomorrow_date} (example)  
#    {{
#      "tool_name": "write_data_to_excel",
#      "arguments": {{
#        "context": "bookings",
#        "data": [
#          [
#            "BKG-<UUID>",
#            "Alice Patel",
#            "",
#            "{tomorrow_date}",
#            "19:00",
#            4,
#            "Confirmed",
#            ""
#          ]
#        ]
#      }}
#    }}

#    d) Edit John Smith’s booking (change Time to 16:00)  
#    {{
#      "tool_name": "update_data_in_excel",
#      "arguments": {{
#        "context": "bookings",
#        "identifier": {{
#          "Customer Name": "John Smith"
#        }},
#        "update_fields": {{
#          "Time": "16:00"
#        }}
#      }}
#    }}

#    e) Cancel booking with Booking ID BKG-789  
#    {{
#      "tool_name": "delete_data_in_excel",
#      "arguments": {{
#        "context": "bookings",
#        "identifier": {{
#          "Booking ID": "BKG-789"
#        }}
#      }}
#    }}

# 4) If the question contains “sale,” “transaction,” or “order,” you must choose one of these (all with "context": "sales"):
#      • read_data_from_excel  
#      • write_data_to_excel  
#      • update_data_in_excel  
#      • delete_data_in_excel  

#    Always convert “today”/“tomorrow” to YYYY-MM-DD as above.

#    a) Fetch transactions for today  
#    (Today is {current_date}.)  
#    {{
#      "tool_name": "read_data_from_excel",
#      "arguments": {{
#        "context": "sales",
#        "filter_criteria": {{
#          "Date": "{current_date}"
#        }}
#      }}
#    }}

#    b) Record a sale: 2 Lattes at $3.50 each on {current_date} at 12:30  
#    {{
#      "tool_name": "write_data_to_excel",
#      "arguments": {{
#        "context": "sales",
#        "data": [
#          [
#            "TRX-<UUID>",
#            "{current_date}",
#            "12:30",
#            "ITEM-001",
#            "Latte",
#            2,
#            3.50,
#            7.00,
#            "Credit Card"
#          ]
#        ]
#      }}
#    }}

#    c) Edit transaction TRX-123 (change Quantity to 3)  
#    {{
#      "tool_name": "update_data_in_excel",
#      "arguments": {{
#        "context": "sales",
#        "identifier": {{
#          "Transaction ID": "TRX-123"
#        }},
#        "update_fields": {{
#          "Quantity": 3
#        }}
#      }}
#    }}

#    d) Delete transaction TRX-456  
#    {{
#      "tool_name": "delete_data_in_excel",
#      "arguments": {{
#        "context": "sales",
#        "identifier": {{
#          "Transaction ID": "TRX-456"
#        }}
#      }}
#    }}

# Important:  
# - Output **only** the JSON object with keys "tool_name" and "arguments".  
# - Do not add any commentary, markdown fences, or extra fields.  
# - Do not supply file paths or sheet names; apply_file_defaults() will add them automatically.  
# - Whenever you see “today” or “tomorrow,” replace with the dynamic dates ({current_date} / {tomorrow_date}).
# """




# # Updated TOOL_SCHEMAS with dynamic paths
# TOOL_SCHEMAS = {
#     "perform_web_search": {
#         "description": "Search web for general knowledge topics",
#         "parameters": {
#             "query": {"type": "string", "description": "Search query"}
#         },
#         "required": ["query"]
#     },
#     "query_enterprise_kg": {
#         "description": "Query cafe knowledge base for Brew Haven-specific info",
#         "parameters": {
#             "query": {"type": "string", "description": "Cafe-related question"}
#         },
#         "required": ["query"]
#     },
#     "read_data_from_excel": {
#         "description": "Retrieve data from Excel files",
#         "parameters": {
#             "context": {
#                 "type": "string",
#                 "description": "Operation context: 'bookings' or 'sales'",
#                 "enum": ["bookings", "sales"]
#             },
#             "filter_criteria": {
#                 "type": "object",
#                 "description": "Column:value pairs to filter results",
#                 "default": {}
#             }
#         },
#         "required": ["context"]
#     },
#     "write_data_to_excel": {
#         "description": "Add new data to Excel files",
#         "parameters": {
#             "context": {
#                 "type": "string",
#                 "description": "Operation context: 'bookings' or 'sales'",
#                 "enum": ["bookings", "sales"]
#             },
#             "data": {
#                 "type": "array",
#                 "description": "Data to add as list of lists (rows)",
#                 "items": {
#                     "type": "array",
#                     "items": {
#                         "type": ["string", "number", "boolean", "null"]
#                     }
#                 }
#             }
#         },
#         "required": ["context", "data"]
#     },
#     "update_data_in_excel": {
#         "description": "Modify existing data in Excel",
#         "parameters": {
#             "context": {
#                 "type": "string",
#                 "description": "Operation context: 'bookings' or 'sales'",
#                 "enum": ["bookings", "sales"]
#             },
#             "identifier": {
#                 "type": "object",
#                 "description": "Key-value pair to identify record"
#             },
#             "update_fields": {
#                 "type": "object",
#                 "description": "Fields to update with new values"
#             }
#         },
#         "required": ["context", "identifier", "update_fields"]
#     },
#     "delete_data_in_excel": {
#         "description": "Delete records from Excel",
#         "parameters": {
#             "context": {
#                 "type": "string",
#                 "description": "Operation context: 'bookings' or 'sales'",
#                 "enum": ["bookings", "sales"]
#             },
#             "identifier": {
#                 "type": "object",
#                 "description": "Key-value pair to identify record"
#             }
#         },
#         "required": ["context", "identifier"]
#     }
# }

# # def apply_file_defaults(tool_name: str, args: dict) -> dict:
# #     """Apply default filepaths based on tool type"""
# #     tool_defaults = {
# #         "read_data_from_excel": {"filepath": RESERVATIONS_FILE},
# #         "write_data_to_excel": {"filepath": RESERVATIONS_FILE},
# #         "get_workbook_metadata": {"filepath": RESERVATIONS_FILE},
# #         # Add other tools with default files
# #     }
    
# #     # Apply defaults if not provided
# #     if tool_name in tool_defaults:
# #         for param, default_value in tool_defaults[tool_name].items():
# #             if param not in args:
# #                 args[param] = default_value
                
# #     return args


# def apply_file_defaults(tool_name: str, args: dict) -> dict:
#     """Apply context-based defaults for Excel tools"""
#     # Set defaults for all tools
#     if tool_name in TOOL_SCHEMAS:
#         tool_schema = TOOL_SCHEMAS[tool_name]
#         for param, param_schema in tool_schema["parameters"].items():
#             if "default" in param_schema and param not in args:
#                 args[param] = param_schema["default"]
    
#     # Set filepath and sheet based on context for Excel tools
#     if tool_name in ["read_data_from_excel", "write_data_to_excel", 
#                    "update_data_in_excel", "delete_data_in_excel"]:
#         context = args.get("context", "bookings")  # Default to bookings
        
#         if context == "bookings":
#             args["filepath"] = RESERVATIONS_FILE
#             args["sheet_name"] = "Bookings"
#         elif context == "sales":
#             args["filepath"] = SALES_FILE
#             args["sheet_name"] = "Transactions"
    
#     return args


# async def unified_tool_router(user_query: str) -> dict:
#     """Route query to appropriate tool with cafe context"""
#     # Prepare tools list for OpenAI
#     openai_tools = [
#         {
#             "type": "function",
#             "function": {
#                 "name": name,
#                 "description": schema["description"],
#                 "parameters": {
#                     "type": "object",
#                     "properties": schema["parameters"],
#                     "required": schema.get("required", [])
#                 }
#             }
#         } for name, schema in TOOL_SCHEMAS.items()
#     ]

#     # Call OpenAI with cafe context
#     response = await ai_client.chat.completions.create(
#         model=OPENAI_MODEL,
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": user_query}
#         ],
#         tools=openai_tools,
#         tool_choice="auto"
#     )

#     print("raw_response", response)
#     # Extract tool call information
#     if response.choices[0].message.tool_calls:
#         tool_call = response.choices[0].message.tool_calls[0]
#         return {
#             "tool_name": tool_call.function.name,
#             "arguments": json.loads(tool_call.function.arguments)
#         }
    
#     # Fallback to knowledge graph for cafe queries
#     return {
#         "tool_name": "query_enterprise_kg",
#         "arguments": {"query": user_query}
#     }


# async def run_all_tools(query,  top_k, location):
#     response_task = asyncio.create_task(response_tool(query, top_k, location))
#     results = await asyncio.gather(response_task)
#     return {"search": results}

# async def search_tool(query, top_k, location):
#     try:
#         res = await run_all_tools(query, top_k, location)
#         return res["search"]
#     except:
#         return "Search failed."

# # Actual implementations of non-MCP tools
# async def perform_web_search(query: str) -> str:
#     """Search the web (implementation)"""
#     response = await search_tool(query, top_k = TOP_K, location = LOCATION)
#     return response

# async def query_enterprise_kg(query: str) -> str:
#     """Query knowledge graph (implementation)"""
#     response = query_kg(query)
#     return response

# async def query_stream_generator(user_input):    
#     # Route the user input
#     route_result = await unified_tool_router(user_input)
#     print("result", route_result)
#     tool_name = route_result["tool_name"]
#     args = route_result["arguments"]
    
#     # Apply defaults
#     args = apply_file_defaults(tool_name, args)
#     print("args", args)
    
#     # Execute the appropriate tool
#     if tool_name == "perform_web_search":
#         response = await perform_web_search(args["query"])
#     elif tool_name == "query_enterprise_kg":
#         response = await query_enterprise_kg(args["query"])
#     else:
#         # Handle Excel tools
#         try:
#             tool_mapping = {
#                 "read_data_from_excel": read_data_from_excel,
#                 "write_data_to_excel": write_data_to_excel,
#                 "update_data_in_excel": update_data_in_excel,
#                 "delete_data_in_excel": delete_data_in_excel,
#             }
            
#             if tool_name in tool_mapping:
#                 # Execute with validation
#                 response = tool_mapping[tool_name](**args)
#             else:
#                 response = f"Tool not implemented: {tool_name}"
#         except Exception as e:
#             response = f"Error executing tool: {str(e)}"

#     return response

# asyncio.run(query_stream_generator("Show bookings for tomorrow"))

############################################################################################################

# import json
# from openai import AsyncOpenAI
# from typing import Dict, Any, List, Optional
# import uuid
# import re
# import asyncio
# import os
# from dotenv import load_dotenv
# from datetime import datetime, timedelta
# import logging
# import ast
# import sys
# import pandas as pd
# from openpyxl import load_workbook

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# load_dotenv()
# current_date = datetime.now().strftime("%Y-%m-%d")
# current_time = datetime.now().strftime("%H:%M")
# tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
# TOP_K = 5
# LOCATION = "Bangalore"
# OPENAI_MODEL = "gpt-4o-mini"
# OPENAI_API_KEY="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"
# ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# # File paths
# CAFE_DATA_PATH = os.path.join(os.getcwd(), "SarposhFoods")
# os.makedirs(CAFE_DATA_PATH, exist_ok=True)  # Ensure directory exists
# RESERVATIONS_FILE = f"{CAFE_DATA_PATH}/reservations.xlsx"
# SALES_FILE = f"{CAFE_DATA_PATH}/sales.xlsx"
# CAFE_NAME = "Sarpoosh Foods"

# # Column definitions
# RESERVATIONS_COLUMNS = [
#     "Booking ID", "Customer Name", "Phone", "Date", "Time", 
#     "Party Size", "Status", "Notes"
# ]

# SALES_COLUMNS = [
#     "Transaction ID", "Date", "Time", "Item ID", "Item Name", 
#     "Quantity", "Unit Price", "Total Price", "Payment Method"
# ]

# # Initialize Excel files if they don't exist
# def initialize_excel_files():
#     # Create reservations file if it doesn't exist
#     if not os.path.exists(RESERVATIONS_FILE):
#         df = pd.DataFrame(columns=RESERVATIONS_COLUMNS)
#         df.to_excel(RESERVATIONS_FILE, index=False, sheet_name="Bookings")
#         logger.info(f"Created reservations file: {RESERVATIONS_FILE}")
    
#     # Create sales file if it doesn't exist
#     if not os.path.exists(SALES_FILE):
#         df = pd.DataFrame(columns=SALES_COLUMNS)
#         df.to_excel(SALES_FILE, index=False, sheet_name="Transactions")
#         logger.info(f"Created sales file: {SALES_FILE}")

# # Initialize files on startup
# initialize_excel_files()

# SYSTEM_PROMPT = f"""
# You are a routing assistant for Sarpoosh Foods. Today's date is {current_date}.
# Your ONLY task is to output JSON with these keys: tool_name, arguments, missing_args.

# STRICT RULES:
# 1. Use tools ONLY for these cases:
#    - perform_web_search: General knowledge (geography, history, science)
#    - query_enterprise_kg: Cafe-specific questions (menu, hours, policies, vegan options)
#    - Excel tools: ONLY for bookings/sales operations
# 2. For Excel tools:
#    - Use "bookings" for reservations
#    - Use "sales" for transactions
#    - Convert "today" to {current_date}, "tomorrow" to {tomorrow_date}
# 3. If arguments are missing, list them in missing_args
# 4. For write operations, generate UUIDs for Booking/Transaction IDs

# EXAMPLES:

# User: What is the capital of France?
# Output:
# {{
#   "tool_name": "perform_web_search",
#   "arguments": {{"query": "What is the capital of France?"}},
#   "missing_args": []
# }}

# User: Show bookings for tomorrow
# Output:
# {{
#   "tool_name": "read_data_from_excel",
#   "arguments": {{
#     "context": "bookings",
#     "filter_criteria": {{"Date": "{tomorrow_date}"}}
#   }},
#   "missing_args": []
# }}

# User: Record sale: 2 Lattes for $3.50 each today at 12:30
# Output:
# {{
#   "tool_name": "write_data_to_excel",
#   "arguments": {{
#     "context": "sales",
#     "data": [
#       ["TRX-{str(uuid.uuid4())[:8]}", "{current_date}", "12:30", "ITEM-001", "Latte", 2, 3.5, 7.0, "Cash"]
#     ]
#   }},
#   "missing_args": []
# }}

# User: What vegan options do you have?
# Output:
# {{
#   "tool_name": "query_enterprise_kg",
#   "arguments": {{"query": "What vegan options do you have?"}},
#   "missing_args": []
# }}

# User: Update booking time
# Output:
# {{
#   "tool_name": "update_data_in_excel",
#   "arguments": {{
#     "context": "bookings",
#     "identifier": {{}},
#     "update_fields": {{"Time": ""}}
#   }},
#   "missing_args": ["identifier.Booking ID"]
# }}

# IMPORTANT: OUTPUT ONLY VALID JSON. DO NOT INCLUDE ANY OTHER TEXT.
# """

# def map_context_to_file(context: str) -> Dict[str, Any]:
#     """Map context to file and sheet details"""
#     if context == "bookings":
#         return {
#             "filepath": RESERVATIONS_FILE,
#             "sheet_name": "Bookings",
#             "columns": RESERVATIONS_COLUMNS
#         }
#     elif context == "sales":
#         return {
#             "filepath": SALES_FILE,
#             "sheet_name": "Transactions",
#             "columns": SALES_COLUMNS
#         }
#     return {}

# def apply_filters(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
#     """Apply filters to dataset"""
#     if not filters:
#         return data
        
#     filtered_data = []
#     for row in data:
#         match = True
#         for key, value in filters.items():
#             if key in row and str(row[key]) != str(value):
#                 match = False
#                 break
#         if match:
#             filtered_data.append(row)
#     return filtered_data

# async def unified_tool_router(user_query: str) -> Dict[str, Any]:
#     """Route query to appropriate tool with argument validation"""
#     logger.info(f"Routing query: {user_query}")
    
#     try:
#         # Call OpenAI with strict JSON response format
#         response = await ai_client.chat.completions.create(
#             model=OPENAI_MODEL,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": user_query}
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.0  # Minimize creativity
#         )
        
#         content = response.choices[0].message.content
#         logger.info(f"LLM response: {content}")
        
#         # Parse JSON response
#         result = json.loads(content)
        
#         # Validate structure
#         if "tool_name" not in result:
#             raise ValueError("Missing tool_name in response")
            
#         return {
#             "tool_name": result.get("tool_name", "query_enterprise_kg"),
#             "arguments": result.get("arguments", {}),
#             "missing_args": result.get("missing_args", [])
#         }
#     except json.JSONDecodeError:
#         logger.error("Failed to parse JSON response from LLM")
#         return {
#             "tool_name": "query_enterprise_kg",
#             "arguments": {"query": user_query},
#             "missing_args": []
#         }
#     except Exception as e:
#         logger.error(f"Routing error: {str(e)}")
#         return {
#             "tool_name": "query_enterprise_kg",
#             "arguments": {"query": user_query},
#             "missing_args": []
#         }

# async def perform_web_search(query: str) -> str:
#     """Search the web implementation"""
#     logger.info(f"Performing web search: {query}")
#     # Simulated search results
#     return f"Search results for: {query}"

# async def query_enterprise_kg(query: str) -> str:
#     """Knowledge graph implementation"""
#     logger.info(f"Querying knowledge graph: {query}")
#     # Simulated KG response
#     return f"Knowledge graph response for: {query}"

# async def read_data_from_excel(filepath: str, sheet_name: str, filter_criteria: Dict[str, Any] = {}) -> str:
#     """Read data from Excel with filtering"""
#     logger.info(f"Reading data from {filepath} ({sheet_name}) with filters: {filter_criteria}")
    
#     try:
#         # Read Excel file into DataFrame
#         df = pd.read_excel(filepath, sheet_name=sheet_name)
        
#         # Convert to list of dictionaries
#         data = df.replace({float('nan'): None}).to_dict(orient='records')
        
#         # Apply filters
#         filtered_data = apply_filters(data, filter_criteria)
        
#         return json.dumps(filtered_data)
#     except Exception as e:
#         logger.error(f"Error reading Excel file: {str(e)}")
#         return f"Error reading data: {str(e)}"

# async def write_data_to_excel(filepath: str, sheet_name: str, data: List[List[Any]]) -> str:
#     """Write data to Excel"""
#     logger.info(f"Writing data to {filepath} ({sheet_name}): {data}")
    
#     try:
#         # Load existing data
#         book = load_workbook(filepath)
#         sheet = book[sheet_name]
        
#         # Find last row with data
#         max_row = sheet.max_row
#         start_row = max_row + 1 if max_row > 1 else 1
        
#         # Write new data
#         for row_idx, row_data in enumerate(data, start=start_row):
#             for col_idx, value in enumerate(row_data, start=1):
#                 sheet.cell(row=row_idx, column=col_idx, value=value)
        
#         # Save workbook
#         book.save(filepath)
#         return "Data written successfully"
#     except Exception as e:
#         logger.error(f"Error writing to Excel: {str(e)}")
#         return f"Error writing data: {str(e)}"

# async def update_data_in_excel(filepath: str, sheet_name: str, identifier: Dict[str, Any], update_fields: Dict[str, Any]) -> str:
#     """Update data in Excel"""
#     logger.info(f"Updating data in {filepath} ({sheet_name}) with identifier {identifier} and updates {update_fields}")
    
#     try:
#         # Load existing data
#         df = pd.read_excel(filepath, sheet_name=sheet_name)
        
#         # Find matching rows
#         mask = pd.Series(True, index=df.index)
#         for key, value in identifier.items():
#             if key in df.columns:
#                 mask = mask & (df[key].astype(str) == str(value))
        
#         # Apply updates
#         if mask.any():
#             for key, value in update_fields.items():
#                 if key in df.columns:
#                     df.loc[mask, key] = value
            
#             # Save updated data
#             with pd.ExcelWriter(filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
#                 writer.book = load_workbook(filepath)
#                 df.to_excel(writer, sheet_name=sheet_name, index=False)
#             return "Data updated successfully"
#         else:
#             return "No matching records found"
#     except Exception as e:
#         logger.error(f"Error updating Excel: {str(e)}")
#         return f"Error updating data: {str(e)}"

# async def delete_data_in_excel(filepath: str, sheet_name: str, identifier: Dict[str, Any]) -> str:
#     """Delete data in Excel"""
#     logger.info(f"Deleting data in {filepath} ({sheet_name}) with identifier {identifier}")
    
#     try:
#         # Load existing data
#         df = pd.read_excel(filepath, sheet_name=sheet_name)
        
#         # Find matching rows
#         mask = pd.Series(True, index=df.index)
#         for key, value in identifier.items():
#             if key in df.columns:
#                 mask = mask & (df[key].astype(str) == str(value))
        
#         # Delete rows
#         if mask.any():
#             df = df[~mask]
            
#             # Save updated data
#             with pd.ExcelWriter(filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
#                 writer.book = load_workbook(filepath)
#                 df.to_excel(writer, sheet_name=sheet_name, index=False)
#             return "Data deleted successfully"
#         else:
#             return "No matching records found"
#     except Exception as e:
#         logger.error(f"Error deleting from Excel: {str(e)}")
#         return f"Error deleting data: {str(e)}"

# async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
#     """Execute tool with arguments"""
#     logger.info(f"Executing {tool_name} with arguments: {arguments}")
    
#     try:
#         # Handle context mapping for Excel tools
#         if "context" in arguments:
#             context_config = map_context_to_file(arguments["context"])
#             if context_config:
#                 arguments.update(context_config)
        
#         # Execute the appropriate tool
#         if tool_name == "perform_web_search":
#             return await perform_web_search(arguments.get("query", ""))
#         elif tool_name == "query_enterprise_kg":
#             return await query_enterprise_kg(arguments.get("query", ""))
#         elif tool_name == "read_data_from_excel":
#             return await read_data_from_excel(
#                 arguments.get("filepath", ""),
#                 arguments.get("sheet_name", ""),
#                 arguments.get("filter_criteria", {})
#             )
#         elif tool_name == "write_data_to_excel":
#             return await write_data_to_excel(
#                 arguments.get("filepath", ""),
#                 arguments.get("sheet_name", ""),
#                 arguments.get("data", [])
#             )
#         elif tool_name == "update_data_in_excel":
#             return await update_data_in_excel(
#                 arguments.get("filepath", ""),
#                 arguments.get("sheet_name", ""),
#                 arguments.get("identifier", {}),
#                 arguments.get("update_fields", {})
#             )
#         elif tool_name == "delete_data_in_excel":
#             return await delete_data_in_excel(
#                 arguments.get("filepath", ""),
#                 arguments.get("sheet_name", ""),
#                 arguments.get("identifier", {})
#             )
#         else:
#             return f"Unknown tool: {tool_name}"
#     except Exception as e:
#         logger.error(f"Tool execution error: {str(e)}")
#         return f"Error executing tool: {str(e)}"

# async def query_stream_generator(user_input: str) -> str:
#     """Handle user query with tool routing"""
#     # Route the query
#     route_result = await unified_tool_router(user_input)
#     tool_name = route_result["tool_name"]
#     arguments = route_result["arguments"]
#     missing_args = route_result["missing_args"]
    
#     # Handle missing arguments
#     if missing_args:
#         return f"Missing arguments: {', '.join(missing_args)}. Please provide these details."
    
#     # Execute the tool
#     return await execute_tool_call(tool_name, arguments)

# # Example usage
# if __name__ == "__main__":
#     # Test different scenarios
#     print("Testing bookings read...")
#     bookings = asyncio.run(query_stream_generator("Show bookings for tomorrow"))
#     print(bookings)
    
#     print("\nTesting sales write...")
#     new_sale = asyncio.run(query_stream_generator(
#         "Record sale: 2 Lattes for $3.50 each today at 12:30"
#     ))
#     print(new_sale)
    
#     print("\nTest web search...")
#     web_search = asyncio.run(query_stream_generator("What is the capital of France?"))
#     print(web_search)
    
#     print("\nTest KG query...")
#     kg_query = asyncio.run(query_stream_generator("What are your vegan options?"))
#     print(kg_query)
    
#     print("\nTest missing arguments...")
#     missing_args_test = asyncio.run(query_stream_generator("Update booking time"))
#     print(missing_args_test)
    
#     print("\nTest booking update...")
#     booking_update = asyncio.run(query_stream_generator(
#         "Update booking BKG-001 to 20:00"
#     ))
#     print(booking_update)


import json
from openai import AsyncOpenAI
from typing import Dict, Any, List, Union
import uuid
import re
import asyncio
import os
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import pandas as pd
from openpyxl import load_workbook
from nexra.src.tools import response_tool
from runner import query_kg
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Dates and times
current_date = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M")
tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Constants
TOP_K = 5
LOCATION = "Bangalore"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY="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"
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# File paths
CAFE_DATA_PATH = os.path.join(os.getcwd(), "User")
os.makedirs(CAFE_DATA_PATH, exist_ok=True)
RESERVATIONS_FILE = f"{CAFE_DATA_PATH}/reservations.xlsx"
SALES_FILE = f"{CAFE_DATA_PATH}/sales.xlsx"
CAFE_NAME = os.getenv("NAME")

# Column definitions
RESERVATIONS_COLUMNS = [
    "Booking ID",    # str (UUID-based)
    "Customer Name", # str
    "Phone",         # str
    "Date",          # date (YYYY-MM-DD)
    "Time",          # str (HH:MM)
    "Party Size",    # int
    "Status",        # str
    "Notes"          # str
]

SALES_COLUMNS = [
    "Transaction ID", # str (UUID-based)
    "Date",           # date (YYYY-MM-DD)
    "Time",           # str (HH:MM)
    "Item ID",        # str
    "Item Name",      # str
    "Quantity",       # int
    "Unit Price",     # float
    "Total Price",    # float
    "Payment Method"  # str
]

# ─── SYSTEM_PROMPT ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""
        You are a routing assistant for {CAFE_NAME}. Today's date is {current_date}.
        Your ONLY task is to output JSON with these keys: tool_name, arguments, missing_args.

        STRICT RULES:
        1. Use tools ONLY for these cases:
        - perform_web_search: General knowledge (geography, history, science)
        - query_enterprise_kg: Cafe-specific questions (menu, hours, policies, vegan options)
        - Excel tools: ONLY for bookings/sales operations
        2. For Excel tools:
        - Use "bookings" for reservations
        - Use "sales" for transactions
        - Convert "today" to {current_date}, "tomorrow" to {tomorrow_date}
        3. If arguments are missing, list them in missing_args
        4. For NEW bookings/sales, ALWAYS use write_data_to_excel
        5. For EXISTING bookings/sales, use update_data_in_excel
        6. Always generate UUIDs for new Booking/Transaction IDs
        7. For data retrieval (show, list, get), ALWAYS use read_data_from_excel

        EXAMPLES:

        User: Show bookings for tomorrow
        Output:
        {{
        "tool_name": "read_data_from_excel",
        "arguments": {{
            "context": "bookings",
            "filter_criteria": {{"Date": "{tomorrow_date}"}}
        }},
        "missing_args": []
        }}

        User: Show booking for John Doe with phone 555-1234
        Output:
        {{
        "tool_name": "read_data_from_excel",
        "arguments": {{
            "context": "bookings",
            "filter_criteria": {{"Customer Name": "John Doe", "Phone": "555-1234"}}
        }},
        "missing_args": []
        }}

        User: Book a table for John Doe tomorrow at 19:00
        Output:
        {{
        "tool_name": "write_data_to_excel",
        "arguments": {{
            "context": "bookings",
            "data": [
            ["BKG-{str(uuid.uuid4())[:8]}", "John Doe", "555-1234", "{tomorrow_date}", "19:00", 4, "Confirmed", ""]
            ]
        }},
        "missing_args": []
        }}

        User: Update booking for John Doe to 20:00
        Output:
        {{
        "tool_name": "update_data_in_excel",
        "arguments": {{
            "context": "bookings",
            "identifier": {{"Customer Name": "John Doe", "Phone": "555-1234"}},
            "update_fields": {{"Time": "20:00"}}
        }},
        "missing_args": []
        }}

        User: Delete booking for John Doe
        Output:
        {{
        "tool_name": "delete_data_in_excel",
        "arguments": {{
            "context": "bookings",
            "identifier": {{"Customer Name": "John Doe", "Phone": "555-1234"}}
        }},
        "missing_args": []
        }}

        User: What vegan options do you have?
        Output:
        {{
        "tool_name": "query_enterprise_kg",
        "arguments": {{"query": "What vegan options do you have?"}},
        "missing_args": []
        }}

        User: Record sale: 2 Lattes for $3.50 each today at 12:30
        Output:
        {{
        "tool_name": "write_data_to_excel",
        "arguments": {{
            "context": "sales",
            "data": [
            ["TRX-{str(uuid.uuid4())[:8]}", "{current_date}", "12:30", "ITEM-001", "Latte", 2, 3.5, 7.0, "Cash"]
            ]
        }},
        "missing_args": []
        }}

        IMPORTANT: 
        - For greetings or general knowledge queries not needing a tool, ALWAYS return tool_name="answer_directly" and put your text reply into arguments.response.
        - For data retrieval (show, list, get), ALWAYS use read_data_from_excel
        - For NEW records, ALWAYS use write_data_to_excel
        - For EXISTING records, use update_data_in_excel
        - OUTPUT ONLY VALID JSON. DO NOT INCLUDE ANY OTHER TEXT.
"""

# ─── COLUMN → TYPE MAPPING ────────────────────────────────────────────────────────

def get_column_types(context: str) -> Dict[str, Any]:
    """
    Return a dict mapping column names to Python types (or parsing functions)
    for 'bookings' vs. 'sales'.
    """
    if context == "bookings":
        return {
            "Booking ID": str,
            "Customer Name": str,
            "Phone": str,
            "Date": lambda v: datetime.strptime(v, "%Y-%m-%d").date() if isinstance(v, str) else v,
            "Time": str,
            "Party Size": int,
            "Status": str,
            "Notes": str,
        }
    elif context == "sales":
        return {
            "Transaction ID": str,
            "Date": lambda v: datetime.strptime(v, "%Y-%m-%d").date() if isinstance(v, str) else v,
            "Time": str,
            "Item ID": str,
            "Item Name": str,
            "Quantity": int,
            "Unit Price": float,
            "Total Price": float,
            "Payment Method": str,
        }
    else:
        return {}

# ─── COMPARISON UTILITY ──────────────────────────────────────────────────────────

def compare_values(
    actual: Any,
    filter_value: Union[str, int, float, datetime.date],
    col_type: Any
) -> bool:
    """
    Compare a single cell (actual) against the filter_value.
    - If filter_value is a string starting with one of >, <, >=, <=, ==, do numeric/date comparison.
    - If col_type is str, do a case-insensitive equality (unless filter_value has a comparison).
    - Otherwise do a normal equality comparison after casting to col_type.
    """
    # 1) Check if filter_value is a string with a comparison operator prefix
    if isinstance(filter_value, str):
        match = re.match(r"^(>=|<=|>|<|==)\s*(.+)$", filter_value)
        if match:
            op, rhs_raw = match.groups()
            # Cast rhs_raw to appropriate type
            try:
                if col_type in (int, float):
                    rhs = col_type(rhs_raw)
                elif col_type == str:
                    rhs = rhs_raw.lower()
                elif callable(col_type) and col_type.__name__ == "<lambda>":
                    rhs = datetime.strptime(rhs_raw, "%Y-%m-%d").date()
                else:
                    rhs = rhs_raw
            except Exception:
                return False

            # Prepare left-hand value
            if actual is None:
                return False
            if col_type in (int, float):
                try:
                    left = float(actual)
                    right = float(rhs)
                except Exception:
                    return False
            elif col_type == str:
                left = str(actual).lower()
                right = str(rhs).lower()
            else:
                # date case
                if isinstance(actual, str):
                    try:
                        left = datetime.strptime(actual, "%Y-%m-%d").date()
                    except Exception:
                        return False
                else:
                    left = actual
                right = rhs

            # Perform comparison
            if op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "==":
                return left == right
            else:
                return False

        # 2) If column type is str and no operator, do case-insensitive equality
        if col_type == str:
            return str(actual).lower() == filter_value.lower()

    # 3) Otherwise, attempt strict equality after casting
    try:
        if col_type in (int, float):
            return float(actual) == float(filter_value)
        elif col_type == str:
            return str(actual).lower() == str(filter_value).lower()
        elif callable(col_type) and col_type.__name__ == "<lambda>":
            # date case
            if isinstance(actual, str):
                actual_date = datetime.strptime(actual, "%Y-%m-%d").date()
            else:
                actual_date = actual
            if isinstance(filter_value, str):
                target_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            else:
                target_date = filter_value
            return actual_date == target_date
        else:
            return actual == filter_value
    except Exception:
        return False

def apply_filters(
    data: List[Dict[str, Any]],
    filters: Dict[str, Any],
    context: str
) -> List[Dict[str, Any]]:
    """
    Apply the given filters to the data (list of row-dicts), using column types
    based on context ("bookings" or "sales").
    """
    if not filters:
        return data

    col_types = get_column_types(context)
    filtered_data = []

    for row in data:
        match_all = True
        for key, raw_filter_val in filters.items():
            # If the filter key isn't in our column mapping or in the row, no match
            if key not in col_types or key not in row:
                match_all = False
                break

            col_type = col_types[key]
            actual_val = row.get(key)

            if not compare_values(actual_val, raw_filter_val, col_type):
                match_all = False
                break

        if match_all:
            filtered_data.append(row)

    return filtered_data

# ─── ROUTING AND TOOL-RELATED FUNCTIONS ──────────────────────────────────────────

def map_context_to_file(context: str) -> Dict[str, Any]:
    """Map context ("bookings" or "sales") to file, sheet, and columns."""
    if context == "bookings":
        return {
            "filepath": RESERVATIONS_FILE,
            "sheet_name": "Bookings",
            "columns": RESERVATIONS_COLUMNS
        }
    elif context == "sales":
        return {
            "filepath": SALES_FILE,
            "sheet_name": "Transactions",
            "columns": SALES_COLUMNS
        }
    return {}



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

async def perform_web_search(query: str) -> str:
    """Simulated web search implementation."""
    logger.info(f"Performing web search: {query}")
    return await search_tool(query, TOP_K, LOCATION )

async def query_enterprise_kg(query: str) -> str:
    """Simulated knowledge graph response."""
    logger.info(f"Querying knowledge graph: {query}")
    return query_kg(query)

async def read_data_from_excel(
    filepath: str,
    sheet_name: str,
    filter_criteria: Dict[str, Any] = {},
    context: str = ""
) -> str:
    """
    Read data from Excel and apply filters via apply_filters().
    """
    logger.info(f"Reading data from {filepath} ({sheet_name}) with filters: {filter_criteria}")
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        data = df.replace({float("nan"): None}).to_dict(orient="records")

        if filter_criteria:
            filtered_data = apply_filters(data, filter_criteria, context)
        else:
            filtered_data = data
        print("+++++++++++++++++++++++++++++++=")
        print(json.dumps(filtered_data))
        print("+++++++++++++++++++++++++++++++=")
        return json.dumps(filtered_data)
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return f"Error reading data: {str(e)}"

async def write_data_to_excel(
    filepath: str,
    sheet_name: str,
    data: List[List[Any]],
    columns: List[str]
) -> str:
    """
    Append new rows to an existing Excel sheet or create it if missing.
    """
    try:
        new_df = pd.DataFrame(data, columns=columns)
        if os.path.exists(filepath):
            existing_df = pd.read_excel(filepath, sheet_name=sheet_name)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_excel(filepath, index=False, sheet_name=sheet_name)
        return "Data written successfully"
    except Exception as e:
        return f"Error writing data: {str(e)}"

async def update_data_in_excel(
    filepath: str,
    sheet_name: str,
    identifier: Dict[str, Any],
    update_fields: Dict[str, Any]
) -> str:
    """Update rows matching identifier with update_fields."""
    logger.info(f"Updating data in {filepath} ({sheet_name}) with identifier {identifier} and updates {update_fields}")
    try:
        book = load_workbook(filepath)
        sheet = book[sheet_name]

        headers = [cell.value for cell in sheet[1]]
        rows_to_update = []

        for row_idx in range(2, sheet.max_row + 1):
            match = True
            for key, value in identifier.items():
                if key in headers:
                    col_idx = headers.index(key) + 1
                    if str(sheet.cell(row=row_idx, column=col_idx).value) != str(value):
                        match = False
                        break
            if match:
                rows_to_update.append(row_idx)

        if not rows_to_update:
            return "No matching records found"

        for row_idx in rows_to_update:
            for key, value in update_fields.items():
                if key in headers:
                    col_idx = headers.index(key) + 1
                    sheet.cell(row=row_idx, column=col_idx, value=value)

        book.save(filepath)
        return "Data updated successfully"
    except Exception as e:
        logger.error(f"Error updating Excel: {str(e)}")
        return f"Error updating data: {str(e)}"

async def delete_data_in_excel(
    filepath: str,
    sheet_name: str,
    identifier: Dict[str, Any]
) -> str:
    """Delete rows matching identifier."""
    logger.info(f"Deleting data in {filepath} ({sheet_name}) with identifier {identifier}")
    try:
        book = load_workbook(filepath)
        sheet = book[sheet_name]

        headers = [cell.value for cell in sheet[1]]
        rows_to_delete = []

        for row_idx in range(2, sheet.max_row + 1):
            match = True
            for key, value in identifier.items():
                if key in headers:
                    col_idx = headers.index(key) + 1
                    if str(sheet.cell(row=row_idx, column=col_idx).value) != str(value):
                        match = False
                        break
            if match:
                rows_to_delete.append(row_idx)

        if not rows_to_delete:
            return "No matching records found"

        # Delete from bottom to top
        for row_idx in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(row_idx)

        book.save(filepath)
        return "Data deleted successfully"
    except Exception as e:
        logger.error(f"Error deleting from Excel: {str(e)}")
        return f"Error deleting data: {str(e)}"

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────────

def generate_booking_data(
    customer_name: str,
    phone: str,
    date: str,
    time: str,
    party_size: int
) -> List[List[Any]]:
    """Generate a new booking row."""
    return [[
        f"BKG-{str(uuid.uuid4())[:8]}",
        customer_name,
        phone,
        date,
        time,
        party_size,
        "Confirmed",
        ""
    ]]

def generate_sale_data(
    date: str,
    time: str,
    item_id: str,
    item_name: str,
    quantity: int,
    unit_price: float,
    total_price: float,
    payment_method: str
) -> List[List[Any]]:
    """Generate a new sale row."""
    return [[
        f"TRX-{str(uuid.uuid4())[:8]}",
        date,
        time,
        item_id,
        item_name,
        quantity,
        unit_price,
        total_price,
        payment_method
    ]]

# ─── TOOL EXECUTION ROUTER ───────────────────────────────────────────────────────

async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute the specified tool, passing along file, sheet, and context information
    for Excel operations. Handles special rerouting if an 'update' is actually a create.
    """
    logger.info(f"Executing {tool_name} with arguments: {arguments}")
    try:
        # If this is an Excel context, attach filepath/sheet/columns
        if "context" in arguments:
            context_config = map_context_to_file(arguments["context"])
            if context_config:
                arguments.update(context_config)

        # Special case: If user meant to create a booking but the router returned update_data_in_excel
        if tool_name == "update_data_in_excel" and arguments.get("context") == "bookings":
            if ("customer_name" in arguments) or ("Customer Name" in arguments.get("update_fields", {})):
                logger.warning("Rerouting booking creation to write_data_to_excel")
                customer_name = arguments.get("customer_name") or arguments.get("update_fields", {}).get("Customer Name", "")
                phone = arguments.get("phone") or arguments.get("update_fields", {}).get("Phone", "")
                date = arguments.get("date") or arguments.get("update_fields", {}).get("Date", "")
                time = arguments.get("time") or arguments.get("update_fields", {}).get("Time", "")
                party_size = arguments.get("party_size") or arguments.get("update_fields", {}).get("Party Size", 0)

                data = generate_booking_data(customer_name, phone, date, time, int(party_size))
                return await write_data_to_excel(
                    arguments.get("filepath", ""),
                    arguments.get("sheet_name", ""),
                    data,
                    columns=arguments.get("columns", [])
                )

        # Special case: If user meant to create a sale but the router returned update_data_in_excel
        if tool_name == "update_data_in_excel" and arguments.get("context") == "sales":
            if ("item_name" in arguments) or ("Item Name" in arguments.get("update_fields", {})):
                logger.warning("Rerouting sale creation to write_data_to_excel")
                date = arguments.get("date") or arguments.get("update_fields", {}).get("Date", "")
                time = arguments.get("time") or arguments.get("update_fields", {}).get("Time", "")
                item_id = arguments.get("item_id") or arguments.get("update_fields", {}).get("Item ID", "")
                item_name = arguments.get("item_name") or arguments.get("update_fields", {}).get("Item Name", "")
                quantity = arguments.get("quantity") or arguments.get("update_fields", {}).get("Quantity", 0)
                unit_price = arguments.get("unit_price") or arguments.get("update_fields", {}).get("Unit Price", 0)
                total_price = arguments.get("total_price") or arguments.get("update_fields", {}).get("Total Price", 0)
                payment_method = arguments.get("payment_method") or arguments.get("update_fields", {}).get("Payment Method", "")

                data = generate_sale_data(date, time, item_id, item_name, int(quantity), float(unit_price), float(total_price), payment_method)
                return await write_data_to_excel(
                    arguments.get("filepath", ""),
                    arguments.get("sheet_name", ""),
                    data,
                    columns=arguments.get("columns", [])
                )

        # Route to the correct function
        if tool_name == "perform_web_search":
            return await perform_web_search(arguments.get("query", ""))
        elif tool_name == "query_enterprise_kg":
            return await query_enterprise_kg(arguments.get("query", ""))
        elif tool_name == "read_data_from_excel":
            return await read_data_from_excel(
                arguments.get("filepath", ""),
                arguments.get("sheet_name", ""),
                arguments.get("filter_criteria", {}),
                arguments.get("context", "")
            )
        elif tool_name == "write_data_to_excel":
            return await write_data_to_excel(
                arguments.get("filepath", ""),
                arguments.get("sheet_name", ""),
                arguments.get("data", []),
                columns=arguments.get("columns", [])
            )
        elif tool_name == "update_data_in_excel":
            return await update_data_in_excel(
                arguments.get("filepath", ""),
                arguments.get("sheet_name", ""),
                arguments.get("identifier", {}),
                arguments.get("update_fields", {})
            )
        elif tool_name == "delete_data_in_excel":
            return await delete_data_in_excel(
                arguments.get("filepath", ""),
                arguments.get("sheet_name", ""),
                arguments.get("identifier", {})
            )
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return f"Error executing tool: {str(e)}"

async def unified_tool_router(user_query: str, conversation_history: List) -> Dict[str, Any]:
    """
    Route the incoming user query to the correct tool. Expects the LLM to return
    a JSON object with keys: tool_name, arguments, missing_args.
    """
    logger.info(f"Routing query: {user_query} with history: {len(conversation_history)} messages")
    print("=========================================================")
    print(conversation_history)
    # Build messages including conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add conversation history
    for msg in conversation_history:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    
    # Add current user query
    messages.append({"role": "user", "content": user_query})
    
    try:
        response = await ai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        # response = await ai_client.chat.completions.create(
        #     model=OPENAI_MODEL,
        #     messages=[
        #         {"role": "system", "content": SYSTEM_PROMPT},
        #         {"role": "user", "content": user_query}
        #     ],
        #     response_format={"type": "json_object"},
        #     temperature=0.0
        # )
        content = response.choices[0].message.content
        logger.info(f"LLM response: {content}")

        result = json.loads(content)
        if "tool_name" not in result:
            raise ValueError("Missing tool_name in response")

        return {
            "tool_name": result["tool_name"],
            "arguments": result.get("arguments", {}),
            "missing_args": result.get("missing_args", [])
        }
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON response from LLM")
        return {
            "tool_name": "query_enterprise_kg",
            "arguments": {"query": user_query},
            "missing_args": []
        }
    except Exception as e:
        logger.error(f"Routing error: {str(e)}")
        return {
            "tool_name": "query_enterprise_kg",
            "arguments": {"query": user_query},
            "missing_args": []
        }

async def query_stream_generator(user_input: str, conversation_history: List) -> str:
    """
    Accept a user query, route it, handle missing arguments, and execute the tool.
    """
    route_result = await unified_tool_router(user_input, conversation_history)
    tool_name = route_result["tool_name"]
    arguments = route_result["arguments"]
    missing_args = route_result["missing_args"]

    if missing_args:
        return f"Missing arguments: {', '.join(missing_args)}. Please provide these details."

    if tool_name == "answer_directly":
        return arguments.get("response", "")

    return await execute_tool_call(tool_name, arguments)

# ─── INITIALIZATION ──────────────────────────────────────────────────────────────

def initialize_excel_files():
    """
    Ensure that the Excel files for bookings and sales exist with the proper columns.
    """
    os.makedirs(CAFE_DATA_PATH, exist_ok=True)

    for context in ["bookings", "sales"]:
        config = map_context_to_file(context)
        if not os.path.exists(config["filepath"]):
            df = pd.DataFrame(columns=config["columns"])
            df.to_excel(config["filepath"], index=False, sheet_name=config["sheet_name"])
            logger.info(f"Created file: {config['filepath']} with sheet {config['sheet_name']}")


async def route_query(query: str, conversation_history: List = []) -> str:
    """
    Initialize files and then await the query_stream_generator coroutine.
    """
    initialize_excel_files()
    return await query_stream_generator(query, conversation_history)


# if __name__ == "__main__":
#     initialize_excel_files()

#     # Demo: Add 10 example bookings
#     print("\n===== 10 Bookings Demo =====")
#     for i in range(1, 11):
#         booking_query = (
#             f"Book table for Customer{i}, phone 555-000{i}, "
#             f"for tomorrow at {18 + (i % 4)}:00 for {2 + (i % 5)} people"
#         )
#         result = asyncio.run(query_stream_generator(booking_query))
#         print(f"Added booking {i}: {result}")

#     # Demo: Show bookings for tomorrow with party size > 4
#     print("\n===== Filter: Large Party Bookings =====")
#     filter_query = "Show bookings for tomorrow with party size > 4"
#     search_result = asyncio.run(query_stream_generator(filter_query))
#     print(f"Large party bookings:\n{search_result}")

#     # Demo: Update a booking
#     print("\n===== Update Booking Example =====")
#     update_query = "Update booking for Customer3 with phone 555-0003 to 19:30"
#     update_result = asyncio.run(query_stream_generator(update_query))
#     print(f"Update result: {update_result}")

#     # Verify the update
#     print("\n===== Verify Update =====")
#     verify_query = "Show booking for Customer3 with phone 555-0003"
#     verify_result = asyncio.run(query_stream_generator(verify_query))
#     print(f"Updated booking:\n{verify_result}")
