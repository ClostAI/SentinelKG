## Start Docker:

sudo docker compose up --build

## Start whatsa-app MCP:
wget http://localhost:8000/whatsapp/start

## Initialize KG:
curl -X POST http://localhost:8000/initialize\
     -H "Content-Type: application/json" \
     -d '{
           "urls": [
                  
             "https://sarposhfoods.com"
           ]
         }'
