import subprocess
import os
import sys
import uuid
import shutil
from pathlib import Path
from .s3_service import upload_video_to_s3

def execute_manim_code(code: str, upload_to_s3: bool = True) -> tuple[str, str]:
    """
    Executes the given Manim code and returns the S3 key and local path of the generated video.
    Uses GPU-accelerated OpenGL rendering for maximum speed without quality loss.
    
    Args:
        code: The Manim Python code to execute
        upload_to_s3: Whether to upload the video to S3 (default: True)
    
    Returns:
        Tuple of (s3_key, local_path) if upload_to_s3 is True
        Tuple of (None, local_path) if upload_to_s3 is False
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
    
    # Cairo renderer for cloud-compatible CPU-based rendering (1080p @ 60fps)
    cmd = [
        sys.executable, "-m", "manim",
        "-qh",  # Quality High (1080p @ 60fps)
        "--disable_caching",  # Skip caching overhead
        "--media_dir", str(output_root),
        str(filepath),
        "GenScene"
    ]
    
    print(f"Executing Manim (Cairo renderer): {' '.join(cmd)}")
    
    # Run process
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
    except FileNotFoundError:
        raise Exception("Manim command not found. Please ensure manim is installed and in your PATH.")

    # Check for rendering errors
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
    
    # Cleanup temp python file and intermediate folders
    try:
        os.remove(filepath)
        # Also cleanup the scene folder to save disk space
        scene_folder = output_root / "videos" / scene_name_folder
        if scene_folder.exists():
            shutil.rmtree(scene_folder, ignore_errors=True)
    except OSError:
        pass
    
    # Upload to S3 if enabled
    s3_key = None
    if upload_to_s3:
        try:
            s3_key = upload_video_to_s3(str(final_path))
            print(f"Video uploaded to S3: {s3_key}")
            
            # Delete local file after successful upload to save disk space
            try:
                os.remove(final_path)
                print(f"Deleted local file: {final_path}")
            except OSError as e:
                print(f"Warning: Could not delete local file: {e}")
                
        except Exception as e:
            print(f"Warning: S3 upload failed, keeping local file: {e}")
            # Return local filename if S3 upload fails
            return (None, final_filename)
    
    return (s3_key, final_filename)

