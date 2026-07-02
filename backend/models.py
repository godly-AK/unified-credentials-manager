# models.py
from sqlalchemy import Column, String, Boolean, TIMESTAMP
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "test"

    usernames = Column(String, primary_key=True)
    password_hashes = Column(String, nullable=False)
    emails = Column(String, nullable=False)
    last_access_time = Column(TIMESTAMP(timezone=True))
    token = Column(String)
    last_ip_addr = Column(String)
    public_key = Column(String, nullable=True)
    passwd_changed = Column("passwd_change", TIMESTAMP(timezone=True))  # DB column name
    blocked = Column(Boolean, default=False)  # use the same name as DB

