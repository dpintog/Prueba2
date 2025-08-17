import google.generativeai as genai
from backend.config import settings

def get_gemini_client():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai
