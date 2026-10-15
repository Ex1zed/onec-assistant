import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:3b")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
CONFIG_SRC = ROOT / os.getenv("CONFIG_SRC", "data/sample_config")
