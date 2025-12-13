"""
Video Generation Task for RQ Worker.

This module contains the heavy-lifting video generation logic that runs
asynchronously in an RQ worker. Progress is reported via Redis for
real-time SSE streaming to the frontend.
"""

import json
import asyncio
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


def process_video_generation(
    prompt: str,
    length: str,
    clerk_id: str,
    job_id: str
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
    
    Returns:
        dict with video_url, code, chat_id on success
        or error information on failure
    """
    redis_conn = get_redis_connection()
    
    try:
        # Step 1: Analyzing prompt
        report_progress(redis_conn, job_id, 1, "analyzing", "Analyzing your prompt...")
        
        # We need to run async code in sync context
        # Create new event loop for this worker thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 2: Generating code
            report_progress(redis_conn, job_id, 2, "generating", "Generating Manim code...")
            
            from .llm_service import generate_manim_code
            code = loop.run_until_complete(generate_manim_code(prompt, length))
            
            # Step 3: Code ready
            report_progress(redis_conn, job_id, 3, "code_ready", "Code generated successfully!")
            
            # Step 4: Rendering animation
            report_progress(redis_conn, job_id, 4, "rendering", "Rendering animation frames...")
            
            from .manim_service import execute_manim_code
            s3_key, local_filename = execute_manim_code(code)
            
            # Step 5: Uploading to cloud
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
                chat_id = loop.run_until_complete(
                    _save_chat_to_mongo(clerk_id, prompt, length, video_url, s3_key, code)
                )
            except Exception as db_error:
                print(f"⚠️ Failed to save chat to MongoDB: {db_error}")
            
            # Increment usage
            from .user_service import increment_usage
            loop.run_until_complete(increment_usage(clerk_id))
            
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
            
        finally:
            loop.close()
            
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
