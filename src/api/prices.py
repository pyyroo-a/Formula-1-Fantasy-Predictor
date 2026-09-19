"""
F1 Fantasy price endpoints.
"""
from fastapi import APIRouter
from src.api import state

router = APIRouter()


@router.get("/prices")
def get_prices():
    return state.current_prices


@router.get("/price-changes")
def get_price_changes():
    return state.price_changes
