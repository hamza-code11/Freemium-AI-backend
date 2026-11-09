import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.api.routers.product import router as product_router
from app.api.routers.auth import router as auth_router
from app.api.routers.business_profile import router as business_profile_router
from app.api.routers.admin_auth import router as admin_auth_router
from app.api.routers.ai import router as ai_router
from app.api.routers.campaign import router as campaign_router
from app.api.routers.growth_recommendations import router as growth_router
from app.api.routers.history import router as history_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.support import router as support_router

load_dotenv()

Path("uploads/products").mkdir(parents=True, exist_ok=True)
Path("uploads/users").mkdir(parents=True, exist_ok=True)
Path("uploads/admins").mkdir(parents=True, exist_ok=True)
Path("uploads/support").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Python Backend API",
    description="Product Management API",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Comma separated: "https://my-app.vercel.app,http://localhost:3001"
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_URLS", "http://localhost:3001").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router)
app.include_router(auth_router)
app.include_router(business_profile_router)
app.include_router(admin_auth_router)
app.include_router(ai_router)
app.include_router(campaign_router)
app.include_router(growth_router)
app.include_router(history_router)
app.include_router(dashboard_router)
app.include_router(support_router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def home():
    return {"message": "API is running successfully"}
