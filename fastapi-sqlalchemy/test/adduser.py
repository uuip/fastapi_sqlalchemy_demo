from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from deps.authorization import make_password
from model import User
from config import settings

db = create_engine(settings.db)
Session = sessionmaker(bind=db)
with Session() as s:
    s.execute(delete(User).where(User.username == "dev"))
    password = make_password("abdfskjl")
    user = User(username="dev", password=password)
    s.add(user)
    s.commit()
