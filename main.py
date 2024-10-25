from fastapi import FastAPI, File, UploadFile, HTTPException
from pdfminer.high_level import extract_text
import pytesseract
from io import BytesIO
from PIL import Image
import os
import requests
import nltk
from typing import Dict

# Define the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if stopwords corpus is already downloaded, if not, download it
try:
    nltk.data.find('corpora/stopwords.zip')
except LookupError:
    nltk.download('stopwords')

app = FastAPI(debug=True)

# Ensure the 'resumes' directory exists
if not os.path.exists('resumes'):
    os.makedirs('resumes')

@app.get("/")
def read_root():
    return {"message": "Welcome to Resume Analyzer API!"}

# Function to call the Gemini API
def call_gemini_api(text: str) -> Dict:
    url = "https://gemini.api.flashmodel.com/v1/analyze"
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": text,
        "max_tokens": 500,
        "temperature": 0.7,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {response.text}")

    return response.json()

# Endpoint to upload and parse a resume
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)) -> Dict:
    # Check for valid file types
    if file.content_type not in [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF or Word files are accepted.")
    
    file_location = f"resumes/{file.filename}"

    try:
        # Save uploaded file to 'resumes' directory
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())

        # Extract text based on file type
        if file.content_type == "application/pdf":
            text = extract_text(file_location)
        elif file.content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            text = extract_text_from_word(file_location)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        # Call the Gemini API with the extracted text
        response = call_gemini_api(text)

        # Clean up the saved file after extraction
        os.remove(file_location)

        return {"gemini_response": response}

    except Exception as e:
        # Log and re-raise the exception with details
        print(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Function to parse text from Word files
def extract_text_from_word(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from Word file: {str(e)}")

# Function to parse text from PDFs (this can be used for further functionalities)
def extract_text_from_pdf(file: UploadFile) -> str:
    try:
        file_bytes = file.file.read()
        file_stream = BytesIO(file_bytes)
        pdf_text = extract_text(file_stream)
        return pdf_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")

# Function to parse text from images using OCR (Optional for future)
def extract_text_from_image(file: UploadFile) -> str:
    try:
        image = Image.open(BytesIO(file.file.read()))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from image: {str(e)}")
