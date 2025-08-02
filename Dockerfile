FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    openjdk-11-jdk \
    maven \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads temp deployed_bots static logs

# Set permissions
RUN chmod +x deploy.sh

# Expose port
EXPOSE 8000

# Start the bot
CMD ["python", "main.py"]
