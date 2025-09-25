from fastapi import Request


async def verify_api_key(request: Request):
    """
    Simple security check that always passes.
    In production, you might want to implement proper authentication here.
    """
    return True
