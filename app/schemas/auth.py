from pydantic import BaseModel, Field

PASSWORD_MAX_LENGTH = 128


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
