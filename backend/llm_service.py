import ast
import asyncio
import json
import os
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
import groq
import httpx
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import openai as openai_mod

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Azure OpenAI (primary) – uses the v1 API (no api-version needed)
azure_openai_api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
azure_openai_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2-chat").strip()
azure_openai_base_url = f"{azure_openai_endpoint.rstrip('/')}/openai/v1" if azure_openai_endpoint else ""
if not azure_openai_api_key or not azure_openai_endpoint:
    print(f"Warning: AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT not found in environment. Checked path: {env_path}")

# Groq (fallback)
groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not groq_api_key:
    print(f"Warning: GROQ_API_KEY not found in environment. Checked path: {env_path}")
DEFAULT_GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"

# Cerebras (fallback)
cerebras_api_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
CEREBRAS_BASE_URL = os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1").strip()
DEFAULT_CEREBRAS_MODEL = "qwen-3-235b-a22b-instruct-2507"

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_FILES = {
    "composer_system": "composer_system.md",
    "codegen_system": "codegen_system.md",
    "repair_system": "repair_system.md",
    "runtime_repair_system": "runtime_repair_system.md",
    "visual_repair_system": "visual_repair_system.md",
    "length_profiles": "length_profiles.json",
}

SCENE_PLAN_REQUIRED_KEYS = {"title", "hook", "narrative_arc", "scenes"}
SCENE_REQUIRED_KEYS = {
    "name",
    "purpose",
    "duration_seconds",
    "visuals",
    "technical_notes",
    "layout_zone",
    "camera_strategy",
    "max_concurrent_text_blocks",
    "clear_policy",
    "focus_targets",
}
ALLOWED_SCENE_BASES = {"Scene", "ThreeDScene", "MovingCameraScene"}
FORBIDDEN_MATH_UNICODE = {
    "\u00d7": "\\times",
    "\u00f7": "\\div",
    "\u03c0": "\\pi",
    "\u2248": "\\approx",
    "\u2211": "\\sum",
    "\u221a": "\\sqrt",
    "\u2264": "\\leq",
    "\u2265": "\\geq",
    "\u221e": "\\infty",
    "\u03b8": "\\theta",
}
ANIMATION_FN_NAMES = {
    "Create",
    "Write",
    "FadeIn",
    "FadeOut",
    "Transform",
    "ReplacementTransform",
    "TransformMatchingTex",
    "TransformMatchingShapes",
    "TransformFromCopy",
    "DrawBorderThenFill",
    "GrowFromCenter",
    "GrowArrow",
    "MoveToTarget",
    "Indicate",
    "Circumscribe",
    "Flash",
    "FlashAround",
    "AnimationGroup",
    "Succession",
    "LaggedStart",
    "Uncreate",
    "ShrinkToCenter",
    "Rotate",
    "MoveAlongPath",
}
EXTERNAL_ASSET_MOBJECTS = {"SVGMobject", "ImageMobject"}
FORBIDDEN_TEX_MACROS = {
    r"\checkmark": "Text('OK')",
}

ProgressCallback = Optional[Callable[[str, str], None]]

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

ALLOWED_LAYOUT_ZONES = {
    "golden",
    "top_title_center_visual_bottom_formula",
    "center_focus",
    "split_left_right",
    "grid",
    "full_frame",
}
ALLOWED_CLEAR_POLICIES = {"fade_out", "clear", "retain"}
ALLOWED_CAMERA_STRATEGIES = {
    "static",
    "moving_auto_zoom",
    "manual_zoom_pan",
    "3d_orbit",
}


def _load_int_env(name: str, default: int, minimum: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        print(f"Warning: invalid integer for {name}='{raw_value}', using default {default}")
        return default
    return max(minimum, value)


def _load_float_env(name: str, default: float, minimum: float) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        print(f"Warning: invalid float for {name}='{raw_value}', using default {default}")
        return default
    return max(minimum, value)


def _load_bool_env(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    print(f"Warning: invalid boolean for {name}='{raw_value}', using default {default}")
    return default


def _parse_fallback_models(raw_value: str) -> List[str]:
    parsed: List[str] = []
    seen: Set[str] = set()
    for item in raw_value.split(","):
        model_name = item.strip()
        if not model_name or model_name in seen:
            continue
        parsed.append(model_name)
        seen.add(model_name)
    return parsed


# Groq model candidates (primary)
_primary_groq_model = (os.environ.get("GROQ_MODEL") or "").strip()
PRIMARY_GROQ_MODEL = _primary_groq_model or DEFAULT_GROQ_MODEL
FALLBACK_GROQ_MODELS = _parse_fallback_models(os.environ.get("GROQ_FALLBACK_MODELS", ""))
if PRIMARY_GROQ_MODEL in FALLBACK_GROQ_MODELS:
    FALLBACK_GROQ_MODELS = [m for m in FALLBACK_GROQ_MODELS if m != PRIMARY_GROQ_MODEL]

# Cerebras model candidates (fallback)
_cerebras_model = (os.environ.get("CEREBRAS_MODEL") or "").strip()
CEREBRAS_MODEL = _cerebras_model or DEFAULT_CEREBRAS_MODEL

LLM_TEMPERATURE = _load_float_env("LLM_TEMPERATURE", default=0.2, minimum=0.0)
LLM_RETRY_ATTEMPTS = _load_int_env("LLM_RETRY_ATTEMPTS", default=3, minimum=1)
LLM_RETRY_BASE_SECONDS = _load_float_env("LLM_RETRY_BASE_SECONDS", default=1.0, minimum=0.1)
LLM_RETRY_MAX_SECONDS = _load_float_env("LLM_RETRY_MAX_SECONDS", default=12.0, minimum=0.1)
if LLM_RETRY_MAX_SECONDS < LLM_RETRY_BASE_SECONDS:
    LLM_RETRY_MAX_SECONDS = LLM_RETRY_BASE_SECONDS

MANIM_VISUAL_QA_ENABLED = _load_bool_env("MANIM_VISUAL_QA_ENABLED", default=False)
_visual_qa_mode_raw = (os.environ.get("MANIM_VISUAL_QA_MODE", "balanced") or "").strip().lower()
if _visual_qa_mode_raw not in {"balanced", "max"}:
    print(
        f"Warning: invalid MANIM_VISUAL_QA_MODE='{_visual_qa_mode_raw}', defaulting to 'balanced'"
    )
    _visual_qa_mode_raw = "balanced"
MANIM_VISUAL_QA_MODE = _visual_qa_mode_raw
_default_visual_repairs = 1 if MANIM_VISUAL_QA_MODE == "balanced" else 2
MANIM_VISUAL_QA_MAX_REPAIRS = _load_int_env(
    "MANIM_VISUAL_QA_MAX_REPAIRS",
    default=_default_visual_repairs,
    minimum=0,
)

# Unified candidate list: Azure OpenAI first, then Groq, then Cerebras as fallback
MODEL_CANDIDATES: List[Tuple[str, str]] = []
if azure_openai_api_key and azure_openai_endpoint:
    MODEL_CANDIDATES.append(("azure", azure_openai_deployment))
else:
    print("Info: Azure OpenAI not configured \u2013 Azure fallback disabled.")
MODEL_CANDIDATES.extend(("groq", m) for m in [PRIMARY_GROQ_MODEL, *FALLBACK_GROQ_MODELS])
if cerebras_api_key:
    MODEL_CANDIDATES.append(("cerebras", CEREBRAS_MODEL))
else:
    print("Info: CEREBRAS_API_KEY not set \u2013 Cerebras fallback disabled.")


@lru_cache(maxsize=16)
def _get_llm_client(provider: str, model_name: str):
    """Return a LangChain chat model for the given provider."""
    if provider == "azure":
        return ChatOpenAI(
            model=model_name,
            api_key=azure_openai_api_key,
            base_url=azure_openai_base_url,
            max_completion_tokens=16384,
        )
    if provider == "cerebras":
        return ChatOpenAI(
            model=model_name,
            api_key=cerebras_api_key,
            base_url=CEREBRAS_BASE_URL,
            temperature=LLM_TEMPERATURE,
        )
    # Default: Groq
    return ChatGroq(
        model=model_name,
        api_key=groq_api_key,
        temperature=LLM_TEMPERATURE,
    )


# Backward compatibility for any direct imports/tests.
_default_provider = "azure" if (azure_openai_api_key and azure_openai_endpoint) else "groq"
_default_model = azure_openai_deployment if _default_provider == "azure" else PRIMARY_GROQ_MODEL
llm = _get_llm_client(_default_provider, _default_model)


def _is_retryable_llm_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            groq.InternalServerError,
            groq.RateLimitError,
            groq.APITimeoutError,
            groq.APIConnectionError,
            openai_mod.InternalServerError,
            openai_mod.RateLimitError,
            openai_mod.APITimeoutError,
            openai_mod.APIConnectionError,
            openai_mod.NotFoundError,
            httpx.TimeoutException,
            httpx.TransportError,
        ),
    ):
        return True

    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code in RETRYABLE_STATUS_CODES or status_code >= 500

    message = str(exc).lower()
    transient_markers = (
        "over capacity",
        "temporarily unavailable",
        "service unavailable",
        "try again",
        "timeout",
    )
    return any(marker in message for marker in transient_markers)


