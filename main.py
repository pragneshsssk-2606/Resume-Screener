from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import re
import os
import io

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

app = FastAPI(title="Smart Resume Screener")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

candidates = []


SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "sql",
    "html",
    "css",
    "react",
    "angular",
    "vue",
    "node.js",
    "node",
    "express",
    "fastapi",
    "flask",
    "django",
    "spring",
    "spring boot",
    "mongodb",
    "mysql",
    "postgresql",
    "oracle",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "github",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data science",
    "pandas",
    "numpy",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "nlp",
    "power bi",
    "tableau",
    "excel",
    "rest api",
    "api",
    "linux",
    "terraform",
    "jenkins",
}


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_skills(text):
    text = normalize_text(text)

    found = []

    for skill in sorted(SKILLS, key=len, reverse=True):
        pattern = r"(?<![a-z0-9+#.])" + re.escape(skill) + r"(?![a-z0-9+#.])"

        if re.search(pattern, text):
            found.append(skill)

    return found


async def extract_resume_text(file):
    content = await file.read()

    filename = file.filename.lower()

    if filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):
        if PdfReader is None:
            raise Exception("PDF support is not installed. Run: pip install pypdf")

        reader = PdfReader(io.BytesIO(content))

        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n".join(pages)

    raise Exception("Only PDF and TXT files are supported.")


def calculate_match(resume_skills, jd_skills):
    if not jd_skills:
        return 0

    matched = set(resume_skills).intersection(set(jd_skills))

    score = round((len(matched) / len(set(jd_skills))) * 100)

    return min(score, 100)


def get_recommendation(score):
    if score >= 80:
        return "Strongly Recommended"

    if score >= 60:
        return "Recommended"

    if score >= 40:
        return "Consider"

    return "Not Recommended"


@app.get("/")
def home():
    return FileResponse(
        os.path.join(STATIC_DIR, "index.html")
    )


@app.get("/api/candidates")
def get_candidates():
    return {
        "candidates": candidates
    }


@app.post("/api/screen")
async def screen_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        if not resume.filename:
            return {
                "error": "No resume file selected."
            }

        if not job_description.strip():
            return {
                "error": "Job description is required."
            }

        resume_text = await extract_resume_text(resume)

        if not resume_text.strip():
            return {
                "error": "Could not extract text from the resume."
            }

        resume_skills = extract_skills(resume_text)

        jd_skills = extract_skills(job_description)

        matched_skills = sorted(
            set(resume_skills).intersection(set(jd_skills))
        )

        missing_skills = sorted(
            set(jd_skills) - set(resume_skills)
        )

        match_score = calculate_match(
            resume_skills,
            jd_skills
        )

        recommendation = get_recommendation(
            match_score
        )

        if matched_skills:
            justification = (
                f"The resume matches {len(matched_skills)} "
                f"of {len(set(jd_skills))} identified job skills."
            )
        else:
            justification = (
                "No matching skills were identified between "
                "the resume and job description."
            )

        result = {
            "filename": resume.filename,
            "match_score": match_score,
            "recommendation": recommendation,
            "justification": justification,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills
        }

        candidates.append(result)

        return result

    except Exception as e:
        return {
            "error": str(e)
        }


@app.get("/api/health")
def health():
    return {
        "status": "ok"
    }