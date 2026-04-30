from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi_sqlalchemy.core.config import settings
from fastapi_sqlalchemy.models import User, Base

engine = create_engine(settings.db_url)
SessionMaker = sessionmaker(bind=engine)

Base.metadata.create_all(bind=engine)
