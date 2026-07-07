"""
Application Tracker Copilot — FastAPI backend.

Run with: uvicorn main:app --reload --port 8000
"""
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from bson.errors import InvalidId

from models import (
    ApplicationCreate,
    ApplicationUpdate,
    ParseJDRequest,
    ParseJDResponse,
    GenerateAnswerRequest,
    GenerateAnswerResponse,
)
from db import get_applications_collection
from llm import parse_job_description, draft_answer
from retrieval import retrieve, build_index

app = FastAPI(title="Application Tracker Copilot")

# Streamlit runs on a different port locally — allow it through CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def _object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid application id")


@app.on_event("startup")
async def startup():
    # Build the resume index eagerly so the first /generate-answer call isn't slow.
    # If resume.txt doesn't exist yet, don't crash the whole app — just log it.
    try:
        build_index()
    except FileNotFoundError as e:
        print(f"[startup warning] {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/applications")
async def create_application(payload: ApplicationCreate):
    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow()
    collection = get_applications_collection()
    result = await collection.insert_one(doc)
    created = await collection.find_one({"_id": result.inserted_id})
    return _serialize(created)


@app.get("/applications")
async def list_applications(status: Optional[str] = None):
    collection = get_applications_collection()
    query = {"status": status} if status else {}
    docs = await collection.find(query).sort("created_at", -1).to_list(length=200)
    return [_serialize(d) for d in docs]


@app.get("/applications/{application_id}")
async def get_application(application_id: str):
    collection = get_applications_collection()
    doc = await collection.find_one({"_id": _object_id(application_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Application not found")
    return _serialize(doc)


@app.patch("/applications/{application_id}")
async def update_application(application_id: str, payload: ApplicationUpdate):
    collection = get_applications_collection()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await collection.update_one({"_id": _object_id(application_id)}, {"$set": updates})
    doc = await collection.find_one({"_id": _object_id(application_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Application not found")
    return _serialize(doc)


@app.delete("/applications/{application_id}")
async def delete_application(application_id: str):
    collection = get_applications_collection()
    result = await collection.delete_one({"_id": _object_id(application_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"deleted": True}


@app.post("/parse-jd", response_model=ParseJDResponse)
async def parse_jd(payload: ParseJDRequest):
    parsed = parse_job_description(payload.jd_text)
    return ParseJDResponse(
        company=parsed.get("company"),
        role=parsed.get("role"),
        deadline=parsed.get("deadline"),
        key_requirements=parsed.get("key_requirements", []),
    )


@app.post("/generate-answer", response_model=GenerateAnswerResponse)
async def generate_answer(payload: GenerateAnswerRequest):
    resume_chunks = retrieve(payload.question, top_k=3)
    resume_context = "\n---\n".join(resume_chunks)

    jd_context = ""
    if payload.application_id:
        collection = get_applications_collection()
        doc = await collection.find_one({"_id": _object_id(payload.application_id)})
        if doc and doc.get("jd_text"):
            jd_context = doc["jd_text"]

    answer = draft_answer(payload.question, resume_context, jd_context)
    return GenerateAnswerResponse(answer=answer, sources_used=resume_chunks)
