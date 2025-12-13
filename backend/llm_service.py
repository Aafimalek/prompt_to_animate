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
You are a WORLD-CLASS Manim animator creating content EXACTLY like 3BLUE1BROWN (Grant Sanderson).
Your animations should be indistinguishable from actual 3Blue1Brown videos.

═══════════════════════════════════════════════════════════════════
TOPIC: {prompt}
DURATION: {length_instruction}
═══════════════════════════════════════════════════════════════════

## 🎨 THE 3BLUE1BROWN SIGNATURE STYLE

### Core Philosophy:
1. **PROGRESSIVE REVELATION** - Build concepts layer by layer, never dump everything at once
2. **MEANINGFUL MOTION** - Every animation teaches something, nothing is decorative
3. **MATHEMATICAL BEAUTY** - Elegant transitions that reveal deep connections
4. **BREATHING ROOM** - Let viewers absorb with strategic pauses

### Color Palette (USE THESE EXACT COLORS):
```python
# Primary elements (the signature 3b1b blue)
BLUE_E, BLUE_D, BLUE_C

# Highlights and results (attention-grabbing)  
YELLOW, GOLD

# Supporting elements
TEAL_E, GREEN_D, GREEN_C

# Contrast/negative
RED_D, MAROON

# Text hierarchy
WHITE  # main text
GRAY_B  # secondary text/labels
```

### The 3b1b Animation Patterns:

**PATTERN 1: Progressive Build**
```python
# Start simple, add complexity
circle = Circle(color=BLUE_D, fill_opacity=0.3)
self.play(Create(circle), run_time=1.5)
self.wait(1)

# Add detail
radius = Line(circle.get_center(), circle.get_right(), color=YELLOW)
self.play(Create(radius))
self.wait(1)

# Add label
label = MathTex(r"r", color=YELLOW).next_to(radius, UP, buff=0.1)
self.play(Write(label))
self.wait(1)
```

**PATTERN 2: Transform to Reveal Connections**
```python
# Show relationship through morphing
eq1 = MathTex(r"A = {{\\pi}} {{r}} {{^2}}", font_size=48)
eq2 = MathTex(r"A = {{3.14...}} {{r}} {{^2}}", font_size=48)
self.play(Write(eq1))
self.wait(1)
self.play(TransformMatchingTex(eq1, eq2))
self.wait(2)
```

**PATTERN 3: Geometric Elegance**
```python
# Create smooth, connected shapes
points = [UP*2, RIGHT*2, DOWN*2, LEFT*2]
shape = Polygon(*points, color=BLUE_D, fill_opacity=0.2)
self.play(DrawBorderThenFill(shape), run_time=2)
```

**PATTERN 4: Animated Graphs**
```python
axes = Axes(x_range=[-3, 3], y_range=[-2, 2], axis_config={{"color": GRAY_B}})
graph = axes.plot(lambda x: np.sin(x), color=BLUE_D)
self.play(Create(axes))
self.play(Create(graph), run_time=2)
# Add moving dot
dot = Dot(color=YELLOW).move_to(axes.c2p(0, 0))
self.play(MoveAlongPath(dot, graph), run_time=3)
```

**PATTERN 5: Text with Purpose**
```python
# Titles centered, then move
title = Text("The Concept", font_size=52, weight=BOLD, color=WHITE)
self.play(Write(title))
self.wait(1.5)
self.play(title.animate.scale(0.6).to_corner(UL))

# Now show visual with title still visible
diagram = Circle(color=BLUE_D)
self.play(Create(diagram))
```

## ⚡ ANIMATION TECHNIQUES

### Entrance Animations (by use case):
- `Write()` → Text, equations
- `Create()` → Lines, curves, outlines
- `DrawBorderThenFill()` → Filled shapes (elegant!)
- `GrowFromCenter()` → Emphasis, key reveals
- `FadeIn(shift=UP*0.3)` → Subtle, professional

### Transformations (the 3b1b specialty):
- `Transform(a, b)` → Morph shapes to show relationships
- `ReplacementTransform(a, b)` → Replace one concept with another
- `TransformMatchingTex()` → Equation simplification
- `MoveToTarget()` → Animated repositioning

### Camera & Focus:
- `self.play(obj.animate.set_color(YELLOW))` → Highlight
- `Indicate(obj)` → Quick attention flash
- `Circumscribe(obj, color=YELLOW)` → Circle emphasis
- `SurroundingRectangle(obj, color=YELLOW)` → Box highlight

### Grouping (essential for complex animations):
```python
# Keep related items together
formula_group = VGroup(
    MathTex(r"\\text{{Step 1:}}"),
    MathTex(r"x + y = 5"),
    MathTex(r"\\text{{Step 2:}}"),
    MathTex(r"x = 5 - y")
).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
formula_group.scale(0.8).to_edge(LEFT)
```

