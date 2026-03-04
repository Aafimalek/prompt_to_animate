from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import json


TEXT_TYPE_MARKERS = (
    "Text",
    "Tex",
    "MathTex",
    "MarkupText",
    "Paragraph",
    "DecimalNumber",
)


@dataclass
class QualityIssue:
    severity: str
    issue_type: str
    message: str
    frame_index: int
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "issue_type": self.issue_type,
            "message": self.message,
            "frame_index": self.frame_index,
            "details": self.details,
        }


@dataclass
class QualityReport:
    passed: bool
    score: int
    error_count: int
    warning_count: int
    frames_analyzed: int
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "frames_analyzed": self.frames_analyzed,
            "issues": [issue.to_dict() for issue in self.issues],
            "metrics": self.metrics,
        }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_text_like(mobject_type: str) -> bool:
    return any(marker in (mobject_type or "") for marker in TEXT_TYPE_MARKERS)


def _intersection_area(a: Dict[str, float], b: Dict[str, float]) -> float:
    overlap_left = max(a["left"], b["left"])
    overlap_right = min(a["right"], b["right"])
    overlap_bottom = max(a["bottom"], b["bottom"])
    overlap_top = min(a["top"], b["top"])

    overlap_w = max(0.0, overlap_right - overlap_left)
    overlap_h = max(0.0, overlap_top - overlap_bottom)
    return overlap_w * overlap_h


