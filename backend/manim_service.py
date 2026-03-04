import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .visual_quality import analyze_visual_log_file, merge_external_issues
from .vlm_critic import run_vlm_keyframe_critic

# Resolution to Manim quality flag mapping
QUALITY_FLAGS = {
    "720p": "-qm",   # 720p @ 30fps (medium quality)
    "1080p": "-qh",  # 1080p @ 60fps (high quality)
    "4k": "-qk",     # 4K @ 60fps (production quality)
}

QA_SCENE_CLASS = "GenSceneVisualQA"
QA_QUALITY_FLAG = "-ql"
RENDER_TIMEOUT_SECONDS = 180
QA_TIMEOUT_SECONDS = 180
MAX_RENDER_TIMEOUT_SECONDS = 3600

LENGTH_TARGET_SECONDS = {
    "Medium (15s)": 20,
    "Long (1m)": 65,
    "Deep Dive (2m)": 130,
    "Extended (5m)": 320,
}

RESOLUTION_TIMEOUT_FACTOR = {
    "720p": 1.6,
    "1080p": 2.1,
    "4k": 2.8,
}


def _load_bool_env(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_int_env(name: str, default: int, minimum: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(minimum, value)


MANIM_VLM_CRITIC_ENABLED = _load_bool_env("MANIM_VLM_CRITIC_ENABLED", default=False)
MANIM_VLM_CRITIC_FRAME_COUNT = _load_int_env("MANIM_VLM_CRITIC_FRAME_COUNT", default=1, minimum=1)


def _get_runtime_temp_dir() -> Path:
    configured = (os.environ.get("MANIM_TEMP_DIR") or "").strip()
    if configured:
        temp_root = Path(configured).resolve()
    else:
        temp_root = Path(tempfile.gettempdir()) / "prompt_to_animate_manim"
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def _compute_render_timeout_seconds(length: str | None, resolution: str) -> int:
    base_timeout = _load_int_env("MANIM_RENDER_TIMEOUT_SECONDS", RENDER_TIMEOUT_SECONDS, 30)
    max_timeout = _load_int_env("MANIM_RENDER_TIMEOUT_MAX_SECONDS", MAX_RENDER_TIMEOUT_SECONDS, base_timeout)

    if not length:
        return min(base_timeout, max_timeout)

    target_seconds = LENGTH_TARGET_SECONDS.get(length, 60)
    factor = RESOLUTION_TIMEOUT_FACTOR.get(resolution, 2.0)
    # Includes fixed setup/teardown overhead for ffmpeg + scene assembly.
    computed = int(target_seconds * factor + 120)
    return min(max(base_timeout, computed), max_timeout)


def _extract_clean_error(error_msg: str) -> str:
    import re

    lines = (error_msg or "").split("\n")
    filtered_lines = []
    for line in lines:
        if re.search(r"\d+%\s*\|", line):
            continue
        if line.startswith("Animation ") and "it/s]" in line:
            continue
        filtered_lines.append(line)

    clean_msg = "\n".join(filtered_lines)
    error_match = re.search(
        r"(TypeError|AttributeError|ValueError|NameError|SyntaxError|KeyError|IndexError|RuntimeError|FileNotFoundError|OSError):\s*(.+)",
        clean_msg,
    )

    if error_match:
        error_type = error_match.group(1)
        error_detail = error_match.group(2).strip()[:500]
        return f"Code error ({error_type}): {error_detail}"

    meaningful = [line.strip() for line in filtered_lines if line.strip() and not line.startswith("+")]
    return meaningful[-1] if meaningful else "Rendering failed. Please try a simpler prompt."


def _run_manim(
    script_path: Path,
    scene_name: str,
    quality_flag: str,
    media_dir: Path,
    timeout_seconds: int,
    extra_env: Dict[str, str] | None = None,
    extra_args: List[str] | None = None,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "manim",
        quality_flag,
        "--disable_caching",
        "--media_dir",
        str(media_dir),
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend([str(script_path), scene_name])

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    print(f"Executing Manim (Cairo renderer): {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
        env=env,
    )


def _find_scene_outputs(output_root: Path, script_name: str) -> Tuple[Path, list[Path]]:
    scene_folder_name = script_name.replace(".py", "")
    search_path = output_root / "videos" / scene_folder_name
    found_videos = list(search_path.rglob("GenScene.mp4"))
    if not found_videos:
        found_videos = list(search_path.rglob("*.mp4"))
    return search_path, found_videos


def _cleanup_script_and_scene(script_path: Path, scene_folder: Path) -> None:
    try:
        if script_path.exists():
            os.remove(script_path)
    except OSError:
        pass

    try:
        if scene_folder.exists():
            shutil.rmtree(scene_folder, ignore_errors=True)
    except OSError:
        pass


def _truncate_code_to_sections(code: str, keep_sections: int) -> str:
    """
    Keep only the first N construct sections identified by comments.

    A section marker is any comment line inside construct() starting with:
      - # section ...
      - # scene ...
      - # --- ...
    """
    if keep_sections <= 0:
        return code

    lines = code.split("\n")
    section_pattern = re.compile(r"^\s*#\s*(section|scene|---)", flags=re.IGNORECASE)

    def _indent_of(line: str) -> int:
        return len(line) - len(line.lstrip())

    construct_index = -1
    construct_indent = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("def construct(") and stripped.endswith(":"):
            construct_index = idx
            construct_indent = _indent_of(line)
            break

    if construct_index < 0:
        return code

    section_count = 0
    insert_return_at: Optional[int] = None
    for idx in range(construct_index + 1, len(lines)):
        line = lines[idx]
        stripped = line.strip()
        if stripped and _indent_of(line) <= construct_indent:
            break
        if section_pattern.match(line):
            section_count += 1
            if section_count > keep_sections:
                insert_return_at = idx
                break

    if insert_return_at is None:
        return code

    body_indent = construct_indent + 4
    for idx in range(construct_index + 1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue
        if _indent_of(lines[idx]) > construct_indent:
            body_indent = _indent_of(lines[idx])
            break

    lines.insert(insert_return_at, " " * body_indent + "return")
    return "\n".join(lines)


def execute_manim_code(
    code: str,
    upload_to_s3: bool = True,
    resolution: str = "1080p",
    length: str | None = None,
    preview_sections: int | None = None,
) -> tuple[str, str]:
    """
    Execute Manim code and return the uploaded S3 key and/or local output filename.
    """
    file_id = str(uuid.uuid4())
    filename = f"scene_{file_id}.py"

    temp_dir = _get_runtime_temp_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    filepath = temp_dir / filename
    render_code = code
    if preview_sections is not None and preview_sections > 0:
        render_code = _truncate_code_to_sections(code, preview_sections)

    filepath.write_text(render_code, encoding="utf-8")

    output_root = Path("generated_animations").resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    quality_flag = QUALITY_FLAGS.get(resolution, "-qh")
    render_timeout_seconds = _compute_render_timeout_seconds(length=length, resolution=resolution)
    print(
        f"Rendering at {resolution} using {quality_flag} "
        f"(timeout {render_timeout_seconds}s, length={length or 'unknown'})"
    )

    try:
        result = _run_manim(
            script_path=filepath,
            scene_name="GenScene",
            quality_flag=quality_flag,
            media_dir=output_root,
            timeout_seconds=render_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        _cleanup_script_and_scene(filepath, output_root / "videos" / filename.replace(".py", ""))
        raise Exception(
            f"Code error (TimeoutError): Manim render exceeded {render_timeout_seconds}s timeout. "
            "Simplify the animation (fewer objects, lower resolution, shorter duration)."
        )
    except FileNotFoundError:
        raise Exception("Manim command not found. Please ensure manim is installed and in your PATH.")

    search_path, found_videos = _find_scene_outputs(output_root, filename)

    if result.returncode != 0:
        _cleanup_script_and_scene(filepath, search_path)
        raise Exception(_extract_clean_error(result.stderr or result.stdout or "Unknown error"))

    if not found_videos:
        _cleanup_script_and_scene(filepath, search_path)
        raise Exception("Video file was not generated at expected path. Check Manim logs.")

    expected_path = found_videos[0]
    final_filename = f"{file_id}.mp4"
    final_path = output_root / final_filename
    shutil.move(str(expected_path), str(final_path))

    _cleanup_script_and_scene(filepath, search_path)

    s3_key = None
    if upload_to_s3:
        try:
            from .s3_service import upload_video_to_s3
            s3_key = upload_video_to_s3(str(final_path))
            print(f"Video uploaded to S3: {s3_key}")
            try:
                os.remove(final_path)
            except OSError as exc:
                print(f"Warning: Could not delete local file: {exc}")
        except Exception as exc:
            print(f"Warning: S3 upload failed, keeping local file: {exc}")
            return (None, final_filename)

    return (s3_key, final_filename)


def _build_visual_qa_script(code: str) -> str:
    qa_wrapper = f'''

import json as _qa_json
import os as _qa_os

class {QA_SCENE_CLASS}(GenScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qa_snapshots = []
        self._qa_frame = {{
            "x_radius": float(config.frame_x_radius),
            "y_radius": float(config.frame_y_radius),
        }}

    def _qa_is_text_like(self, mob_type: str) -> bool:
        return (
            "Text" in mob_type
            or "Tex" in mob_type
            or mob_type in {{"Paragraph", "DecimalNumber"}}
        )

    def _qa_capture(self, event_name: str):
        snapshot = {{"event": event_name, "mobjects": []}}
        for mob in list(getattr(self, "mobjects", [])):
            try:
                members = mob.family_members_with_points()
            except Exception:
                members = []
            if not members:
                continue

            try:
                left = float(mob.get_critical_point(LEFT)[0])
                right = float(mob.get_critical_point(RIGHT)[0])
                top = float(mob.get_critical_point(UP)[1])
                bottom = float(mob.get_critical_point(DOWN)[1])
            except Exception:
                continue

            m_type = mob.__class__.__name__
            snapshot["mobjects"].append(
                {{
                    "id": f"{{m_type}}:{{id(mob)}}",
                    "type": m_type,
                    "is_text": self._qa_is_text_like(m_type),
                    "bounds": {{
                        "left": left,
                        "right": right,
                        "top": top,
                        "bottom": bottom,
                    }},
                }}
            )

        self._qa_snapshots.append(snapshot)

    def add(self, *mobjects):
        result = super().add(*mobjects)
        self._qa_capture("add")
        return result

    def play(self, *args, **kwargs):
        result = super().play(*args, **kwargs)
        self._qa_capture("play")
        return result

    def wait(self, *args, **kwargs):
        result = super().wait(*args, **kwargs)
        self._qa_capture("wait")
        return result

    def clear(self):
        result = super().clear()
        self._qa_capture("clear")
        return result

    def construct(self):
        super().construct()
        self._qa_capture("final")
        report_path = _qa_os.environ.get("MANIM_VISUAL_QA_OUTPUT")
        if report_path:
            payload = {{
                "frame": self._qa_frame,
                "snapshots": self._qa_snapshots,
            }}
            with open(report_path, "w", encoding="utf-8") as _qa_f:
                _qa_json.dump(payload, _qa_f)
'''
    return f"{code.rstrip()}\n{qa_wrapper}\n"


def _render_vlm_keyframes(
    script_path: Path,
    output_root: Path,
    frame_count: int,
) -> List[Path]:
    if frame_count <= 0:
        return []

    try:
        result = _run_manim(
            script_path=script_path,
            scene_name=QA_SCENE_CLASS,
            quality_flag=QA_QUALITY_FLAG,
            media_dir=output_root,
            timeout_seconds=min(QA_TIMEOUT_SECONDS, 90),
            extra_args=["-s", "--format", "png"],
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    scene_name = script_path.stem
    image_folder = output_root / "images" / scene_name
    if not image_folder.exists():
        return []

    images = sorted(image_folder.rglob("*.png"))
    return images[: max(1, frame_count)]


def run_visual_quality_check(
    code: str,
    mode: str = "balanced",
    topic_hint: str = "",
) -> Dict[str, object]:
    """
    Run a low-quality QA render and return visual quality diagnostics.
    """
    qa_file_id = str(uuid.uuid4())
    script_name = f"scene_{qa_file_id}_qa.py"

    temp_dir = _get_runtime_temp_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    script_path = temp_dir / script_name
    report_path = temp_dir / f"visual_qa_report_{qa_file_id}.json"
    script_path.write_text(_build_visual_qa_script(code), encoding="utf-8")

    output_root = Path("generated_animations/qa").resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        result = _run_manim(
            script_path=script_path,
            scene_name=QA_SCENE_CLASS,
            quality_flag=QA_QUALITY_FLAG,
            media_dir=output_root,
            timeout_seconds=QA_TIMEOUT_SECONDS,
            extra_env={"MANIM_VISUAL_QA_OUTPUT": str(report_path)},
        )
    except subprocess.TimeoutExpired:
        _cleanup_script_and_scene(script_path, output_root / "videos" / script_name.replace(".py", ""))
        if report_path.exists():
            report_path.unlink(missing_ok=True)
        raise Exception(
            f"Code error (TimeoutError): Visual QA render exceeded {QA_TIMEOUT_SECONDS}s timeout."
        )
    except FileNotFoundError:
        raise Exception("Manim command not found. Please ensure manim is installed and in your PATH.")

    scene_name = script_name.replace(".py", "")
    scene_folder, _ = _find_scene_outputs(output_root, script_name)
    image_folder = output_root / "images" / scene_name

    if result.returncode != 0 and not report_path.exists():
        _cleanup_script_and_scene(script_path, scene_folder)
        if image_folder.exists():
            shutil.rmtree(image_folder, ignore_errors=True)
        raise Exception(_extract_clean_error(result.stderr or result.stdout or "Unknown error"))

    if not report_path.exists():
        _cleanup_script_and_scene(script_path, scene_folder)
        if image_folder.exists():
            shutil.rmtree(image_folder, ignore_errors=True)
        raise Exception("Visual QA failed: report file was not generated.")

    report = analyze_visual_log_file(report_path, mode=mode).to_dict()

    if MANIM_VLM_CRITIC_ENABLED:
        keyframes = _render_vlm_keyframes(
            script_path=script_path,
            output_root=output_root,
            frame_count=MANIM_VLM_CRITIC_FRAME_COUNT,
        )
        vlm_issues = run_vlm_keyframe_critic(keyframes, topic_hint=topic_hint)
        if vlm_issues:
            report = merge_external_issues(report, vlm_issues, source_label="vlm")

    keep_artifacts = _load_bool_env("MANIM_VISUAL_QA_LOG_ARTIFACTS", default=False)
    if not keep_artifacts:
        _cleanup_script_and_scene(script_path, scene_folder)
        if image_folder.exists():
            shutil.rmtree(image_folder, ignore_errors=True)
        report_path.unlink(missing_ok=True)

    return report
