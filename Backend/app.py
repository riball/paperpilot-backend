from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
import shutil
import os
import httpx

from core.zipper import create_zip
from core.parser import parse_sections
from core.formatter import generate_formats, get_available_formats
from file_handlers.docx_handler import extract_text_from_docx
from file_handlers.pdf_handler import extract_text_from_pdf
from file_handlers.txt_handler import extract_text_from_txt
from file_handlers.latex_handler import extract_text_from_latex

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # primary
GROQ_MODEL_FALLBACK = "llama3-8b-8192"   # fallback if primary unavailable


@app.get("/")
def home():
    return {"message": "Research Paper Formatter API Running"}


@app.get("/formats/")
def list_formats():
    return {"available_formats": get_available_formats()}


@app.get("/download/")
def download_file(path: str):
    if not os.path.exists(path):
        return {"status": "error", "message": "File not found"}
    return FileResponse(path, filename=os.path.basename(path))


@app.post("/convert/")
async def convert_file(
    file: UploadFile = File(...),
    formats: str = Form(...),
    output_type: str = Form("pdf")
):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        filename_lower = file.filename.lower()

        if filename_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(file_path)
            content = parse_sections(raw_text)
        elif filename_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_path)
            content = parse_sections(raw_text)
        elif filename_lower.endswith(".txt"):
            raw_text = extract_text_from_txt(file_path)
            content = parse_sections(raw_text)
        elif filename_lower.endswith(".tex"):
            raw_text = extract_text_from_latex(file_path)
            content = parse_sections(raw_text)
        else:
            return {
                "status": "error",
                "message": "Unsupported file type. Please upload .pdf, .docx, .txt, or .tex file."
            }

        formats_list = [f.strip().lower() for f in formats.split(",")]
        available_formats = get_available_formats()
        selected_formats = [fmt for fmt in formats_list if fmt in available_formats]

        if not selected_formats:
            return {"status": "error", "message": "No valid formats selected"}

        outputs = generate_formats(content, selected_formats, output_type)
        if not outputs:
            return {"status": "error", "message": "No files generated"}

        if len(outputs) > 1:
            zip_path = create_zip(outputs)
            return {"status": "success", "zip_file": zip_path}

        format_name = list(outputs.keys())[0]
        files = outputs[format_name]
        return {"status": "success", "format": format_name, "files": files}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── AI Critique ───────────────────────────────────────────────────────────────

CRITIQUE_SYSTEM_PROMPT = """You are a senior academic peer reviewer with expertise across computer science, 
engineering, and natural sciences. You provide professional, structured, and constructive critiques 
of research papers, the kind you would expect from a rigorous journal reviewer.

When critiquing a section, evaluate clarity and precision of writing, depth and rigor of content,
logical flow and coherence, completeness (what is missing), strengths worth highlighting,
and give concrete suggestions for improvement.

Be direct and specific. Use academic language. Format your response with these exact markdown headings:
## Strengths
## Weaknesses  
## Suggestions for Improvement
## Summary Score
(Give a score out of 10 at the end with a one-line justification)"""


SECTION_PROMPTS = {
    "title": "Evaluate this research paper title for clarity, specificity, informativeness, and impact.",
    "abstract": "Critique this abstract. Does it clearly state the problem, methodology, key findings, and contributions? Is it concise yet complete?",
    "keywords": "Evaluate these keywords for relevance, discoverability, and alignment with the paper's scope.",
    "introduction": "Critique this introduction. Does it adequately motivate the problem, review relevant literature, state the research gap, and clearly present the paper's contributions?",
    "methodology": "Critique this methodology section. Is the approach clearly described, reproducible, and well-justified? Are there gaps or ambiguities?",
    "results": "Critique the results section. Are findings clearly presented, properly contextualized, and supported with appropriate evidence? Is the analysis rigorous?",
    "conclusion": "Critique this conclusion. Does it effectively summarize contributions, acknowledge limitations, and suggest meaningful future work?",
    "references": "Review the references section. Comment on the quality, recency, diversity, and completeness of citations.",
}


@app.post("/critique/")
async def critique_paper(request: Request):
    try:
        body = await request.json()
        sections: dict = body.get("sections", {})
        target_section: str = body.get("target_section", None)

        if not sections:
            return {"status": "error", "message": "No sections provided."}

        api_key = GROQ_API_KEY
        if not api_key:
            return {"status": "error", "message": "GROQ_API_KEY not set in server .env"}

        sections_to_critique = (
            {target_section: sections[target_section]}
            if target_section and target_section in sections
            else sections
        )

        critiques = {}
        async with httpx.AsyncClient(timeout=60.0) as client:
            for section_name, section_content in sections_to_critique.items():
                if not section_content or not section_content.strip():
                    continue

                section_prompt = SECTION_PROMPTS.get(
                    section_name,
                    f"Critique this '{section_name}' section of a research paper."
                )

                user_message = (
                    f"{section_prompt}\n\n"
                    f"--- BEGIN {section_name.upper()} ---\n"
                    f"{section_content.strip()}\n"
                    f"--- END {section_name.upper()} ---"
                )

                payload = {
                    "messages": [
                        {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 1024,
                }
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                # Try primary model, fall back if unavailable
                for model in (GROQ_MODEL, GROQ_MODEL_FALLBACK):
                    response = await client.post(
                        GROQ_URL,
                        headers=headers,
                        json={**payload, "model": model},
                    )
                    data = response.json()
                    if response.status_code == 200 and "choices" in data:
                        break  # success
                    # If model not found, try fallback; otherwise surface error
                    groq_error = data.get("error", {})
                    err_type = groq_error.get("type", "")
                    if err_type != "model_not_found" and "model" not in groq_error.get("message", "").lower():
                        msg = groq_error.get("message", str(data))
                        return {"status": "error", "message": f"Groq API error: {msg}"}

                if "choices" not in data:
                    groq_error = data.get("error", {})
                    msg = groq_error.get("message", str(data))
                    return {"status": "error", "message": f"Groq API error: {msg}"}

                critique_text = data["choices"][0]["message"]["content"]
                critiques[section_name] = critique_text

        return {"status": "success", "critiques": critiques}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Parse Sections (for AI Critique upload mode) ──────────────────────────────

@app.post("/parse-sections/")
async def parse_sections_endpoint(file: UploadFile = File(...)):
    """
    Extracts sections from uploaded file and returns them as a dict.
    Used by AI Critique to auto-populate section text areas.
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        filename_lower = file.filename.lower()

        if filename_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(file_path)
        elif filename_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(file_path)
        elif filename_lower.endswith(".txt"):
            raw_text = extract_text_from_txt(file_path)
        elif filename_lower.endswith(".tex"):
            raw_text = extract_text_from_latex(file_path)
        else:
            return {
                "status": "error",
                "message": "Unsupported file type."
            }

        sections = parse_sections(raw_text)
        return {"status": "success", "sections": sections}

    except Exception as e:
        return {"status": "error", "message": str(e)}
