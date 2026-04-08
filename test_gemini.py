import os
import yaml
import asyncio
from google import genai
from google.genai import types

async def test_gemini():
    try:
        # Load API key from config
        with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        api_key = config.get("gemini_api_key")
        print(f"API Key loaded: {api_key[:10]}...")
        
        # Initialize Client
        client = genai.Client(api_key=api_key)
        
        print("Testing model generation...")
        prompt = "Hello, what model are you?"
        
        print("Testing model generation...")
        prompt = "Hello, what model are you?"
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        
        print("Success! Gemini response:")
        print(response.text)
        
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
