import os

from fastapi import FastAPI, Security, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.handler import handler

# Orígenes explícitos separados por comas. Si no se define, se conserva el
# comportamiento anterior de orígenes comodín, pero sin credenciales.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if o.strip()
]

app = FastAPI(version="0.33")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(handler)
