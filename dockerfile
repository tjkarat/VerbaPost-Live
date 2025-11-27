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

# --- THE FIX: Create a dummy secrets file to silence Streamlit error ---
RUN mkdir -p .streamlit && echo "" > .streamlit/secrets.toml

# Expose Port 8080
EXPOSE 8080

# Launch App
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]