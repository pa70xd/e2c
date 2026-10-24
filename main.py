from fastapi import FastAPI, Security, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.handler import handler

app = FastAPI(version="0.33")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(handler)
