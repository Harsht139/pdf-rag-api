from uuid import UUID, uuid4

from fastapi import Request

# This is a default user ID that will be used when no user is authenticated
# Using a fixed UUID v4 for the default user
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


async def get_current_user(request: Request):
    """
    Return a simple user object with a valid UUID.
    In production, you would implement proper user authentication here.
    """
    return {"id": DEFAULT_USER_ID, "is_active": True}
