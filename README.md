## Start Docker:
<img width="1305" alt="Screenshot 2025-06-11 at 11 11 01 AM" src="https://github.com/user-attachments/assets/587ca116-b6a8-4107-bee1-e9aff824d394" />


sudo docker compose up --build

## Start whatsa-app MCP:
wget http://localhost:8000/whatsapp/start

## Initialize KG:
<code>
curl -X POST http://localhost:8000/initialize \
     -H "Content-Type: application/json" \
     -d '{
           "urls": [
             "https://sarposhfoods.com"
           ]
         }'
</code>

## Call from chat
curl -N "http://localhost:8000/stream?query=hello&bot=agni&top_k=5&session_id=test123"
