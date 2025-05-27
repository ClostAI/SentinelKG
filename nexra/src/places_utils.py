import os
from dotenv import load_dotenv
import logging
import json 
import googlemaps
import difflib
logging.basicConfig( level=logging.ERROR)
logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_place_details(entity, query: str, area: str):
    """
    Tool to fetch details for each cafe and update the JSON data.
    """
    API_KEY = GOOGLE_API_KEY  # make sure this is defined
    data = entity
    try:
        gmaps = googlemaps.Client(key=API_KEY)
    except Exception as e:
        logger.error("Error initializing Google Maps client: %s", e)
        return {"error": "Failed to initialize Google Maps client."}
    
    for extraction in data.get("extractions", []):
        try:
            name = extraction.get('entity')
            if not name:
                logger.error("Entity entry missing name. Skipping entry.")
                continue

            input_text = f"{name} {area}"
            try:
                find_response = gmaps.find_place(
                    input=input_text,
                    input_type="textquery",
                    fields=["place_id"]
                )
            except Exception as e:
                logger.error("Error during find_place for %s: %s", name, e)
                continue

            if find_response.get('status') != "OK" or not find_response.get("candidates"):
                logger.error("No candidate found for %s (%s)", name, query)
                continue

            place_id = find_response["candidates"][0].get("place_id")
            try:
                details_response = gmaps.place(
                    place_id=place_id,
                    fields=[
                        "name",
                        "formatted_address",
                        "photo",
                        "opening_hours",
                        "price_level",
                        "rating",
                        "formatted_phone_number",
                        "geometry"
                    ]
                )
            except Exception as e:
                logger.error("Error during place details fetch for %s: %s", name, e)
                continue

            if details_response.get('status') != "OK":
                logger.error("Error fetching details for %s (%s): %s", name, query, details_response.get('status'))
                continue

            details = details_response.get("result", {})
            cutoff = 0.6

            # Check if the name in details roughly matches the cafe's name.
            if details.get("name") and difflib.SequenceMatcher(None, details.get("name").lower(), name.lower()).ratio() < cutoff:
                continue

            # Normalize opening hours if available.
            if "opening_hours" in details and "weekday_text" in details["opening_hours"]:
                details["opening_hours"] = details["opening_hours"]["weekday_text"]

            # Process photos.
            photos = details.get("photos", [])
            photo_urls = []
            for photo in photos:
                photo_ref = photo.get("photo_reference")
                if photo_ref:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={API_KEY}"
                    photo_urls.append(photo_url)
                else:
                    logger.error("Missing photo_reference in photo for %s", name)
            details["photo_urls"] = photo_urls
            details["photos"] = ""  # Clear original photos field if not needed.

            # Extract geometry information.
            geometry = details.get("geometry", {})
            if geometry:
                location = geometry.get("location", {})
                details["lat"] = location.get("lat")
                details["lon"] = location.get("lng")
            
            # Update the cafe's entry with the fetched details.
            extraction['place_details'] = details
        except Exception as e:
            logger.error("Error processing cafe %s: %s", entity.get("name", "Unknown"), e)
            continue
    output_path = os.path.join(os.getcwd(), 'nexra/src/tmp/response_places.json')
    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Error writing JSON to file (%s): %s", output_path, e)
    return json.dumps(data, indent=2)