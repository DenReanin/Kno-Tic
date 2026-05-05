from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyzer import analyze_message, analyze_image_content, analyze_url, learn_indicator
from db import init_db, save_analysis, get_history, get_stats, save_feedback

app = FastAPI(title="Kno-Tic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


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


@app.get("/")
def root():
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
