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

# Detailed length guides with STRICT timing limits
LENGTH_GUIDE = {
    "Short (5s)": """
TARGET: 5-7 seconds. STRICT MAXIMUM: 7 seconds.
⚠️ ANY VIDEO OVER 7 SECONDS IS UNACCEPTABLE.

TIME BUDGET (you MUST follow this):
- Title entrance: 1.5s (run_time=1, wait(0.5))
- Main visual: 3-4s (run_time=1-2, wait(1-2))
- Total wait() calls: MAX 2-3, each ≤1 second

STRUCTURE:
- 1 title card (1.5s total)
- 1 main visual with the SINGLE core concept (3-4s)
- THAT'S IT. No more. Keep it punchy.

RULES:
- Maximum 2 text elements on screen
- DO NOT add explanations - just show the visual
- Use self.wait(0.5) or self.wait(1) ONLY
""",
    
    "Medium (15s)": """
TARGET: 15-17 seconds. STRICT MAXIMUM: 18 seconds.
⚠️ ANY VIDEO OVER 18 SECONDS IS UNACCEPTABLE.

TIME BUDGET:
- Title: 2s (run_time=1, wait(1))
- Section 1: 4-5s
- Section 2: 4-5s
- Section 3: 4-5s
- Total: 14-17 seconds MAX

STRUCTURE:
- Title/intro (2s)
- 2-3 content sections (4-5s each)
- Clear transitions with FadeOut between sections

RULES:
- Maximum 4 total wait() calls
- Each wait() is 1-2 seconds max
- Count your seconds: animations default to ~1s each
""",
    
    "Long (1m)": """
TARGET: 55-65 seconds. STRICT MAXIMUM: 70 seconds.
⚠️ ANY VIDEO OVER 70 SECONDS IS UNACCEPTABLE.

TIME BUDGET (calculate before coding):
- Title: 4s
- Section 1: 12-15s
- Section 2: 15-18s
- Section 3: 15-18s
- Conclusion: 5-8s
- TOTAL: 55-65 seconds

STRUCTURE:
- Title with brief intro (4s)
- 3 main content sections (12-18s each)
- Brief conclusion/summary (5-8s)

RULES:
- Maximum 12 wait() calls total
- Average wait() = 2 seconds
- Clear each section with FadeOut before next
- Count your time budget in comments
""",
    
    "Deep Dive (2m)": """
TARGET: 120-130 seconds. STRICT MAXIMUM: 135 seconds.
⚠️ ANY VIDEO OVER 135 SECONDS (2:15) IS UNACCEPTABLE.

TIME BUDGET (MANDATORY - write this in comments):
- Title & Hook: 8s
- Definition: 18s
- How it works: 25s
- Example 1: 25s
- Example 2: 20s
- Tips/Summary: 20s
- TOTAL: ~120 seconds

STRUCTURE (6 sections):
1. Title & Hook (5-8s)
2. What is it? Definition (15-20s)
3. How does it work? (20-25s)
4. Example 1 with walkthrough (20-25s)
5. Example 2 or application (15-20s)
6. Summary & key points (15-20s)

RULES:
- Maximum 25 wait() calls
- Average wait() = 2-3 seconds
- MUST include time budget comment at top of construct()
- If running long, CUT content, don't speed up
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

**Layout Principles & OVERLAP PREVENTION (CRITICAL)**:
- Center important content: `.move_to(ORIGIN)` or `.to_edge(UP)`
- Group related items: `VGroup(a, b, c).arrange(DOWN, buff=0.5)`
- Use consistent spacing: `buff=0.5` for tight, `buff=1` for loose
- Keep content within visible bounds (stay within 5.5 units from center)

⚠️ OVERLAP PREVENTION RULES (MUST FOLLOW):
- ALWAYS clear screen between MAJOR sections: `self.play(FadeOut(*self.mobjects))`
- TEXT LIMIT: Maximum 2-3 text labels visible at once (prevents reading confusion)
- VISUAL ELEMENTS: Can show more shapes/diagrams if arranged properly using:
  * `VGroup(...).arrange(RIGHT, buff=0.3)` for horizontal layouts
  * `VGroup(...).arrange(DOWN, buff=0.3)` for vertical layouts
  * Grid layouts for complex diagrams like CNN layers
- For COMPLEX DIAGRAMS (CNN, neural networks, flowcharts):
  * Build progressively: show one component, explain, then add next
  * Use `.scale(0.5)` to `.scale(0.7)` for fitting multiple components
  * Group related elements: `layer1 = VGroup(nodes, connections)`
  * Use `.shift()` to position groups in different screen areas
- Reserve screen ZONES (don't put text in diagram area):
  * TOP ZONE (y > 2.5): Titles only
  * CENTER ZONE (-2.5 < y < 2.5): Main diagrams
  * BOTTOM ZONE (y < -2.5): Explanatory text, formulas
- Position EVERY element explicitly with:
  * `.to_edge(UP/DOWN/LEFT/RIGHT)`
  * `.next_to(other_element, direction, buff=0.5)`
- For long text: `Text(...).scale_to_fit_width(12)` to prevent overflow
- When adding new elements, decide: keep existing OR fade them out

**Animation Quality**:
- Entrance: `Write()` for text, `Create()` for shapes, `GrowFromCenter()` for emphasis
- Transitions: `FadeOut()` old content BEFORE `FadeIn()` new content
- Highlights: `Indicate()`, `Circumscribe()`, `Flash()` for emphasis
- Movement: `shift()`, `move_to()` with smooth animations
- ALWAYS chain related animations: `self.play(Create(a), Create(b))`
- For complex diagrams: Build incrementally, showing one part at a time

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

### TIMING CONTROL (CRITICAL - YOUR VIDEO WILL BE REJECTED IF TOO LONG):

⏱️ TIME BUDGET CALCULATION (MANDATORY):
Before writing code, mentally calculate your total runtime:
- Count each self.play() as ~1 second (unless run_time specified)
- Add all self.wait(X) durations
- SUM MUST BE WITHIN ±2 SECONDS OF TARGET

Reference:
- `self.wait(0.5)` = half second
- `self.wait(1)` = 1 second 
- `self.wait(2)` = 2 seconds
- `self.play(..., run_time=1.5)` = 1.5 seconds

⚠️ DURATION LIMITS:
- Short (5s): MAX 3 wait() calls, MAX 7 seconds total
- Medium (15s): MAX 6 wait() calls, MAX 18 seconds total  
- Long (1m): MAX 12 wait() calls, MAX 70 seconds total
- Deep Dive (2m): MAX 25 wait() calls, MAX 135 seconds total

RULE: If your animation seems long, REMOVE CONTENT. Do not try to speed up.

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
