from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from .config import QDRANT_URL
from .db import cursor
from .llm import embed

COLLECTION = "procedures"


def qdrant():
    return QdrantClient(url=QDRANT_URL)


def run(batch_size=16):
    q = qdrant()
    if not q.collection_exists(COLLECTION):
        q.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
    with cursor() as c:
        c.execute(
            "SELECT p.id, p.name, p.body, p.body_hash, m.path, m.object_name "
            "FROM procedures p JOIN modules m ON m.id=p.module_id "
            "WHERE p.indexed_hash IS NULL OR p.indexed_hash <> p.body_hash"
        )
        rows = c.fetchall()
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            texts = [f"{r['object_name']} / {r['name']}\n{r['body'][:6000]}" for r in chunk]
            vecs = embed(texts)
            q.upsert(
                COLLECTION,
                points=[
                    PointStruct(id=r["id"], vector=v, payload={"name": r["name"], "module": r["path"]})
                    for r, v in zip(chunk, vecs)
                ],
            )
            c.executemany(
                "UPDATE procedures SET indexed_hash=%s WHERE id=%s",
                [(r["body_hash"], r["id"]) for r in chunk],
            )
            print(f"indexed {min(i + batch_size, len(rows))}/{len(rows)}")
        if not rows:
            print("index is up to date")
