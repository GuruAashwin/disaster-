from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, matches
from app.routers.persons import router as persons_router
from app.routers import videos
from app.models import User
from app.auth import get_current_user

# Create tables on startup (dev mode — use Alembic for production migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Disaster Family Reunification API",
    version="1.0.0",
    description="Match found persons to missing person reports after a disaster.",
)

# Allow any origin on the LAN.
# allow_credentials is False because auth uses Bearer tokens (Authorization header),
# not cookies — so the browser never sends credentials automatically.
# This also makes the wildcard origin legal per the CORS spec.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(persons_router)
app.include_router(videos.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API is running"}


@app.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.username}", "role": current_user.role}
