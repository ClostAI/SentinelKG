# import json
# import logging
# import warnings
# from sentence_transformers import SentenceTransformer
# import weaviate
# from weaviate.util import generate_uuid5
# from weaviate.classes.init import AdditionalConfig, Timeout
# from weaviate.auth import AuthClientPassword


# warnings.filterwarnings("ignore", category=ResourceWarning)
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# CLASS_NAME = "Nexra"

# def clean_json_string(raw_input):
#     """
#     Cleans a list-wrapped markdown-style JSON string by removing code fences and labels like 'json'.
#     """
#     if isinstance(raw_input, list):
#         raw_input = raw_input[0]
#     cleaned = raw_input.strip()
#     # Remove markdown code block markers and optional 'json' tag
#     if cleaned.startswith("```"):
#         cleaned = "\n".join(
#             line for line in cleaned.splitlines()
#             if not line.strip().startswith("```") and not line.strip().lower() == "json"
#         )
#     return cleaned



# # Load the embedding model
# EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
# def get_weaviate_client(
#     host="localhost", 
#     port=8081, 
#     grpc_port=50051,
#     user=None, 
#     password=None
# ):
#     auth = AuthClientPassword(user, password) if user and password else None
#     client = weaviate.connect_to_local(
#         host=host,
#         port=port,
#         grpc_port=grpc_port,
#         auth_credentials=auth,
#         additional_config=AdditionalConfig(timeout=Timeout(init=30))
#     )
#     if not client.is_ready():
#         raise RuntimeError("Weaviate is not ready")
#     return client

# CLIENT = get_weaviate_client()
# # Ensure the schema exists
# if not CLIENT.collections.exists(CLASS_NAME):
#     schema = {
#         "class": CLASS_NAME,
#         "vectorizer": "none",
#         "properties": [
#             {"name": "name", "dataType": ["string"]},
#             {"name": "attributes", "dataType": ["string"]},
#             {"name": "text", "dataType": ["text"]},
#         ]
#     }
#     CLIENT.collections.create_from_dict(schema)
#     logger.info(f"Created schema class '{CLASS_NAME}'")
# else:
#     logger.info(f"Schema class '{CLASS_NAME}' already exists")

# def parse_attributes(attr_str: str) -> dict:
#     """Parse the attributes string into a dictionary."""
#     attrs = {}
#     if not attr_str:
#         return attrs
#     parts = attr_str.split(", ")
#     for part in parts:
#         if ": " not in part:
#             continue
#         key, value = part.split(": ", 1)
#         attrs[key] = value
#     return attrs

# def get_object_by_id(client, class_name: str, uuid: str) -> dict:
#     path = f"/objects/{class_name}/{uuid}"
#     response = client._connection.get(path)

#     if response.status_code == 200:
#         return response.json()  # just return the full JSON object
#     elif response.status_code == 404:
#         return None
#     else:
#         raise Exception(f"Error retrieving object: {response.text}")


# def process_json_and_insert_in_weaviate(json_input: str | dict):
#     data = json.loads(json_input) if isinstance(json_input, str) else json_input
#     extractions = data.get("extractions", [])
#     if not extractions:
#         logger.warning("No extractions found.")
#         return

#     collection = CLIENT.collections.get(CLASS_NAME)
#     inserted = 0
#     skipped = 0
#     updated = 0

#     insert_records = []
#     update_records = []

#     for item in extractions:
#         entity = item.get("entity", "").strip()
#         if not entity:
#             continue
#         new_attrs = item.get("attributes", {})
#         uid = generate_uuid5(entity)

#         # Check if the entity exists
#         if collection.data.exists(uuid=uid):
#             # Retrieve the existing object via a direct REST call
#             existing_obj = get_object_by_id(CLIENT, CLASS_NAME, uid)
#             if not existing_obj:
#                 logger.warning(f"Expected existing object for entity '{entity}' not found.")
#                 continue
#             properties = existing_obj.get("properties", {})
#             existing_attrs_str = properties.get("attributes", "")
#             existing_attrs = parse_attributes(existing_attrs_str)

