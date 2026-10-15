import hashlib
import re
from pathlib import Path

from .db import cursor
from .parser import parse_module


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_modules(root):
    root = Path(root)
    seen = set()
    with cursor() as c:
        for f in root.rglob("*.bsl"):
            rel = f.relative_to(root)
            path = rel.as_posix()
            seen.add(path)
            obj = "/".join(p for p in rel.parts[:-1] if p != "Ext")
            c.execute(
                "INSERT INTO modules (path, object_name, module_type) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE object_name=VALUES(object_name), module_type=VALUES(module_type)",
                (path, obj, f.stem),
            )
            c.execute("SELECT id FROM modules WHERE path=%s", (path,))
            mid = c.fetchone()["id"]
            names = []
            for p in parse_module(f):
                names.append(p["name"])
                c.execute(
                    "INSERT INTO procedures (module_id, name, kind, params, exported, body, body_hash) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE kind=VALUES(kind), params=VALUES(params), "
                    "exported=VALUES(exported), body=VALUES(body), body_hash=VALUES(body_hash)",
                    (mid, p["name"], p["kind"], p["params"], p["exported"], p["body"], sha(p["body"])),
                )
            if names:
                fmt = ",".join(["%s"] * len(names))
                c.execute(
                    f"DELETE FROM procedures WHERE module_id=%s AND name NOT IN ({fmt})",
                    (mid, *names),
                )
            else:
                c.execute("DELETE FROM procedures WHERE module_id=%s", (mid,))
        c.execute("SELECT id, path FROM modules")
        for m in c.fetchall():
            if m["path"] not in seen:
                c.execute("DELETE FROM modules WHERE id=%s", (m["id"],))


def build_calls():
    with cursor() as c:
        c.execute("SELECT id, name, body FROM procedures")
        rows = c.fetchall()
        by_name = {}
        for r in rows:
            by_name.setdefault(r["name"].lower(), []).append(r["id"])
        pairs = set()
        for r in rows:
            tokens = {t.lower() for t in re.findall(r"\w+", r["body"])}
            for t in tokens & by_name.keys():
                for callee in by_name[t]:
                    if callee != r["id"]:
                        pairs.add((r["id"], callee))
        c.execute("DELETE FROM calls")
        pairs = list(pairs)
        for i in range(0, len(pairs), 1000):
            c.executemany(
                "INSERT IGNORE INTO calls (caller_id, callee_id) VALUES (%s, %s)",
                pairs[i : i + 1000],
            )
    return len(pairs)


def run(root):
    load_modules(root)
    n = build_calls()
    with cursor() as c:
        c.execute("SELECT COUNT(*) AS n FROM procedures")
        procs = c.fetchone()["n"]
    print(f"procedures: {procs}, calls: {n}")
    from pathlib import Path
from .bsl_report import run_bsl_ls, load_report


def load_bsl_diagnostics(src_dir, out_dir=None):
    """Прогоняет BSL LS и сохраняет диагностики + метрики в MySQL."""
    if out_dir is None:
        out_dir = Path("/tmp/bsl-report")

    json_path = run_bsl_ls(Path(src_dir), out_dir)

    with cursor() as c:
        c.execute("DELETE FROM diagnostics")
        c.execute("DELETE FROM metrics")

        for fi in load_report(json_path):
            for d in fi["diagnostics"]:
                c.execute(
                    "INSERT INTO diagnostics (module_path, code, message, severity, `line`, character_pos) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (fi["path"], d["code"], d["message"], d["severity"], d["line"], d["character"]),
                )

            m = fi["metrics"]
            c.execute(
                "INSERT INTO metrics (module_path, procedures, functions, `lines`, ncloc, comments, "
                "statements, cognitive_complexity, cyclomatic_complexity) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE procedures=VALUES(procedures), functions=VALUES(functions), "
                "`lines`=VALUES(`lines`), ncloc=VALUES(ncloc), comments=VALUES(comments), "
                "statements=VALUES(statements), cognitive_complexity=VALUES(cognitive_complexity), "
                "cyclomatic_complexity=VALUES(cyclomatic_complexity)",
                (fi["path"], m.get("procedures", 0), m.get("functions", 0), m.get("lines", 0),
                 m.get("ncloc", 0), m.get("comments", 0), m.get("statements", 0),
                 m.get("cognitiveComplexity", 0), m.get("cyclomaticComplexity", 0)),
            )
