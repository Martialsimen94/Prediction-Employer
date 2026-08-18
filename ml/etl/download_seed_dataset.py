"""Reproducibly fetch the seed dataset: the public IBM HR Analytics Employee
Attrition & Performance dataset (1,470 employees, 35 features), a
well-known fictional dataset published by IBM for HR analytics tutorials.

Not committed to the repo (see .gitignore ml/data/raw/) — run this script
to (re)fetch it. A sha256 checksum guards against silently picking up a
tampered or unrelated file from a mirror.
"""

import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen

SOURCE_URL = (
    "https://raw.githubusercontent.com/nelson-wu/employee-attrition-ml/"
    "master/WA_Fn-UseC_-HR-Employee-Attrition.csv"
)
EXPECTED_SHA256 = "a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659"
RAW_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
TARGET_PATH = RAW_DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv"


def download(target_path: Path = TARGET_PATH) -> Path:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with urlopen(SOURCE_URL) as response:  # noqa: S310 - fixed, known HTTPS source
        content = response.read()

    digest = hashlib.sha256(content).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(
            f"Downloaded file checksum mismatch: expected {EXPECTED_SHA256}, got {digest}. "
            "The source may have changed or been tampered with."
        )

    target_path.write_bytes(content)
    return target_path


if __name__ == "__main__":
    path = download()
    print(f"Saved seed dataset to {path}")  # noqa: T201 - CLI script output
    sys.exit(0)
