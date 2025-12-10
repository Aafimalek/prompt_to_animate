from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
import asyncio
import uvicorn
from .llm_service import generate_manim_code
from .manim_service import execute_manim_code

app = FastAPI(title="Prompt to Animate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount generated videos to serve them statically
os.makedirs("generated_animations", exist_ok=True)
app.mount("/videos", StaticFiles(directory="generated_animations"), name="videos")


class AnimationRequest(BaseModel):
    prompt: str
    length: str = "Short (5s)"  # Default


class AnimationResponse(BaseModel):
    video_url: str
    code: str


@app.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    """Original endpoint - kept for backward compatibility."""
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


@app.post("/generate-stream")
async def generate_animation_stream(request: AnimationRequest):
    """
    Streaming endpoint that sends progress updates as Server-Sent Events.
    """
    async def event_generator():
        try:
            # Step 1: Analyzing prompt
            yield f"data: {json.dumps({'step': 1, 'status': 'analyzing', 'message': 'Analyzing your prompt...'})}\n\n"
            await asyncio.sleep(0.5)
            
            # Step 2: Generating code
            yield f"data: {json.dumps({'step': 2, 'status': 'generating', 'message': 'Generating Manim code...'})}\n\n"
            code = await generate_manim_code(request.prompt, request.length)
            
            # Step 3: Code generated
            yield f"data: {json.dumps({'step': 3, 'status': 'code_ready', 'message': 'Code generated successfully!'})}\n\n"
            await asyncio.sleep(0.3)
            
            # Step 4: Rendering
            yield f"data: {json.dumps({'step': 4, 'status': 'rendering', 'message': 'Rendering animation frames...'})}\n\n"
            
            from fastapi.concurrency import run_in_threadpool
            video_filename = await run_in_threadpool(execute_manim_code, code)
            
            # Step 5: Finalizing
            yield f"data: {json.dumps({'step': 5, 'status': 'finalizing', 'message': 'Finalizing video...'})}\n\n"
            await asyncio.sleep(0.3)
            
            # Step 6: Complete
            video_url = f"http://localhost:8000/videos/{video_filename}"
            yield f"data: {json.dumps({'step': 6, 'status': 'complete', 'message': 'Video ready!', 'video_url': video_url, 'code': code})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
