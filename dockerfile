FROM python:3.10-slim

# Install System Dependencies (for PDF/Fonts/Audio)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python Dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy Code
COPY . .

# Expose Port
EXPOSE 8080

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run Streamlit
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]