def _compute_retry_delay_seconds(attempt: int) -> float:
    # Full-jitter backoff to avoid synchronized retries under provider load.
    upper_bound = min(
        LLM_RETRY_MAX_SECONDS,
        LLM_RETRY_BASE_SECONDS * (2 ** max(0, attempt - 1)),
    )
    return random.uniform(0.0, upper_bound)


async def _invoke_with_resilience(
    prompt_template: ChatPromptTemplate,
    payload: Dict[str, Any],
    operation: str,
) -> str:
    last_error: Optional[Exception] = None
    total_candidates = len(MODEL_CANDIDATES)

    for cand_index, (provider, model_name) in enumerate(MODEL_CANDIDATES, start=1):
        chain = prompt_template | _get_llm_client(provider, model_name) | StrOutputParser()

        for attempt in range(1, LLM_RETRY_ATTEMPTS + 1):
            try:
                return await chain.ainvoke(payload)
            except Exception as exc:
                last_error = exc
                if not _is_retryable_llm_error(exc):
                    raise

                on_last_attempt = attempt == LLM_RETRY_ATTEMPTS
                on_last_candidate = cand_index == total_candidates
                if on_last_attempt and on_last_candidate:
                    break

                if on_last_attempt:
                    print(
                        f"LLM {operation}: {provider}/{model_name} unavailable after "
                        f"{LLM_RETRY_ATTEMPTS} attempts. Trying next model."
                    )
                    break

                delay = _compute_retry_delay_seconds(attempt)
                print(
                    f"LLM {operation}: transient error on {provider}/{model_name} "
                    f"(attempt {attempt}/{LLM_RETRY_ATTEMPTS}): {exc}. "
                    f"Retrying in {delay:.2f}s."
                )
                await asyncio.sleep(delay)

    model_list = ", ".join(f"{p}/{m}" for p, m in MODEL_CANDIDATES)
    raise RuntimeError(
        f"LLM {operation} failed across all configured models ({model_list}): {last_error}"
    ) from last_error


def _load_prompt_assets() -> Dict[str, Any]:
    assets: Dict[str, Any] = {}
    for key, filename in PROMPT_FILES.items():
        file_path = PROMPTS_DIR / filename
        if not file_path.exists():
            raise RuntimeError(f"Required prompt asset missing: {file_path}")

        raw_text = file_path.read_text(encoding="utf-8-sig").strip()
        if not raw_text:
            raise RuntimeError(f"Prompt asset is empty: {file_path}")

        if filename.endswith(".json"):
            try:
                assets[key] = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON in prompt asset {file_path}: {exc}") from exc
        else:
            assets[key] = raw_text

    length_profiles = assets["length_profiles"]
    if not isinstance(length_profiles, dict):
        raise RuntimeError("length_profiles.json must be a JSON object")

    default_length = length_profiles.get("default_length")
    profiles = length_profiles.get("profiles")
    if not isinstance(default_length, str) or not default_length:
        raise RuntimeError("length_profiles.json is missing a valid 'default_length'")
    if not isinstance(profiles, dict) or not profiles:
        raise RuntimeError("length_profiles.json is missing a valid 'profiles' object")
    if default_length not in profiles:
        raise RuntimeError("length_profiles.json default_length does not exist in profiles")

    required_profile_keys = {
        "target_seconds_min",
        "target_seconds_max",
        "minimum_wait_calls",
        "sections_hint",
        "summary",
    }
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            raise RuntimeError(f"Length profile '{name}' must be an object")
        missing = required_profile_keys - set(profile.keys())
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise RuntimeError(f"Length profile '{name}' missing keys: {missing_list}")

    return assets


PROMPT_ASSETS = _load_prompt_assets()


def get_length_profile(length: str) -> Dict[str, Any]:
    profiles = PROMPT_ASSETS["length_profiles"]["profiles"]
    default_length = PROMPT_ASSETS["length_profiles"]["default_length"]
    if length in profiles:
        profile = dict(profiles[length])
    else:
        profile = dict(profiles[default_length])
    profile["length_name"] = length if length in profiles else default_length
    return profile