#             # If the attributes are the same, skip this entity
#             if existing_attrs == new_attrs:
#                 skipped += 1
#                 logger.info(f"Skipping duplicate entity: {entity}")
#                 continue
#             else:
#                 # Merge attributes: new attributes override existing ones
#                 merged_attrs = {**existing_attrs, **new_attrs}
#                 merged_attr_text = ", ".join(f"{k}: {v}" for k, v in merged_attrs.items())
#                 merged_text_repr = f"{entity} — {merged_attr_text}" if merged_attr_text else entity
#                 new_embedding = EMBED_MODEL.encode(merged_text_repr, convert_to_numpy=True)
#                 update_records.append({
#                     "uuid": uid,
#                     "properties": {
#                         "name": entity,
#                         "attributes": merged_attr_text,
#                         "text": merged_text_repr
#                     },
#                     "vector": new_embedding.tolist()
#                 })
#         else:
#             attr_text = ", ".join(f"{k}: {v}" for k, v in new_attrs.items())
#             text_repr = f"{entity} — {attr_text}" if attr_text else entity
#             embedding = EMBED_MODEL.encode(text_repr, convert_to_numpy=True)
#             insert_records.append({
#                 "uuid": uid,
#                 "properties": {
#                     "name": entity,
#                     "attributes": attr_text,
#                     "text": text_repr
#                 },
#                 "vector": embedding.tolist()
#             })

#     # Batch insert new entities
#     if insert_records:
#         with collection.batch.dynamic() as batch:
#             for rec in insert_records:
#                 batch.add_object(
#                     properties=rec["properties"],
#                     uuid=rec["uuid"],
#                     vector=rec["vector"]
#                 )
#         inserted = len(insert_records)
#         logger.info(f"Inserted {inserted} new entities.")

#     # Update existing entities with merged attributes
#     if update_records:
#         for rec in update_records:
#             collection.data.update(
#                 uuid=rec["uuid"],
#                 properties=rec["properties"],
#                 vector=rec["vector"]
#             )
#         updated = len(update_records)
#         logger.info(f"Updated {updated} existing entities.")

#     logger.info(f"Completed: {inserted} inserted, {updated} updated, {skipped} skipped.")

# def search_entities(query: str, top_k: int = 5):
#     q_vec = EMBED_MODEL.encode([query], convert_to_numpy=True)[0]
#     collection = CLIENT.collections.get(CLASS_NAME)
#     response = collection.query.near_vector(
#         near_vector=q_vec.tolist(),
#         limit=top_k,
#         return_properties=["name", "attributes", "text"],
#         return_metadata=["distance"]
#     )
#     results = []
#     for obj in response.objects:
#         props = obj.properties
#         results.append({
#             "name": props["name"],
#             "attributes": props["attributes"],
#             "text": props["text"],
#             "distance": obj.metadata.distance
#         })
#     return results


# def store_db_utils(entry_record):
#     record = entry_record #clean_json_string(entry_record) 
#     process_json_and_insert_in_weaviate(record)

# def find_record(query, top_k):
#     matches = search_entities(query, top_k=3)
#     matches = []
#     for m in matches:
#         record = {
#             "entity":{m['name']},
#             "attr" : {m['attributes']}
#         }
#         matches.append(record)
#     return matches


import json
import warnings
import logging
from sentence_transformers import SentenceTransformer
import weaviate
import os
from weaviate.auth import AuthClientPassword
from weaviate.classes.init import AdditionalConfig, Timeout
from uuid import uuid5, NAMESPACE_DNS

