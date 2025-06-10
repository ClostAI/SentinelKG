FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Install system deps for Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    poppler-utils \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libsm6 \
    libxrender-dev \
  && rm -rf /var/lib/apt/lists/*

# 2. Install Playwright and browsers
RUN pip install playwright
RUN playwright install

WORKDIR /app

# 3. Install Python dependencies, including docker SDK
COPY requirements.txt .
# Ensure requirements.txt includes: docker
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt  # :contentReference[oaicite:7]{index=7}

# Install Docker CLI via Debian repo (older) or Docker’s official repo
RUN apt-get update && apt-get install -y docker.io
RUN apt-get update && apt-get install -y curl

RUN curl -SL https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose

# Set permissions
RUN chmod +x /usr/local/bin/docker-compose

# Verify installation
RUN docker-compose --version
# or for newer CLI:
# RUN apt-get update && apt-get install -y \
#     ca-certificates curl gnupg lsb-release \
#   && mkdir -p /etc/apt/keyrings \
#   && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
#   && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
#         > /etc/apt/sources.list.d/docker.list \
#   && apt-get update && apt-get install -y docker-ce-cli docker-compose-plugin


# 4. Copy application code
RUN pip install -q -U google-generativeai
COPY . .
RUN export EXCEL_FILES_PATH=/home/clostinfra/clost/SentinelKG/User && echo $EXCEL_FILES_PATH

EXPOSE 8000

CMD ["uvicorn", "clost_web_server_markdown:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]