def _emit_progress(progress_callback: ProgressCallback, status: str, message: str) -> None:
    if not progress_callback:
        return
    try:
        progress_callback(status, message)
    except Exception:
        # Progress reporting must never break generation.
        return


def _strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)


def _remove_markdown_fences(text: str) -> str:
    text = re.sub(r"^\s*```(?:python|py)?\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*```\s*$", "", text, flags=re.MULTILINE)
    return text


def sanitize_generated_code(raw_code: str) -> str:
    """Strip chain-of-thought tags and markdown wrappers from model output."""
    text = (raw_code or "").replace("\r\n", "\n")
    text = _strip_think_blocks(text)
    text = _remove_markdown_fences(text).strip()

    manim_import_match = re.search(r"(?m)^\s*from\s+manim\s+import\s+\*\s*$", text)
    class_match = re.search(r"(?m)^\s*class\s+GenScene\b", text)

    if manim_import_match:
        text = text[manim_import_match.start():]
    elif class_match:
        text = text[class_match.start():]

    return text.strip()


def _extract_json_object(text: str) -> str:
    cleaned = _strip_think_blocks(_remove_markdown_fences(text)).strip()
    if not cleaned:
        raise ValueError("Empty scene plan response")

    # Fast path: entire response is valid JSON.
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    if start == -1:
        raise ValueError("Scene plan response does not contain a JSON object")

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(cleaned)):
        char = cleaned[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start:idx + 1]

    raise ValueError("Could not extract a complete JSON object from scene plan response")


def _normalize_scene_plan(scene_plan: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(scene_plan, dict):
        raise ValueError("Scene plan must be a JSON object")

    missing_top_level = SCENE_PLAN_REQUIRED_KEYS - set(scene_plan.keys())
    if missing_top_level:
        missing_list = ", ".join(sorted(missing_top_level))
        raise ValueError(f"Scene plan missing required keys: {missing_list}")

    scenes = scene_plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Scene plan must include a non-empty 'scenes' array")

    normalized_scenes = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene #{index} must be an object")

        missing_scene_keys = SCENE_REQUIRED_KEYS - set(scene.keys())
        if missing_scene_keys:
            missing_list = ", ".join(sorted(missing_scene_keys))
            raise ValueError(f"Scene #{index} missing keys: {missing_list}")

        try:
            duration_seconds = int(scene["duration_seconds"])
        except (TypeError, ValueError):
            raise ValueError(f"Scene #{index} has invalid duration_seconds")

        if duration_seconds <= 0:
            raise ValueError(f"Scene #{index} duration_seconds must be > 0")

        visuals = scene.get("visuals")
        technical_notes = scene.get("technical_notes")
        focus_targets = scene.get("focus_targets")
        if not isinstance(visuals, list) or not visuals:
            raise ValueError(f"Scene #{index} must include non-empty visuals list")
        if not isinstance(technical_notes, list) or not technical_notes:
            raise ValueError(f"Scene #{index} must include non-empty technical_notes list")
        if not isinstance(focus_targets, list) or not focus_targets:
            raise ValueError(f"Scene #{index} must include non-empty focus_targets list")

        layout_zone = str(scene.get("layout_zone", "")).strip()
        if not layout_zone:
            raise ValueError(f"Scene #{index} has empty layout_zone")
        if layout_zone not in ALLOWED_LAYOUT_ZONES:
            raise ValueError(
                f"Scene #{index} layout_zone '{layout_zone}' must be one of: "
                + ", ".join(sorted(ALLOWED_LAYOUT_ZONES))
            )

        camera_strategy = str(scene.get("camera_strategy", "")).strip()
        if not camera_strategy:
            raise ValueError(f"Scene #{index} has empty camera_strategy")
        if camera_strategy not in ALLOWED_CAMERA_STRATEGIES:
            raise ValueError(
                f"Scene #{index} camera_strategy '{camera_strategy}' must be one of: "
                + ", ".join(sorted(ALLOWED_CAMERA_STRATEGIES))
            )

        clear_policy = str(scene.get("clear_policy", "")).strip()
        if not clear_policy:
            raise ValueError(f"Scene #{index} has empty clear_policy")
        if clear_policy not in ALLOWED_CLEAR_POLICIES:
            raise ValueError(
                f"Scene #{index} clear_policy '{clear_policy}' must be one of: "
                + ", ".join(sorted(ALLOWED_CLEAR_POLICIES))
            )

        try:
            max_concurrent_text_blocks = int(scene["max_concurrent_text_blocks"])
        except (TypeError, ValueError):
            raise ValueError(f"Scene #{index} has invalid max_concurrent_text_blocks")
        if max_concurrent_text_blocks <= 0:
            raise ValueError(f"Scene #{index} max_concurrent_text_blocks must be > 0")

        normalized_focus_targets = [
            str(item).strip() for item in focus_targets if str(item).strip()
        ]
        if not normalized_focus_targets:
            raise ValueError(f"Scene #{index} must include non-empty focus_targets values")

        normalized_scenes.append(
            {
                "name": str(scene["name"]).strip(),
                "purpose": str(scene["purpose"]).strip(),
                "duration_seconds": duration_seconds,
                "visuals": [str(item).strip() for item in visuals if str(item).strip()],
                "technical_notes": [
                    str(item).strip() for item in technical_notes if str(item).strip()
                ],
                "layout_zone": layout_zone,
                "camera_strategy": camera_strategy,
                "max_concurrent_text_blocks": max_concurrent_text_blocks,
                "clear_policy": clear_policy,
                "focus_targets": normalized_focus_targets,
                # Pass through optional enriched fields from the composer
                **({"emotional_beat": str(scene["emotional_beat"]).strip()} if "emotional_beat" in scene else {}),
                **({"animations": [str(a).strip() for a in scene["animations"] if str(a).strip()]} if isinstance(scene.get("animations"), list) else {}),
            }
        )

    return {
        "title": str(scene_plan.get("title", "")).strip(),
        "hook": str(scene_plan.get("hook", "")).strip(),
        "narrative_arc": str(scene_plan.get("narrative_arc", "")).strip(),
        "scenes": normalized_scenes,
        # Pass through optional enriched fields from the composer
        **({"narrative_pattern": str(scene_plan["narrative_pattern"]).strip()} if "narrative_pattern" in scene_plan else {}),
        **({"color_palette": scene_plan["color_palette"]} if isinstance(scene_plan.get("color_palette"), dict) else {}),
    }


def _format_scene_plan_schema_hint() -> str:
    return (
        '{"title":"string","hook":"string","narrative_arc":"string",'
        '"scenes":[{"name":"string","purpose":"string",'
        '"duration_seconds":10,"visuals":["string"],'
        '"technical_notes":["string"],'
        '"layout_zone":"golden","camera_strategy":"static",'
        '"max_concurrent_text_blocks":3,"clear_policy":"fade_out",'
        '"focus_targets":["string"]}]}'
    )


async def compose_scene_plan(prompt: str, length: str) -> Dict[str, Any]:
    profile = get_length_profile(length)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_ASSETS["composer_system"]),
            (
                "human",
                "User prompt:\n{prompt}\n\n"
                "Length selection: {length_name}\n"
                "Length profile JSON:\n{length_profile_json}\n\n"
                "Produce a scene plan with strong educational flow and concrete visual steps.\n"
                "Return JSON only using this schema:\n{schema_hint}",
            ),
        ]
    )

    raw_response = await _invoke_with_resilience(
        prompt_template,
        {
            "prompt": prompt,
            "length_name": profile["length_name"],
            "length_profile_json": json.dumps(profile, indent=2),
            "schema_hint": _format_scene_plan_schema_hint(),
        },
        operation="compose_scene_plan",
    )

    parsed = json.loads(_extract_json_object(raw_response))
    return _normalize_scene_plan(parsed)


