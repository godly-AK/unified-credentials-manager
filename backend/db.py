from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:strongpassword@localhost/test")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()  # <- define Base here ONCE

def init_db():
    # DO NOT import Base again; just import your models so they register
    import models  # your models.py should use the same Base
    Base.metadata.create_all(bind=engine)
