from datetime import UTC, datetime

from app.schemas.account import AccountSchema


class AccountObject:
    id = 1
    username = "alice"
    password = "hashed-password"
    updated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    created_at = datetime(2026, 1, 1, 3, 4, 5, tzinfo=UTC)
    energy = 123


def test_account_schema_validates_from_object_attributes():
    schema = AccountSchema.model_validate(AccountObject())

    assert schema.id == 1
    assert schema.username == "alice"
    assert schema.energy == 123


def test_account_schema_transforms_timestamp_ints():
    schema = AccountSchema.model_validate(
        {
            "id": 1,
            "username": "alice",
            "password": "hashed-password",
            "updated_at": 1767225600,
            "created_at": 1767225600,
            "energy": 123,
        }
    )

    assert schema.created_at.year == 2026
    assert schema.updated_at.year == 2026


def test_account_schema_serializes_datetimes_to_shanghai_timezone():
    schema = AccountSchema.model_validate(AccountObject())

    data = schema.model_dump()

    assert data["created_at"] == "2026-01-01 11:04:05+0800"
    assert data["updated_at"] == "2026-01-02 11:04:05+0800"
    assert data["someattr"] == 2026