def _parse_snapshot_mobjects(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    raw_mobjects = snapshot.get("mobjects")
    if not isinstance(raw_mobjects, list):
        return parsed

    for raw in raw_mobjects:
        if not isinstance(raw, dict):
            continue
        bounds = raw.get("bounds")
        if not isinstance(bounds, dict):
            continue

        left = _safe_float(bounds.get("left"))
        right = _safe_float(bounds.get("right"))
        top = _safe_float(bounds.get("top"))
        bottom = _safe_float(bounds.get("bottom"))
        width = max(0.0, right - left)
        height = max(0.0, top - bottom)

        if width <= 0.0 or height <= 0.0:
            continue

        m_type = str(raw.get("type", ""))
        parsed.append(
            {
                "id": str(raw.get("id", "unknown")),
                "type": m_type,
                "is_text": bool(raw.get("is_text", _is_text_like(m_type))),
                "bounds": {
                    "left": left,
                    "right": right,
                    "top": top,
                    "bottom": bottom,
                },
                "width": width,
                "height": height,
            }
        )
    return parsed


def _mode_thresholds(mode: str) -> Dict[str, float]:
    normalized = (mode or "balanced").strip().lower()
    if normalized == "max":
        return {
            "overlap_error_ratio": 0.15,
            "overlap_warning_ratio": 0.08,
            "max_text_blocks": 4,
            "edge_warning_margin": 0.35,
        }

    return {
        "overlap_error_ratio": 0.20,
        "overlap_warning_ratio": 0.10,
        "max_text_blocks": 5,
        "edge_warning_margin": 0.25,
    }


def analyze_visual_snapshots(payload: Dict[str, Any], mode: str = "balanced") -> QualityReport:
    frame = payload.get("frame") if isinstance(payload, dict) else {}
    if not isinstance(frame, dict):
        frame = {}
    x_radius = _safe_float(frame.get("x_radius"), 7.0)
    y_radius = _safe_float(frame.get("y_radius"), 4.0)

    snapshots = payload.get("snapshots") if isinstance(payload, dict) else []
    if not isinstance(snapshots, list):
        snapshots = []

    thresholds = _mode_thresholds(mode)
    issues: List[QualityIssue] = []
    out_of_frame_count = 0
    overlap_error_count = 0
    overlap_warning_count = 0
    crowding_warning_count = 0

    for frame_index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            continue

        mobjects = _parse_snapshot_mobjects(snapshot)
        if not mobjects:
            continue

        text_like = [m for m in mobjects if m["is_text"]]

        for mob in text_like:
            b = mob["bounds"]
            outside = (
                b["left"] < -x_radius
                or b["right"] > x_radius
                or b["top"] > y_radius
                or b["bottom"] < -y_radius
            )
            near_edge = (
                b["left"] < (-x_radius + thresholds["edge_warning_margin"])
                or b["right"] > (x_radius - thresholds["edge_warning_margin"])
                or b["top"] > (y_radius - thresholds["edge_warning_margin"])
                or b["bottom"] < (-y_radius + thresholds["edge_warning_margin"])
            )

            if outside:
                out_of_frame_count += 1
                issues.append(
                    QualityIssue(
                        severity="error",
                        issue_type="out_of_frame",
                        message=f"{mob['type']} is out of frame in checkpoint {frame_index}",
                        frame_index=frame_index,
                        details={
                            "id": mob["id"],
                            "bounds": b,
                            "frame": {
                                "x_radius": x_radius,
                                "y_radius": y_radius,
                            },
                        },
                    )
                )
            elif near_edge:
                issues.append(
                    QualityIssue(
                        severity="warning",
                        issue_type="near_frame_edge",
                        message=f"{mob['type']} is too close to frame edge in checkpoint {frame_index}",
                        frame_index=frame_index,
                        details={"id": mob["id"], "bounds": b},
                    )
                )

        if len(text_like) > int(thresholds["max_text_blocks"]):
            crowding_warning_count += 1
            issues.append(
                QualityIssue(
                    severity="warning",
                    issue_type="text_crowding",
                    message=(
                        f"Checkpoint {frame_index} has {len(text_like)} text blocks; "
                        f"target <= {int(thresholds['max_text_blocks'])}"
                    ),
                    frame_index=frame_index,
                    details={"text_block_count": len(text_like)},
                )
            )

        for i in range(len(text_like)):
            for j in range(i + 1, len(text_like)):
                a = text_like[i]
                b = text_like[j]
                inter = _intersection_area(a["bounds"], b["bounds"])
                if inter <= 0.0:
                    continue
                min_area = min(a["width"] * a["height"], b["width"] * b["height"])
                if min_area <= 0.0:
                    continue

                overlap_ratio = inter / min_area
                if overlap_ratio >= float(thresholds["overlap_error_ratio"]):
                    overlap_error_count += 1
                    issues.append(
                        QualityIssue(
                            severity="error",
                            issue_type="text_overlap",
                            message=(
                                f"Text overlap ratio {overlap_ratio:.2f} in checkpoint {frame_index}"
                            ),
                            frame_index=frame_index,
                            details={
                                "ids": [a["id"], b["id"]],
                                "types": [a["type"], b["type"]],
                                "overlap_ratio": overlap_ratio,
                            },
                        )
                    )
                elif overlap_ratio >= float(thresholds["overlap_warning_ratio"]):
                    overlap_warning_count += 1
                    issues.append(
                        QualityIssue(
                            severity="warning",
                            issue_type="text_overlap_warning",
                            message=(
                                f"Minor text overlap ratio {overlap_ratio:.2f} in checkpoint {frame_index}"
                            ),
                            frame_index=frame_index,
                            details={
                                "ids": [a["id"], b["id"]],
                                "overlap_ratio": overlap_ratio,
                            },
                        )
                    )

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")

    score = 100 - (error_count * 20) - (warning_count * 5)
    score = max(0, min(100, score))
    passed = error_count == 0 and score >= 85

    return QualityReport(
        passed=passed,
        score=score,
        error_count=error_count,
        warning_count=warning_count,
        frames_analyzed=len(snapshots),
        issues=issues,
        metrics={
            "out_of_frame_count": out_of_frame_count,
            "overlap_error_count": overlap_error_count,
            "overlap_warning_count": overlap_warning_count,
            "crowding_warning_count": crowding_warning_count,
            "frame_radius": {
                "x": x_radius,
                "y": y_radius,
            },
        },
    )


def load_snapshots(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_visual_log_file(path: Path, mode: str = "balanced") -> QualityReport:
    payload = load_snapshots(path)
    return analyze_visual_snapshots(payload, mode=mode)
