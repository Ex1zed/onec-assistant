import re
from pathlib import Path

PATTERN = re.compile(
    r"^[ \t]*(Процедура|Функция|Procedure|Function)[ \t]+(\w+)[ \t]*\((.*?)\)[ \t]*(Экспорт|Export)?"
    r"(.*?)"
    r"^[ \t]*(КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)


def parse_module(path: Path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for m in PATTERN.finditer(text):
        yield {
            "kind": m.group(1).lower(),
            "name": m.group(2),
            "params": " ".join(m.group(3).split()),
            "exported": bool(m.group(4)),
            "body": m.group(0).strip(),
        }