async def generate_code_from_plan(prompt: str, length: str, scene_plan: Dict[str, Any]) -> str:
    profile = get_length_profile(length)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_ASSETS["codegen_system"]),
            (
                "human",
                "User prompt:\n{prompt}\n\n"
                "Length selection: {length_name}\n"
                "Length profile JSON:\n{length_profile_json}\n\n"
                "Scene plan JSON:\n{scene_plan_json}\n\n"
                "Generate executable Python code for ManimCE.\n"
                "Return code only.",
            ),
        ]
    )

    raw_response = await _invoke_with_resilience(
        prompt_template,
        {
            "prompt": prompt,
            "length_name": profile["length_name"],
            "length_profile_json": json.dumps(profile, indent=2),
            "scene_plan_json": json.dumps(scene_plan, indent=2),
        },
        operation="generate_code_from_plan",
    )

    return sanitize_generated_code(raw_response)


def _get_call_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _contains_animate_builder(node: ast.AST) -> bool:
    current = node
    while isinstance(current, ast.Attribute):
        if current.attr == "animate":
            return True
        current = current.value
    return False


def _is_animation_expression(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False

    func_name = _get_call_name(node.func)
    if func_name in ANIMATION_FN_NAMES:
        return True

    if isinstance(node.func, ast.Attribute) and _contains_animate_builder(node.func):
        return True

    return False


def _collect_animation_variables(tree: ast.AST) -> Set[str]:
    animation_vars: Set[str] = set()
    for node in ast.walk(tree):
        value_node = None
        target_nodes: List[ast.AST] = []

        if isinstance(node, ast.Assign):
            value_node = node.value
            target_nodes = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            target_nodes = [node.target]

        if value_node is None or not _is_animation_expression(value_node):
            continue

        for target in target_nodes:
            if isinstance(target, ast.Name):
                animation_vars.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        animation_vars.add(elt.id)

    return animation_vars


def _has_required_manim_import(tree: ast.AST) -> bool:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ImportFrom) and node.module == "manim":
            for alias in node.names:
                if alias.name == "*":
                    return True
    return False


def _has_valid_genscene_class(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "GenScene":
            continue

        for base in node.bases:
            base_name = _get_call_name(base)
            if base_name in ALLOWED_SCENE_BASES:
                return True

    return False


def _detect_play_antipatterns(tree: ast.AST) -> List[str]:
    errors: List[str] = []
    animation_vars = _collect_animation_variables(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute) or node.func.attr != "play":
            continue

        for arg in node.args:
            if isinstance(arg, ast.Starred):
                continue

            if isinstance(arg, ast.Name) and arg.id not in animation_vars:
                errors.append(
                    f"Line {arg.lineno}: possible raw mobject passed to self.play('{arg.id}')"
                )

    return errors


def _iter_tex_string_literals(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node.func)
        if func_name not in {"MathTex", "Tex"}:
            continue

        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield arg.lineno, arg.value
            elif isinstance(arg, ast.JoinedStr):
                parts = []
                for part in arg.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        parts.append(part.value)
                if parts:
                    yield arg.lineno, "".join(parts)


def _detect_forbidden_unicode_math(tree: ast.AST) -> List[str]:
    errors: List[str] = []
    for lineno, tex_literal in _iter_tex_string_literals(tree):
        for symbol, replacement in FORBIDDEN_MATH_UNICODE.items():
            if symbol in tex_literal:
                errors.append(
                    f"Line {lineno}: use LaTeX '{replacement}' instead of unicode '{symbol}'"
                )
    return errors


def _detect_forbidden_tex_macros(tree: ast.AST) -> List[str]:
    errors: List[str] = []
    for lineno, tex_literal in _iter_tex_string_literals(tree):
        normalized_tex = re.sub(r"\\{2,}", r"\\", tex_literal)
        for macro, replacement in FORBIDDEN_TEX_MACROS.items():
            if macro in tex_literal or macro in normalized_tex:
                errors.append(
                    f"Line {lineno}: avoid LaTeX macro '{macro}' (package-dependent); use {replacement} instead"
                )
    return errors


def _extract_string_literal(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: List[str] = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                parts.append(part.value)
        if parts:
            return "".join(parts)
    return None


def _detect_external_asset_dependencies(tree: ast.AST) -> List[str]:
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node.func)
        if func_name not in EXTERNAL_ASSET_MOBJECTS:
            continue

        for arg in node.args:
            literal = _extract_string_literal(arg)
            if literal:
                errors.append(
                    f"Line {node.lineno}: external asset reference '{literal}' is not allowed; use built-in Manim primitives instead"
                )
                break

    return errors


def _is_point_like_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False

    func_name = _get_call_name(node.func)
    if func_name in {"get_center", "get_start", "get_end", "c2p", "n2p", "coords_to_point"}:
        return True
    return False


def _is_numpy_array_call_with_length(node: ast.AST, expected_length: int) -> bool:
    if not isinstance(node, ast.Call):
        return False

    if isinstance(node.func, ast.Attribute):
        is_numpy_array = (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"np", "numpy"}
            and node.func.attr == "array"
        )
    else:
        is_numpy_array = isinstance(node.func, ast.Name) and node.func.id == "array"

    if not is_numpy_array or not node.args:
        return False

    first_arg = node.args[0]
    if isinstance(first_arg, (ast.List, ast.Tuple)):
        return len(first_arg.elts) == expected_length
    return False


def _contains_two_item_numpy_array(node: ast.AST) -> bool:
    return any(_is_numpy_array_call_with_length(subnode, 2) for subnode in ast.walk(node))


def _contains_point_like_expression(node: ast.AST) -> bool:
    return any(_is_point_like_call(subnode) for subnode in ast.walk(node))


