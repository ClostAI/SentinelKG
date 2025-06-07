#!/bin/sh
set -e

# 1) Ensure OpenAI key is set (or prompt interactively)
if [ -z "$OPENAI_API_KEY" ]; then
  echo "⚠️  OPENAI_API_KEY is not set."
  printf "Enter your OpenAI API key: "
  read -r OPENAI_API_KEY
  export OPENAI_API_KEY
fi

# 2) Start Go bridge (foreground prints QR)
echo "🔑 Starting WhatsApp bridge—please scan the QR code with your phone..."
whatsapp-bridge --store /data/store &

# Allow bridge to initialize and show QR
sleep 2

# 3) Launch Python MCP server
echo "🤖 Starting Python MCP server..."
exec /app/.venv/bin/python mcp_runner.py


#sudo docker build -t whatsapp-mcp-app:latest .
#sudo docker stop whatsapp-mcp
#sudo docker run -it   -e OPENAI_API_KEY="<your-openai-key-here>"   -v "$(pwd)/data/store:/data/store"   -p 8000:8000   whatsapp-mcp-app:latest