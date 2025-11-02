from config import db_name
import datetime
from sqlalchemy import Column, Integer, String, Numeric, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

class SubscriptionCodes(Base):
    __tablename__ = 'subscription_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Numeric, nullable=False)
    subscription_id = Column(Integer, nullable=False)
    code = Column(String, nullable=False)
    used_at = Column(String)


def get_unused_code(user_id, subscription_id):
    """
    Возвращает неиспользованный код для указанного пользователя и подписки.
    Если не найден — возвращает None.
    """
    session = Session()
    code_entry = session.query(SubscriptionCodes).filter(
        SubscriptionCodes.user_id == user_id,
        SubscriptionCodes.subscription_id == subscription_id,
        (SubscriptionCodes.used_at == None) | (SubscriptionCodes.used_at == "")
    ).first()
    session.close()
    return code_entry

def get_user_and_subscription_by_code(code):
    """
    Возвращает id пользователя и id абонемента по коду
    """
    session = Session()
    sub_code = session.query(SubscriptionCodes).filter(
        SubscriptionCodes.code == code,
        (SubscriptionCodes.used_at == None) | (SubscriptionCodes.used_at == "")
    ).first()
    session.close()
    return (sub_code.user_id, sub_code.subscription_id) if sub_code else (None, None)

def set_code(user_id, subscription_id, code):
    """
    Устанавливает код для пользователя
    """
    entry = SubscriptionCodes(
            user_id=user_id,
            subscription_id=subscription_id,
            code=code,
            used_at=None
    )
    session = Session()
    session.add(entry)

    session.commit()
    session.close()

def set_usage_time(user_id, subscription_id):
    """
    Находит неиспользованный код и устанавливает текущее время его использования.
    """
    session = Session()
    entry = session.query(SubscriptionCodes).filter(
        SubscriptionCodes.user_id == user_id,
        SubscriptionCodes.subscription_id == subscription_id,
        (SubscriptionCodes.used_at == None) | (SubscriptionCodes.used_at == "")
    ).first()

    if entry:
        entry.used_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        session.commit()

    session.close()

def get_last_usage_time(user_id, subscription_id):
    """
    Возвращает последнее время использования кода пользователя по подписке.
    """
    session = Session()
    entry = session.query(SubscriptionCodes).filter(
        SubscriptionCodes.user_id == user_id,
        SubscriptionCodes.subscription_id == subscription_id,
        SubscriptionCodes.used_at != None
    ).order_by(SubscriptionCodes.id.desc()).first()

    session.close()
    return entry.used_at if entry else None