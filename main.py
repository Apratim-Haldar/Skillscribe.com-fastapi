from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

from dotenv import load_dotenv

import openai
import os
import json
import requests

load_dotenv()

openai.api_key = os.getenv("OPEN_AI_KEY")
openai.organization = os.getenv("OPEN_AI_ORG")
elevenlabs_key = os.getenv("ELEVENLABS_KEY")

app = FastAPI()

origins = [
    "http://localhost:5174",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://skillscribe-com.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/talk")
async def post_audio(
    file: UploadFile,
    interview_topic: str = Query(..., title="Interview Topic", description="The topic of the interview")
):
    user_message = transcribe_audio(file)
    chat_response = get_chat_response(user_message, interview_topic)
    audio_output = text_to_speech(chat_response)

    async def audio_stream():
        yield audio_output

    return StreamingResponse(audio_stream(), media_type="audio/mpeg")
@app.get("/clear")
async def clear_history():
    file = 'database.json'
    open(file, 'w')
    return {"message": "Chat history has been cleared"}

# Functions
def transcribe_audio(file):
    # Save the blob first
    with open(file.filename, 'wb') as buffer:
        buffer.write(file.file.read())
    audio_file = open(file.filename, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    print(transcript)
    return transcript

def get_chat_response(user_message, interview_topic):
    messages = load_messages(interview_topic)
    messages.append({"role": "user", "content": user_message['text']})

    # Send to ChatGpt/OpenAi
    gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    parsed_gpt_response = gpt_response['choices'][0]['message']['content']

    # Save messages
    save_messages(user_message['text'], parsed_gpt_response, interview_topic)
    return parsed_gpt_response

def load_messages(interview_topic):
    messages = []
    file = 'database.json'

    empty = os.stat(file).st_size == 0

    if not empty:
        with open(file) as db_file:
            data = json.load(db_file)
            for item in data:
                messages.append(item)
    else:
        # Generate dynamic system content based on the interview topic
        system_content = f"You are interviewing the user for a {interview_topic} position. Ask short questions that are relevant to a junior level developer. Your name is Greg. The user is Travis. Keep responses under 30 words and be funny sometimes."

        messages.append({"role": "system", "content": system_content})

    return messages


def save_messages(user_message, gpt_response, interview_topic):
    file = 'database.json'
    messages = load_messages(interview_topic)
    messages.append({"role": "user", "content": user_message})
    messages.append({"role": "assistant", "content": gpt_response})
    with open(file, 'w') as f:
        json.dump(messages, f)

def text_to_speech(text):
    voice_id = 'oCrq2rImpPsxuDKWkxVI'
    
    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0,
            "style": 0.5,
            "use_speaker_boost": True
        }
    }

    headers = {
        "Content-Type": "application/json",
        "accept": "audio/mpeg",
        "xi-api-key": elevenlabs_key
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    try:
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200 and response.content is not None:
            return response.content
        else:
            print(f'Something went wrong. Status Code: {response.status_code}')
            print(f'Something went wrong: {response}')

    except Exception as e:
        print(f'Error during text-to-speech conversion: {e}')

    # Return a default value if there's an issue
    return b''  # An empty bytes object
    

#1. Send in audio, and have it transcribed
#2. We want to send it to chatgpt and get a response
#3. We want to save the chat history to send back and forth for context.

