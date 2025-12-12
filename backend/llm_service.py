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

# Detailed length guides with STRICT timing limits - 3BLUE1BROWN STYLE
LENGTH_GUIDE = {
    "Medium (15s)": """
TARGET: 15-18 seconds. STRICT MAXIMUM: 20 seconds.
⚠️ ANY VIDEO OVER 20 SECONDS IS UNACCEPTABLE.

TIME BUDGET:
- Title: 2-3s (run_time=1.5, wait(1))
- Section 1: 5-6s (main concept introduction)
- Section 2: 5-6s (visual demonstration)
- Conclusion: 2-3s

STRUCTURE:
- Clean title with topic name (2-3s)
- 2 well-paced content sections (5-6s each)
- Clear transitions with FadeOut between sections

RULES:
- Maximum 5 total wait() calls, each 1-2 seconds
- Count your seconds: animations default to ~1s each
- Clear previous content before adding new
""",
    
    "Long (1m)": """
TARGET: 55-65 seconds. STRICT MAXIMUM: 70 seconds.
⚠️ ANY VIDEO OVER 70 SECONDS IS UNACCEPTABLE.

TIME BUDGET (calculate before coding):
- Title: 4-5s
- Section 1: 12-15s (introduce topic)
- Section 2: 15-18s (explain mechanism/process)
- Section 3: 15-18s (examples/applications)
- Conclusion: 6-8s

STRUCTURE:
- Title with brief intro (4-5s)
- 3 main content sections (12-18s each)
- Brief conclusion/summary (6-8s)

RULES:
- Maximum 15 wait() calls total
- Average wait() = 2 seconds
- Clear each section with FadeOut before next
- Write time budget in comments
""",
    
    "Deep Dive (2m)": """
⚠️ CRITICAL MINIMUM: 110 SECONDS. ANY VIDEO UNDER 110 SECONDS WILL BE REJECTED.
TARGET: 115-125 seconds. This is a COMPREHENSIVE educational video.

YOU MUST REACH AT LEAST 110 SECONDS. Count your time carefully!

TIME BUDGET (MANDATORY - WRITE THIS COMMENT IN YOUR CODE):
```
# TIME BUDGET PLAN:
# Section 1 - Title & Hook: 8-10s
# Section 2 - Definition: 18-22s
# Section 3 - Core Concept: 22-28s
# Section 4 - Visual Demo: 22-28s
# Section 5 - Example: 18-24s
# Section 6 - Summary: 12-18s
# TOTAL: 115-125 seconds ✓
```

MANDATORY STRUCTURE (6 full sections):
1. Title & Hook (8-10s): Title + engaging intro visual + wait(3)
2. What is it? (18-22s): Multiple text reveals, diagram
3. Core Mechanism (22-28s): Step-by-step breakdown with animations
4. Visual Demonstration (22-28s): Show the concept in action
5. Concrete Example (18-24s): Real-world application
6. Summary & Key Points (12-18s): Recap main ideas

TIMING RULES:
- MINIMUM 30 self.wait() calls (averaging 2-3 seconds each)
- Use self.wait(3) liberally - let viewers absorb content
- Each section MUST have at least 4 wait() calls
- Use run_time=2 or run_time=2.5 for complex animations
""",

    "Extended (5m)": """
⚠️ CRITICAL: TARGET 280-320 SECONDS (4.5-5.5 MINUTES).
This is a COMPREHENSIVE MINI-LECTURE. Think university-level explanation.

MINIMUM: 280 seconds. MAXIMUM: 330 seconds.

TIME BUDGET (MANDATORY - CALCULATE CAREFULLY):
```
# TIME BUDGET PLAN:
# Section 1 - Title & Hook: 12-15s
# Section 2 - Introduction & Overview: 30-40s
# Section 3 - Fundamentals/Basics: 40-50s
# Section 4 - Core Mechanism (Part A): 40-50s
# Section 5 - Core Mechanism (Part B): 40-50s
# Section 6 - Visual Demonstration: 35-45s
# Section 7 - Real-World Examples: 35-45s
# Section 8 - Summary & Key Takeaways: 20-30s
# TOTAL: ~300 seconds (5 minutes) ✓
```

MANDATORY STRUCTURE (8 comprehensive sections):
1. Title & Hook (12-15s): Engaging title + hook question/visual
2. Introduction & Overview (30-40s): Set context, why this matters
3. Fundamentals/Basics (40-50s): Foundation concepts, prerequisites
4. Core Mechanism Part A (40-50s): First half of main explanation
5. Core Mechanism Part B (40-50s): Second half, deeper details
6. Visual Demonstration (35-45s): Detailed animated walkthrough
7. Real-World Examples (35-45s): 2-3 practical applications
8. Summary & Key Takeaways (20-30s): Recap all main points

TIMING RULES (CRITICAL):
- MINIMUM 60 self.wait() calls throughout
- Use self.wait(3) and self.wait(4) frequently
- Each section MUST have at least 6 wait() calls
- Use run_time=2.5 or run_time=3 for important animations
- Build diagrams progressively - never rush
- This should feel like a relaxed, thorough explanation
"""
}


