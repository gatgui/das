import das # pylint: disable=import-error

class TupleEcho(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "mix.tuple"

  def __init__(self, *args, **kwargs):
    super(TupleEcho, self).__init__(*args, **kwargs)

  def niceEcho(self):
    print("Tuple value : '%s', '%s', '%s'" % (self[0], self[1], self[2]))

class SequenceEcho(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "mix.sequence"

  def __init__(self, *args, **kwargs):
    super(SequenceEcho, self).__init__(*args, **kwargs)

  def niceEcho(self):
    print("Sequence value [%s] : [%s]" % (len(self), ", ".join(map(lambda x: "'%s'" % x, self))))

class SetEcho(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "mix.set"

  def __init__(self, *args, **kwargs):
    super(SetEcho, self).__init__(*args, **kwargs)

  def niceEcho(self):
    print("Set value [%s] : (%s)" % (len(self), ", ".join(map(lambda x: "'%s'" % x, self))))

class DictEcho(das.Mixin):
  @classmethod
  def get_schema_type(klass):
    return "mix.dict"

  def __init__(self, *args, **kwargs):
    super(DictEcho, self).__init__(*args, **kwargs)

  def niceEcho(self):
    print("Dict value [%s] : {%s}" % (len(self), ", ".join(map(lambda x: "%s = '%s'" % x, self.items()))))

das.register_mixins(TupleEcho, SequenceEcho, SetEcho, DictEcho)