# Set up warnings and logging
warnings.filterwarnings("ignore", category=ResourceWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
CLASS_NAME = "Nexra"

def clean_json_string(raw_input):
    """
    Cleans a list-wrapped markdown-style JSON string by removing code fences and labels like 'json'.
    """
    if isinstance(raw_input, list):
        raw_input = raw_input[0]
    cleaned = raw_input.strip()
    # Remove markdown code block markers and optional 'json' tag
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines()
            if not line.strip().startswith("```") and not line.strip().lower() == "json"
        )
    return cleaned

# Load the embedding model
EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def generate_uuid5(name: str) -> str:
    # Generate a UUID5 using a fixed namespace.
    return str(uuid5(NAMESPACE_DNS, name))

def get_weaviate_client(
    host=None, 
    port=None, 
    grpc_port=50051,
    user=None, 
    password=None
):
    # Pull from env if not explicitly passed
    host = host or os.getenv("WEAVIATE_HOST", "weaviate")
    port = int(port or os.getenv("WEAVIATE_PORT", 8085))
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", grpc_port))
    user = user or os.getenv("WEAVIATE_USER")
    password = password or os.getenv("WEAVIATE_PASSWORD")

    auth = AuthClientPassword(user, password) if user and password else None
    client = weaviate.connect_to_local(
        host=host,
        port=port,
        grpc_port=grpc_port,
        auth_credentials=auth,
        additional_config=AdditionalConfig(timeout=Timeout(init=30))
    )
    if not client.is_ready():
        raise RuntimeError("Weaviate is not ready")
    return client

CLIENT = get_weaviate_client()

# Ensure the schema exists (adding place_details field)
if not CLIENT.collections.exists(CLASS_NAME):
    schema = {
        "class": CLASS_NAME,
        "vectorizer": "none",
        "properties": [
            {"name": "name", "dataType": ["string"]},
            {"name": "attributes", "dataType": ["string"]},
            {"name": "text", "dataType": ["text"]},
            {"name": "place_details", "dataType": ["text"]}  # new property
        ]
    }
    CLIENT.collections.create_from_dict(schema)
    logger.info(f"Created schema class '{CLASS_NAME}'")
else:
    logger.info(f"Schema class '{CLASS_NAME}' already exists")

def parse_attributes(attr_str: str) -> dict:
    """Parse the attributes string into a dictionary."""
    attrs = {}
    if not attr_str:
        return attrs
    parts = attr_str.split(", ")
    for part in parts:
        if ": " not in part:
            continue
        key, value = part.split(": ", 1)
        attrs[key] = value
    return attrs

def get_object_by_id(client, class_name: str, uuid: str) -> dict:
    path = f"/objects/{class_name}/{uuid}"
    response = client._connection.get(path)

    if response.status_code == 200:
        return response.json()  # return the full JSON object
    elif response.status_code == 404:
        return None
    else:
        raise Exception(f"Error retrieving object: {response.text}")

def to_dict(obj):
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(elem) for elem in obj]
    else:
        return obj


