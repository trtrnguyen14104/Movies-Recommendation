from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import movies, ai_summary, recommendations

app = FastAPI(
    title="CineView API",
    description="Movie preview platform with AI-powered review analysis",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(movies.router)
app.include_router(ai_summary.router)
app.include_router(recommendations.router)


@app.get("/")
async def root():
    return {"message": "CineView API", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
