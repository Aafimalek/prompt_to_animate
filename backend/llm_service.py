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
    temperature=0.2  # Slightly higher for creativity, but still focused
)

# Detailed length guides with concrete timing breakdowns
LENGTH_GUIDE = {
    "Short (5s)": """
TARGET: 5-10 seconds total.
STRUCTURE:
- 1 title card (2s with self.wait(2))
- 1 main visual showing the core concept (3-5s)
- Simple, impactful, minimal text
TIMING: Use self.wait(1) to self.wait(2) sparingly. Keep it punchy.
""",
    
    "Medium (15s)": """
TARGET: 15-25 seconds total.
STRUCTURE:
- Title/intro (3s)
- 2-3 main content sections (4-5s each)
- Brief conclusion/summary (2-3s)
TIMING: Use self.wait(2) after each major element. Total ~6-8 wait calls.
""",
    
    "Long (1m)": """
TARGET: 55-70 seconds total (approximately 1 minute).
STRUCTURE:
- Title with topic introduction (5s)
- Section 1: Define/Explain the concept (10-15s)
- Section 2: Show how it works with visuals (15-20s)
- Section 3: Example or application (15-20s)
- Conclusion/Key takeaway (5-10s)
TIMING: Use self.wait(2) to self.wait(3) after EVERY text block and visual transition.
Minimum 15 self.wait() calls throughout. Clear each section with FadeOut before next.
""",
    
    "Deep Dive (2m)": """
TARGET: 120-150 seconds total (2+ minutes). THIS MUST BE A LONG VIDEO.
STRUCTURE (6-8 distinct phases):
1. Title & Hook (5-10s): Attention-grabbing intro
2. What is it? (15-20s): Clear definition with visuals
3. Why does it matter? (15-20s): Real-world relevance
4. How does it work? (25-30s): Step-by-step breakdown with animations
5. Example 1 (20-25s): Concrete worked example
6. Example 2 or Edge Case (15-20s): Additional example or special cases
7. Common Mistakes/Tips (10-15s): What to watch out for
8. Summary & Recap (10-15s): Key points review

TIMING RULES (CRITICAL):
- self.wait(3) after EVERY text block
- self.wait(2) between animation steps
- self.wait(4) after complex diagrams to let viewers absorb
- Minimum 25-30 self.wait() calls total
- If content seems short, ADD MORE EXAMPLES or show the concept from different angles
"""
}

