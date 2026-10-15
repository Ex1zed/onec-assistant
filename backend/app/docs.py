import json

from jinja2 import Template

from .db import cursor
from .llm import chat

SYSTEM = (
    "Ты технический писатель для кодовой базы 1С. Описывай только то, что видно в коде. "
    "Отвечай строго JSON без пояснений."
)

TEMPLATE = Template(
    """# {{ p.name }}

Модуль: {{ p.object_name }} ({{ p.path }})
Тип: {{ p.kind }}{% if p.exported %}, экспортная{% endif %}
Параметры в сигнатуре: {{ p.params or "нет" }}

## Назначение
{{ d.purpose }}

## Параметры
{% for x in d.params %}- {{ x.name }}: {{ x.description }}
{% else %}Нет.
{% endfor %}
## Возвращаемое значение
{{ d.returns or "Нет." }}

## Вызывает
{% for n in callees %}- {{ n }}
{% else %}Нет.
{% endfor %}
## Вызывается из
{% for n in callers %}- {{ n }}
{% else %}Нет.
{% endfor %}
## Побочные эффекты
{{ d.side_effects or "Не выявлены." }}
"""
)


def normalize(d):
    if not isinstance(d, dict):
        d = {"purpose": str(d)}
    params = d.get("params") or []
    if not isinstance(params, list):
        params = [params]
    params = [
        x if isinstance(x, dict) else {"name": "", "description": str(x)} for x in params
    ]
    params = [
        {"name": str(x.get("name", "")), "description": str(x.get("description", ""))}
        for x in params
    ]
    return {
        "purpose": str(d.get("purpose", "")),
        "params": params,
        "returns": str(d.get("returns", "")),
        "side_effects": str(d.get("side_effects", "")),
    }


def build_prompt(p, callees, callers, comment):
    text = (
        f"Процедура {p['name']} в модуле {p['object_name']}.\n\n"
        f"Код:\n{p['body'][:5000]}\n\n"
        f"Вызывает: {', '.join(callees) or 'нет'}\n"
        f"Вызывается из: {', '.join(callers) or 'нет'}\n\n"
        "Верни JSON с ключами: purpose (строка, 1-3 предложения), "
        "params (список объектов name и description), returns (строка), "
        "side_effects (строка: запись в БД, регистры, внешние вызовы и т.п.)."
    )
    if comment:
        text += f"\n\nЗамечание главного разработчика к предыдущей версии, учти его: {comment}"
    return text


def render(p, d, callees, callers):
    return TEMPLATE.render(p=p, d=d, callees=callees, callers=callers)


def generate(pid, comment=None):
    with cursor() as c:
        c.execute(
            "SELECT p.*, m.path, m.object_name FROM procedures p "
            "JOIN modules m ON m.id=p.module_id WHERE p.id=%s",
            (pid,),
        )
        p = c.fetchone()
        if not p:
            return None
        c.execute(
            "SELECT x.name FROM calls k JOIN procedures x ON x.id=k.callee_id WHERE k.caller_id=%s",
            (pid,),
        )
        callees = [r["name"] for r in c.fetchall()]
        c.execute(
            "SELECT x.name FROM calls k JOIN procedures x ON x.id=k.caller_id WHERE k.callee_id=%s",
            (pid,),
        )
        callers = [r["name"] for r in c.fetchall()]
        raw = chat(SYSTEM, build_prompt(p, callees, callers, comment), json_mode=True)
        try:
            d = normalize(json.loads(raw))
        except json.JSONDecodeError:
            d = normalize({"purpose": raw})
        md = render(p, d, callees, callers)
        c.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM docs WHERE procedure_id=%s",
            (pid,),
        )
        version = c.fetchone()["v"]
        c.execute(
            "INSERT INTO docs (procedure_id, content_md, source_hash, version) VALUES (%s, %s, %s, %s)",
            (pid, md, p["body_hash"], version),
        )
        return md


def generate_missing(limit=None):
    with cursor() as c:
        c.execute(
            "SELECT p.id FROM procedures p "
            "LEFT JOIN docs d ON d.procedure_id=p.id "
            "AND d.version=(SELECT MAX(version) FROM docs WHERE procedure_id=p.id) "
            "WHERE d.id IS NULL OR d.source_hash <> p.body_hash"
        )
        ids = [r["id"] for r in c.fetchall()]
    if limit:
        ids = ids[:limit]
    for n, pid in enumerate(ids, 1):
        generate(pid)
        print(f"docs {n}/{len(ids)}")
    if not ids:
        print("docs are up to date")
