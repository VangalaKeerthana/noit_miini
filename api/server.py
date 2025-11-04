import os
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from utils.db import SessionLocal, init_db, User, Query as QueryModel
from utils.auth import (
    get_password_hash, verify_password,
    create_access_token, get_current_user, TokenData
)

# Try to import your orchestrator; fallback to echo in dev
try:
    from controller.orchestrator import Orchestrator
    HAS_ORCH = True
except Exception:
    HAS_ORCH = False

app = FastAPI(title="Noit Research Mini API", version="1.1")

# --- Strict CORS: allow only the configured front-end origin(s) ---
# Set FRONTEND_ORIGIN="http://localhost:8080" (or multiple, comma-separated)
origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:8080").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,   # set True if you later use cookies
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
)

class SignupIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class QueryIn(BaseModel):
    query: str
    model: Optional[str] = "gpt-4o-mini"

class QueryOut(BaseModel):
    id: int
    question: str
    answer: Optional[str]

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "allowed_origins": origins}

@app.post("/signup", response_model=TokenOut)
def signup(payload: SignupIn):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        user = User(email=payload.email, password_hash=get_password_hash(payload.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

@app.post("/login", response_model=TokenOut)
def login(payload: LoginIn):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

@app.post("/query")
def query(q: QueryIn, current: TokenData = Depends(get_current_user)):
    db = SessionLocal()
    try:
        if HAS_ORCH:
            orch = Orchestrator(model_name=q.model or "gpt-4o-mini")
            answer = orch.run(q.query)
        else:
            answer = f"(Dev fallback) You asked: {q.query}"
        row = QueryModel(user_id=current.user_id, question=q.query, answer=answer)
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"answer": answer, "id": row.id}
    finally:
        db.close()

@app.get("/history", response_model=List[QueryOut])
def history(current: TokenData = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = (
            db.query(QueryModel)
            .filter(QueryModel.user_id == current.user_id)
            .order_by(QueryModel.created_at.desc())
            .limit(50)
            .all()
        )
        return [{"id": r.id, "question": r.question, "answer": r.answer} for r in rows]
    finally:
        db.close()
