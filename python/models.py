from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import *

from settings import settings

db = create_engine(settings.db, echo=False)
AutoBase = automap_base()
INITFLAG = False


class Users(AutoBase):
    __tablename__ = "users"
    trees_collection = relationship("Trees", back_populates="user")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id} {self.name}>"


class Trees(AutoBase):
    __tablename__ = "trees"
    user = relationship("Users", back_populates="trees_collection", overlaps="users")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


if not INITFLAG:
    AutoBase.prepare(autoload_with=db)
    INITFLAG = True
