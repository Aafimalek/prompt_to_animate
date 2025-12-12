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
# NOTE: LLM consistently under-produces, so we DOUBLE the wait requirements
LENGTH_GUIDE = {
    "Medium (15s)": """
⏱️ TARGET: EXACTLY 15-20 SECONDS. Count every second!

MANDATORY TIME BUDGET (ADD THIS AS A CODE COMMENT):
```python
# TIME BUDGET:
# Title: 3s (Write + wait(2))
# Main Visual: 8s (Create + wait(2) + animate + wait(2) + wait(2))
# Conclusion: 4s (Transform + wait(3))
# TOTAL: 15s ✓
```

STRUCTURE (2 clear sections):
1. Title card (3s): Write(title), wait(2)
2. Main concept (12s): Create shapes, animate, multiple wait(2) calls

TIMING COMMANDS YOU MUST USE:
- self.wait(2) after EVERY major visual change
- run_time=1.5 for animations
- MINIMUM 6 wait() calls, each 2 seconds = 12+ seconds of pauses alone

VALIDATION: Your play() calls + wait() calls MUST add up to 15+ seconds.
""",
    
    "Long (1m)": """
⏱️ TARGET: EXACTLY 55-65 SECONDS. This is a FULL MINUTE video.

⚠️ COMMON MISTAKE: Videos come out 30-40s. You MUST add more content and wait() calls!

MANDATORY TIME BUDGET (ADD THIS AS A CODE COMMENT):
```python
# TIME BUDGET:
# Section 1 - Title: 5s (Write + wait(3) + wait(2))
# Section 2 - Intro Concept: 15s (multiple animations + wait(3)*5)  
# Section 3 - Core Explanation: 20s (step-by-step + wait(3)*6)
# Section 4 - Example: 15s (demo + wait(3)*4)
# Section 5 - Summary: 10s (recap + wait(3)*3)
# TOTAL: 65s ✓
```

STRUCTURE (5 sections, NOT 3):
1. Title & Hook (5s)
2. Introduction/Definition (15s) 
3. Core Concept Explanation (20s)
4. Visual Example/Demo (15s)
5. Summary (10s)

TIMING COMMANDS:
- MINIMUM 25 wait() calls throughout the video
- Use wait(3) as your DEFAULT (not wait(1) or wait(2))
- After EVERY text/shape appears: wait(3)
- After EVERY transformation: wait(3)
- run_time=2 for all major animations

⚠️ SECTION CLEARING: At the END of each section, clear the screen:
`self.play(FadeOut(*self.mobjects))`

VALIDATION: 25 wait(3) calls = 75 seconds of pauses. Add animations on top.
""",
    
    "Deep Dive (2m)": """
⏱️ TARGET: EXACTLY 110-130 SECONDS (2 full minutes).

⚠️ CRITICAL: Your video MUST be at least 110 seconds. Count carefully!

MANDATORY TIME BUDGET (ADD THIS EXACT COMMENT IN YOUR CODE):
```python
# TIME BUDGET - MUST TOTAL 120 SECONDS:
# Section 1 - Title & Hook: 10s (title + hook visual + wait(3) + wait(3))
# Section 2 - Definition: 20s (text reveals + diagram + wait(3)*6)
# Section 3 - Mechanism Part A: 25s (step 1,2,3 + wait(3)*8)
# Section 4 - Mechanism Part B: 25s (step 4,5,6 + wait(3)*8)
# Section 5 - Visual Demo: 20s (animated walkthrough + wait(3)*6)
# Section 6 - Summary: 20s (key points + final visual + wait(3)*6)
# TOTAL: 120s ✓ (40+ wait calls × 3s average = 120s+)
```

MANDATORY STRUCTURE (6 substantial sections):
1. Title & Hook (10s): Engaging title + hook question
2. Definition (20s): What is this? Multiple reveals
3. Mechanism Part A (25s): First half of how it works
4. Mechanism Part B (25s): Second half, deeper
5. Visual Demo (20s): Show it in action
6. Summary (20s): Recap ALL key points

TIMING COMMANDS (CRITICAL):
- MINIMUM 40 wait() calls throughout
- wait(3) is your DEFAULT - use it after EVERYTHING
- Each section needs 6-8 wait() calls minimum
- run_time=2.5 for main animations
- Add wait(4) before transitions for extra breathing room

⚠️ SECTION CLEARING (PREVENT OVERLAP):
- At the END of each section: `self.play(FadeOut(*self.mobjects))`
- Start each new section with a CLEAN screen

DO THE MATH: 40 waits × 3 seconds = 120 seconds minimum.
""",

    "Extended (5m)": """
⏱️ TARGET: EXACTLY 280-320 SECONDS (5 FULL MINUTES).

⚠️ CRITICAL WARNING: Previous attempts only hit 150s. You need DOUBLE the content!

THIS IS A UNIVERSITY MINI-LECTURE. Take your time. Explain thoroughly.

MANDATORY TIME BUDGET (ADD THIS EXACT COMMENT IN YOUR CODE):
```python
# TIME BUDGET - MUST TOTAL 300 SECONDS (5 MINUTES):
# Section 1 - Title & Hook: 15s (dramatic title + hook + wait(4)*3)
# Section 2 - Why This Matters: 35s (context + motivation + wait(4)*8)
# Section 3 - Prerequisites/Basics: 40s (foundation + wait(4)*10)
# Section 4 - Core Concept Part A: 45s (first half explanation + wait(4)*11)
# Section 5 - Core Concept Part B: 45s (second half + wait(4)*11)  
# Section 6 - Detailed Visual Demo: 40s (walk through example + wait(4)*10)
# Section 7 - Real Applications: 40s (2-3 examples + wait(4)*10)
# Section 8 - Summary & Takeaways: 40s (comprehensive recap + wait(4)*10)
# TOTAL: 300s ✓ (80+ wait calls = 320s of pauses alone!)
```

MANDATORY STRUCTURE (8 FULL SECTIONS - NO SHORTCUTS):
1. Title & Hook (15s): Dramatic entrance, pose a question
2. Why This Matters (35s): Real-world impact, motivation  
3. Prerequisites/Basics (40s): Foundation concepts needed
4. Core Concept Part A (45s): Detailed first half
5. Core Concept Part B (45s): Detailed second half
6. Visual Demonstration (40s): Complete animated walkthrough
7. Real Applications (40s): Multiple concrete examples
8. Summary & Takeaways (40s): Recap EVERY major point

TIMING COMMANDS (ABSOLUTELY REQUIRED):
- MINIMUM 80 wait() calls (yes, eighty!)
- wait(4) is your DEFAULT for this video length
- Each section MUST have 8-12 wait() calls
- run_time=3 for ALL major animations
- Use wait(5) between sections for clear separation
- Add self.wait(3) after EVERY single text or shape

⚠️ SECTION CLEARING (CRITICAL FOR LONG VIDEOS):
- At the END of EVERY section, ALWAYS clear the screen:
  ```python
  self.play(FadeOut(*self.mobjects))
  self.wait(1)
  ```
- NEVER have text from one section still visible when next section starts
- Before each new section: ensure screen is EMPTY, then add new content

DO THE MATH: 80 waits × 4 seconds average = 320 seconds = 5+ minutes.

PACING: This should feel SLOW and RELAXED. Viewers need time to think.
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
        surface = Surface(lambda u, v: np.array([u, v, np.sin(u)*np.cos(v)]), ...)
        
        # Camera animation
        self.move_camera(phi=60*DEGREES, theta=30*DEGREES, run_time=2)
```
ONLY use ThreeDScene when the topic genuinely needs 3D (e.g., 3D surfaces, spheres, spatial relationships).

### ⚠️ 3D OVERLAP PREVENTION (CRITICAL FOR 3D SCENES):
In 3D scenes, text and 3D objects MUST be shown SEPARATELY to avoid overlap:

**RULE 1: NEVER show text and 3D objects at the same time**
```python
# WRONG - text overlaps with 3D surface:
surface = Surface(...)
text = Text("Explanation").to_edge(UP)
self.play(Create(surface), Write(text))  # ❌ OVERLAP!

# CORRECT - show separately:
# Step 1: Show 3D object alone
surface = Surface(...)
self.play(Create(surface))
self.wait(2)

# Step 2: FadeOut 3D, then show text
self.play(FadeOut(surface))
text = Text("Explanation").to_edge(UP)
self.play(Write(text))
self.wait(2)

# Step 3: FadeOut text, show 3D again if needed
self.play(FadeOut(text))
self.play(FadeIn(surface))
```

**RULE 2: For 3D scenes with labels, use fixed_in_frame_mobjects**
```python
# This keeps text fixed to camera (doesn't move with 3D rotation)
label = Text("Label", font_size=32).to_corner(UL)
self.add_fixed_in_frame_mobjects(label)  # Text stays in corner
self.play(Write(label))
```

**RULE 3: Position 3D objects to leave space for text**
```python
# Scale down and position 3D objects to lower half of screen
surface = Surface(...).scale(0.6).shift(DOWN * 0.5)
axes = ThreeDAxes().scale(0.6).shift(DOWN * 0.5)
# Now upper area is free for fixed text labels
```

**RULE 4: Clear screen between 3D and text sections**
- When transitioning from 3D to text: `self.play(FadeOut(*self.mobjects))`
- When transitioning from text to 3D: `self.play(FadeOut(*self.mobjects))`
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
- **BOUNDS CHECK**: Keep ALL content within visible frame (x: -6.5 to 6.5, y: -3.5 to 3.5)

⚠️ OVERLAP PREVENTION RULES:

**TITLE RULE:**
- Show title FIRST, ALONE on screen
- FadeOut title BEFORE showing diagrams:
  ```python
  title = Text("Topic Name", font_size=48).to_edge(UP)
  self.play(Write(title))
  self.wait(1.5)
  self.play(FadeOut(title))
  # Now show diagrams
  ```

**TEXT vs VISUAL ELEMENTS (IMPORTANT DISTINCTION):**
- TEXT elements (labels, explanations): MAX 2-3 on screen at once
- VISUAL elements (shapes, diagrams, arrows): CAN have many, if properly arranged
- For complex diagrams (neural networks, flowcharts, etc.):
  * Scale the entire diagram: `.scale(0.5)` to `.scale(0.7)`
  * Use `VGroup` to keep related parts together
  * Position the group in CENTER zone

**POSITIONING RULE:**
- Reserve screen ZONES:
  * TOP (y > 2.5): Titles only
  * CENTER (-2 < y < 2): Main diagrams
  * BOTTOM (y < -2.5): Text explanations
- Always position explicitly: `.to_edge()`, `.move_to()`, `.next_to()`

**PREVENTING OFF-SCREEN ELEMENTS:**
- After creating shapes, ALWAYS scale and position BEFORE animating
- Use `.scale_to_fit_width(12)` for wide content
- Group and arrange: `VGroup(...).arrange(RIGHT, buff=0.3).move_to(ORIGIN)`
- Check bounds: nothing should exceed x=±6 or y=±3

**Animation Quality (3Blue1Brown Style)**:
ENTRANCE ANIMATIONS (choose appropriately):
- `Write()` for text - reveals character by character
- `Create()` for shapes - draws the outline
- `DrawBorderThenFill()` for filled shapes - elegant reveal  
- `GrowFromCenter()` for dramatic emphasis
- `FadeIn(shift=UP*0.3)` for subtle entrances

TRANSFORMATIONS (the 3b1b signature):
- `Transform(a, b)` - morph one shape into another
- `ReplacementTransform(a, b)` - replace with morph effect
- `TransformFromCopy(a, b)` - copy then morph
- Use these to show RELATIONSHIPS between concepts

TRANSITIONS BETWEEN SECTIONS:
- `self.play(FadeOut(*self.mobjects))` - clear everything
- `self.wait(2)` - pause after clearing
- Then introduce new section

HIGHLIGHTS & EMPHASIS:
- `Indicate(obj)` - brief attention pulse
- `Circumscribe(obj)` - draw circle around
- `Flash(obj)` - bright flash
- `obj.animate.set_color(YELLOW)` - color change

SMOOTH MOTION:
- Use `run_time=2` minimum for important animations
- `rate_func=smooth` for natural movement (default)
- Chain related animations: `self.play(Create(a), Create(b))`

BUILD COMPLEXITY PROGRESSIVELY:
- Show simple version first
- Add details layer by layer
- Explain each addition before adding more
- Never show complex diagram all at once

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

7. **NEVER use `about_vector` in Rotate() - use `axis` instead**:
   ❌ `Rotate(obj, angle=PI, about_vector=[1,0,0])`
   ✅ `Rotate(obj, angle=PI, axis=RIGHT)`
   ✅ `Rotate(obj, angle=PI, axis=np.array([1,0,0]))`

8. **Rotate syntax for 3D objects**:
   ✅ `self.play(Rotate(sphere, angle=PI, axis=UP, run_time=2))`
   ✅ `sphere.rotate(PI/2, axis=RIGHT)` for instant rotation

9. **ALWAYS close parentheses properly**:
   ❌ `self.play(Rotate(sphere, angle=PI, axis=UP),` (missing closing paren)
   ✅ `self.play(Rotate(sphere, angle=PI, axis=UP))`

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