def _detect_mixed_point_dimension_expressions(tree: ast.AST) -> List[str]:
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        if not isinstance(node.op, (ast.Add, ast.Sub)):
            continue

        left_has_point = _contains_point_like_expression(node.left)
        right_has_point = _contains_point_like_expression(node.right)
        left_has_2d_array = _contains_two_item_numpy_array(node.left)
        right_has_2d_array = _contains_two_item_numpy_array(node.right)

        if (left_has_point and right_has_2d_array) or (right_has_point and left_has_2d_array):
            errors.append(
                f"Line {node.lineno}: mixing 3D Manim points with 2D np.array([...]) may crash "
                "with broadcast shape errors; use 3D arrays like np.array([x, y, 0])"
            )

    return errors


def _detect_bare_opacity_kwarg(tree: ast.AST) -> List[str]:
    """Detect `opacity=...` passed as a keyword argument to constructors.

    ManimCE Mobjects do not accept a bare ``opacity`` kwarg.  The correct
    parameters are ``fill_opacity`` and ``stroke_opacity``, or calling
    ``.set_opacity()`` after creation.

    We exempt method calls where ``opacity`` IS a valid keyword:
      set_fill, set_stroke, set_style, set_opacity.
    """
    _EXEMPT_METHODS = {"set_fill", "set_stroke", "set_style", "set_opacity"}

    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Determine the method/function name being called
        call_name: Optional[str] = None
        if isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            call_name = node.func.id

        if call_name in _EXEMPT_METHODS:
            continue

        for kw in node.keywords:
            if kw.arg == "opacity":
                errors.append(
                    f"Line {kw.col_offset}: 'opacity' is not a valid Mobject keyword; "
                    "use 'fill_opacity' or 'stroke_opacity' instead"
                )
    return errors


_MATH_LATEX_PATTERN = re.compile(
    r"\\(?:frac|vec|cos|sin|tan|theta|alpha|beta|gamma|pi|lvert|rvert|lVert|rVert"
    r"|sqrt|sum|prod|int|infty|cdot|times|div|leq|geq|neq|approx|equiv"
    r"|left|right|begin|end|hat|bar|dot|tilde|mathbb|mathcal|mathrm|operatorname)"
)


def _detect_math_in_text_mode(tree: ast.AST) -> List[str]:
    """Detect math LaTeX commands inside Brace.get_text() or Text() calls.

    ``Brace.get_text()`` creates a ``Tex`` object in TEXT mode.  Passing math
    commands (\\vec, \\frac, \\cos, etc.) without ``$...$`` wrapping causes
    a LaTeX DVI compilation error.  The fix is to use ``brace.get_tex()`` for
    math expressions, or wrap in ``$...$``.
    """
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node.func)
        is_get_text = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get_text"
        )
        is_text_constructor = func_name == "Text"

        if not is_get_text and not is_text_constructor:
            continue

        for arg in node.args:
            literal = _extract_string_literal(arg)
            if literal and _MATH_LATEX_PATTERN.search(literal):
                if is_get_text:
                    errors.append(
                        f"Line {node.lineno}: get_text() is TEXT mode; math commands will cause "
                        "a DVI error. Use get_tex() for math expressions, or plain text for labels"
                    )
                else:
                    errors.append(
                        f"Line {node.lineno}: Text() is Pango, not LaTeX; LaTeX commands will "
                        "render as raw text. Use MathTex() or Tex() for LaTeX expressions"
                    )
                break

    return errors


# Manim constructors that accept point/coordinate arguments
_POINT_ACCEPTING_CONSTRUCTORS = {
    "Arrow", "Line", "DashedLine", "DoubleArrow", "Vector",
    "CurvedArrow", "Dot", "Dot3D", "Arrow3D", "Arc",
    "Polygon", "Brace", "RightAngle",
}


def _is_2d_slice(node: ast.AST) -> bool:
    """Check if node is a [:2] subscript slice, e.g. vec[:2]."""
    if not isinstance(node, ast.Subscript):
        return False
    sl = node.slice
    if isinstance(sl, ast.Slice):
        if sl.upper is not None and isinstance(sl.upper, ast.Constant) and sl.upper.value == 2:
            if sl.lower is None and sl.step is None:
                return True
    return False


def _contains_2d_slice(node: ast.AST) -> bool:
    """Recursively check if any sub-expression contains a [:2] slice."""
    for child in ast.walk(node):
        if _is_2d_slice(child):
            return True
    return False


def _detect_2d_slices_in_constructors(tree: ast.AST) -> List[str]:
    """Detect vec[:2] passed as arguments to Manim point-accepting constructors."""
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node.func)
        if func_name not in _POINT_ACCEPTING_CONSTRUCTORS:
            continue

        for arg in node.args:
            if _contains_2d_slice(arg):
                errors.append(
                    f"Line {node.lineno}: {func_name}() receives a [:2] sliced (2D) array; "
                    "Manim requires 3D coordinates — use the full vector or np.array([x, y, 0])"
                )
                break

        for kw in node.keywords:
            if kw.arg in ("start", "end", "point", "direction") and _contains_2d_slice(kw.value):
                errors.append(
                    f"Line {node.lineno}: {func_name}({kw.arg}=) receives a [:2] sliced (2D) array; "
                    "Manim requires 3D coordinates"
                )

    return errors


def _detect_angle_misuse(tree: ast.AST) -> List[str]:
    """Detect Angle() called with radius as a positional arg (causes 'multiple values' TypeError)."""
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node.func)
        if func_name != "Angle":
            continue

        # Angle(line1, line2) is fine (2 positional args)
        # Angle(line1, line2, something) with 3+ positional args means radius is positional
        if len(node.args) >= 3:
            has_radius_kw = any(kw.arg == "radius" for kw in node.keywords)
            if has_radius_kw:
                errors.append(
                    f"Line {node.lineno}: Angle() has radius as both positional and keyword arg; "
                    "use Angle(line1, line2, radius=value) with radius as keyword only"
                )
            else:
                errors.append(
                    f"Line {node.lineno}: Angle() has too many positional args; "
                    "use Angle(line1, line2, radius=value) with radius as keyword only"
                )

    return errors


# Deprecated ManimCE API names → replacements
_DEPRECATED_API_MAP = {
    "ShowCreation": "Create",
    "ShowDestruction": "Uncreate",
    "ShowPassingFlashAround": "ShowPassingFlash",
    "FadeInFromDown": "FadeIn(mob, shift=DOWN)",
    "FadeOutAndShift": "FadeOut(mob, shift=direction)",
    "GrowFromEdge": "GrowFromEdge",  # still exists but API changed
    "ShowIncreasingSubsets": "ShowIncreasingSubsets",
    "FadeInFrom": "FadeIn(mob, shift=direction)",
    "FadeInFromLarge": "FadeIn(mob, scale=2)",
    "FadeOutToPoint": "FadeOut(mob, target_position=point)",
}


