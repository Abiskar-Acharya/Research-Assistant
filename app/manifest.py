"""
Paper Manifest Manager for ArXivMind

Tracks indexed papers with SHA-256 hashes for deduplication,
metadata (title, page count, chunk count), and indexing timestamps.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

MANIFEST_PATH = Path("/app/data/manifest.json")


class ManifestManager:
    def __init__(self, manifest_path: Path = MANIFEST_PATH):
        self.manifest_path = manifest_path
        self._data: Dict = self._load()

    def _load(self) -> Dict:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                return json.load(f)
        return {"papers": {}}

    def _save(self):
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def compute_hash(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def is_indexed(self, filename: str, sha256: str) -> bool:
        entry = self._data["papers"].get(filename)
        return entry is not None and entry.get("sha256") == sha256

    def add_paper(self, filename: str, title: str, page_count: int, chunk_count: int, sha256: str):
        self._data["papers"][filename] = {
            "title": title,
            "page_count": page_count,
            "chunk_count": chunk_count,
            "sha256": sha256,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def remove_paper(self, filename: str):
        self._data["papers"].pop(filename, None)
        self._save()

    def get_papers(self) -> List[Dict]:
        return [
            {"filename": k, **v}
            for k, v in self._data["papers"].items()
        ]

    def get_paper(self, filename: str) -> Optional[Dict]:
        entry = self._data["papers"].get(filename)
        if entry:
            return {"filename": filename, **entry}
        return None
