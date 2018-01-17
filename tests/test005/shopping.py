import das

CurrencyRates = {"yen": 110.30,
                 "euro": 0.81,
                 "dollar": 1}
DefaultCurrency = "yen"

def get_currency_key(currency):
  ck = currency
  if not ck in CurrencyRates:
    ck = ck.lower()
    if not ck in CurrencyRates and ck.endswith("s"):
      ck = ck[:-1]
  return (ck if ck in CurrencyRates else None)

def is_currency_supported(currency):
  return (get_currency_key(currency) is not None)

def get_currency_rate(currency):
  return CurrencyRates.get(get_currency_key(currency), 0.0)

def convert_currencies(amount, source_currency, destination_currency):
  fc = get_currency_key(source_currency)
  tc = get_currency_key(destination_currency)
  if fc is None or tc is None:
    raise Exception("Invalid currency conversion: %s -> %s" % (source_currency, destination_currency))
  return (amount * CurrencyRates[tc] / CurrencyRates[fc])


class Item(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "shopping.item"

  def __init__(self, *args, **kwargs):
    super(Item, self).__init__(*args, **kwargs)

  def value_in(self, currency=DefaultCurrency):
    return convert_currencies(self.value, self.currency, currency)
    

class Basket(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "shopping.basket"

  def __init__(self, *args, **kwargs):
    super(Basket, self).__init__(*args, **kwargs)

  def value_in(self, currency=DefaultCurrency):
    return reduce(lambda x, y: x + y.value_in(currency), self.items, 0.0)


das.register_mixins(Item, Basket)
