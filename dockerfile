# Use a slim Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required by playwright and others
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

# Install dependencies including playwright
RUN pip install playwright

# Download the required browser binaries
RUN playwright install

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
RUN pip install -q -U google-generativeai
COPY . .

# Expose port 8000
EXPOSE 8000

# Run the application using uvicorn
CMD ["uvicorn", "clost_web_server_markdown:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
