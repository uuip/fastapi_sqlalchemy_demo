from fastapi import APIRouter, status

from app.core.token import Token
from app.deps import SessionDep
from app.schemas.auth import LoginRequest
from app.schemas.response import Rsp, default_router_responses, error_response
from app.services.auth import login_user

token_api = APIRouter(
    prefix="/token",
    tags=["Token Management"],
    responses=default_router_responses()
    | {
        status.HTTP_401_UNAUTHORIZED: error_response(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password"),
        status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed"
        ),
    },
)


@token_api.post(
    "",
    response_model=Rsp[Token],
    summary="Login and get access token",
    description="Authenticate with username and password to receive a JWT token",
)
async def login(s: SessionDep, credentials: LoginRequest) -> Rsp[Token]:
    return Rsp(await login_user(s, username=credentials.username, password=credentials.password))
