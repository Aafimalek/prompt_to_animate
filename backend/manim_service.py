import subprocess
import os
import sys
import uuid
import shutil
from pathlib import Path

def execute_manim_code(code: str) -> str:
    """
    Executes the given Manim code and returns the filename of the generated video.
    """
    # Create temp file
    file_id = str(uuid.uuid4())
    filename = f"scene_{file_id}.py"
    
    # We'll use a temp directory inside backend to store the script
    temp_dir = Path("backend/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = temp_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    # Output directory for the final video
    # We want it in "generated_animations" at the project root preferably
    output_root = Path("generated_animations").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    
    # Manim command
    # manim -ql scene.py GenScene --media_dir ...
    # -ql: Quality Low (480p15) - fast for preview
    # -qm: Quality Medium (720p30) - better balance
    # Let's use -ql for speed during dev, maybe configurable later
    
    # Manim command
    # manim -ql scene.py GenScene --media_dir ...
    # -ql: Quality Low (480p15) - fast for preview
    # -qm: Quality Medium (720p30) - better balance
    # Let's use -ql for speed during dev, maybe configurable later
    
    cmd = [
        sys.executable, "-m", "manim",
        "-qh", # Quality High (1080p60)
        "--media_dir", str(output_root),
        str(filepath),
        "GenScene"
    ]
    
    print(f"Executing Manim: {' '.join(cmd)}")
    
    # Run process
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise Exception("Manim command not found. Please ensure manim is installed and in your PATH.")

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown error"
        raise Exception(f"Manim execution failed:\n{error_msg}")
        
    # Locate the output file
    # Structure: output_root/videos/scene_{uuid}/1080p60/GenScene.mp4 or similar
    # We will search recursively for GenScene.mp4 in the specific scene folder
    scene_name_folder = filename.replace(".py", "") # scene_{uuid}
    search_path = output_root / "videos" / scene_name_folder
    
    found_videos = list(search_path.rglob("GenScene.mp4"))
    
    if not found_videos:
        # device fallback? sometimes it might be just .mp4
        found_videos = list(search_path.rglob("*.mp4"))
        
    if not found_videos:
        print(f"Expected video not found under {search_path}")
        raise Exception(f"Video file was not generated at expected path. Check Manim logs.")
    
    expected_path = found_videos[0]
    
    # Move/Rename to a simple path: generated_animations/{uuid}.mp4
    final_filename = f"{file_id}.mp4"
    final_path = output_root / final_filename
    
    shutil.move(str(expected_path), str(final_path))
    
    # Cleanup temp script
    try:
        os.remove(filepath)
    except OSError:
        pass
    
    return final_filename
