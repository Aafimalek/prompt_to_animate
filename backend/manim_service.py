import subprocess
import os
import sys
import uuid
import shutil
from pathlib import Path

def execute_manim_code(code: str) -> str:
    """
    Executes the given Manim code and returns the filename of the generated video.
    Uses GPU-accelerated OpenGL rendering for maximum speed without quality loss.
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
    output_root = Path("generated_animations").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    
    # GPU-Accelerated Manim command for FAST 1080p60 rendering
    # Using OpenGL renderer for GPU acceleration - significantly faster
    cmd = [
        sys.executable, "-m", "manim",
        "-qh",  # Quality High (1080p @ 60fps)
        "--renderer=opengl",  # GPU-accelerated rendering (MUCH faster)
        "--write_to_movie",  # Write directly to movie file
        "--disable_caching",  # Skip caching overhead
        "--media_dir", str(output_root),
        str(filepath),
        "GenScene"
    ]
    
    # Environment with optimizations
    env = os.environ.copy()
    # Force hardware acceleration where available
    env["PYOPENGL_PLATFORM"] = ""  # Let it auto-detect the best platform
    
    print(f"Executing Manim (OpenGL GPU-accelerated): {' '.join(cmd)}")
    
    # Run process
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False,
            env=env
        )
    except FileNotFoundError:
        raise Exception("Manim command not found. Please ensure manim is installed and in your PATH.")

    # If OpenGL fails, fallback to Cairo renderer
    if result.returncode != 0:
        print("OpenGL rendering failed, falling back to Cairo renderer...")
        cmd_fallback = [
            sys.executable, "-m", "manim",
            "-qh",  # Quality High (1080p @ 60fps)
            "--disable_caching",
            "--media_dir", str(output_root),
            str(filepath),
            "GenScene"
        ]
        
        try:
            result = subprocess.run(
                cmd_fallback, 
                capture_output=True, 
                text=True, 
                check=False
            )
        except FileNotFoundError:
            raise Exception("Manim command not found.")
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise Exception(f"Manim execution failed:\n{error_msg}")
        
    # Locate the output file
    # Structure: output_root/videos/scene_{uuid}/1080p60/GenScene.mp4
    scene_name_folder = filename.replace(".py", "")  # scene_{uuid}
    search_path = output_root / "videos" / scene_name_folder
    
    found_videos = list(search_path.rglob("GenScene.mp4"))
    
    if not found_videos:
        found_videos = list(search_path.rglob("*.mp4"))
        
    if not found_videos:
        print(f"Expected video not found under {search_path}")
        raise Exception(f"Video file was not generated at expected path. Check Manim logs.")
    
    expected_path = found_videos[0]
    
    # Move/Rename to a simple path: generated_animations/{uuid}.mp4
    final_filename = f"{file_id}.mp4"
    final_path = output_root / final_filename
    
    shutil.move(str(expected_path), str(final_path))
    
    # Cleanup temp files and intermediate folders
    try:
        os.remove(filepath)
        # Also cleanup the scene folder to save disk space
        scene_folder = output_root / "videos" / scene_name_folder
        if scene_folder.exists():
            shutil.rmtree(scene_folder, ignore_errors=True)
    except OSError:
        pass
    
    return final_filename
