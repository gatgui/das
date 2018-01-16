# DaS
Dictionary As Struct

## Getting started
### Basic Usage
Creating a struct from a standard python dictionary is simply done by using the *das.Struct* class.

For the most part, the available instance methods are identical to python's *dict* class, but for the fact that method names that conflict with field names will be renamed with a leading *_* (a warning message will be issued once then)

```
>>> import das
>>> 
>>> s = das.Struct({"group": {"field1": [0, 1, 2], "field2": "aaa"},
...                 "field4": 3.0,
...                 "field5": "bbb"})
>>> s.group.field1.append(10)
>>> print(s)
{'group': {'field2': 'aaa', 'field1': [0, 1, 2, 10]}, 'field4': 3.0, 'field5': 'bbb'}
```

**das** has a utility pretty print function *pprint* too
```
>>> das.pprint(s)
{
  'field4': 3.0,
  'field5': 'bbb',
  'group': {
    'field1': [
      0,
      1,
      2,
      10
    ],
    'field2': 'aaa'
  }
}
```

### Advanced Usage
#### Type validation
#### Schema
shopping.schema
```
{
  "currency": String(default="Yen", choices=["Yen", "Euro", "Dollar"]),
  "item": Struct(name=String(),
                 value=Real(min=0.0),
                 currency=SchemaType("currency"),
                 description=String()),
  "basket": Struct(size=Tuple(Real(), Real(), Real()),
                   items=Sequence(type=SchemaType("item")))
}
```
#### Schema module & mixins
shopping.py
```
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
  return (amount * CurrencyRages[tc] / CurrencyRates[fc])


class Item(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "shopping.item"

  def __init__(self, *args, **kwargs):
    super(Item, object).__init__(*args, **kwargs)

  def value_in(self, currency=DefaultCurrency):
    return convert_currencies(self.value, self.currency, currency)
    

class Basket(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "shopping.basket"

  def __init__(self, *args, **kwargs):
    super(Item, object).__init__(*args, **kwargs)

  def value_in(self, currency=DefaultCurrency):
    return reduce(lambda x, y: x+y.value_in(currency), self.items)


das.register_mixins(Item, Basket)
```
#### Built-in schema types
1. Boolean
2. Integer
3. Real
4. String
5. Tuple
6. Sequence
7. Struct
8. Dict
9. SchemaType (NamedType)
10. Class
11. Or
12. Optional
13. Empty
14. Deprecated

#### Mixins

## Developing
### Run unit tests
Running the command
```
python tests/run.py
```
in top level directory will execute all registered tests within the 'tests' folder.

### Staging package
Running the command
```
scons
```
in top level directory will create a simple package distribution folder within the top level directory 'release' folder.

### Creating Ecosystem distribution
Run the command
```
scons eco
```
in top level directory will create Ecosystem distribution in top level directory 'eco' folder.
To specify a custom defined directory, use the eco-dir= flag
```
scons eco eco-dir=path/to/target/directory
```


