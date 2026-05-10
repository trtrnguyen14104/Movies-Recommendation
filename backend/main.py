from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from routers import movies, ai_summary, recommendations
import uuid

app = FastAPI(
    title="CineView API",
    description="Movie preview platform with AI-powered review analysis and personalized recommendations",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def set_user_id_cookie(request: Request, call_next):
    """Auto-assign a user ID cookie for personalization tracking."""
    response: Response = await call_next(request)
    if "cineview_user_id" not in request.cookies:
        user_id = str(uuid.uuid4())[:12]
        response.set_cookie(
            key="cineview_user_id",
            value=user_id,
            max_age=60 * 60 * 24 * 365,  # 1 year
            httponly=False,
            samesite="lax",
        )
    return response


app.include_router(movies.router)
app.include_router(ai_summary.router)
app.include_router(recommendations.router)


@app.get("/")
async def root():
    return {"message": "CineView API", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
