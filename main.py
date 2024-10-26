from fastapi import FastAPI, File, UploadFile, HTTPException
from pdfminer.high_level import extract_text
import pytesseract
from io import BytesIO
from PIL import Image
import os
import google.generativeai as genai
from typing import Dict

# Configure Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY is not set in the environment variables")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(debug=True)

# Ensure the 'resumes' directory exists
if not os.path.exists('resumes'):
    os.makedirs('resumes')

@app.get("/")
def read_root():
    return {"message": "Welcome to Resume Analyzer API!"}

# Function to call the Gemini API
def call_gemini_api(text: str) -> Dict:
    try:
        response = model.generate_content(text)
        return {"response_text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

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
