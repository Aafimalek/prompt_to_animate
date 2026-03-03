import asyncio

from backend import llm_service


VALID_MEDIUM_CODE = """from manim import *

class GenScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
"""


def test_sanitize_generated_code_removes_think_and_fences():
    raw = """<think>internal reasoning</think>
```python
Some intro text that should be removed.
from manim import *

class GenScene(Scene):
    def construct(self):
        self.wait(1)
```
"""
    cleaned = llm_service.sanitize_generated_code(raw)

    assert "<think>" not in cleaned
    assert "```" not in cleaned
    assert cleaned.startswith("from manim import *")


def test_validate_code_detects_required_structure_errors():
    code = """class NotGenScene:
    pass
"""
    errors = llm_service.validate_code(code, "Medium (15s)")

    assert any("Missing required import" in error for error in errors)
    assert any("Missing class GenScene" in error for error in errors)


def test_validate_code_detects_antipattern_and_unicode_math():
    bad_code = """from manim import *

class GenScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(circle)
        eq = MathTex("\u03c0")
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
"""
    errors = llm_service.validate_code(bad_code, "Medium (15s)")

    assert any("possible raw mobject passed" in error for error in errors)
    assert any("\\pi" in error for error in errors)


def test_validate_code_detects_external_asset_dependency():
    bad_code = """from manim import *

class GenScene(Scene):
    def construct(self):
        icon = SVGMobject("brain.svg")
        self.play(FadeIn(icon))
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
"""
    errors = llm_service.validate_code(bad_code, "Medium (15s)")
    assert any("external asset reference" in error for error in errors)


def test_validate_code_detects_forbidden_tex_macro():
    bad_code = """from manim import *

class GenScene(Scene):
    def construct(self):
        mark = Tex(r"\\checkmark")
        self.play(FadeIn(mark))
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
"""
    errors = llm_service.validate_code(bad_code, "Medium (15s)")
    assert any("avoid LaTeX macro '\\checkmark'" in error for error in errors)


def test_validate_code_detects_2d_array_added_to_3d_point():
    bad_code = """from manim import *
import numpy as np

class GenScene(Scene):
    def construct(self):
        dot = Dot()
        _ = dot.get_center() + np.array([1, 0])
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
        self.wait(1)
"""
    errors = llm_service.validate_code(bad_code, "Medium (15s)")
    assert any("mixing 3D Manim points with 2D np.array" in error for error in errors)


def test_generate_manim_code_repairs_after_first_invalid_attempt(monkeypatch):
    async def fake_compose_scene_plan(prompt: str, length: str):
        return {
            "title": "Demo",
            "hook": "Hook",
            "narrative_arc": "Arc",
            "scenes": [
                {
                    "name": "Scene 1",
                    "purpose": "Purpose",
                    "duration_seconds": 15,
                    "visuals": ["Circle"],
                    "technical_notes": ["Use Create"],
                }
            ],
        }

    async def fake_generate_code_from_plan(prompt: str, length: str, scene_plan):
        return """from manim import *

class GenScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(circle)
        self.wait(1)
"""

    async def fake_repair_code(prompt: str, length: str, scene_plan, bad_code: str, errors):
        return VALID_MEDIUM_CODE

    monkeypatch.setattr(llm_service, "compose_scene_plan", fake_compose_scene_plan)
    monkeypatch.setattr(llm_service, "generate_code_from_plan", fake_generate_code_from_plan)
    monkeypatch.setattr(llm_service, "repair_code", fake_repair_code)

    status_log = []

    def progress(status: str, message: str):
        status_log.append((status, message))

    result = asyncio.run(
        llm_service.generate_manim_code(
            prompt="Explain circles",
            length="Medium (15s)",
            progress_callback=progress,
        )
    )

    assert "from manim import *" in result
    assert any(status == "repairing" for status, _ in status_log)


def test_generate_manim_code_fails_after_two_repairs(monkeypatch):
    async def fake_compose_scene_plan(prompt: str, length: str):
        return {
            "title": "Demo",
            "hook": "Hook",
            "narrative_arc": "Arc",
            "scenes": [
                {
                    "name": "Scene 1",
                    "purpose": "Purpose",
                    "duration_seconds": 15,
                    "visuals": ["Circle"],
                    "technical_notes": ["Use Create"],
                }
            ],
        }

    async def fake_generate_code_from_plan(prompt: str, length: str, scene_plan):
        return "class Broken: pass"

    async def fake_repair_code(prompt: str, length: str, scene_plan, bad_code: str, errors):
        return "class StillBroken: pass"

    monkeypatch.setattr(llm_service, "compose_scene_plan", fake_compose_scene_plan)
    monkeypatch.setattr(llm_service, "generate_code_from_plan", fake_generate_code_from_plan)
    monkeypatch.setattr(llm_service, "repair_code", fake_repair_code)

    try:
        asyncio.run(llm_service.generate_manim_code("Bad", "Medium (15s)"))
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "after 2 repair attempts" in str(exc)


