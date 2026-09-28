import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set in environment or .env")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
    contents="what is dyslexia",
)

print(response.text)