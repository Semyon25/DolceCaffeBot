def to_float(user_input):
  if user_input is None:
    return None

  user_input = user_input.strip()  # Удаляем пробелы в начале и конце
  if not user_input:  # Проверяем, что строка не пустая после удаления пробелов
    return None

  try:
    num = float(user_input)
    return num
  except ValueError:
    return None
