FROM python:3.9-slim

# Install FFMPEG (Required for Whisper AI) and git
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy App Code
COPY . .

# Create a dummy secrets file to silence Streamlit warning
RUN mkdir -p .streamlit && echo "" > .streamlit/secrets.toml

# --- THE FIX: RUN SEO INJECTOR ---
# This modifies the core Streamlit HTML files to include your keywords
RUN python seo_injector.py

# Expose Port 8080
EXPOSE 8080

# Launch App
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.enableWebsocketCompression=true"]