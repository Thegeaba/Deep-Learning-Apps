from fastapi import FastAPI
from pydantic import BaseModel
import requests
import base64

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pymongo import MongoClient
import random
import string
from datetime import datetime

from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
import shutil
import os
import io


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict it to specific domains)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (including POST)
    allow_headers=["*"],  # Allow all headers
)

client = MongoClient("mongodb://localhost:27017")
db = client["Dreambooth"]
images_collection = db["Images"]

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

IMAGES_FOLDER = 'images'
if not os.path.exists(IMAGES_FOLDER):
    os.makedirs(IMAGES_FOLDER)
app.mount("/images", StaticFiles(directory="images"), name="images")


@app.get("/")
async def root():
    return {"message": "API is running!"}

# Define the Pydantic model for input validation from the frontend
class GenerateRequest(BaseModel):
    prompt: str
    negativePrompt: str
    seed: int
    sampler_name: str
    steps: int
    cfg_scale: float
    width: int = 512
    height: int = 512

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    # Stable Diffusion API URL
    url = "http://127.0.0.1:7860"

    # Construct the payload for the txt2img API request
    print(request)
    payload = {
        "prompt": request.prompt,
        "negative_prompt": request.negativePrompt,
        "seed": request.seed,
        "sampler_name": request.sampler_name,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "width": request.width,
        "height": request.height,
    }

    try:
        # Make the POST request to the Stable Diffusion API
        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
        response.raise_for_status()
        r = response.json()

        # Decode the base64 image data
        image_data = base64.b64decode(r['images'][0])

        # Salvează imaginea în UPLOAD_FOLDER
        file_name = os.path.join(UPLOAD_FOLDER, "output.png")
        # file_name = os.path.join(UPLOAD_FOLDER, ''.join(random.choices(string.digits, k=8)) + ".png")
        with open(file_name, 'wb') as f:
            f.write(image_data)

        # Trimite imaginea la endpoint-ul de upload
        file = UploadFile(io.BytesIO(image_data), filename=file_name)

        # Apelează funcția de upload a imaginii
        upload_response = await upload_image(file)
        
        # Returnează imaginea ca base64 string și calea fișierului salvat
        return JSONResponse(content={
            "image": r['images'][0], 
            "file_info": upload_response, 
            "seed": request.seed
        })

    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
# Endpoint pentru încărcarea imaginilor
@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Generare nume de fișier aleatoriu cu extensia .png
        file_name = ''.join(random.choices(string.digits, k=8)) + ".png"
        file_location = f"{IMAGES_FOLDER}/{file_name}"
        
        # Salvează fișierul în folderul uploads
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Structura documentului pentru MongoDB
        image_document = {
            "filename": file_name,
            "file_path": file_location,
        }
        
        # Inserare document în colecția Images
        images_collection.insert_one(image_document)
        
        return {"info": f"File '{file_name}' uploaded successfully", "file_path": file_location}
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)



@app.get("/image-list")
def list_images():
    IMAGES_FOLDER = "C:/Users/crist/OneDrive/Desktop/Aplicatii ale deep learning pentru personalizarea generării de imagini/backend/images"
    files = os.listdir(IMAGES_FOLDER)
    image_files = [f"/images/{file}" for file in files if file.endswith(('png', 'jpg', 'jpeg', 'gif'))]
    return {"images": image_files}

"""
payload = {
    "prompt": "photo of zwx person as a samurai",
    "negative_prompt": "",
    "seed": -1,
    "sampler_name": "DPM++ 2M",
    "steps": 20,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
}
"""