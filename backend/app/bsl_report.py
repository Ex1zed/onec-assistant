import json
import subprocess
from pathlib import Path
from urllib.parse import unquote

BSL_JAR = Path(__file__).resolve().parents[2] / "bsl-language-server.jar"


def run_bsl_ls(src_dir: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["java", "-jar", str(BSL_JAR), "analyze",
         "--srcDir", str(src_dir), "-r", "json", "-o", str(out_dir)],
        capture_output=True,
        timeout=600,
        check=True,
    )
    return out_dir / "bsl-json.json"


def load_report(json_path: Path):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    root_prefix = "file://"

    for fi in data.get("fileinfos", []):
        raw_path = fi["path"]
        if raw_path.startswith(root_prefix):
            raw_path = raw_path[len(root_prefix):]
        decoded = unquote(raw_path)
        marker = "/data/"
        idx = decoded.find(marker)
        rel_path = decoded[idx + len(marker):] if idx != -1 else decoded

        yield {
            "path": rel_path,
            "diagnostics": [
                {
                    "code": d["code"],
                    "message": d["message"],
                    "severity": d["severity"],
                    "line": d["range"]["start"]["line"] + 1,
                    "character": d["range"]["start"]["character"] + 1,
                }
                for d in fi.get("diagnostics", [])
            ],
            "metrics": fi.get("metrics", {}),
        }