def _detect_deprecated_apis(tree: ast.AST) -> List[str]:
    """Detect usage of deprecated ManimCE animation/mobject names."""
    # Only flag the ones that will actually crash at runtime
    _HARD_DEPRECATED = {"ShowCreation", "ShowDestruction", "FadeInFromDown", "FadeOutAndShift",
                        "FadeInFrom", "FadeInFromLarge", "FadeOutToPoint"}
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _get_call_name(node.func)
        if func_name in _HARD_DEPRECATED:
            replacement = _DEPRECATED_API_MAP.get(func_name, "the modern equivalent")
            errors.append(
                f"Line {node.lineno}: '{func_name}' is deprecated in ManimCE; "
                f"use {replacement} instead"
            )
    return errors


def _detect_fstring_in_mathtex(tree: ast.AST) -> List[str]:
    """Detect f-strings used as arguments to MathTex() or Tex().

    f-strings containing backslashes (``\\frac``, ``\\pi``, etc.) will cause
    a SyntaxError in Python 3.11 and below, and even in 3.12+ the backslashes
    are often mangled.  The safe pattern is ``MathTex(r'...', ...)`` with
    ``.set_color_by_tex`` or string concatenation for dynamic parts.
    """
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _get_call_name(node.func)
        if func_name not in {"MathTex", "Tex"}:
            continue
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                errors.append(
                    f"Line {node.lineno}: f-string in {func_name}() may break LaTeX backslashes; "
                    "use raw strings (r'...') and .set_color_by_tex() or string concatenation"
                )
                break
    return errors


def _detect_3d_without_camera_setup(tree: ast.AST) -> List[str]:
    """Detect ThreeDScene subclass that doesn't call set_camera_orientation().

    Forgetting to set the camera before adding 3D content causes the default
    top-down view which makes 3D objects appear flat/invisible.
    """
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "GenScene":
            continue

        is_3d = any(
            _get_call_name(base) == "ThreeDScene" for base in node.bases
        )
        if not is_3d:
            continue

        # Walk the class body looking for set_camera_orientation call
        has_camera_setup = False
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr in ("set_camera_orientation", "move_camera"):
                    has_camera_setup = True
                    break

        if not has_camera_setup:
            errors.append(
                "ThreeDScene missing set_camera_orientation() call; "
                "3D objects will appear flat without proper camera setup"
            )

    return errors


def _count_wait_calls(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Attribute) and node.func.attr == "wait":
            count += 1
        elif isinstance(node.func, ast.Name) and node.func.id == "wait":
            count += 1

    return count


def validate_code(code: str, length: str) -> List[str]:
    errors: List[str] = []
    normalized = (code or "").strip()

    if not normalized:
        return ["Generated code is empty"]

    if "<think>" in normalized.lower():
        errors.append("Output still contains <think> tags")
    if "```" in normalized:
        errors.append("Output still contains markdown code fences")

    try:
        tree = ast.parse(normalized)
    except SyntaxError as exc:
        errors.append(f"Syntax error at line {exc.lineno}: {exc.msg}")
        return errors

    if not _has_required_manim_import(tree):
        errors.append("Missing required import: from manim import *")

    if not _has_valid_genscene_class(tree):
        errors.append("Missing class GenScene inheriting Scene/ThreeDScene/MovingCameraScene")

    errors.extend(_detect_play_antipatterns(tree))
    errors.extend(_detect_forbidden_unicode_math(tree))
    errors.extend(_detect_forbidden_tex_macros(tree))
    errors.extend(_detect_external_asset_dependencies(tree))
    errors.extend(_detect_mixed_point_dimension_expressions(tree))
    errors.extend(_detect_bare_opacity_kwarg(tree))
    errors.extend(_detect_math_in_text_mode(tree))
    errors.extend(_detect_2d_slices_in_constructors(tree))
    errors.extend(_detect_angle_misuse(tree))
    errors.extend(_detect_deprecated_apis(tree))
    errors.extend(_detect_fstring_in_mathtex(tree))
    errors.extend(_detect_3d_without_camera_setup(tree))

    min_wait_calls = int(get_length_profile(length).get("minimum_wait_calls", 0))
    wait_calls = _count_wait_calls(tree)
    if wait_calls < min_wait_calls:
        errors.append(
            f"Insufficient pacing: found {wait_calls} wait() calls, require >= {min_wait_calls} for {length}"
        )

    # De-duplicate while preserving order
    deduped: List[str] = []
    seen: Set[str] = set()
    for error in errors:
        if error not in seen:
            deduped.append(error)
            seen.add(error)
    return deduped


async def repair_code(
    prompt: str,
    length: str,
    scene_plan: Dict[str, Any],
    bad_code: str,
    errors: List[str],
) -> str:
    profile = get_length_profile(length)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_ASSETS["repair_system"]),
            (
                "human",
                "User prompt:\n{prompt}\n\n"
                "Length selection: {length_name}\n"
                "Length profile JSON:\n{length_profile_json}\n\n"
                "Scene plan JSON:\n{scene_plan_json}\n\n"
                "Validation errors (must all be fixed):\n{errors}\n\n"
                "Current code:\n{bad_code}\n\n"
                "Return corrected executable code only.",
            ),
        ]
    )

    raw_response = await _invoke_with_resilience(
        prompt_template,
        {
            "prompt": prompt,
            "length_name": profile["length_name"],
            "length_profile_json": json.dumps(profile, indent=2),
            "scene_plan_json": json.dumps(scene_plan, indent=2),
            "errors": "\n".join(f"- {item}" for item in errors),
            "bad_code": bad_code,
        },
        operation="repair_code",
    )

    return sanitize_generated_code(raw_response)


async def repair_code_from_runtime_error(
    prompt: str,
    length: str,
    bad_code: str,
    runtime_error: str,
) -> str:
    profile = get_length_profile(length)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_ASSETS["runtime_repair_system"]),
            (
                "human",
                "User prompt:\n{prompt}\n\n"
                "Length selection: {length_name}\n"
                "Length profile JSON:\n{length_profile_json}\n\n"
                "Render-time error:\n{runtime_error}\n\n"
                "Current code:\n{bad_code}\n\n"
                "Fix all runtime issues while keeping pacing constraints and ManimCE compatibility.\n"
                "Return corrected executable code only.",
            ),
        ]
    )

    raw_response = await _invoke_with_resilience(
        prompt_template,
        {
            "prompt": prompt,
            "length_name": profile["length_name"],
            "length_profile_json": json.dumps(profile, indent=2),
            "runtime_error": runtime_error,
            "bad_code": bad_code,
        },
        operation="repair_code_from_runtime_error",
    )

    repaired_code = sanitize_generated_code(raw_response)

    # Apply the same mechanical auto-fixes used in the primary generation path
    # so that recurring LLM mistakes (e.g. bare opacity=) are caught before
    # validation rejects the repaired code.
    repaired_code = _apply_all_auto_fixes(repaired_code, length)

    errors = validate_code(repaired_code, length)
    if errors and all(item.startswith("Insufficient pacing:") for item in errors):
        repaired_code = _force_pad_wait_calls(repaired_code, length)
        errors = validate_code(repaired_code, length)

    if errors:
        raise ValueError(
            "Runtime repair produced invalid code: " + _summarize_errors(errors)
        )
    return repaired_code


