from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="PaperSage")

#middleware
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix = "/api/v1")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the PaperSage API"}