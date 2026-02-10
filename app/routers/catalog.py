from fastapi import APIRouter

from app.services.product_config import get_product_config

router = APIRouter(tags=["catalog"])


@router.get("/channels")
async def list_channels():
    config = get_product_config()
    return config["channels"]


@router.get("/styles")
async def list_styles():
    config = get_product_config()
    return config["styles"]


@router.get("/languages")
async def list_languages():
    config = get_product_config()
    return config["languages"]


@router.get("/lengths")
async def list_lengths():
    config = get_product_config()
    return config.get("lengths", {})
