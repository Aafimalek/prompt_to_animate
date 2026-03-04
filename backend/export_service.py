from __future__ import annotations

import re
from typing import Any, Dict, List

from .pacing import estimate_code_duration_seconds


SECTION_PATTERN = re.compile(r"^\s*#\s*(?:section|scene)\b[:\-\s]*(.+)$", re.IGNORECASE)


def extract_section_labels(code: str) -> List[str]:
    labels: List[str] = []
    for line in (code or "").splitlines():
        match = SECTION_PATTERN.match(line)
        if not match:
            continue
        label = match.group(1).strip() or f"Section {len(labels) + 1}"
        labels.append(label)
    if not labels:
        labels = ["Intro", "Core Idea", "Summary"]
    return labels


def build_interactive_manifest(
    code: str,
    title: str,
    length: str,
    scene_plan: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    labels = extract_section_labels(code)
    duration = estimate_code_duration_seconds(code).total_seconds
    if duration <= 0:
        duration = 30.0
    chapter_seconds = max(1.0, duration / max(1, len(labels)))
    chapters: List[Dict[str, Any]] = []
    for i, label in enumerate(labels):
        start = int(round(i * chapter_seconds))
        end = int(round((i + 1) * chapter_seconds))
        chapters.append(
            {
                "id": i + 1,
                "label": label,
                "start_second": start,
                "end_second": end,
            }
        )

    return {
        "title": title or "Interactive Export",
        "length": length,
        "estimated_duration_seconds": int(round(duration)),
        "chapters": chapters,
        "scene_plan_title": (scene_plan or {}).get("title", ""),
    }


def build_manim_slides_outline(manifest: Dict[str, Any]) -> str:
    chapters = manifest.get("chapters", [])
    lines = [
        "# Manim Slides Outline",
        "",
        f"Title: {manifest.get('title', '')}",
        "",
    ]
    for chapter in chapters:
        label = chapter.get("label", "Chapter")
        start = chapter.get("start_second", 0)
        end = chapter.get("end_second", start)
        lines.append(f"- [{start:>4}s - {end:>4}s] {label}")
    lines.append("")
    lines.append("Use this with manim-slides to map slide breakpoints.")
    return "\n".join(lines)