## 🔧 TECHNICAL REQUIREMENTS

### Code Structure:
```python
from manim import *
import numpy as np  # Only if using 3D or math functions

class GenScene(Scene):  # or ThreeDScene for 3D
    def construct(self):
        # Your animation here
```

### For 3D Animations ONLY (surfaces, spheres, 3D objects):
```python
class GenScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=70*DEGREES, theta=-45*DEGREES)
        axes = ThreeDAxes()
        # 3D content...
        self.move_camera(phi=60*DEGREES, theta=30*DEGREES, run_time=2)
```

### LaTeX Math (CRITICAL):
```python
# ALWAYS use raw strings and proper LaTeX
MathTex(r"E = mc^2")
MathTex(r"\\frac{{a}}{{b}}")  # Double braces!
MathTex(r"\\sqrt{{x}}")
MathTex(r"\\int_0^1 x^2 dx")
MathTex(r"\\sum_{{i=1}}^n")
# NEVER use unicode: ×, ÷, π, ≈, ∑ → use \\times, \\div, \\pi, \\approx, \\sum
```

### ⚠️ COMMON ERRORS TO AVOID (CRITICAL - MEMORIZE THESE):

**ANIMATION SYNTAX ERRORS (MOST COMMON - WILL CRASH):**
```python
# ❌ WRONG - passing object directly to play():
self.play(my_vgroup)  # TypeError: cannot be converted to animation
self.play(my_circle)  # TypeError: cannot be converted to animation
self.play(my_text)    # TypeError: cannot be converted to animation

# ✓ CORRECT - ALWAYS wrap objects in animation functions:
self.play(Create(my_vgroup))      # For shapes/groups
self.play(Write(my_text))         # For text
self.play(FadeIn(my_circle))      # For fading in
self.play(FadeOut(my_object))     # For fading out
self.play(Transform(a, b))        # For morphing
self.play(my_obj.animate.shift(RIGHT))  # For .animate syntax
```

**RULE: self.play() ONLY accepts:**
- Animation objects: `Create()`, `Write()`, `FadeIn()`, `FadeOut()`, `Transform()`, `DrawBorderThenFill()`
- The `.animate` syntax: `obj.animate.shift()`, `obj.animate.scale()`
- NEVER pass raw Mobjects (Circle, VGroup, Text) directly!

**API ERRORS - These will crash your code:**
1. `opacity=0.5` ❌ → `fill_opacity=0.5` ✓
2. `about_vector=UP` ❌ → `axis=UP` ✓
3. `axes.x_axis_end` ❌ → `axes.x_axis.get_end()` ✓
4. `axes.y_axis_end` ❌ → `axes.y_axis.get_end()` ✓
5. `axes.z_axis_end` ❌ → `axes.z_axis.get_end()` ✓
6. `Surface(opacity=0.5)` ❌ → `Surface(fill_opacity=0.5)` ✓
7. `self.play(vgroup)` ❌ → `self.play(Create(vgroup))` ✓
8. Scene for 3D ❌ → ThreeDScene ✓

**LATEX ERRORS:**
9. Unicode symbols (×, ÷, π) ❌ → LaTeX commands (\\times, \\div, \\pi) ✓
10. Single braces in template ❌ → Double braces {{}} ✓

**STYLE ERRORS:**
11. Font size > 52 ❌ → font_size ≤ 48 ✓
12. No scaling before display ❌ → Always .scale() first ✓

**SYNTAX ERRORS (WILL CRASH - CHECK CAREFULLY):**
13. Mismatched brackets ❌ → Match every ( with ), [ with ], curly with curly ✓
14. Missing closing parenthesis ❌ → Count opening and closing parens ✓
15. Mixing [] and () ❌ → Lists use [], function calls use () ✓

```python
# ❌ WRONG - mismatched brackets:
self.play(Create(VGroup(*[item1, item2]))  # Missing )
Arrow3D(start=ORIGIN, end=[1, 2, 3)  # ] and ) mixed up

# ✓ CORRECT - properly matched:
self.play(Create(VGroup(*[item1, item2])))  # All matched
Arrow3D(start=ORIGIN, end=[1, 2, 3])  # Correct
```

**3D SPECIFIC ERRORS (CRITICAL - THESE WILL CRASH):**
13. `ThreeDAxes.x_axis_end` ❌ → Does not exist! Use `axes.c2p(x_max, 0, 0)` ✓
14. Camera without set_camera_orientation ❌ → Always call it first ✓
15. Text in 3D without add_fixed_in_frame_mobjects ❌ → Add text to fixed frame ✓
16. `Arrow3D.vector` ❌ → Does not exist! Use `arrow.get_end() - arrow.get_start()` ✓
17. `Arrow3D(direction=...)` ❌ → Use `Arrow3D(start=ORIGIN, end=RIGHT*2)` ✓
18. `Vector3D` ❌ → Does not exist! Use `Arrow3D` or `Line3D` ✓
19. `arrow.get_vector()` ❌ → Use `arrow.get_end() - arrow.get_start()` ✓

