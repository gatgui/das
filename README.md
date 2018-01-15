# DaS
Dictionary As Struct

## Getting started
### Basic Usage
Creating a struct from a standard dictionary is simply done by using the *das.Struct* class.

For the most part, the functionality are identical to python *dict* class except for the fact that method names that conflicts with field names will be renamed with a leading *_* (a warning message will be issued once then)

```
import das

s = das.Struct({"group": {"field1": [0, 1, 2], "field2": "aaa"},
                "field4": 3.0,
                "field5": "bbb"})
s.group.field1.append(10)
print(s)
```
*Expected output*
```
{'group': {'field2': 'aaa', 'field1': [0, 1, 2, 10]}, 'field4': 3.0, 'field5': 'bbb'}
```

**das** has a utility pretty print function *pprint* too
```
das.pprint(s)
```
will output
```
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


