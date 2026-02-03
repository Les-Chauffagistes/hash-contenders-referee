from .models.User import User
from .models.APIData import APIDataPayload
from .base import send_request


    
async def get_every_user_data() -> APIDataPayload:
    return await send_request("data")

async def get_user_stats(user_address: str) -> User:
    return await send_request(f"stats/{user_address}")