**CORRECT 3D ARROW PATTERNS (USE THESE EXACTLY):**
```python
# Creating 3D arrows - ALWAYS use start and end points
arrow_x = Arrow3D(start=ORIGIN, end=[2, 0, 0], color=RED)
arrow_y = Arrow3D(start=ORIGIN, end=[0, 2, 0], color=GREEN)
arrow_z = Arrow3D(start=ORIGIN, end=[0, 0, 2], color=BLUE)

# Getting the direction vector from an arrow
direction = arrow_x.get_end() - arrow_x.get_start()  # Returns numpy array

# Creating arrows from one point to another
arrow = Arrow3D(start=[1, 1, 1], end=[3, 2, 4], color=YELLOW)

# NEVER use these (they don't exist):
# arrow.vector ❌
# arrow.get_vector() ❌
# Arrow3D(direction=UP) ❌
# Vector3D(...) ❌
```

**CORRECT 3D AXES PATTERNS:**
```python
# Getting axis endpoints
axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-3, 3])
x_end = axes.c2p(3, 0, 0)  # Point at end of x-axis
y_end = axes.c2p(0, 3, 0)  # Point at end of y-axis
z_end = axes.c2p(0, 0, 3)  # Point at end of z-axis

# For axis labels in 3D
x_label = MathTex("x").next_to(axes.c2p(3, 0, 0), RIGHT)
self.add_fixed_in_frame_mobjects(x_label)
```

**SAFE 3D OBJECTS TO USE:**
- `Sphere(radius=1, color=BLUE)` ✓
- `Cube(side_length=2, color=RED)` ✓
- `Arrow3D(start=ORIGIN, end=[1,1,1])` ✓
- `Line3D(start=ORIGIN, end=[2,0,0])` ✓
- `Surface(func, u_range, v_range, fill_opacity=0.7)` ✓
- `ThreeDAxes()` ✓
- `Dot3D(point=[1,2,3])` ✓

## ⚠️ CRITICAL: PREVENT OFF-SCREEN ELEMENTS (MANDATORY)

**THE SCREEN BOUNDS ARE ABSOLUTE - NOTHING MAY EXCEED THEM:**
- Horizontal: x must be between -5.5 and 5.5 (USE SMALLER BOUNDS FOR SAFETY)
- Vertical: y must be between -3.0 and 3.0 (USE SMALLER BOUNDS FOR SAFETY)

### MANDATORY SCALING RULES (USE SMALLER SCALES):

**RULE 1: Always scale content SMALL**
```python
# For any complex diagram or group:
my_group = VGroup(item1, item2, item3, item4)
my_group.arrange(RIGHT, buff=0.2)
my_group.scale_to_fit_width(10)  # Use 10, NOT 12
my_group.move_to(ORIGIN)  # Center it
```

**RULE 2: NEVER show text and diagrams at the same time**
```python
# WRONG - causes overlap:
title = Text("Title").to_edge(UP)
diagram = Circle()
self.play(Write(title), Create(diagram))  # OVERLAP!

# CORRECT - show separately:
title = Text("Title", font_size=42)
self.play(Write(title))
self.wait(1.5)
self.play(FadeOut(title))  # Remove title FIRST
diagram = Circle().scale(0.5)  # Then show diagram
self.play(Create(diagram))
```

**RULE 2: Use scale() for large objects**
```python
# Scale large shapes BEFORE adding to scene
big_diagram = create_complex_diagram()
big_diagram.scale(0.6)  # Scale down to 60%
big_diagram.move_to(ORIGIN)  # Then center
self.play(Create(big_diagram))
```

**RULE 3: Use safe positioning methods**
```python
# SAFE - stays on screen:
obj.to_edge(LEFT, buff=0.5)   # buff keeps it away from edge
obj.to_corner(UL, buff=0.3)   # Corner with buffer
obj.move_to(ORIGIN)           # Center
obj.next_to(other, RIGHT, buff=0.3)  # Relative to another

# DANGEROUS - can go off screen:
obj.shift(RIGHT * 8)  # ❌ Too far!
obj.move_to([10, 0, 0])  # ❌ Outside bounds!
```

**RULE 4: For multiple items, arrange then scale**
```python
# Create items
boxes = VGroup(*[Square().scale(0.5) for _ in range(8)])
# Arrange in a row
boxes.arrange(RIGHT, buff=0.2)
# Scale entire group to fit
boxes.scale_to_fit_width(11)  # Leave margin
boxes.move_to(ORIGIN)
```

