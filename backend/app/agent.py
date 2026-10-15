from .db import cursor
from .indexer import qdrant, COLLECTION
from .llm import embed, chat

SYSTEM = (
    "Ты помощник разработчика 1С. Отвечай на русском, только на основе предоставленного кода и документации. "
    "Если данных недостаточно, прямо скажи об этом. Не придумывай процедуры и модули, которых нет в контексте. "
    "В конце перечисли использованные модули и процедуры."
)


def fetch(c, ids):
    if not ids:
        return []
    fmt = ",".join(["%s"] * len(ids))
    c.execute(
        "SELECT p.id, p.name, p.kind, p.params, p.body, m.path, m.object_name "
        f"FROM procedures p JOIN modules m ON m.id=p.module_id WHERE p.id IN ({fmt})",
        ids,
    )
    rows = {r["id"]: r for r in c.fetchall()}
    return [rows[i] for i in ids if i in rows]


def related(c, ids, limit=8):
    fmt = ",".join(["%s"] * len(ids))
    c.execute(
        f"SELECT callee_id AS id FROM calls WHERE caller_id IN ({fmt}) "
        f"UNION SELECT caller_id FROM calls WHERE callee_id IN ({fmt}) LIMIT {limit}",
        ids + ids,
    )
    return [r["id"] for r in c.fetchall() if r["id"] not in ids]


def latest_doc(c, pid):
    c.execute(
        "SELECT content_md FROM docs WHERE procedure_id=%s ORDER BY version DESC LIMIT 1",
        (pid,),
    )
    row = c.fetchone()
    return row["content_md"] if row else None


def ask(question, k=5):
    hits = qdrant().query_points(COLLECTION, query=embed([question])[0], limit=k).points
    with cursor() as c:
        main = fetch(c, [h.id for h in hits])
        ids = [p["id"] for p in main]
        rel = fetch(c, related(c, ids)) if ids else []
        parts = []
        for p in main:
            block = f"### {p['object_name']} / {p['name']} ({p['path']})\n{p['body'][:2500]}"
            doc = latest_doc(c, p["id"])
            if doc:
                block += f"\n\nДокументация:\n{doc[:800]}"
            parts.append(block)
        for p in rel:
            parts.append(
                f"### Связанная процедура: {p['object_name']} / {p['name']}({p['params']}) ({p['path']})"
            )
    user = "Контекст:\n\n" + "\n\n".join(parts) + f"\n\nВопрос: {question}"
    answer = chat(SYSTEM, user)
    sources = [
        {"id": p["id"], "name": p["name"], "module": p["path"]} for p in main + rel
    ]
    return {"answer": answer, "sources": sources}
