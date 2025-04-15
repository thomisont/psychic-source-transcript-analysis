import os
import requests
import sys

# Force output to stderr to debug
sys.stderr.write("Script started\n")
sys.stderr.flush()

voice_id = "XfNU2rGpBa01ckF309OY"  # Nichalia Schwartz voice ID
text = "Hello Lilly here with your operational status report"
api_key = "598b1e922a4b3e935358db0dba288663"  # From Get_User_Info response

sys.stderr.write(f"API Key used: {api_key}\n")
sys.stderr.flush()

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
sys.stderr.write(f"URL: {url}\n")
sys.stderr.flush()

headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json"
}

data = {
    "text": text,
    "model_id": "eleven_turbo_v2",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}

sys.stderr.write("Sending request to ElevenLabs API...\n")
sys.stderr.flush()
try:
    response = requests.post(url, json=data, headers=headers)
    sys.stderr.write(f"Response status code: {response.status_code}\n")
    sys.stderr.flush()
    
    if response.status_code == 200:
        # Save the audio file
        with open("lilly_status_report_nichalia.mp3", "wb") as f:
            f.write(response.content)
        sys.stderr.write("Audio file saved as lilly_status_report_nichalia.mp3\n")
        sys.stderr.flush()
    else:
        sys.stderr.write(f"Error: {response.status_code}\n")
        sys.stderr.write(f"{response.text}\n")
        sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"Exception occurred: {e}\n")
    sys.stderr.flush()

sys.stderr.write("Script completed\n")
sys.stderr.flush() 