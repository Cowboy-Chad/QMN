from fastapi import APIRouter, HTTPException

from backend.rumble.channel_service import list_channel_videos

router = APIRouter(prefix="/api/channel")


@router.get("/videos")
async def get_channel_videos(limit: int = 100):
    try:
        videos = await list_channel_videos(max_results=limit)
        return {"videos": videos}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))