def run_visual_quality_check_for_code(code: str, mode: str) -> Dict[str, Any]:
    """Run visual QA in a low-quality preflight render and return a structured report."""
    from .manim_service import run_visual_quality_check

    return run_visual_quality_check(code=code, mode=mode)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_quality_report(report: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "passed": False,
            "score": 0,
            "error_count": 1,
            "warning_count": 0,
            "issues": [
                {
                    "severity": "error",
                    "issue_type": "quality_report_invalid",
                    "message": "Visual quality report has invalid structure",
                    "frame_index": -1,
                    "details": {},
                }
            ],
            "metrics": {},
        }

    normalized = {
        "passed": bool(report.get("passed", False)),
        "score": int(report.get("score", 0)),
        "error_count": int(report.get("error_count", 0)),
        "warning_count": int(report.get("warning_count", 0)),
        "issues": [],
        "metrics": report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {},
    }

    issues = report.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            normalized["issues"].append(
                {
                    "severity": str(issue.get("severity", "warning")),
                    "issue_type": str(issue.get("issue_type", "unspecified")),
                    "message": str(issue.get("message", "Unspecified quality issue")),
                    "frame_index": _safe_int(issue.get("frame_index", -1), default=-1),
                    "details": issue.get("details", {}) if isinstance(issue.get("details"), dict) else {},
                }
            )
    return normalized


async def repair_code_from_visual_issues(
    prompt: str,
    length: str,
    scene_plan: Dict[str, Any],
    bad_code: str,
    quality_report: Dict[str, Any],
) -> str:
    profile = get_length_profile(length)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PROMPT_ASSETS["visual_repair_system"]),
            (
                "human",
                "User prompt:\n{prompt}\n\n"
                "Length selection: {length_name}\n"
                "Length profile JSON:\n{length_profile_json}\n\n"
                "Scene plan JSON:\n{scene_plan_json}\n\n"
                "Visual QA report JSON:\n{quality_report_json}\n\n"
                "Current code:\n{bad_code}\n\n"
                "Fix all visual quality issues while preserving narrative flow.\n"
                "Return corrected executable code only.",
            ),
        ]
    )

    raw_response = await _invoke_with_resilience(
        prompt_template,
        {
            "prompt": prompt,
            "length_name": profile["length_name"],
            "length_profile_json": json.dumps(profile, indent=2),
            "scene_plan_json": json.dumps(scene_plan, indent=2),
            "quality_report_json": json.dumps(_normalize_quality_report(quality_report), indent=2),
            "bad_code": bad_code,
        },
        operation="repair_code_from_visual_issues",
    )

    repaired_code = sanitize_generated_code(raw_response)
    repaired_code = _apply_all_auto_fixes(repaired_code, length)
    errors = validate_code(repaired_code, length)
    if errors:
        raise ValueError(
            "Visual repair produced invalid code: " + _summarize_errors(errors)
        )
    return repaired_code


def _summarize_errors(errors: List[str], max_items: int = 6) -> str:
    if not errors:
        return "No validation errors"
    clipped = errors[:max_items]
    summary = "; ".join(clipped)
    if len(errors) > max_items:
        summary += f"; ... (+{len(errors) - max_items} more)"
    return summary


