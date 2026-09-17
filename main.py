from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import Base, engine, get_db
from models import School, Check, Completion

API_KEY = "change-me"   # move to .env in production

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Statutory Compliance API", lifespan=lifespan)

def auth(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ---------- schemas ----------
class SchoolIn(BaseModel):
    name: str
    slug: str

class CheckIn(BaseModel):
    name: str
    category: str
    frequency_days: int
    last_completed: date

class CompleteIn(BaseModel):
    completed_on: date
    completed_by: str
    notes: str | None = None

# ---------- schools ----------
@app.post("/schools", dependencies=[Depends(auth)])
def create_school(payload: SchoolIn, db: Session = Depends(get_db)):
    s = School(**payload.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s

@app.get("/schools", dependencies=[Depends(auth)])
def list_schools(db: Session = Depends(get_db)):
    return db.query(School).all()

# ---------- checks ----------
@app.post("/schools/{school_id}/checks", dependencies=[Depends(auth)])
def create_check(school_id: int, payload: CheckIn, db: Session = Depends(get_db)):
    if not db.get(School, school_id):
        raise HTTPException(404, "School not found")
    c = Check(school_id=school_id, **payload.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c

@app.get("/schools/{school_id}/checks", dependencies=[Depends(auth)])
def list_checks(school_id: int, db: Session = Depends(get_db)):
    rows = db.query(Check).filter(Check.school_id == school_id).all()
    return [
        {"id": c.id, "name": c.name, "category": c.category,
         "next_due": c.next_due, "rag": c.rag}
        for c in rows
    ]

# ---------- mark complete (rolls the schedule forward) ----------
@app.post("/checks/{check_id}/complete", dependencies=[Depends(auth)])
def complete_check(check_id: int, payload: CompleteIn, db: Session = Depends(get_db)):
    c = db.get(Check, check_id)
    if not c:
        raise HTTPException(404, "Check not found")
    c.last_completed = payload.completed_on
    db.add(Completion(check_id=check_id, **payload.model_dump()))
    db.commit(); db.refresh(c)
    return {"id": c.id, "next_due": c.next_due, "rag": c.rag}

# ---------- dashboard ----------
@app.get("/schools/{school_id}/dashboard", dependencies=[Depends(auth)])
def dashboard(school_id: int, db: Session = Depends(get_db)):
    rows = db.query(Check).filter(Check.school_id == school_id).all()
    counts = {"Red": 0, "Amber": 0, "Green": 0}
    for c in rows:
        counts[c.rag] += 1
    return {"school": school_id, "counts": counts,
            "due_soon": [c.name for c in rows if c.rag != "Green"]}
