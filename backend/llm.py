"""
LLM calls for the Application Tracker Copilot.

Two jobs only, kept deliberately separate:
  1. parse_job_description -> structured fields from raw JD text
  2. draft_answer -> first-pass answer to a take-home/application question,
     grounded in retrieved resume context

Requires GROQ_API_KEY to be set in your environment / .env file.
"""
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# gpt-oss-120b is Groq's current recommended flagship model (their Llama 3.x
# models were deprecated June 2026). Swap to "openai/gpt-oss-20b" for a
# faster/cheaper option if 120b feels slow or you hit rate limits.
MODEL = "openai/gpt-oss-120b"


def _strip_code_fences(text: str) -> str:
    return re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


def parse_job_description(jd_text: str) -> dict:
    """Extract company, role, deadline, and key requirements from raw JD text."""
    system_prompt = (
        "You extract structured data from job descriptions. "
        "Respond with ONLY a JSON object, no preamble, no markdown fences. "
        "Schema: {\"company\": string or null, \"role\": string or null, "
        "\"deadline\": string or null (raw text as written, do not invent one), "
        "\"key_requirements\": array of up to 6 short strings}. "
        "If a field isn't present in the text, use null (or empty array for key_requirements)."
    )
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": jd_text},
        ],
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError:
        # Fail loud but don't crash the request — return an empty-ish shell
        return {"company": None, "role": None, "deadline": None, "key_requirements": []}


def draft_answer(question: str, resume_context: str, jd_context: str = "") -> str:
    """Draft a first-pass answer to an application/take-home question.

    This is meant to produce a STARTING DRAFT for you to edit, not a final
    submission — the value is saving the blank-page time, not replacing your judgment.
    """
    system_prompt = (
        "You help a candidate draft first-pass answers to job application and "
        "take-home questions, grounded strictly in the resume context provided. "
        "Do not invent experience that isn't in the context. Write in first person, "
        "concise, concrete, no fluff or generic phrases. Flag with [VERIFY] any "
        "claim you are not fully certain is supported by the context."
    )
    user_content = (
        f"RESUME CONTEXT:\n{resume_context}\n\n"
        + (f"JOB CONTEXT:\n{jd_context}\n\n" if jd_context else "")
        + f"QUESTION:\n{question}"
    )
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content