def test_invoke_with_resilience_retries_transient_failure(monkeypatch):
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, payload):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("over capacity")
            return "ok"

    class FakePipeAfterLLM:
        def __init__(self, llm):
            self.llm = llm

        def __or__(self, _parser):
            return self

        async def ainvoke(self, payload):
            return await self.llm.ainvoke(payload)

    class FakePrompt:
        def __or__(self, llm):
            return FakePipeAfterLLM(llm)

    fake_llm = FakeLLM()

    monkeypatch.setattr(llm_service, "MODEL_CANDIDATES", [("cerebras", "primary-model")])
    monkeypatch.setattr(llm_service, "LLM_RETRY_ATTEMPTS", 2)
    monkeypatch.setattr(llm_service, "_get_llm_client", lambda provider, model_name: fake_llm)
    monkeypatch.setattr(llm_service, "_compute_retry_delay_seconds", lambda attempt: 0.0)

    result = asyncio.run(
        llm_service._invoke_with_resilience(FakePrompt(), {"prompt": "x"}, operation="test")
    )

    assert result == "ok"
    assert fake_llm.calls == 2


def test_invoke_with_resilience_uses_fallback_model(monkeypatch):
    class FakeLLM:
        def __init__(self, responses):
            self._responses = list(responses)

        async def ainvoke(self, payload):
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    class FakePipeAfterLLM:
        def __init__(self, llm):
            self.llm = llm

        def __or__(self, _parser):
            return self

        async def ainvoke(self, payload):
            return await self.llm.ainvoke(payload)

    class FakePrompt:
        def __or__(self, llm):
            return FakePipeAfterLLM(llm)

    llm_by_model = {
        "primary-model": FakeLLM([RuntimeError("service unavailable")]),
        "fallback-model": FakeLLM(["fallback-ok"]),
    }

    monkeypatch.setattr(
        llm_service, "MODEL_CANDIDATES", [("cerebras", "primary-model"), ("cerebras", "fallback-model")]
    )
    monkeypatch.setattr(llm_service, "LLM_RETRY_ATTEMPTS", 1)
    monkeypatch.setattr(llm_service, "_get_llm_client", lambda provider, model_name: llm_by_model[model_name])

    result = asyncio.run(
        llm_service._invoke_with_resilience(FakePrompt(), {"prompt": "x"}, operation="test")
    )

    assert result == "fallback-ok"


def test_invoke_with_resilience_does_not_retry_non_transient_error(monkeypatch):
    class FakeLLM:
        async def ainvoke(self, payload):
            raise ValueError("invalid request payload")

    class FakePipeAfterLLM:
        def __init__(self, llm):
            self.llm = llm

        def __or__(self, _parser):
            return self

        async def ainvoke(self, payload):
            return await self.llm.ainvoke(payload)

    class FakePrompt:
        def __or__(self, llm):
            return FakePipeAfterLLM(llm)

    monkeypatch.setattr(llm_service, "MODEL_CANDIDATES", [("cerebras", "primary-model")])
    monkeypatch.setattr(llm_service, "LLM_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(llm_service, "_get_llm_client", lambda provider, model_name: FakeLLM())

    try:
        asyncio.run(
            llm_service._invoke_with_resilience(FakePrompt(), {"prompt": "x"}, operation="test")
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "invalid request payload" in str(exc)


def test_repair_code_from_runtime_error_returns_valid_code(monkeypatch):
    async def fake_invoke(prompt_template, payload, operation):
        return VALID_MEDIUM_CODE

    monkeypatch.setattr(llm_service, "_invoke_with_resilience", fake_invoke)

    result = asyncio.run(
        llm_service.repair_code_from_runtime_error(
            prompt="Explain circles",
            length="Medium (15s)",
            bad_code="class Broken: pass",
            runtime_error="Code error (ValueError): operands could not be broadcast together",
        )
    )

    assert result.startswith("from manim import *")


def test_repair_code_from_runtime_error_rejects_invalid_code(monkeypatch):
    async def fake_invoke(prompt_template, payload, operation):
        return "class Broken: pass"

    monkeypatch.setattr(llm_service, "_invoke_with_resilience", fake_invoke)

    try:
        asyncio.run(
            llm_service.repair_code_from_runtime_error(
                prompt="Explain circles",
                length="Medium (15s)",
                bad_code="class Broken: pass",
                runtime_error="Code error (ValueError): operands could not be broadcast together",
            )
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Runtime repair produced invalid code" in str(exc)

