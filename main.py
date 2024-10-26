from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from pdfminer.high_level import extract_text
import pytesseract
from io import BytesIO
from PIL import Image
import os
import google.generativeai as genai

# Configure Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY is not set in the environment variables")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(debug=True)

# Ensure the 'resumes' and 'job_descriptions' directories exist
if not os.path.exists('resumes'):
    os.makedirs('resumes')
if not os.path.exists('job_descriptions'):
    os.makedirs('job_descriptions')

# Data model for Job Description
class JobDescription(BaseModel):
    job_title: str
    description: str

# Store job descriptions in memory (for simplicity; can be extended to a database)
job_descriptions_store: List[JobDescription] = []

@app.get("/")
def read_root():
    """
    Root endpoint to check if API is running.
    """
    return {"message": "Welcome to Resume Analyzer and Job Matcher API!"}

# Function to call the Gemini API
def call_gemini_api(text: str) -> Dict:
    """
    Calls the Gemini API with extracted text from the resume.
    
    Parameters:
    - text (str): The text extracted from the resume file.
    
    Returns:
    - Dict: The response from Gemini API.
    """
    try:
        response = model.generate_content(text)
        return {"response_text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

# Endpoint to upload and parse a resume
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)) -> Dict:
    """
    Endpoint to upload a resume and get analysis from Gemini API.
    
    Parameters:
    - file (UploadFile): The resume file uploaded by the user.
    
    Returns:
    - Dict: The response from Gemini API with resume analysis.
    """
    if file.content_type not in [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF or Word files are accepted.")
    
    file_location = f"resumes/{file.filename}"

    try:
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())

        if file.content_type == "application/pdf":
            text = extract_text(file_location)
        elif file.content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            text = extract_text_from_word(file_location)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        response = call_gemini_api(text)
        os.remove(file_location)
        return {"gemini_response": response}

    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Function to parse text from Word files
def extract_text_from_word(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from Word file: {str(e)}")

# Endpoint to upload job descriptions
@app.post("/upload-job-descriptions/")
async def upload_job_descriptions(jobs: List[JobDescription]) -> Dict:
    """
    Endpoint to upload multiple job descriptions.
    
    Parameters:
    - jobs (List[JobDescription]): List of job descriptions with titles.
    
    Returns:
    - Dict: Success message with count of jobs uploaded.
    """
    job_descriptions_store.extend(jobs)
    return {"message": f"{len(jobs)} job descriptions uploaded successfully."}

# Endpoint to match resume with uploaded job descriptions
@app.post("/match-resume-to-jobs/")
async def match_resume_to_jobs(file: UploadFile = File(...)) -> Dict:
    """
    Endpoint to match uploaded resume against job descriptions and get scores.
    
    Parameters:
    - file (UploadFile): The resume file uploaded by the user.
    
    Returns:
    - Dict: List of matching scores for each job description.
    """
    if file.content_type not in [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF or Word files are accepted.")
    
    file_location = f"resumes/{file.filename}"

    try:
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())

        if file.content_type == "application/pdf":
            resume_text = extract_text(file_location)
        elif file.content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            resume_text = extract_text_from_word(file_location)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        os.remove(file_location)

        match_results = []
        for job in job_descriptions_store:
            # Creating a comparison prompt for Gemini model
            prompt = f"Match the following resume with the job description and provide a score:\n\nResume:\n{resume_text}\n\nJob Title: {job.job_title}\nJob Description: {job.description}"
            response = model.generate_content(prompt)
            match_results.append({
                "job_title": job.job_title,
                "matching_score": response.text  # assuming the response contains a score
            })

        return {"match_results": match_results}

    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
