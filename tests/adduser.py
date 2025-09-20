from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from config import settings
from model import User

db = create_engine(settings.db)
Session = sessionmaker(bind=db)
with Session() as s:
    s.execute(delete(User).where(User.username == "dev"))
    user = User(username="admin", password="admin123")
    s.add(user)
    s.commit()