def _auto_pad_wait_calls(code: str, length: str) -> str:
    """Insert extra ``self.wait(1)`` calls if the code is just under the minimum.

    This is a best-effort safety net applied *after* LLM repair attempts.  It
    locates every ``self.play(...)`` call and inserts a ``self.wait(1)`` after
    any that isn't already followed by a ``self.wait``.  It stops once the
    minimum threshold is satisfied.
    """
    import re as _re

    min_wait = int(get_length_profile(length).get("minimum_wait_calls", 0))
    if min_wait <= 0:
        return code

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    current_waits = _count_wait_calls(tree)
    deficit = min_wait - current_waits
    if deficit <= 0:
        return code

    lines = code.split("\n")
    # Find self.play(...) lines that are NOT immediately followed by self.wait
    insert_positions: List[int] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _re.match(r"self\.play\(", stripped):
            # Check if next non-blank line is already a wait
            for j in range(i + 1, min(i + 3, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if next_stripped.startswith("self.wait"):
                    break
                insert_positions.append(i)
                break
            else:
                insert_positions.append(i)

    if not insert_positions:
        return code

    # Insert from bottom to top so line numbers stay valid
    inserted = 0
    for pos in reversed(insert_positions):
        if inserted >= deficit:
            break
        indent = len(lines[pos]) - len(lines[pos].lstrip())
        pad_line = " " * indent + "self.wait(1)"
        lines.insert(pos + 1, pad_line)
        inserted += 1

    return "\n".join(lines)


def _force_pad_wait_calls(code: str, length: str) -> str:
    """Force insert wait() calls near the end of construct() to satisfy pacing.

    Unlike `_auto_pad_wait_calls`, this fallback does not require nearby
    `self.play(...)` lines. It appends waits at the tail of construct() when
    runtime-repaired code still fails pacing validation.
    """
    min_wait = int(get_length_profile(length).get("minimum_wait_calls", 0))
    if min_wait <= 0:
        return code

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    current_waits = _count_wait_calls(tree)
    deficit = min_wait - current_waits
    if deficit <= 0:
        return code

    lines = code.split("\n")

    def _indent_of(line: str) -> int:
        return len(line) - len(line.lstrip())

    construct_index = -1
    construct_indent = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("def construct(") and stripped.endswith(":"):
            construct_index = i
            construct_indent = _indent_of(line)
            break

    if construct_index < 0:
        return code

    body_indent = construct_indent + 4
    for j in range(construct_index + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped:
            continue
        line_indent = _indent_of(lines[j])
        if line_indent > construct_indent:
            body_indent = line_indent
            break

    insert_at = len(lines)
    for k in range(construct_index + 1, len(lines)):
        stripped = lines[k].strip()
        if not stripped:
            continue
        if _indent_of(lines[k]) <= construct_indent:
            insert_at = k
            break

    wait_line = " " * body_indent + "self.wait(1)"
    padding = [wait_line for _ in range(deficit)]
    lines[insert_at:insert_at] = padding
    return "\n".join(lines)


def _auto_fix_bare_opacity(code: str) -> str:
    """Replace bare `opacity=` keyword args with `fill_opacity=`.

    ManimCE Mobjects do not accept a bare ``opacity`` kwarg in constructors.
    The correct parameters are ``fill_opacity`` and ``stroke_opacity``, or
    calling ``.set_opacity()`` after creation.

    However, `opacity` IS a valid positional-keyword in these method calls:
      - set_fill(color, opacity=val)
      - set_stroke(color, width=..., opacity=val)
      - set_style(..., fill_opacity / stroke_opacity / ... opacity=...)
      - set_opacity(val)
    So we must NOT rewrite those.

    Strategy: process line-by-line; skip lines whose call context is an exempt
    method, then apply the substitution on the remainder.
    """
    import re as _re

    # Methods where `opacity=` is a legitimate keyword argument
    _EXEMPT_METHODS = _re.compile(
        r'\.\s*(?:set_fill|set_stroke|set_style|set_opacity)\s*\('
    )

    out_lines: list[str] = []
    for line in code.split("\n"):
        if _EXEMPT_METHODS.search(line):
            # This line calls an exempt method — leave it untouched
            out_lines.append(line)
        else:
            out_lines.append(
                _re.sub(r'(?<!fill_)(?<!stroke_)\bopacity\s*=', 'fill_opacity=', line)
            )
    return "\n".join(out_lines)


def _auto_fix_showcreation(code: str) -> str:
    """Replace deprecated ``ShowCreation`` with ``Create``.

    ``ShowCreation`` was renamed to ``Create`` in ManimCE 0.16.  The LLM
    occasionally produces the old name because older tutorials still use it.
    """
    import re as _re
    return _re.sub(r'\bShowCreation\b', 'Create', code)


def _auto_fix_group_to_vgroup(code: str) -> str:
    """Replace bare ``Group(`` with ``VGroup(`` when used for VMobjects.

    In ManimCE, ``Group`` is for generic Mobjects and ``VGroup`` is for
    VMobjects (shapes, text, graphs, etc.).  Passing VMobjects to ``Group``
    instead of ``VGroup`` causes rendering issues.  Since virtually all
    user-generated Manim code works with VMobjects, this swap is safe.
    """
    import re as _re
    # Match standalone `Group(` that is NOT part of AnimationGroup, VGroup, etc.
    return _re.sub(
        r'(?<!Animation)(?<!V)(?<!Sub)\bGroup\s*\(',
        'VGroup(',
        code,
    )


def _auto_fix_2d_numpy_arrays(code: str) -> str:
    """Replace ``np.array([x, y])`` with ``np.array([x, y, 0])`` in common patterns.

    Manim requires 3D coordinate arrays.  When the LLM produces 2-element
    arrays they crash with broadcast shape errors.  This fix targets the
    most common pattern: ``np.array([<expr>, <expr>])`` without a third element.
    """
    import re as _re
    # Match np.array([...]) with exactly 2 comma-separated items (no nested brackets)
    return _re.sub(
        r'np\.array\(\[\s*([^,\[\]]+),\s*([^,\[\]]+)\s*\]\)',
        r'np.array([\1, \2, 0])',
        code,
    )


def _apply_all_auto_fixes(code: str, length: str) -> str:
    """Apply every mechanical auto-fix in sequence, then pad wait calls if needed.

    This is the single entry-point called from both the primary generation
    pipeline and the runtime repair path.
    """
    code = _auto_fix_bare_opacity(code)
    code = _auto_fix_showcreation(code)
    code = _auto_fix_group_to_vgroup(code)
    code = _auto_fix_2d_numpy_arrays(code)
    code = _auto_pad_wait_calls(code, length)
    return code


async def generate_manim_code(
    prompt: str,
    length: str,
    progress_callback: ProgressCallback = None,
) -> str:
    """Generate Manim code using compose -> codegen -> validate -> repair pipeline."""
    _emit_progress(progress_callback, "composing", "Composing internal scene plan...")
    scene_plan = await compose_scene_plan(prompt, length)

    _emit_progress(progress_callback, "generating", "Generating Manim code from scene plan...")
    code = await generate_code_from_plan(prompt, length, scene_plan)

    _emit_progress(progress_callback, "validating", "Validating generated code...")
    errors = validate_code(code, length)

    max_retries = 2
    retry = 0
    while errors and retry < max_retries:
        retry += 1
        _emit_progress(
            progress_callback,
            "repairing",
            f"Repairing invalid code (attempt {retry}/{max_retries})...",
        )
        code = await repair_code(prompt, length, scene_plan, code, errors)
        _emit_progress(progress_callback, "validating", "Re-validating repaired code...")
        errors = validate_code(code, length)

    if errors:
        # Last-resort: apply all mechanical auto-fixes
        code = _apply_all_auto_fixes(code, length)
        errors = validate_code(code, length)

    if errors:
        raise ValueError(
            "Code validation failed after 2 repair attempts: " + _summarize_errors(errors)
        )

    if MANIM_VISUAL_QA_ENABLED:
        quality_attempt = 0
        while True:
            _emit_progress(
                progress_callback,
                "quality_checking",
                "Running visual quality checks...",
            )
            try:
                quality_report = run_visual_quality_check_for_code(
                    code=code,
                    mode=MANIM_VISUAL_QA_MODE,
                )
            except Exception as exc:
                quality_report = {
                    "passed": False,
                    "score": 0,
                    "error_count": 1,
                    "warning_count": 0,
                    "issues": [
                        {
                            "severity": "error",
                            "issue_type": "qa_render_failure",
                            "message": str(exc),
                            "frame_index": -1,
                            "details": {},
                        }
                    ],
                    "metrics": {},
                }

            quality_report = _normalize_quality_report(quality_report)
            if quality_report["passed"]:
                break

            if quality_attempt >= MANIM_VISUAL_QA_MAX_REPAIRS:
                raise ValueError(
                    "Visual quality gate failed: "
                    + _summarize_errors(
                        [
                            issue["message"]
                            for issue in quality_report["issues"]
                            if issue.get("severity") == "error"
                        ]
                        or ["Visual score below threshold"]
                    )
                )

            quality_attempt += 1
            _emit_progress(
                progress_callback,
                "quality_repairing",
                (
                    f"Repairing visual layout (attempt {quality_attempt}/"
                    f"{MANIM_VISUAL_QA_MAX_REPAIRS})..."
                ),
            )
            code = await repair_code_from_visual_issues(
                prompt=prompt,
                length=length,
                scene_plan=scene_plan,
                bad_code=code,
                quality_report=quality_report,
            )

    return code

