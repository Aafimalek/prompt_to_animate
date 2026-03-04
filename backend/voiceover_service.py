from __future__ import annotations

from typing import Any, Dict, List


def build_voiceover_script(
    prompt: str,
    scene_plan: Dict[str, Any],
    provided_voiceover_text: str | None = None,
) -> Dict[str, Any]:
    scenes = scene_plan.get("scenes") if isinstance(scene_plan, dict) else []
    if not isinstance(scenes, list):
        scenes = []

    if provided_voiceover_text and provided_voiceover_text.strip():
        script_text = provided_voiceover_text.strip()
        chunks = [line.strip() for line in script_text.splitlines() if line.strip()]
        if not chunks:
            chunks = [script_text]
    else:
        chunks = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            purpose = str(scene.get("purpose", "")).strip()
            focus = scene.get("focus_targets") if isinstance(scene.get("focus_targets"), list) else []
            focus_text = ", ".join(str(item) for item in focus[:2]) if focus else "key visual"
            chunks.append(f"{purpose}. Focus on {focus_text}.")

    timed_chunks: List[Dict[str, Any]] = []
    cursor = 0
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        duration = scene.get("duration_seconds", 8)
        try:
            duration_i = max(1, int(duration))
        except (TypeError, ValueError):
            duration_i = 8
        text = chunks[index] if index < len(chunks) else chunks[-1] if chunks else prompt
        timed_chunks.append(
            {
                "scene_name": str(scene.get("name", f"Scene {index + 1}")),
                "start_second": cursor,
                "end_second": cursor + duration_i,
                "duration_seconds": duration_i,
                "text": text,
            }
        )
        cursor += duration_i

    return {
        "enabled": bool(timed_chunks),
        "total_seconds": cursor,
        "chunks": timed_chunks,
    }


def voiceover_script_to_srt(script: Dict[str, Any]) -> str:
    chunks = script.get("chunks") if isinstance(script, dict) else []
    if not isinstance(chunks, list):
        return ""

    def _format_timestamp(second: int) -> str:
        s = max(0, int(second))
        hour = s // 3600
        minute = (s % 3600) // 60
        sec = s % 60
        return f"{hour:02d}:{minute:02d}:{sec:02d},000"

    lines: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            continue
        start = int(chunk.get("start_second", 0))
        end = int(chunk.get("end_second", start + 1))
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        lines.append(str(idx))
        lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()


def build_word_timing(script: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks = script.get("chunks") if isinstance(script, dict) else []
    if not isinstance(chunks, list):
        return []

    word_timing: List[Dict[str, Any]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        start = int(chunk.get("start_second", 0))
        end = int(chunk.get("end_second", start + 1))
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        words = [w for w in text.split() if w]
        if not words:
            continue
        total = max(1, end - start)
        step = total / float(len(words))
        cursor = float(start)
        for word in words:
            next_cursor = min(float(end), cursor + step)
            word_timing.append(
                {
                    "word": word,
                    "start": round(cursor, 3),
                    "end": round(next_cursor, 3),
                }
            )
            cursor = next_cursor
    return word_timing


def script_to_voiceover_metadata(script: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "enabled": bool(script.get("enabled", False)),
        "total_seconds": int(script.get("total_seconds", 0)),
        "chunks": script.get("chunks", []),
        "subtitles_srt": voiceover_script_to_srt(script),
        "word_timing": build_word_timing(script),
    }
