from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, Text,ForeignKey
from sqlalchemy.dialects.sqlite import JSON

engine = create_engine("sqlite:///database.db")
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    password = Column(String)
    email = Column(String)



Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()