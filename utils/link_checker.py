from aiogram.types import Message

def check_if_text_is_feedback_link(message : Message):
  entities = message.entities or []
  link = None
  for entity in entities:
      if entity.type == "url":
          link = entity.extract_from(message.text)
  if link is not None and link.startswith('https://yandex.ru/maps/'):
    return link
  return None