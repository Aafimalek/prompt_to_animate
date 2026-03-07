from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Tuple
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
from .user_service import check_can_generate, get_user_usage, add_basic_credits, set_pro_subscription
from .export_service import build_interactive_manifest, build_manim_slides_outline
from .scene_memory import record_quality_feedback, retrieve_scene_memories
from .voiceover_service import script_to_voiceover_metadata
from .reward_training import train_reward_model_from_mongo
from .collab_service import (
    add_chat_comment,
    code_diff,
    create_ab_variant,
    create_branch,
    get_chat_code,
    get_variant_code,
    list_branches,
    list_ab_variants,
    list_chat_comments,
    merge_branch_into_chat,
)


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


class InteractiveExportRequest(BaseModel):
    code: str
    length: str = "Medium (15s)"
    title: str = "Interactive Export"
    scene_plan: Optional[Dict[str, Any]] = None


class QualityFeedbackRequest(BaseModel):
    clerk_id: str
    chat_id: str
    rating: int
    note: str = ""


class ChatCommentRequest(BaseModel):
    message: str
    anchor: str = ""


class ChatVariantRequest(BaseModel):
    label: str = "variant"
    code: str
    prompt_override: str = ""
    branch_id: str = ""


class VoiceoverScriptRequest(BaseModel):
    script: Dict[str, Any]


class RewardRetrainRequest(BaseModel):
    limit: int = 500


class BranchRequest(BaseModel):
    name: str
    base_variant_id: str = ""


class MergeBranchRequest(BaseModel):
    strategy: str = "latest_variant"


def progress_signature(progress: dict) -> Tuple[int, str, str]:
    """Build a comparable signature used to decide SSE emission."""
    return (
        int(progress.get("step", 0)),
        str(progress.get("status", "")),
        str(progress.get("message", "")),
    )


def should_emit_progress(
    last_signature: Optional[Tuple[int, str, str]],
    progress: dict
) -> Tuple[bool, Tuple[int, str, str]]:
    """
    Return whether this progress update should be emitted.

    We emit when any of (step, status, message) changes so same-step
    phase updates are streamed to clients.
    """
    signature = progress_signature(progress)
    return signature != last_signature, signature


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
            args=(
                request.prompt,
                request.length,
                request.clerk_id or "anonymous",
                job_id,
                request.resolution,
            ),
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
                args=(
                    request.prompt,
                    request.length,
                    request.clerk_id,
                    job_id,
                    request.resolution,
                ),
                job_id=job_id,
                job_timeout=600,  # 10 minute timeout for long videos
                result_ttl=3600,  # Keep result for 1 hour
                failure_ttl=3600  # Keep failed job info for 1 hour
            )
            
            print(f"📤 Enqueued job {job_id} for user {request.clerk_id}")
            
            # Poll for progress updates
            last_signature: Optional[Tuple[int, str, str]] = None
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
                    current_status = progress.get("status", "")
                    
                    # Emit if step/status/message changed
                    should_emit, signature = should_emit_progress(last_signature, progress)
                    if should_emit:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_signature = signature
                        
                        # Check if job is complete or failed
                        if current_status == "complete" or current_step == -1:
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


# ============== Advanced Feature Endpoints ==============

@app.post("/export/interactive")
async def export_interactive(request: InteractiveExportRequest):
    """Generate chapter manifest and manim-slides outline from generated code."""
    try:
        manifest = build_interactive_manifest(
            code=request.code,
            title=request.title,
            length=request.length,
            scene_plan=request.scene_plan,
        )
        outline = build_manim_slides_outline(manifest)
        return {
            "status": "ok",
            "manifest": manifest,
            "slides_outline": outline,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voiceover/subtitles")
async def generate_voiceover_subtitles(payload: VoiceoverScriptRequest):
    """Generate subtitle and word-level timing metadata from a voiceover script."""
    try:
        return {"status": "ok", "voiceover": script_to_voiceover_metadata(payload.script)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scene-memory/search")
async def search_scene_memory(prompt: str, top_k: int = 3):
    """Retrieve similar high-quality historical scene memories."""
    try:
        memories = await retrieve_scene_memories(prompt, top_k=max(1, min(10, top_k)))
        return {"prompt": prompt, "results": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback/quality")
async def submit_quality_feedback(payload: QualityFeedbackRequest):
    """Submit user quality feedback to improve candidate reranking."""
    try:
        feedback_id = await record_quality_feedback(
            chat_id=payload.chat_id,
            clerk_id=payload.clerk_id,
            rating=payload.rating,
            note=payload.note,
        )
        return {"status": "ok", "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback/quality/retrain")
async def retrain_quality_reward_model(payload: RewardRetrainRequest):
    """Retrain and persist reranker weights from historical feedback + QA metrics."""
    try:
        result = await train_reward_model_from_mongo(limit=max(50, min(5000, payload.limit)))
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{clerk_id}/{chat_id}/comments")
async def create_comment(clerk_id: str, chat_id: str, payload: ChatCommentRequest):
    try:
        comment_id = await add_chat_comment(
            chat_id=chat_id,
            clerk_id=clerk_id,
            message=payload.message,
            anchor=payload.anchor,
        )
        return {"status": "ok", "comment_id": comment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{clerk_id}/{chat_id}/comments")
async def get_comments(clerk_id: str, chat_id: str):
    try:
        comments = await list_chat_comments(chat_id=chat_id)
        return {"status": "ok", "comments": comments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{clerk_id}/{chat_id}/variants")
async def create_variant(clerk_id: str, chat_id: str, payload: ChatVariantRequest):
    try:
        variant_id = await create_ab_variant(
            chat_id=chat_id,
            clerk_id=clerk_id,
            label=payload.label,
            code=payload.code,
            prompt_override=payload.prompt_override,
            branch_id=payload.branch_id,
        )
        return {"status": "ok", "variant_id": variant_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{clerk_id}/{chat_id}/variants")
async def get_variants(clerk_id: str, chat_id: str):
    try:
        variants = await list_ab_variants(chat_id=chat_id, clerk_id=clerk_id)
        return {"status": "ok", "variants": variants}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{clerk_id}/{chat_id}/branches")
async def create_chat_branch(clerk_id: str, chat_id: str, payload: BranchRequest):
    try:
        branch_id = await create_branch(
            chat_id=chat_id,
            clerk_id=clerk_id,
            name=payload.name,
            base_variant_id=payload.base_variant_id,
        )
        return {"status": "ok", "branch_id": branch_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{clerk_id}/{chat_id}/branches")
async def get_chat_branches(clerk_id: str, chat_id: str):
    try:
        branches = await list_branches(chat_id=chat_id, clerk_id=clerk_id)
        return {"status": "ok", "branches": branches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{clerk_id}/{chat_id}/branches/{branch_id}/merge")
async def merge_chat_branch(
    clerk_id: str,
    chat_id: str,
    branch_id: str,
    payload: MergeBranchRequest,
):
    try:
        result = await merge_branch_into_chat(
            chat_id=chat_id,
            clerk_id=clerk_id,
            branch_id=branch_id,
            strategy=payload.strategy,
        )
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{clerk_id}/{chat_id}/variants/{variant_id}/diff")
async def get_variant_diff(clerk_id: str, chat_id: str, variant_id: str):
    try:
        base_code = await get_chat_code(chat_id=chat_id, clerk_id=clerk_id)
        variant_code = await get_variant_code(chat_id=chat_id, variant_id=variant_id, clerk_id=clerk_id)
        diff_text = code_diff(base_code, variant_code)
        return {"status": "ok", "diff": diff_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
