from aiogram.types import Message

def check_if_text_is_feedback_link(message : Message):
  entities = message.entities or []
  link = None
  for entity in entities:
      if entity.type == "url":
          link = entity.extract_from(message.text)
  if link is not None and link.startswith('https://yandex.ru/maps/org/230301174806/reviews?reviews%5BpublicId') and 'utm_source=my_review' in link:
    return link
  return None