FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip curl
RUN pip3 install -U vllm --pre --extra-index-url https://wheels.vllm.ai/nightly
RUN pip3 install transformers-v4.55.0-GLM-4.5V-preview

WORKDIR /app
COPY start.py /app/

# Temp directory for video processing
RUN mkdir -p /tmp/media

EXPOSE 8000
CMD ["python3", "start.py"]
