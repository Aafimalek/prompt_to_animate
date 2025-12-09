from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from .llm_service import generate_manim_code
from .manim_service import execute_manim_code

app = FastAPI(title="Prompt to Animate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount generated videos to serve them statically
os.makedirs("generated_animations", exist_ok=True)
app.mount("/videos", StaticFiles(directory="generated_animations"), name="videos")

class AnimationRequest(BaseModel):
    prompt: str
    length: str = "Short (5s)" # Default

class AnimationResponse(BaseModel):
    video_url: str
    code: str

@app.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    print(f"Received request: {request}")
    try:
        # 1. Generate Code
        print("Generating Manim code...")
        code = await generate_manim_code(request.prompt, request.length)
        print("Code generated.")
        
        # 2. Execute Manim
        print("Executing Manim...")
        from fastapi.concurrency import run_in_threadpool
        video_filename = await run_in_threadpool(execute_manim_code, code)
        print(f"Video generated: {video_filename}")
        
        video_url = f"http://localhost:8000/videos/{video_filename}"
        
        return AnimationResponse(video_url=video_url, code=code)
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
