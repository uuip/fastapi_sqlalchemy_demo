from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.apps.accounts.schemas.auth import PASSWORD_MAX_LENGTH

USERNAME_MAX_LENGTH = 64


class UserSchema(BaseModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    energy: int = 0


class UserUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    energy: int


class UserPatch(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=USERNAME_MAX_LENGTH)
    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)
    energy: int | None = None

    @field_validator("username", "password", "energy")
    @classmethod
    def _reject_explicit_null(cls, v):
        # Fires only on explicit null; defaults skip validation in Pydantic v2.
        if v is None:
            raise ValueError("must not be null")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    energy: int
