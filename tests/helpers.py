from pathlib import Path


def read_sample(relative_path: str) -> str:
    return Path("samples", relative_path).read_text(encoding="utf-8")
