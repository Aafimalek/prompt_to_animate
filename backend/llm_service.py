import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Ensure API Key is set
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print(f"Warning: GROQ_API_KEY not found in environment. Checked path: {env_path}")

llm = ChatGroq(
    model="moonshotai/kimi-k2-instruct-0905", 
    api_key=api_key,
    temperature=0.0 # Low temperature for deterministic code
)

LENGTH_GUIDE = {
    "Short (5s)": "Target duration: 5-10 seconds. Focus on a single, quick visual impact. No complex narration.",
    "Medium (15s)": "Target duration: 15-20 seconds. Explain the core concept with 2-3 clear steps. Moderate pacing.",
    "Long (1m)": "Target duration: ~60 seconds. Comprehensive explanation. Break down into 4-5 sections. Use `self.wait(2)` often. Detailed step-by-step.",
    "Deep Dive (2m)": "Target duration: 120+ seconds (CRITICAL: MUST BE LONG). this is a full tutorial. \n- Break content into 6-8 distinct phases.\n- Explain 'Why', 'How', and 'Examples'.\n- Use `self.wait(3)` or more after every text block.\n- If the topic is simple, show multiple examples or edge cases to fill time."
}

template = """
You are an expert Manim (Community Edition) Animation Developer.
Your goal is to create STUNNING, HIGH-QUALITY, and ACCURATE educational videos.

User Prompt: {prompt}
Target Length: {length_instruction}

### VISUAL STYLE GUIDE (STRICT):
1. **Colors**: Use Manim's standard colors (BLUE, TEAL, YELLOW, RED, GREEN). Avoid default white for everything.
2. **Typography**: Use `Text` or `MarkupText` with clean fonts. Scale text appropriately (not too huge, not too tiny).
3. **Layout**:
     - distinct sections should be cleared with `self.play(FadeOut(...))` before new ones start.
     - Use `VGroup` to arrange elements: `group.arrange(DOWN, buff=0.5)`.
     - Center main content.
4. **Animations**: 
     - Use `Write` for text, `Create` for shapes, `DrawBorderThenFill` for boxes.
     - Use `Transform` or `ReplacementTransform` to show changes.
     - ALWAYS use `self.wait(...)` to let the user read text.

### CRITICAL REQUIREMENTS:
1. **Imports**: Start with `from manim import *`.
2. **Class**: Define strictly one class `class GenScene(Scene):`.
3. **Method**: Implement `def construct(self):`.
4. **Assets**: NO external images/sounds. Use only Manim primitives.
5. **Length**: {length_instruction}
   - The user explicitly requested this length. logic: simpler visuals + longer waits = longer video. More steps = longer video.
6. **Robustness**: 
   - Ensure specific variable names are defined before use.
   - Avoid infinite loops.
   - Use `math` module if needed, it is available standard python.

### PLAN BEFORE YOU CODE:
(Write these as comments inside the generate code block, at the top)
# PLAN:
# 1. Intro (0-5s): ...
# 2. Main Concept (5-X s): ...
# ...
# Total expected time: ~Y seconds

Return ONLY the Python code. No markdown backticks, no text before/after.
"""

def clean_code(code: str) -> str:
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()

async def generate_manim_code(prompt: str, length: str) -> str:
    # Resolve length instruction
    length_instruction = LENGTH_GUIDE.get(length, "Target duration: ~15 seconds. Standard explanation.")
    
    prompt_template = ChatPromptTemplate.from_template(template)
    chain = prompt_template | llm | StrOutputParser()
    
    response = await chain.ainvoke({
        "prompt": prompt, 
        "length_instruction": length_instruction
    })
    
    return clean_code(response)
