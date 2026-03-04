from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


DEFAULT_PLAY_SECONDS = 1.2
DEFAULT_WAIT_SECONDS = 1.0


@dataclass
class DurationEstimate:
    total_seconds: float
    wait_seconds: float
    play_seconds: float
    wait_calls: int
    play_calls: int


def _numeric_literal(node: ast.AST | None) -> float | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _numeric_literal(node.operand)
        if value is None:
            return None
        return value if isinstance(node.op, ast.UAdd) else -value
    return None


def estimate_code_duration_seconds(code: str) -> DurationEstimate:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return DurationEstimate(
            total_seconds=0.0,
            wait_seconds=0.0,
            play_seconds=0.0,
            wait_calls=0,
            play_calls=0,
        )

    wait_seconds = 0.0
    play_seconds = 0.0
    wait_calls = 0
    play_calls = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "wait":
                wait_calls += 1
                arg_duration = (
                    _numeric_literal(node.args[0]) if node.args else DEFAULT_WAIT_SECONDS
                )
                if arg_duration is None:
                    arg_duration = DEFAULT_WAIT_SECONDS
                wait_seconds += max(0.0, arg_duration)
            elif node.func.attr == "play":
                play_calls += 1
                run_time = None
                for kw in node.keywords:
                    if kw.arg == "run_time":
                        run_time = _numeric_literal(kw.value)
                        break
                if run_time is None:
                    run_time = DEFAULT_PLAY_SECONDS
                play_seconds += max(0.0, run_time)

    total = wait_seconds + play_seconds
    return DurationEstimate(
        total_seconds=total,
        wait_seconds=wait_seconds,
        play_seconds=play_seconds,
        wait_calls=wait_calls,
        play_calls=play_calls,
    )


def build_scene_timeline(scene_plan: Dict[str, Any]) -> Dict[str, Any]:
    scenes = scene_plan.get("scenes")
    if not isinstance(scenes, list):
        return {"total_seconds": 0, "scene_windows": []}

    total = 0
    windows: List[Dict[str, Any]] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        duration = scene.get("duration_seconds", 0)
        try:
            dur_i = max(1, int(duration))
        except (TypeError, ValueError):
            dur_i = 1
        start = total
        end = start + dur_i
        total = end
        windows.append(
            {
                "scene_name": str(scene.get("name", f"Scene {len(windows) + 1}")),
                "start_second": start,
                "end_second": end,
                "duration_seconds": dur_i,
            }
        )

    return {"total_seconds": total, "scene_windows": windows}


def _replace_scaled_literals(pattern: str, code: str, scale: float) -> str:
    compiled = re.compile(pattern, flags=re.IGNORECASE)

    def _repl(match: re.Match[str]) -> str:
        prefix = match.group(1)
        value_raw = match.group(2)
        suffix = match.group(3)
        try:
            value = float(value_raw)
        except ValueError:
            return match.group(0)
        scaled = max(0.05, value * scale)
        return f"{prefix}{scaled:.2f}{suffix}"

    return compiled.sub(_repl, code)


def rescale_code_timing(
    code: str,
    target_min: int,
    target_max: int,
    min_scale: float = 0.55,
    max_scale: float = 1.9,
) -> Tuple[str, DurationEstimate]:
    estimate = estimate_code_duration_seconds(code)
    if estimate.total_seconds <= 0.0:
        return code, estimate

    if target_min <= estimate.total_seconds <= target_max:
        return code, estimate

    target_mid = max(1.0, (target_min + target_max) / 2.0)
    raw_scale = target_mid / max(estimate.total_seconds, 0.1)
    scale = max(min_scale, min(max_scale, raw_scale))

    if abs(scale - 1.0) < 0.06:
        return code, estimate

    updated = code
    updated = _replace_scaled_literals(
        r"(\bself\.wait\(\s*)([0-9]+(?:\.[0-9]+)?)(\s*\))",
        updated,
        scale,
    )
    updated = _replace_scaled_literals(
        r"(\brun_time\s*=\s*)([0-9]+(?:\.[0-9]+)?)(\b)",
        updated,
        scale,
    )
    return updated, estimate_code_duration_seconds(updated)


def pacing_error(
    estimate: DurationEstimate,
    target_min: int,
    target_max: int,
    tolerance_seconds: int = 10,
) -> str | None:
    lower = max(1, target_min - tolerance_seconds)
    upper = target_max + tolerance_seconds
    if estimate.total_seconds < lower:
        return (
            f"Insufficient pacing duration: estimated {estimate.total_seconds:.1f}s, "
            f"require >= {lower}s"
        )
    if estimate.total_seconds > upper:
        return (
            f"Excessive pacing duration: estimated {estimate.total_seconds:.1f}s, "
            f"require <= {upper}s"
        )
    return None