template = """
You are an EXPERT Manim (Community Edition) Animation Developer creating content in the style of 3BLUE1BROWN.
Your animations are used by millions of students worldwide. They must be:
1. **FACTUALLY ACCURATE** - All information MUST be correct. Double-check facts.
2. **VISUALLY STUNNING** - Professional, elegant animations like 3Blue1Brown videos.
3. **PROPERLY TIMED** - Match the requested duration precisely (within ±5 seconds).
4. **MATHEMATICALLY ELEGANT** - Smooth transformations, meaningful visuals, no clutter.

═══════════════════════════════════════════════════════════════════
USER REQUEST: {prompt}
═══════════════════════════════════════════════════════════════════
DURATION REQUIREMENT:
{length_instruction}
═══════════════════════════════════════════════════════════════════

### 3BLUE1BROWN VISUAL STYLE (ESSENTIAL):
Your animations should capture the essence of 3Blue1Brown videos:
- **Mathematical elegance**: Smooth, continuous transformations between concepts
- **Progressive reveals**: Build complexity step-by-step, never overwhelm
- **Meaningful motion**: Every animation should teach, not just look pretty
- **Calm pacing**: Let ideas breathe with adequate wait() calls
- **Geometric beauty**: Use circles, lines, and curves as primary shapes
- Use `Transform()` and `ReplacementTransform()` to morphg between related concepts
- Camera movements should be smooth and purposeful (for 3D)

### 3D ANIMATIONS (Use When Appropriate):
For topics that benefit from 3D visualization (3D geometry, surfaces, spatial concepts):
```python
class GenScene(ThreeDScene):  # Use ThreeDScene instead of Scene
    def construct(self):
        # Set up 3D camera
        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
        
        # Create 3D objects
        axes = ThreeDAxes()
        sphere = Sphere(radius=1, color=BLUE)
        surface = Surface(lambda u, v: [u, v, np.sin(u)*np.cos(v)], ...)
        
        # Camera animation
        self.move_camera(phi=60*DEGREES, theta=30*DEGREES, run_time=2)
```
ONLY use ThreeDScene when the topic genuinely needs 3D (e.g., 3D surfaces, spheres, spatial relationships).
For 2D topics (sorting algorithms, graphs, formulas), use regular `Scene`.

### FACTUAL ACCURACY (CRITICAL):
- Research-level accuracy. If explaining a concept, use correct definitions.
- For math/science: Use correct formulas, units, and relationships.
- For history/facts: Use verified information only.
- If unsure about a specific fact, use general principles that are definitely true.
- DO NOT make up statistics, dates, or claims. Be accurate or be general.

### VISUAL QUALITY STANDARDS:

**Color Palette** (3Blue1Brown signature style):
- Primary: BLUE_E, BLUE_D, BLUE_C for main elements (signature blue)
- Accent: YELLOW, GOLD for highlights, emphasis, and key results
- Secondary: TEAL_E, GREEN_D for supporting elements and comparisons
- Contrast: MAROON, RED_D for important warnings or differences
- Text: WHITE for main text, GRAY_B for labels
- Background elements: Use opacity (e.g., BLUE.set_opacity(0.2))

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

**COMPLEX TOPIC VISUALIZATION (CRITICAL FOR ACCURACY)**:
When explaining technical/scientific topics, use ACCURATE visual representations:

For ALGORITHMS (sorting, searching, etc.):
- Show actual data structures with labeled values
- Animate each step of the algorithm with arrows showing comparisons/swaps
- Use color coding: current element (YELLOW), compared (BLUE), sorted (GREEN)
- Show step counters and complexity notation

For NEURAL NETWORKS / ML:
- Draw actual network architecture with proper layer shapes
- Show data flow with animated arrows
- Label layer types (Input, Conv, Pool, Dense, Output)
- Show dimensions/shapes at each layer
- Animate forward pass with colored activations

For MATH / PHYSICS:
- Use proper mathematical notation (MathTex)
- Show equations step-by-step with annotations
- Animate graphs and functions with actual plot data
- Include units and variable labels
- Show relationships between concepts visually

For CS CONCEPTS (data structures, design patterns):
- Draw the actual structure (tree, graph, stack, queue)
- Show operations with animations (insert, delete, traverse)
- Use consistent visual language (nodes, edges, pointers)
- Label memory addresses or indices where relevant

For PROCESSES / WORKFLOWS:
- Use flowchart style with proper symbols
- Animate the flow with moving highlights
- Show decision branches clearly
- Include timing or sequence indicators

GENERAL ACCURACY RULES:
- RESEARCH the topic before generating - use correct terminology
- Show PROPORTIONS correctly (e.g., scale matters for size comparisons)
- Use REAL examples, not made-up data
- Include CONTEXT - why this matters, where it's used

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

### MANIM API PITFALLS (CRITICAL - WILL CAUSE ERRORS):
⚠️ These are COMMON MISTAKES that will crash your code:

1. **NEVER use `opacity` parameter** - Use `fill_opacity` or `stroke_opacity` instead:
   ❌ `Surface(..., opacity=0.5)`
   ✅ `Surface(..., fill_opacity=0.5)`

2. **For 3D scenes, use ThreeDScene NOT Scene**:
   ❌ `class GenScene(Scene):` with 3D objects
   ✅ `class GenScene(ThreeDScene):` for 3D content

3. **Surface requires specific syntax**:
   ✅ `Surface(lambda u, v: np.array([u, v, func(u,v)]), u_range=[-2,2], v_range=[-2,2], fill_opacity=0.7)`

4. **ThreeDAxes positioning**:
   ✅ `axes.c2p(x, y, z)` to convert coordinates to point

5. **Import numpy for 3D**:
   ✅ `import numpy as np` at top of file for 3D math

6. **Camera setup for 3D**:
   ✅ `self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)`

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
