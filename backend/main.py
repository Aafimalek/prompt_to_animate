from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from bson import ObjectId
import os
import json
import asyncio
import uvicorn
from .llm_service import generate_manim_code
from .manim_service import execute_manim_code
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
    clerk_id: Optional[str] = None  # Clerk user ID for authenticated users


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
        
        # 2. Execute Manim and upload to S3
        print("Executing Manim...")
        from fastapi.concurrency import run_in_threadpool
        s3_key, local_filename = await run_in_threadpool(execute_manim_code, code)
        print(f"Video generated: s3_key={s3_key}, local={local_filename}")
        
        # 3. Generate signed URL
        if s3_key:
            video_url = generate_cloudfront_signed_url(s3_key)
            print(f"Generated CloudFront signed URL")
        else:
            # Fallback to local URL if S3 upload failed
            video_url = f"http://localhost:8000/videos/{local_filename}"
            print(f"Using local fallback URL: {video_url}")
        
        return AnimationResponse(video_url=video_url, code=code)
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-stream")
async def generate_animation_stream(request: AnimationRequest):
    """
    Streaming endpoint that sends progress updates as Server-Sent Events.
    Requires authentication - clerk_id must be provided.
    Saves chat to MongoDB for authenticated users.
    """
    # Authentication check - require clerk_id
    if not request.clerk_id:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Please sign in to generate videos."
        )
    
    async def event_generator():
        try:
            # Step 0: Check usage limits
            usage_check = await check_can_generate(request.clerk_id)
            if not usage_check["allowed"]:
                yield f"data: {json.dumps({'step': -1, 'status': 'error', 'message': usage_check['reason']})}\n\n"
                return
            
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
            s3_key, local_filename = await run_in_threadpool(execute_manim_code, code)
            
            # Step 5: Uploading / Finalizing
            yield f"data: {json.dumps({'step': 5, 'status': 'finalizing', 'message': 'Uploading to cloud storage...'})}\n\n"
            await asyncio.sleep(0.3)
            
            # Step 6: Complete - generate signed URL
            if s3_key:
                video_url = generate_cloudfront_signed_url(s3_key)
            else:
                # Fallback to local URL if S3 upload failed
                video_url = f"http://localhost:8000/videos/{local_filename}"
                s3_key = ""  # Empty string for local fallback
            
            # Save to MongoDB if user is authenticated
            chat_id = None
            if request.clerk_id:
                try:
                    chats_collection = await get_chats_collection()
                    chat_doc = {
                        "clerk_id": request.clerk_id,
                        "prompt": request.prompt,
                        "length": request.length,
                        "video_url": video_url,
                        "s3_key": s3_key or "",
                        "code": code,
                        "created_at": datetime.utcnow()
                    }
                    result = await chats_collection.insert_one(chat_doc)
                    chat_id = str(result.inserted_id)
                    print(f"✅ Chat saved to MongoDB: {chat_id}")
                except Exception as db_error:
                    print(f"⚠️ Failed to save chat to MongoDB: {db_error}")
            
            # Increment usage count after successful generation
            await increment_usage(request.clerk_id)
            
            yield f"data: {json.dumps({'step': 6, 'status': 'complete', 'message': 'Video ready!', 'video_url': video_url, 'code': code, 'chat_id': chat_id})}\n\n"
            
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
