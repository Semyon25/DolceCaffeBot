import os
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_

db_name = os.environ['db_name']
Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


# Модель
class Code(Base):
  __tablename__ = 'codes'
  id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
  user_id = Column(Numeric, primary_key=True, unique=True, nullable=False)
  code = Column(String, nullable=False)
  is_used = Column(Integer, default=0)

def get_code_4(user_id):
    session = Session()
    existing_code = session.query(Code).filter(
        and_(
           Code.user_id == user_id,
           Code.is_used == 0,
           Code.code.length == 4
        )
    ).first()
    session.close()
    return existing_code.code if existing_code else None
    
def set_code(user_id, code):
      new_code = Code(user_id=user_id, code=code)
      session = Session()
      session.add(new_code)
      session.commit()
      session.close()
    
def get_user(code):
    session = Session()
    existing_code = session.query(Code).filter(
        Code.code == code,
        Code.is_used == 0
    ).first()
    session.close()
    return existing_code.user_id if existing_code else None

def confirm_code_usage(code):
    session = Session()
    existing_code = session.query(Code).filter(
        and_(
            Code.code == code,
            Code.is_used == 0
        )
    ).first()
    if existing_code:
        existing_code.is_used = int(1)
        session.commit()
    session.close()

def check_if_code_unique(code):
  session = Session()
  existing_code = session.query(Code).filter(
      and_(
          Code.code == code,
          Code.is_used == 0
      )
  ).first()
  session.close()
  return existing_code is None # True если нет такого кода
  