def escape_backslashes(obj):
    if isinstance(obj, str):
        return obj.replace("\\", "\\\\")
    elif isinstance(obj, dict):
        return {k: escape_backslashes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [escape_backslashes(elem) for elem in obj]
    return obj

def process_json_and_insert_in_weaviate(json_input: str | dict):
    data = json.loads(json_input) if isinstance(json_input, str) else json_input
    data = to_dict(data)
    extractions = data.get("extractions", [])
    if not extractions:
        logger.warning("No extractions found.")
        return

    collection = CLIENT.collections.get(CLASS_NAME)
    inserted = 0
    skipped = 0
    updated = 0
    insert_records = []
    update_records = []
    for item in extractions:
        entity = item.get("entity", "").strip()
        if not entity:
            continue
        new_attrs = item.get("attributes", {})
        import re
        # Check and serialize place_details if provided
        raw_place_details = item.get("place_details")
        if isinstance(raw_place_details, str):
            raw_place_details = re.sub(r',(\s*[}\]])', r'\1', raw_place_details)
            try:
                place_details_obj = json.loads(raw_place_details)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse place_details: {raw_place_details}")
                raise e
        else:
            place_details_obj = raw_place_details

        place_details_text = json.dumps(place_details_obj) if place_details_obj else ""
        uid = generate_uuid5(entity)
        # Check if the entity exists
        if collection.data.exists(uuid=uid):
            existing_obj = get_object_by_id(CLIENT, CLASS_NAME, uid)
            if not existing_obj:
                logger.warning(f"Expected existing object for entity '{entity}' not found.")
                continue
            properties = existing_obj.get("properties", {})
            existing_attrs_str = properties.get("attributes", "")
            existing_attrs = parse_attributes(existing_attrs_str)
            # Compare attributes
            if existing_attrs == new_attrs:
                skipped += 1
                logger.info(f"Skipping duplicate entity: {entity}")
                continue
            else:
                # Merge attributes: new attributes override existing ones
                merged_attrs = {**existing_attrs, **new_attrs}
                merged_attr_text = ", ".join(f"{k}: {v}" for k, v in merged_attrs.items())
                merged_text_repr = f"{entity} — {merged_attr_text}" if merged_attr_text else entity
                new_embedding = EMBED_MODEL.encode(merged_text_repr, convert_to_numpy=True)
                update_records.append({
                    "uuid": uid,
                    "properties": {
                        "name": entity,
                        "attributes": merged_attr_text,
                        "text": merged_text_repr,
                        "place_details": place_details_text or properties.get("place_details", "")
                    },
                    "vector": new_embedding.tolist()
                })
        else:
            attr_text = ", ".join(f"{k}: {v}" for k, v in new_attrs.items())
            text_repr = f"{entity} — {attr_text}" if attr_text else entity
            embedding = EMBED_MODEL.encode(text_repr, convert_to_numpy=True)
            insert_records.append({
                "uuid": uid,
                "properties": {
                    "name": entity,
                    "attributes": attr_text,
                    "text": text_repr,
                    "place_details": place_details_text
                },
                "vector": embedding.tolist()
            })
    # Batch insert new entities
    if insert_records:
        with collection.batch.dynamic() as batch:
            for rec in insert_records:
                batch.add_object(
                    properties=rec["properties"],
                    uuid=rec["uuid"],
                    vector=rec["vector"]
                )
        inserted = len(insert_records)
        logger.info(f"Inserted {inserted} new entities.")

    # Update existing entities with merged attributes and place_details
    if update_records:
        for rec in update_records:
            collection.data.update(
                uuid=rec["uuid"],
                properties=rec["properties"],
                vector=rec["vector"]
            )
        updated = len(update_records)
        logger.info(f"Updated {updated} existing entities.")

    logger.info(f"Completed: {inserted} inserted, {updated} updated, {skipped} skipped.")

def search_entities(query: str, top_k: int = 5):
    q_vec = EMBED_MODEL.encode([query], convert_to_numpy=True)[0]
    collection = CLIENT.collections.get(CLASS_NAME)
    response = collection.query.near_vector(
        near_vector=q_vec.tolist(),
        limit=top_k,
        return_properties=["name", "attributes", "text", "place_details"],
        return_metadata=["distance"]
    )
    results = []
    for obj in response.objects:
        props = obj.properties
        results.append({
            "name": props.get("name", ""),
            "attributes": props.get("attributes", ""),
            "text": props.get("text", ""),
            "place_details": props.get("place_details", ""),
            "distance": obj.metadata.distance
        })
    return results

def store_db_utils(entry_record):
    record = entry_record  # or use clean_json_string(entry_record)
    process_json_and_insert_in_weaviate(record)

def find_record(query, top_k):
    matches = search_entities(query, top_k=top_k)
    records = []
    for m in matches:
        record = {
            "entity": m['name'],
            "attr": m['attributes'],
            "place_details": m.get('place_details', "")
        }
        records.append(record)
    return records