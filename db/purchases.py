import os
import datetime
from sqlalchemy import Column, Integer, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

db_name = os.environ['db_name']
Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


# Модель
class Purchase(Base):
  __tablename__ = 'purchases'
  user_id = Column(Numeric, primary_key=True, unique=True, nullable=False)
  count = Column(Integer, default=0)

def get_count(user_id):
  session = Session()
  current_purchase = session.query(Purchase).filter(Purchase.user_id == user_id).first()
  session.close()
  return current_purchase.count if current_purchase else None

def set_count(user_id, count):
  session = Session()
  current_purchase = session.query(Purchase).filter(Purchase.user_id == user_id).first()
  if current_purchase is None:
    current_purchase = Purchase(user_id=user_id, count=0)
    session.add(current_purchase)
  else:
    current_purchase.count = count
  session.commit()
  session.close()