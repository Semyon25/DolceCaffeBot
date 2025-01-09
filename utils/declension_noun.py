
def beverage_declension(count):
  if count == 1:
    return 'напиток'
  elif count >=2 and count <=4:
    return 'напитка'
  else:
    return 'напитков'