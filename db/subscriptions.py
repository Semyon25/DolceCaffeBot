from config import db_name
from datetime import datetime, date
from utils.date_utils import today
from sqlalchemy import Column, Integer, String, Numeric, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Numeric, unique=True, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    sub_name = Column(String, nullable=False)  # Название абонемента


def create_subscription(user_id, start_date: date, end_date: date, sub_name):
    """Создает новый абонемент"""
    session = Session()
    new_sub = Subscription(user_id=user_id,
                           start_date=start_date.strftime("%d.%m.%Y"),
                           end_date=end_date.strftime("%d.%m.%Y"),
                           sub_name=sub_name)
    session.add(new_sub)
    session.commit()
    session.close()


def get_active_subscription(user_id, sub_name: str):
    """Возвращает активный абонемент, если он есть"""
    session = Session()
    subs = session.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.sub_name == sub_name
    ).all()

    for sub in subs:
        start = datetime.strptime(sub.start_date, "%d.%m.%Y").date()
        end = datetime.strptime(sub.end_date, "%d.%m.%Y").date()
        if start <= today() <= end:
            return sub
    return None
