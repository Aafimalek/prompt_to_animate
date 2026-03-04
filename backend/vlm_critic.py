from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return {}
    snippet = text[start : end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _load_client() -> OpenAI | None:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    base_url = (os.environ.get("OPENAI_BASE_URL") or "").strip()
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _image_to_data_url(path: Path) -> str:
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def run_vlm_keyframe_critic(
    image_paths: List[Path],
    topic_hint: str = "",
    model: str | None = None,
) -> List[Dict[str, Any]]:
    client = _load_client()
    if client is None:
        return []
    if not image_paths:
        return []

    image_blocks = []
    for path in image_paths[:3]:
        if not path.exists():
            continue
        image_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": _image_to_data_url(path)},
            }
        )
    if not image_blocks:
        return []

    chosen_model = (model or os.environ.get("MANIM_VLM_MODEL") or "gpt-4o-mini").strip()

    prompt = (
        "You are a strict visual QA critic for educational animation frames.\n"
        "Find layout bugs only: text overlap, clipping, out-of-frame, unreadably small text, crowded labels.\n"
        "Return JSON only with format:\n"
        '{"issues":[{"severity":"error|warning","issue_type":"string","message":"string","frame_index":0,"details":{}}]}.\n'
        f"Topic hint: {topic_hint[:200]}"
    )

    try:
        response = client.chat.completions.create(
            model=chosen_model,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}, *image_blocks],
                }
            ],
            max_tokens=600,
        )
    except Exception:
        return []

    text = ""
    try:
        choice = response.choices[0]
        message_content = choice.message.content
        if isinstance(message_content, str):
            text = message_content
        elif isinstance(message_content, list):
            for part in message_content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text += str(part.get("text", ""))
    except Exception:
        return []

    parsed = _extract_json_object(text)
    issues = parsed.get("issues")
    if not isinstance(issues, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        normalized.append(
            {
                "severity": str(issue.get("severity", "warning")),
                "issue_type": str(issue.get("issue_type", "vlm_feedback")),
                "message": str(issue.get("message", "VLM flagged a layout issue")),
                "frame_index": int(issue.get("frame_index", -1)),
                "details": issue.get("details", {}) if isinstance(issue.get("details"), dict) else {},
            }
        )
    return normalized

