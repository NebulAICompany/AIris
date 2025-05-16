FROM python:3.9-slim-buster

# Install Java (OpenJDK 11) for Zemberek
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-11-jre && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set Java environment variables
ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy all project files (including zemberek-full.jar)
COPY . .

# Expose port 8000
EXPOSE 8000

# Start the application with Uvicorn
CMD ["uvicorn", "aiiris_backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]