from sqlalchemy import create_engine

from app.apps.file_manager.config import settings
from app.apps.file_manager.models import Base, FileRecord

if __name__ == "__main__":
    engine = create_engine(settings.db_url, echo=False)
    Base.metadata.create_all(bind=engine, tables=[FileRecord.__table__])
