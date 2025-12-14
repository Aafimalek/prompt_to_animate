from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from bson import ObjectId
from uuid import uuid4
import os
import json
import asyncio
import uvicorn

# Redis and job queue
from .redis_utils import get_redis_connection, get_queue, get_progress_key, get_result_key
from .tasks import process_video_generation

# Keep these for non-worker endpoints
from .s3_service import generate_cloudfront_signed_url
from .database import connect_to_mongo, close_mongo_connection, get_chats_collection
from .models import ChatResponse, ChatListResponse
from .user_service import check_can_generate, increment_usage, get_user_usage, add_basic_credits, set_pro_subscription


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(title="Prompt to Animate API", lifespan=lifespan)

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
    length: str = "Medium (15s)"  # Default
    resolution: str = "720p"  # 720p, 1080p, 4k
    clerk_id: Optional[str] = None  # Clerk user ID for authenticated users


class AnimationResponse(BaseModel):
    video_url: str
    code: str


@app.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    """
    Original endpoint - kept for backward compatibility.
    Uses the job queue for consistency with the async architecture.
    """
    print(f"Received request: {request}")
    
    try:
        # Get Redis connection and queue
        redis_conn = get_redis_connection()
        queue = get_queue()
        
        # Generate unique job ID
        job_id = str(uuid4())
        
        # Enqueue the video generation task
        job = queue.enqueue(
            process_video_generation,
            args=(request.prompt, request.length, request.clerk_id or "anonymous", job_id, request.resolution),
            job_id=job_id,
            job_timeout=600,
            result_ttl=3600,
            failure_ttl=3600
        )
        
        print(f"📤 Enqueued job {job_id}")
        
        # Poll for completion (blocking for this endpoint)
        max_wait = 600  # 10 minutes
        poll_interval = 1
        elapsed = 0
        
        while elapsed < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                if result and result.get("status") == "complete":
                    return AnimationResponse(
                        video_url=result.get("video_url", ""),
                        code=result.get("code", "")
                    )
                else:
                    raise HTTPException(status_code=500, detail="Job completed but no result")
            
            if job.is_failed:
                error_msg = str(job.exc_info) if job.exc_info else "Job failed"
                raise HTTPException(status_code=500, detail=error_msg)
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise HTTPException(status_code=504, detail="Job timed out")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-stream")
async def generate_animation_stream(request: AnimationRequest):
    """
    Streaming endpoint that sends progress updates as Server-Sent Events.
    
    This endpoint enqueues the video generation job to Redis and polls
    for progress updates, streaming them to the frontend. The actual
    work is done by an RQ worker running in a separate process/container.
    
    Requires authentication - clerk_id must be provided.
    """
    # Authentication check - require clerk_id
    if not request.clerk_id:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Please sign in to generate videos."
        )
    
    async def event_generator():
        redis_conn = None
        job = None
        
        try:
            # Step 0: Check usage limits
            usage_check = await check_can_generate(request.clerk_id)
            if not usage_check["allowed"]:
                yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': usage_check['reason']})}\n\n"
                return
            
            # Get Redis connection and queue
            redis_conn = get_redis_connection()
            queue = get_queue()
            
            # Generate unique job ID
            job_id = str(uuid4())
            
            # Enqueue the video generation task
            job = queue.enqueue(
                process_video_generation,
                args=(request.prompt, request.length, request.clerk_id, job_id, request.resolution),
                job_id=job_id,
                job_timeout=600,  # 10 minute timeout for long videos
                result_ttl=3600,  # Keep result for 1 hour
                failure_ttl=3600  # Keep failed job info for 1 hour
            )
            
            print(f"📤 Enqueued job {job_id} for user {request.clerk_id}")
            
            # Poll for progress updates
            last_step = 0
            max_polls = 1200  # 10 minutes max (1200 * 0.5s = 600s)
            poll_count = 0
            
            while poll_count < max_polls:
                poll_count += 1
                
                # Check for progress update in Redis
                progress_key = get_progress_key(job_id)
                progress_data = redis_conn.get(progress_key)
                
                if progress_data:
                    progress = json.loads(progress_data)
                    current_step = progress.get("step", 0)
                    
                    # Only yield if we have a new step
                    if current_step != last_step or current_step in [-1, 6]:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_step = current_step
                        
                        # Check if job is complete or failed
                        if current_step == 6 or current_step == -1:
                            break
                
                # Check job status directly
                job.refresh()
                if job.is_failed:
                    error_msg = str(job.exc_info) if job.exc_info else "Job failed unexpectedly"
                    yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': error_msg})}\n\n"
                    break
                
                # Wait before next poll
                await asyncio.sleep(0.5)
            
            # Timeout check
            if poll_count >= max_polls:
                yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': 'Job timed out. Please try again.'})}\n\n"
                
        except Exception as e:
            print(f"❌ SSE Error: {e}")
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


# ============== Job Status Endpoint ==============

