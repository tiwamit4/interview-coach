"""Saved history endpoints."""

from fastapi import APIRouter, HTTPException

from utils.history import get_history, list_history

router = APIRouter()


@router.get("/history")
def get_history_items(limit: int = 50):
    return {"items": list_history(limit)}


@router.get("/history/{item_id}")
def get_history_item(item_id: int):
    item = get_history(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="History item not found.")
    return item