template = """
You are an EXPERT Manim (Community Edition) Animation Developer and an EXPERT Educator.
Your animations are used by millions of students worldwide. They must be:
1. **FACTUALLY ACCURATE** - All information MUST be correct. Double-check facts.
2. **VISUALLY STUNNING** - Professional, polished, broadcast-quality animations.
3. **PROPERLY TIMED** - Match the requested duration precisely.

═══════════════════════════════════════════════════════════════════
USER REQUEST: {prompt}
═══════════════════════════════════════════════════════════════════
DURATION REQUIREMENT:
{length_instruction}
═══════════════════════════════════════════════════════════════════

### FACTUAL ACCURACY (CRITICAL):
- Research-level accuracy. If explaining a concept, use correct definitions.
- For math/science: Use correct formulas, units, and relationships.
- For history/facts: Use verified information only.
- If unsure about a specific fact, use general principles that are definitely true.
- DO NOT make up statistics, dates, or claims. Be accurate or be general.

### VISUAL QUALITY STANDARDS:

**Color Palette** (use these for a professional look):
- Primary: BLUE, BLUE_C, BLUE_D for main elements
- Accent: YELLOW, GOLD for highlights and emphasis
- Secondary: TEAL, GREEN for supporting elements
- Warning/Important: RED, ORANGE for alerts
- Text: WHITE on dark backgrounds, contrasting colors for emphasis
- Background elements: Use opacity (e.g., BLUE.set_opacity(0.3))

**Typography**:
- Titles: `Text("Title", font_size=56, weight=BOLD, color=WHITE)`
- Body text: `Text("Content", font_size=36, color=WHITE)`
- Labels: `Text("Label", font_size=28, color=GRAY_B)`
- Math: `MathTex(r"E = mc^2", font_size=44, color=YELLOW)`
- NEVER use font_size > 60 for body text (it looks amateur)

**Layout Principles**:
- Center important content: `.move_to(ORIGIN)` or `.to_edge(UP)`
- Group related items: `VGroup(a, b, c).arrange(DOWN, buff=0.5)`
- Use consistent spacing: `buff=0.5` for tight, `buff=1` for loose
- Keep content within visible bounds (stay within 6 units from center)
- Section headers at TOP, content in CENTER, supporting info at BOTTOM

**Animation Quality**:
- Entrance: `Write()` for text, `Create()` for shapes, `GrowFromCenter()` for emphasis
- Transitions: `FadeOut()` old content BEFORE `FadeIn()` new content
- Highlights: `Indicate()`, `Circumscribe()`, `Flash()` for emphasis
- Movement: `shift()`, `move_to()` with smooth animations
- ALWAYS chain related animations: `self.play(Create(a), Create(b))`
- NEVER show more than 5-6 elements on screen at once (declutter!)

**Scene Structure**:
```
# Clear previous section
self.play(FadeOut(*self.mobjects))
self.wait(0.5)

# New section
title = Text("Section Title", font_size=48, color=BLUE)
title.to_edge(UP)
self.play(Write(title))
self.wait(1)
```

### TIMING CONTROL (VERY IMPORTANT):
- `self.wait(1)` = 1 second pause
- `self.wait(2)` = 2 seconds (good for reading short text)
- `self.wait(3)` = 3 seconds (good for complex visuals)
- Animation duration: `self.play(..., run_time=2)` for slower, clearer animations
- For longer videos: MORE self.wait() calls, not faster animations

### CODE REQUIREMENTS:
1. Start with: `from manim import *`
2. Define exactly ONE class: `class GenScene(Scene):`
3. Implement: `def construct(self):`
4. NO external assets (images, sounds, files)
5. Use standard Python `math` module if needed
6. All variables must be defined before use

### LaTeX RULES (CRITICAL - AVOID ERRORS):
- NEVER use Unicode symbols in MathTex: ×, ÷, π, ≈, ≤, ≥, ∑, ∫, √, etc.
- Use LaTeX: `\\times`, `\\div`, `\\pi`, `\\approx`, `\\leq`, `\\geq`, `\\sum`, `\\int`, `\\sqrt{{}}`
- For simple text with symbols, use `Text()` instead of `MathTex()`
- Always use raw strings: `MathTex(r"...")`
- Escape backslashes properly

### EXAMPLE STRUCTURE FOR A QUALITY ANIMATION:

```python
from manim import *

class GenScene(Scene):
    def construct(self):
        # PLAN:
        # 1. Title (0-5s)
        # 2. Definition (5-15s)
        # 3. Visual Explanation (15-35s)
        # 4. Example (35-50s)
        # 5. Summary (50-60s)
        # Total: ~60 seconds
        
        # === TITLE ===
        title = Text("Topic Name", font_size=56, weight=BOLD, color=BLUE)
        subtitle = Text("A clear explanation", font_size=32, color=GRAY_B)
        header = VGroup(title, subtitle).arrange(DOWN, buff=0.3)
        
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle, shift=UP*0.2))
        self.wait(2)
        
        # === TRANSITION ===
        self.play(FadeOut(header))
        self.wait(0.5)
        
        # === MAIN CONTENT ===
        # ... continue with educational content ...
```

### YOUR TASK:
Generate a complete, working Manim animation for: "{prompt}"
Duration: Follow the timing guide above EXACTLY.

Return ONLY the Python code. No markdown, no backticks, no explanation.
"""

def clean_code(code: str) -> str:
    """Remove any markdown formatting from the generated code."""
    code = code.strip()
    # Remove markdown code blocks
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    # Remove any leading/trailing whitespace
    code = code.strip()
    # Ensure the code starts with an import
    if not code.startswith("from manim import"):
        # Try to find where the actual code starts
        if "from manim import" in code:
            idx = code.index("from manim import")
            code = code[idx:]
    return code


async def generate_manim_code(prompt: str, length: str) -> str:
    """Generate Manim animation code from a user prompt."""
    # Resolve length instruction
    length_instruction = LENGTH_GUIDE.get(
        length, 
        "Target duration: ~15 seconds. Standard explanation with 2-3 sections."
    )
    
    prompt_template = ChatPromptTemplate.from_template(template)
    chain = prompt_template | llm | StrOutputParser()
    
    response = await chain.ainvoke({
        "prompt": prompt, 
        "length_instruction": length_instruction
    })
    
    return clean_code(response)
