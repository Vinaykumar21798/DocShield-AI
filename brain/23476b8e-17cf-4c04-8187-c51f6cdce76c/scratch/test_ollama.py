import os
from ollama import Client

ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client = Client(host=ollama_host)

# Test prompt from qwen_detector.py
prompt = """You are a senior clinical and PII/PHI information extraction assistant.
Extract all PII and PHI entities from the input text below.
Use ONLY the following entity categories:
- PERSON
- LOCATION

Return EXACTLY this JSON schema:
{
    "results": [
        {
            "entity_type": "PERSON",
            "entity_value": "John Doe",
            "confidence_score": 0.90,
            "start_char": 15,
            "end_char": 23
        }
    ]
}

Strictly ensure start_char and end_char indices represent the exact 0-indexed boundaries in the input text.
Return ONLY valid JSON. No reasoning, no markdown wrappers, no explanation.

Input Text:
The patient John Smith was seen at Boston Clinic.
"""

try:
    print("Sending real prompt to client.chat...")
    response = client.chat(
        model="qwen3:4b",
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={
            "temperature": 0.10,
            "top_p": 0.90,
            "num_predict": 256,
        },
        keep_alive="5m",
    )
    print("Response type:", type(response))
    print("Response object:", response)
    
    # Try dictionary-style access
    try:
        dict_val = response["message"]["content"]
        print("Dictionary access response['message']['content'] succeeded:", repr(dict_val))
    except Exception as e:
        print("Dictionary access failed:", type(e), e)
        
    # Try object attribute-style access
    try:
        obj_val = response.message.content
        print("Object attribute access response.message.content succeeded:", repr(obj_val))
    except Exception as e:
        print("Object attribute access failed:", type(e), e)
        
except Exception as e:
    print("Error during test run:", e)
