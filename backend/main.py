from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analyzer import analyze_image_content, analyze_message, analyze_url, learn_indicator
from db import get_history, get_stats, init_db, save_analysis, save_feedback

app = FastAPI(title="Kno-Tic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


class MessageRequest(BaseModel):
    content: str


class UrlRequest(BaseModel):
    url: str


class FeedbackRequest(BaseModel):
    value: str


class LearnRequest(BaseModel):
    indicator_type: str
    description: str
    summary: str


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Kno-Tic"}


@app.get("/favicon.svg")
def favicon():
    icon_path = FRONTEND_DIST / "favicon.svg"
    if icon_path.is_file():
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    index_file = FRONTEND_DIST / "index.html"
    if "text/html" in accept and index_file.is_file():
        return FileResponse(index_file)
    return {"status": "ok", "app": "Kno-Tic"}


@app.post("/analyze")
async def analyze(request: MessageRequest):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
    try:
        result = await analyze_message(request.content)
        analysis_id = save_analysis(request.content, result)
        return {**result, "analysis_id": analysis_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-image")
async def analyze_img(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen (jpg, png, webp)")
    try:
        contents = await file.read()
        result = await analyze_image_content(contents, file.content_type)
        analysis_id = save_analysis(f"[Imagen: {file.filename}]", result)
        return {**result, "analysis_id": analysis_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-url")
async def analyze_url_endpoint(request: UrlRequest):
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="La URL no puede estar vacía")
    try:
        result = await analyze_url(request.url)
        analysis_id = save_analysis(request.url, result)
        return {**result, "analysis_id": analysis_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/feedback/{analysis_id}")
def feedback(analysis_id: int, request: FeedbackRequest):
    if request.value not in ("correcto", "incorrecto"):
        raise HTTPException(status_code=400, detail="Valor inválido")
    save_feedback(analysis_id, request.value)
    return {"ok": True}


@app.post("/learn")
async def learn(request: LearnRequest):
    try:
        return await learn_indicator(request.indicator_type, request.description, request.summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def history(
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    return get_history(search=search, category=category)


@app.get("/stats")
def statistics():
    return get_stats()
