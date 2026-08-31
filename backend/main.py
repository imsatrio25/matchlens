from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import galaxy, scout

app = FastAPI(title="The Style Galaxy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(galaxy.router)
app.include_router(scout.router)

@app.get("/api/health")
def healthcheck():
    return {"status": "healthy", "service": "style-galaxy-backend"}
