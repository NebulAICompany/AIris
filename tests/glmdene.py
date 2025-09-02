import requests
import base64


# Resim dosyasını base64'e çevir
def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


SERVICE_URL = "YOUR-SERVICE-URL-HERE"  # Önceki adımdan aldığın URL

headers = {"Authorization": "Bearer test-key", "Content-Type": "application/json"}

# Test payload
payload = {
    "model": "glm-4.5v",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Bu resimde ne var?"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,BASE64-IMAGE-HERE"},
                },
            ],
        }
    ],
    "max_tokens": 500,
}

response = requests.post(
    f"{SERVICE_URL}/v1/chat/completions", headers=headers, json=payload
)
print(response.json())
