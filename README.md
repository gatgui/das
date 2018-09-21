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
One can also easily serialize/deserialize struct content to file
```
>>> das.write(s, "/path/to/file.ext")
>>> s2 = das.read("/path/to/file.ext")
>>> das.pprint(s2)
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
tests/test005/shopping.schema
```
{
  "currency_names": String(default="Yen", choices=["Yen", "Euro", "Dollar"]),

  "item": Struct(name=String(),
                 value=Real(min=0.0),
                 currency=SchemaType("currency_names"),
                 description=String()),

  "basket": Struct(items=Sequence(type=SchemaType("item")))
}
```
#### Schema module & mixins
tests/test005/shopping.py
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

```
Usage
```
$ export DAS_SCHEMA_PATH=directory/of/shopping.schema
$ python
>>> import das
>>> b = das.make_default("shopping.basket")
>>> b.items.append(das.make("shopping.item", name="carottes", value=110))
>>> b.items.append(das.make("shopping.item", name="meat", value=320))
>>> das.pprint(b)
{
  'items': [
    {
      'currency': 'Yen',
      'description': '',
      'name': 'carottes',
      'value': 110.0
    },
    {
      'currency': 'Yen',
      'description': '',
      'name': 'meat',
      'value': 320.0
    }
  ]
}
>>> for c in ["yen", "euro", "dollar"]:
...   print("%f %s(s)" % (b.value_in(c), c))
430.000000 yen(s)
3.157752 euro(s)
3.898459 dollar(s)
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
9. SchemaType
10. Class

Require methods:
- ```copy() -> instance```
- ```__str__() and/or __repr__() -> str``` (use when serializing)
- ```__cmp__() -> -1, 0 or 1``` (use when comparing data sets)

Optional methods:
- ```string_to_value(str) -> noreturn``` (used by the editor)
- ```value_to_string() -> str``` (used by the editor)

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

### TODO
- [ ] Implemente copy-paste
- [ ] Allow multiple items drag'n'drop
- [ ] Add a toolbar class (open/save/save as, copy/cut/paste, undo/redo)
