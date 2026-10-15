import json
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from .agent import ask
from .db import cursor
from .docs import generate

app = FastAPI(title="1C assistant")


class AskIn(BaseModel):
    question: str


class FeedbackIn(BaseModel):
    question: str
    answer: str
    procedure_ids: List[int]
    verdict: str
    comment: Optional[str] = None


def regenerate(fid, ids, comment):
    for pid in ids:
        generate(pid, comment)
    with cursor() as c:
        c.execute("UPDATE feedback SET resolved=TRUE WHERE id=%s", (fid,))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask_endpoint(body: AskIn):
    return ask(body.question)


@app.post("/feedback")
def feedback_endpoint(fb: FeedbackIn, bg: BackgroundTasks):
    ids = fb.procedure_ids[:5]
    with cursor() as c:
        c.execute(
            "INSERT INTO feedback (question, answer, procedure_ids, verdict, comment) "
            "VALUES (%s, %s, %s, %s, %s)",
            (fb.question, fb.answer, json.dumps(ids), fb.verdict, fb.comment),
        )
        fid = c.lastrowid
    if fb.verdict == "wrong":
        bg.add_task(regenerate, fid, ids, fb.comment)
    return {"id": fid, "regenerating": fb.verdict == "wrong"}


@app.get("/procedures")
def procedures(q: str):
    with cursor() as c:
        c.execute(
            "SELECT p.id, p.name, m.path FROM procedures p JOIN modules m ON m.id=p.module_id "
            "WHERE p.name LIKE %s ORDER BY p.name LIMIT 50",
            (f"%{q}%",),
        )
        return c.fetchall()


@app.get("/documentation/{pid}")
def documentation(pid: int):
    with cursor() as c:
        c.execute(
            "SELECT content_md, version FROM docs WHERE procedure_id=%s ORDER BY version DESC LIMIT 1",
            (pid,),
        )
        row = c.fetchone()
    return row or {"content_md": None, "version": 0}
