import motor.motor_asyncio
from pydantic import BaseModel

# MongoDB connection setup
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://mongo:27017")
db = client.resume_analyzer

class ResumeModel(BaseModel):
    name: str
    email: str
    phone_number: str
    skills: list
    education: list
    experience: list

class JobDescriptionModel(BaseModel):
    description: str
    required_skills: list
    experience_required: str

async def save_resume(extracted_info):
    resume_data = {
        "name": extracted_info["name"],
        "email": extracted_info["email"],
        "phone_number": extracted_info["phone_number"],
        "skills": extracted_info["skills"],
        "education": extracted_info["education"],
        "experience": extracted_info["experience"],
    }
    result = await db["resumes"].insert_one(resume_data)
    return str(result.inserted_id)

async def save_job_description(job_data):
    result = await db["job_descriptions"].insert_one(job_data.dict())
    return str(result.inserted_id)
