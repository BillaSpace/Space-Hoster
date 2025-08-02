import zipfile, os, json, re
from typing import Dict, Any

class BotValidator:
    @staticmethod
    def validate_zip(zip_path: str, max_mb: int) -> Dict[str, Any]:
        try:
            if os.path.getsize(zip_path) > max_mb * 1024 * 1024:
                return {"ok": False, "error": "File too large"}
            with zipfile.ZipFile(zip_path) as z:
                names = z.namelist()
                if not any(n.endswith((".py", ".js", ".jar")) for n in names):
                    return {"ok": False, "error": "No executable files found"}
            return {"ok": True}
        except zipfile.BadZipFile:
            return {"ok": False, "error": "Bad ZIP archive"}

class TokenValidator:
    PATTERN = re.compile(r"^\d{8,10}:[A-Za-z0-9_-]{35}$")

    @classmethod
    def looks_like_token(cls, txt: str) -> bool:
        return bool(cls.PATTERN.match(txt.strip()))
