"""
Quick test script to check Gemini API and list available models
"""
import os
import google.generativeai as genai

# Load API key
api_key = "AIzaSyAvbh6TwFylPizhnXIIrRTauoJ1mG6291s"

print("Testing Gemini API Connection...")
print(f"API Key: {api_key[:20]}...")

try:
    genai.configure(api_key=api_key)
    
    print("\n✅ API Key configured successfully!")
    
    print("\n📋 Available Models:")
    print("-" * 60)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✓ {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description}")
            print(f"  Input Token Limit: {model.input_token_limit}")
            print(f"  Output Token Limit: {model.output_token_limit}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
