from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from dependencies.authorization import make_password
from models import User
from settings import settings

db = create_engine(settings.db)
Session = sessionmaker(bind=db)
with Session() as s:
    s.execute(delete(User).where(User.username == "dev"))
    password = make_password("abdfskjl")
    user = User(username="dev", password=password)
    s.add(user)
    s.commit()
