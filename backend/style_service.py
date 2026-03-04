from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
STYLE_FILE = PROMPTS_DIR / "style_packs.json"


@lru_cache(maxsize=1)
def _load_catalog() -> Dict[str, Any]:
    if not STYLE_FILE.exists():
        return {"default_style": "classic_clean", "styles": {}}
    raw = STYLE_FILE.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return {"default_style": "classic_clean", "styles": {}}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"default_style": "classic_clean", "styles": {}}
    if not isinstance(parsed, dict):
        return {"default_style": "classic_clean", "styles": {}}
    styles = parsed.get("styles")
    if not isinstance(styles, dict):
        parsed["styles"] = {}
    default_style = parsed.get("default_style")
    if not isinstance(default_style, str) or not default_style:
        parsed["default_style"] = "classic_clean"
    return parsed


def get_style_catalog() -> Dict[str, Any]:
    catalog = _load_catalog()
    return {
        "default_style": catalog.get("default_style", "classic_clean"),
        "styles": catalog.get("styles", {}),
    }


def resolve_style_pack(style_pack: str | None) -> Dict[str, Any]:
    catalog = _load_catalog()
    styles = catalog.get("styles", {})
    default_key = catalog.get("default_style", "classic_clean")
    selected_key = (style_pack or "").strip()
    if selected_key in styles:
        selected_style = styles[selected_key]
        return {"style_id": selected_key, "tokens": selected_style}
    fallback = styles.get(default_key, {})
    return {"style_id": default_key, "tokens": fallback}