**RULE 5: For text with diagrams**
```python
# Title at top (scaled small)
title = Text("Title", font_size=36).to_edge(UP, buff=0.3)

# Diagram in center (scaled to fit remaining space)  
diagram = create_diagram().scale(0.6)
diagram.next_to(title, DOWN, buff=0.5)

# Equation at bottom
eq = MathTex(r"equation").to_edge(DOWN, buff=0.3)
```

**RULE 6: For 3D scenes, always scale down**
```python
# 3D objects appear larger - scale them down
axes = ThreeDAxes().scale(0.5)
surface = Surface(...).scale(0.4)
```

### Screen Zones (stay within these):
- **TOP (y: 2.5 to 3.5)**: Titles only, font_size ≤ 42
- **CENTER (y: -2 to 2)**: Main diagrams, MUST be scaled to fit
- **BOTTOM (y: -3.5 to -2.5)**: Labels and equations, font_size ≤ 36

### Prevent Overlap:
```python
# Show title ALONE first
title = Text("Title", font_size=42)
self.play(Write(title))
self.wait(1.5)
self.play(FadeOut(title))  # THEN show diagram

# OR keep title and scale diagram to fit
title.to_edge(UP)
diagram.scale(0.5).shift(DOWN*0.3)  # Scale DOWN and leave room
```

### Transitions Between Sections:
```python
self.play(FadeOut(*self.mobjects))
self.wait(0.5)
# New section starts on blank canvas
```

## 📝 COMPLETE EXAMPLE (60-second video):

```python
from manim import *

class GenScene(Scene):
    def construct(self):
        # === SECTION 1: TITLE (5s) ===
        title = Text("The Pythagorean Theorem", font_size=48, weight=BOLD)
        self.play(Write(title), run_time=1.5)
        self.wait(2)
        self.play(title.animate.scale(0.5).to_corner(UL))
        
        # === SECTION 2: BUILD THE TRIANGLE (15s) ===
        # Create triangle progressively
        triangle = Polygon(
            ORIGIN, RIGHT*3, RIGHT*3 + UP*4,
            color=BLUE_D, fill_opacity=0.3
        ).move_to(ORIGIN)
        
        self.play(DrawBorderThenFill(triangle), run_time=2)
        self.wait(1)
        
        # Add side labels one by one
        a_label = MathTex("a", color=YELLOW).next_to(triangle, DOWN)
        b_label = MathTex("b", color=YELLOW).next_to(triangle, RIGHT)
        c_label = MathTex("c", color=RED_D).move_to(triangle.get_center() + LEFT*0.8 + UP*0.5)
        
        self.play(Write(a_label))
        self.wait(0.5)
        self.play(Write(b_label))
        self.wait(0.5)
        self.play(Write(c_label))
        self.wait(1.5)
        
        # === SECTION 3: SHOW THE FORMULA (15s) ===
        # Build equation step by step
        eq_parts = VGroup(
            MathTex(r"a^2", color=YELLOW),
            MathTex(r"+", color=WHITE),
            MathTex(r"b^2", color=YELLOW),
            MathTex(r"=", color=WHITE),
            MathTex(r"c^2", color=RED_D)
        ).arrange(RIGHT, buff=0.3).to_edge(DOWN)
        
        for part in eq_parts:
            self.play(Write(part), run_time=0.5)
            self.wait(0.3)
        
        self.wait(2)
        
        # === SECTION 4: HIGHLIGHT THE RELATIONSHIP (10s) ===
        # Flash to show connections
        self.play(Indicate(a_label), Indicate(eq_parts[0]))
        self.wait(1)
        self.play(Indicate(b_label), Indicate(eq_parts[2]))
        self.wait(1)
        self.play(Indicate(c_label), Indicate(eq_parts[4]))
        self.wait(2)
        
        # === SECTION 5: CONCLUSION (15s) ===
        self.play(FadeOut(triangle, a_label, b_label, c_label, title))
        
        final_eq = MathTex(r"a^2 + b^2 = c^2", font_size=72, color=GOLD)
        final_eq.move_to(ORIGIN)
        
        self.play(TransformFromCopy(eq_parts, final_eq), run_time=2)
        self.wait(1)
        
        box = SurroundingRectangle(final_eq, color=BLUE_D, buff=0.3)
        self.play(Create(box))
        self.wait(3)
```

## YOUR TASK:
Create a STUNNING 3Blue1Brown-quality animation for: "{prompt}"

Focus on:
1. Progressive visual construction
2. Meaningful transformations that teach
3. Elegant color usage
4. Proper pacing with wait() calls
5. Mathematical accuracy

Return ONLY executable Python code. No markdown, no explanation.
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
