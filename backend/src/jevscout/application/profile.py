"""Local JSON storage for user profiles."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


class ProfileStore:
    """Store profile documents and create private per-user file directories."""

    _USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @classmethod
    def _safe_username(cls, username: str) -> str:
        if not isinstance(username, str) or not cls._USERNAME.fullmatch(username):
            raise ValueError("invalid username")
        return username

    def _user_dir(self, username: str) -> Path:
        safe_name = self._safe_username(username)
        path = self.root / safe_name
        # Resolve and verify ancestry to avoid following a pre-existing symlink
        # out of the configured user-assets directory.
        resolved_root = self.root.resolve()
        resolved = path.resolve()
        if resolved.parent != resolved_root:
            raise ValueError("invalid username")
        path.mkdir(mode=0o700, exist_ok=True)
        files_dir = path / "files"
        files_dir.mkdir(mode=0o700, exist_ok=True)
        if files_dir.resolve().parent != resolved:
            raise ValueError("invalid user files directory")
        return path

    @staticmethod
    def _atomic_json(path: Path, document: dict[str, Any]) -> None:
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".profile-", delete=False,
            ) as temporary:
                temporary_name = temporary.name
                json.dump(document, temporary, ensure_ascii=False, sort_keys=True, allow_nan=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def exists(self, username: str) -> bool:
        user_dir = self._user_dir(username)
        path = user_dir / "profile.json"
        return path.is_file() and not path.is_symlink()

    def get(self, username: str) -> dict[str, Any]:
        user_dir = self._user_dir(username)
        path = user_dir / "profile.json"
        if not path.exists():
            return {
                "username": username,
                "freeform_context": "",
                "structured_fields": {
                    "role_target": "Software Engineer",
                    "primary_skills": [],
                    "experience_years": 3.0,
                    "preferred_locations": ["India"],
                    "remote_only": False,
                    "secondary_skills": [],
                    "min_salary_inr": None,
                },
            }
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid profile storage")
        with path.open("r", encoding="utf-8") as source:
            document = json.load(source)
        if not isinstance(document, dict) or document.get("username") != username:
            raise ValueError("stored profile has an invalid format")
        return document

    def put(self, username: str, *, freeform_context: str, structured_fields: dict[str, Any]) -> dict[str, Any]:
        self._safe_username(username)
        if not isinstance(freeform_context, str) or not isinstance(structured_fields, dict):
            raise TypeError("invalid profile")
        document = {
            "username": username,
            "freeform_context": freeform_context,
            "structured_fields": structured_fields,
        }
        json.dumps(document, ensure_ascii=False, allow_nan=False)
        user_dir = self._user_dir(username)
        profile_path = user_dir / "profile.json"
        if profile_path.is_symlink():
            raise ValueError("invalid profile storage")
        self._atomic_json(profile_path, document)
        return document
