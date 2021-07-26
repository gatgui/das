**0.13.0**
- Added new method `is_type_compatible` to `TypeValidator` class to check for type compatibility.
- Allow field overrides when extending a `Struct` as long as type is compatible.
- Fixed several issues with `Struct` extensions:
  - missing aliases
  - double fields in serialization

**0.12.3**
- Check for QApplication instance existence before creating it in `dasedit`.
- Removed unnecessary deprecated warnings.

**0.12.2**
- Improved handling of dynamic `Struct` schema type modifications.

**0.12.1**
- Observe optional field editable property in editor.
- Show type/description in editor's new value dialog.

**0.12.0**
- Prelimiray support for Struct type extensions:
  - Struct schema type can be extended dynamically.
  - To extend at the schema level, use `__extends__` keyword argument in the Struct arguments:

```python
{ "MyBaseType": Struct(mybasefield1=Real(default=0.5), name=String()),
  "MyType": Struct(myfield1=Integer(default=1), __extends__=["MyBaseType"])}
```

- Mixins can now be explicitely registered against a specific schema type.
  *NOTES*
  - `schema_type` keyword arguments also accepts a schema type instance (a `TypeValidator` sub-class). It has to be a properly registered type so it won't work with *inline* types.

```python
das.register_mixins(MixinClass1, MixinClass2, schema_type="schemaname.typename")
```

- Added properties to schema type base class with the following methods:
  - has_property
  - set_property
  - get_property
  - set_properties
  - get_properties
  - remove_property

    *NOTES*
    - bound mixins are now stored preferably in the schema type itself,
      whereas it used to only be tracked in the type registry so far)
    - informations about type extensions is tracked using the property system

**0.11.1**
- Allow for more flexible `Class` schema type value assignment.

**0.11.0**
- Improved error reporting.
- Improved `Or` type's `make` method to be more dynamic depending on passed arguments.
- Fixed string representation failure with tuple's schema type default values.
- Enabled usage of mixins with anonymous/inline schema types.
- Re-validate container type objects after element insertion and removal.

**0.10.0**
- Support csv serialization.
- Fix duplication of mixin class names issue.
- Add conform function that conform value to match given schema type.

**0.9.5**
- Support deprecated alias.
- Transfer alias values to their aliased field on read.
- Error on alias value conflicts.

**0.9.4**
- Fixed inline type not being editable.

**0.9.3**
- Fixed a couple of UI issues.

**0.9.2**
- Fixed broken document when using multi-line string.

**0.9.1**
- Improved loose schema reading.
  - Only ignore `Struct`'s unknown keys if all known ones were set.
  - `Or` type tries to first match in strict mode before falling back to loose mode.
- Strict compatibility doesn't let unknown `Struct` keys through anymore.
- Fixed write issue when using alias type value in structs.

**0.9.0**
- Add `das.define_inline_type` function to ease dynamic creation of schema types.
- Improved value shadowing (when a field overrides one of the schema type base class function).
- More flexible boolean type (now accepts strings matching 0,1,off,on,no,yes,false or true).
- Observe struct field order on serialization.

**0.8.0**
- Add dynamic schema type registration.
- Add `das.is_compatible` function, less strict than `das.check` and `das.validate`.
- Avoid double mixin registration.

**0.7.1**
- Fixed error happening when `Struct` schema type constructor `__order__` keyword argument value contained invalid field names.

**0.7.0**
- Added `__order__` keyword argument to `Struct` schema type.
- Fixed issue with `das.cli.eval` function.
- Fixed issue with `daseval` command line tool.

**0.6.1**
- `das.qtui.Model.findIndex` was not consistently returning a QModelIndex.

**0.6.0**
- Fixed issue with `Dict` schema type key adaptation.
- Fixed error happening with sequences of `Or` types.
- Added `updateData` method to Qt model class.
- Added `refreshData` method to Qt editor class
- Added `master_types` metadata to schema.
- Added `New` file menu in `dasedit`.
- Support incremental schema loading scheme.
- Improved editor contextual menu.
- Mixin class initializers are now called upon binding.

**0.5.0**
- `String` schema type's `choices` keyword argument now also accepts functions.
- Add `strict` keyword argument for `String` for use with `choices`.
- Add `enum` keyword argument to `Integer` type.
- Add global validation through mixin `_validate_globally` method.
- Add simple data and schema version checks.
- Add functions to generate empty schema and update schema metadata.
- Add new `strict_schema` keyword argument to `das.read` function (defaults to True).
- Add option to override schema name in its metadata.
- Add `Set` schema type.
- Add `Alias` schema type.
- Better unicode support.
- Add Qt based editor for schema data.
- Add command line interface.

**0.4.1**
- Fix user name environment variable on windows.

**0.4.0**
- `Or` schema type now accepts unlimited number of types.
- `Class` schema type now accepts string as well as class objects.
- Add new `das.read_string` function.
- `das.validate` function now returns the validated value.

**0.3.1**
- Using `Deprecated` schema type was causing error on schema read.
- Don't allow setting new key in `Struct` schema type.
- More consistent deprecated key usage warning 

**0.3.0**
- Reorganized modules.
- Add mixin functionality to dynamically add methods to schema types.
- Auto validation.
- Add sub classes for all standard data containers.
- Add `Empty` schema type.
- Add `Deprecated` schema type.
- Add metadata to file (author, data, schema_type, library version).
- Add new `das.make` function taking arbitraty arguments.
- Deprecated `struct` module.
- Deprecated `Das` type, use `das.types.Struct` instead.
- Deprecated `StaticDict` and `DynamicDict` schema types, use `das.schematypes.Struct` and `das.schematypes.Dict` instead.

**0.2.0**
- Add `make_default` function that takes a schema type name as sole argument.
- `list_schema_types` can now take an optional `schema` argument to limit the listed type to the specified schema.
- Allow default override in SchemaType class.

**0.1.0**
- Initial release.