@app.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get the current status of a video generation job.
    Useful for polling the job status directly without SSE.
    """
    try:
        redis_conn = get_redis_connection()
        
        # Check for progress
        progress_data = redis_conn.get(get_progress_key(job_id))
        if progress_data:
            return json.loads(progress_data)
        
        # Check for final result
        result_data = redis_conn.get(get_result_key(job_id))
        if result_data:
            return json.loads(result_data)
        
        return {"step": 0, "status": "pending", "message": "Job is queued or not found"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Health Check Endpoint ==============

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    Returns the status of Redis and MongoDB connections.
    """
    health = {"status": "healthy", "services": {}}
    
    # Check Redis
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        health["services"]["redis"] = "connected"
    except Exception as e:
        health["services"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Check MongoDB
    try:
        from .database import get_database
        db = await get_database()
        await db.command("ping")
        health["services"]["mongodb"] = "connected"
    except Exception as e:
        health["services"]["mongodb"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    return health


# ============== Chat History Endpoints ==============

@app.get("/chats/{clerk_id}", response_model=ChatListResponse)
async def get_user_chats(clerk_id: str):
    """
    Get all chats for a specific user by their Clerk ID.
    Returns chats sorted by creation date (newest first).
    """
    try:
        chats_collection = await get_chats_collection()
        cursor = chats_collection.find({"clerk_id": clerk_id}).sort("created_at", -1)
        chats = await cursor.to_list(length=100)  # Limit to 100 chats
        
        # Transform to response format
        chat_responses = []
        for chat in chats:
            # Regenerate signed URL if s3_key exists
            video_url = chat.get("video_url", "")
            if chat.get("s3_key"):
                try:
                    video_url = generate_cloudfront_signed_url(chat["s3_key"])
                except Exception:
                    pass  # Keep existing URL if regeneration fails
            
            chat_responses.append(ChatResponse(
                id=str(chat["_id"]),
                prompt=chat.get("prompt", ""),
                length=chat.get("length", "Medium (15s)"),
                video_url=video_url,
                code=chat.get("code", ""),
                created_at=chat.get("created_at", datetime.utcnow()).isoformat()
            ))
        
        return ChatListResponse(chats=chat_responses, total=len(chat_responses))
    
    except Exception as e:
        print(f"Error fetching chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{clerk_id}/{chat_id}", response_model=ChatResponse)
async def get_chat_detail(clerk_id: str, chat_id: str):
    """
    Get a specific chat by ID with a fresh signed URL.
    """
    try:
        chats_collection = await get_chats_collection()
        chat = await chats_collection.find_one({
            "_id": ObjectId(chat_id),
            "clerk_id": clerk_id
        })
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Regenerate signed URL
        video_url = chat.get("video_url", "")
        if chat.get("s3_key"):
            try:
                video_url = generate_cloudfront_signed_url(chat["s3_key"])
            except Exception:
                pass
        
        return ChatResponse(
            id=str(chat["_id"]),
            prompt=chat.get("prompt", ""),
            length=chat.get("length", "Medium (15s)"),
            video_url=video_url,
            code=chat.get("code", ""),
            created_at=chat.get("created_at", datetime.utcnow()).isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chats/{clerk_id}/{chat_id}")
async def delete_chat(clerk_id: str, chat_id: str):
    """
    Delete a specific chat.
    Only the owner (matching clerk_id) can delete their chat.
    """
    try:
        chats_collection = await get_chats_collection()
        result = await chats_collection.delete_one({
            "_id": ObjectId(chat_id),
            "clerk_id": clerk_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat not found or unauthorized")
        
        return {"message": "Chat deleted successfully", "id": chat_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Usage & Credits Endpoints ==============

@app.get("/usage/{clerk_id}")
async def get_usage(clerk_id: str):
    """Get user's current usage and tier info."""
    try:
        usage = await get_user_usage(clerk_id)
        return usage
    except Exception as e:
        print(f"Error getting usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WebhookPayload(BaseModel):
    """Payload for payment webhook."""
    event_type: str
    clerk_id: str
    product_id: Optional[str] = None


@app.post("/webhook/payment")
async def payment_webhook(payload: WebhookPayload):
    """
    Handle payment webhook from frontend.
    Called when Dodo Payments webhook is received.
    """
    try:
        print(f"🔔 Payment webhook: {payload.event_type} for {payload.clerk_id}")
        
        if payload.event_type == "payment_succeeded":
            # Basic pack - add 5 credits
            if payload.product_id and "basic" in payload.product_id.lower():
                await add_basic_credits(payload.clerk_id, credits=5)
                return {"success": True, "message": "Added 5 Basic credits"}
        
        elif payload.event_type == "subscription_active":
            # Pro subscription activated
            await set_pro_subscription(payload.clerk_id, active=True)
            return {"success": True, "message": "Pro subscription activated"}
        
        elif payload.event_type == "subscription_cancelled":
            # Pro subscription cancelled
            await set_pro_subscription(payload.clerk_id, active=False)
            return {"success": True, "message": "Pro subscription cancelled"}
        
        return {"success": True, "message": "Webhook processed"}
    
    except Exception as e:
        print(f"Error processing payment webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
