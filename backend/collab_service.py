from __future__ import annotations

import difflib
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId

from .database import get_database, get_chats_collection


async def _comments_collection():
    db = await get_database()
    return db["chat_comments"]


async def _variants_collection():
    db = await get_database()
    return db["chat_variants"]


async def _branches_collection():
    db = await get_database()
    return db["chat_branches"]


async def add_chat_comment(
    chat_id: str,
    clerk_id: str,
    message: str,
    anchor: str = "",
) -> str:
    collection = await _comments_collection()
    result = await collection.insert_one(
        {
            "chat_id": chat_id,
            "clerk_id": clerk_id,
            "message": message.strip(),
            "anchor": anchor.strip(),
            "created_at": datetime.utcnow(),
        }
    )
    return str(result.inserted_id)


async def list_chat_comments(chat_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    collection = await _comments_collection()
    comments = await collection.find({"chat_id": chat_id}).sort("created_at", 1).limit(limit).to_list(length=limit)
    return [
        {
            "id": str(item.get("_id")),
            "chat_id": chat_id,
            "clerk_id": item.get("clerk_id", ""),
            "message": item.get("message", ""),
            "anchor": item.get("anchor", ""),
            "created_at": item.get("created_at"),
        }
        for item in comments
    ]


async def create_ab_variant(
    chat_id: str,
    clerk_id: str,
    label: str,
    code: str,
    prompt_override: str = "",
    branch_id: str = "",
) -> str:
    collection = await _variants_collection()
    result = await collection.insert_one(
        {
            "chat_id": chat_id,
            "clerk_id": clerk_id,
            "label": label.strip() or "variant",
            "code": code,
            "prompt_override": prompt_override.strip(),
            "branch_id": branch_id.strip(),
            "created_at": datetime.utcnow(),
        }
    )
    return str(result.inserted_id)


async def list_ab_variants(chat_id: str, clerk_id: str) -> List[Dict[str, Any]]:
    collection = await _variants_collection()
    items = await collection.find({"chat_id": chat_id, "clerk_id": clerk_id}).sort("created_at", -1).to_list(length=50)
    return [
        {
            "id": str(item.get("_id")),
            "chat_id": chat_id,
            "label": item.get("label", "variant"),
            "prompt_override": item.get("prompt_override", ""),
            "branch_id": item.get("branch_id", ""),
            "created_at": item.get("created_at"),
        }
        for item in items
    ]


async def create_branch(
    chat_id: str,
    clerk_id: str,
    name: str,
    base_variant_id: str = "",
) -> str:
    collection = await _branches_collection()
    result = await collection.insert_one(
        {
            "chat_id": chat_id,
            "clerk_id": clerk_id,
            "name": name.strip() or "branch",
            "base_variant_id": base_variant_id.strip(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    return str(result.inserted_id)


async def list_branches(chat_id: str, clerk_id: str) -> List[Dict[str, Any]]:
    collection = await _branches_collection()
    items = await collection.find({"chat_id": chat_id, "clerk_id": clerk_id}).sort("updated_at", -1).to_list(length=100)
    return [
        {
            "id": str(item.get("_id")),
            "chat_id": item.get("chat_id", chat_id),
            "name": item.get("name", "branch"),
            "base_variant_id": item.get("base_variant_id", ""),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        for item in items
    ]


async def merge_branch_into_chat(
    chat_id: str,
    clerk_id: str,
    branch_id: str,
    strategy: str = "latest_variant",
) -> Dict[str, Any]:
    variants_collection = await _variants_collection()
    branch_oid = ObjectId(branch_id)
    branch_variants = await variants_collection.find(
        {"chat_id": chat_id, "clerk_id": clerk_id, "branch_id": branch_id}
    ).sort("created_at", -1).to_list(length=20)

    if not branch_variants:
        raise ValueError("No variants found on selected branch")

    selected = branch_variants[0]
    if strategy == "longest_code":
        selected = max(branch_variants, key=lambda row: len(str(row.get("code", ""))))

    merged_code = str(selected.get("code", ""))
    if not merged_code.strip():
        raise ValueError("Selected branch variant has empty code")

    chats = await get_chats_collection()
    update = await chats.update_one(
        {"_id": ObjectId(chat_id), "clerk_id": clerk_id},
        {
            "$set": {
                "code": merged_code,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    if update.matched_count == 0:
        raise ValueError("Chat not found for merge")

    branches_collection = await _branches_collection()
    await branches_collection.update_one(
        {"_id": branch_oid, "chat_id": chat_id, "clerk_id": clerk_id},
        {"$set": {"updated_at": datetime.utcnow()}},
    )
    return {
        "merged_variant_id": str(selected.get("_id", "")),
        "strategy": strategy,
    }


async def get_variant_code(chat_id: str, variant_id: str, clerk_id: str) -> str:
    collection = await _variants_collection()
    row = await collection.find_one(
        {
            "_id": ObjectId(variant_id),
            "chat_id": chat_id,
            "clerk_id": clerk_id,
        }
    )
    if not row:
        raise ValueError("Variant not found")
    return str(row.get("code", ""))


async def get_chat_code(chat_id: str, clerk_id: str) -> str:
    chats = await get_chats_collection()
    row = await chats.find_one({"_id": ObjectId(chat_id), "clerk_id": clerk_id})
    if not row:
        raise ValueError("Chat not found")
    return str(row.get("code", ""))


def code_diff(base_code: str, variant_code: str, context: int = 3) -> str:
    base_lines = (base_code or "").splitlines()
    variant_lines = (variant_code or "").splitlines()
    return "\n".join(
        difflib.unified_diff(
            base_lines,
            variant_lines,
            fromfile="base.py",
            tofile="variant.py",
            lineterm="",
            n=context,
        )
    )
