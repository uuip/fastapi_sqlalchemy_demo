from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base

engine = create_engine(settings.db_url)
SessionMaker = sessionmaker(bind=engine)

Base.metadata.create_all(bind=engine)
