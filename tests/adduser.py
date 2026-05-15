import uuid
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.apps.accounts.models import User
from app.apps.accounts.models.base import Base
from app.common.config import settings
from app.common.security.token import create_token

engine = create_engine(settings.db_url)
SessionMaker = sessionmaker(bind=engine)

Base.metadata.create_all(bind=engine)
with SessionMaker() as session:
    user = User(username=str(uuid.uuid7()), password="test")
    session.add(user)
    session.commit()

    token_expires = timedelta(days=settings.jwt_expire_days)
    token= create_token(data={"id": user.id}, expires_delta=token_expires)
    print("Authorization", f"Bearer {token.access_token}")
