import logging

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def _get_id_from_state(request: Request, key: str) -> int | None:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        logger.warning(
            "Invalid request.state.user type: %s",
            type(user).__name__,
        )
        return None

    current_id = user.get(key) or getattr(request.state, key, None)
    if current_id in (None, ""):
        logger.warning("Missing required field '%s' in request.state.user", key)
        return None
    return int(current_id)


def get_optional_user_id(request: Request) -> int | None:
    """depends for current user's id."""
    return _get_id_from_state(request, "user_id")


def get_current_user_id(request: Request) -> int:
    user_id = _get_id_from_state(request, "user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    return user_id
