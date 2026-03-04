"""
Video Generation Task for RQ Worker.

This module contains the heavy-lifting video generation logic that runs
asynchronously in an RQ worker. Progress is reported via Redis for
real-time SSE streaming to the frontend.
"""

import json
import asyncio
import os
from datetime import datetime
from typing import Optional
from redis import Redis

from .redis_utils import get_redis_connection, get_progress_key, get_result_key


def report_progress(redis_conn: Redis, job_id: str, step: int, status: str, message: str, **extra):
    """
    Report job progress to Redis for SSE streaming.
    
    Args:
        redis_conn: Redis connection
        job_id: Unique job identifier
        step: Progress step number (1-6, or -1 for error)
        status: Status string (analyzing, generating, rendering, etc.)
        message: Human-readable message
        **extra: Additional data (video_url, code, chat_id, etc.)
    """
    progress_data = {
        "step": step,
        "status": status,
        "message": message,
        **extra
    }
    redis_conn.set(
        get_progress_key(job_id),
        json.dumps(progress_data),
        ex=3600  # Expire after 1 hour
    )


# Persistent event loop for the entire worker process.  Motor's
# AsyncIOMotorClient caches the loop it was first used on; if we close
# that loop and create a new one, Motor tries to dispatch work on the old
# (closed) loop and raises "Event loop is closed".  A single long-lived
# loop avoids the issue entirely.
_worker_loop: asyncio.AbstractEventLoop = None


def _run_async(coro):
    """Run an async coroutine on the persistent worker event loop."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coro)


def process_video_generation(
    prompt: str,
    length: str,
    clerk_id: str,
    job_id: str,
    resolution: str = "720p"
) -> dict:
    """
    Main video generation task - runs in RQ worker.
    
    This function is enqueued by the FastAPI endpoint and executed
    asynchronously by an RQ worker. Progress is reported via Redis
    so the API can stream updates to the frontend.
    
    Args:
        prompt: User's animation prompt
        length: Video length selection
        clerk_id: Clerk user ID
        job_id: Unique job identifier for progress tracking
        resolution: Video resolution (720p, 1080p, 4k)
    
    Returns:
        dict with video_url, code, chat_id on success
        or error information on failure
    """
    redis_conn = get_redis_connection()
    
    try:
        # Step 1: Analyzing prompt
        report_progress(redis_conn, job_id, 1, "analyzing", "Analyzing your prompt...")
        
        # Step 2-4: Compose, generate, validate (+repair if needed)
        report_progress(redis_conn, job_id, 2, "composing", "Composing internal scene plan...")
        
        from .llm_service import generate_manim_code, repair_code_from_runtime_error

        def llm_progress(status: str, message: str) -> None:
            step_map = {
                "composing": 2,
                "generating": 3,
                "validating": 4,
                "repairing": 4,
                "repairing_runtime": 4,
            }
            step = step_map.get(status, 4)
            report_progress(redis_conn, job_id, step, status, message)

        code = _run_async(
            generate_manim_code(prompt, length, progress_callback=llm_progress)
        )
        
        from .manim_service import execute_manim_code
        max_render_repairs_raw = os.environ.get("MANIM_RENDER_REPAIR_ATTEMPTS", "2")
        try:
            max_render_repairs = max(0, int(max_render_repairs_raw))
        except ValueError:
            max_render_repairs = 1

        render_attempt = 0
        while True:
            # Step 5: Rendering animation
            if max_render_repairs > 0:
                attempt_label = f" (attempt {render_attempt + 1}/{max_render_repairs + 1})"
            else:
                attempt_label = ""
            report_progress(
                redis_conn,
                job_id,
                5,
                "rendering",
                f"Rendering at {resolution}{attempt_label}...",
            )

            try:
                s3_key, local_filename = execute_manim_code(code, resolution=resolution)
                break
            except Exception as render_error:
                render_error_text = str(render_error)
                can_attempt_repair = (
                    render_attempt < max_render_repairs
                    and render_error_text.startswith("Code error")
                )
                if not can_attempt_repair:
                    raise

                render_attempt += 1
                report_progress(
                    redis_conn,
                    job_id,
                    4,
                    "repairing_runtime",
                    f"Render failed; repairing code (attempt {render_attempt}/{max_render_repairs})...",
                )
                code = _run_async(
                    repair_code_from_runtime_error(
                        prompt=prompt,
                        length=length,
                        bad_code=code,
                        runtime_error=render_error_text,
                    )
                )
        
        # Step 5: Uploading/finalizing
        report_progress(redis_conn, job_id, 5, "finalizing", "Uploading to cloud storage...")
        
        # Generate signed URL
        from .s3_service import generate_cloudfront_signed_url
        if s3_key:
            video_url = generate_cloudfront_signed_url(s3_key)
        else:
            # Fallback - this shouldn't happen in production
            video_url = f"http://localhost:8000/videos/{local_filename}"
            s3_key = ""
        
        # Save to MongoDB
        chat_id = None
        try:
            chat_id = _run_async(
                _save_chat_to_mongo(clerk_id, prompt, length, video_url, s3_key, code)
            )
        except Exception as db_error:
            print(f"⚠️ Failed to save chat to MongoDB: {db_error}")
        
        # Increment usage with resolution-based cost
        from .user_service import increment_usage
        _run_async(increment_usage(clerk_id, resolution=resolution))
        
        # Step 6: Complete
        result = {
            "step": 6,
            "status": "complete",
            "message": "Video ready!",
            "video_url": video_url,
            "code": code,
            "chat_id": chat_id
        }
        report_progress(redis_conn, job_id, 6, "complete", "Video ready!",
                      video_url=video_url, code=code, chat_id=chat_id)
        
        # Also store the final result separately
        redis_conn.set(
            get_result_key(job_id),
            json.dumps(result),
            ex=3600
        )
        
        return result
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Job {job_id} failed: {error_msg}")
        
        error_result = {
            "step": -1,
            "status": "error",
            "message": error_msg
        }
        report_progress(redis_conn, job_id, -1, "error", error_msg)
        
        redis_conn.set(
            get_result_key(job_id),
            json.dumps(error_result),
            ex=3600
        )
        
        # Re-raise to mark job as failed in RQ
        raise


async def _save_chat_to_mongo(
    clerk_id: str,
    prompt: str,
    length: str,
    video_url: str,
    s3_key: str,
    code: str
) -> Optional[str]:
    """
    Save the generated chat to MongoDB.
    
    Returns:
        chat_id string if successful, None otherwise
    """
    from .database import get_chats_collection
    
    chats_collection = await get_chats_collection()
    chat_doc = {
        "clerk_id": clerk_id,
        "prompt": prompt,
        "length": length,
        "video_url": video_url,
        "s3_key": s3_key or "",
        "code": code,
        "created_at": datetime.utcnow()
    }
    result = await chats_collection.insert_one(chat_doc)
    chat_id = str(result.inserted_id)
    print(f"✅ Chat saved to MongoDB: {chat_id}")
    return chat_id
