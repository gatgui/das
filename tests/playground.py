import os
import re
import sys
import glob

thisdir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(thisdir, "..", "python"))
dirs = map(lambda y: thisdir + "/" + y, filter(lambda x: re.match("test\d+", x), os.listdir(thisdir)))
os.environ["DAS_SCHEMA_PATH"] = os.pathsep.join(dirs)

import das

def print_types():
   print("=== Print default for all 'hud' schema types")
   stl = das.list_schema_types("hud")
   for st in stl:
      print("=== %s" % st)
      v = das.make_default(st)
      print(type(v).__name__)
      das.pprint(v)
      if hasattr(v, "_schema_type"):
         print(v._schema_type)


def test_mixin1():
   print("=== Mixin tests using timeline.ClipSource schema type ===")

   class Range(das.Mixin):
      @classmethod
      def get_schema_type(klass):
         return "timeline.Range"

      def __init__(self, *args, **kwargs):
         super(Range, self).__init__(*args, **kwargs)

      def expand(self, start, end):
         cs, ce = self[0], self[1]
         if start < cs:
            cs = start
         if end > ce:
            ce = end
         self[0], self[1] = cs, ce


   class ClipSource(das.Mixin):
      @classmethod
      def get_schema_type(klass):
         return "timeline.ClipSource"

      def __init__(self, *args, **kwargs):
         super(ClipSource, self).__init__(*args, **kwargs)

      def set_media(self, path):
         _, ext = map(lambda x: x.lower(), os.path.splitext(path))
         if ext == ".fbx":
            print("Get range from FBX file")
         elif ext == ".abc":
            print("Get range from Alembic file")
         elif ext == ".mov":
            print("Get range from Movie file")
         self.media = os.path.abspath(path).replace("\\", "/")

      def set_clip_offsets(self, start, end):
         data_start, data_end = self.dataRange
         clip_start = min(data_end, data_start + max(0, start))
         clip_end = max(data_start, data_end + min(end, 0))
         if clip_start == data_start and clip_end == data_end:
            self.clipRange = None
         else:
            self.clipRange = (clip_start, clip_end)

   das.register_mixins(Range, ClipSource)

   print("-- make def (1)")
   dv = das.make_default("timeline.ClipSource")
   print("-- write (1)")
   das.write(dv, "./out.tl")
   print("-- make def (2)")
   cs = das.make_default("timeline.ClipSource")
   print("-- read (1)")
   cs = das.read("./out.tl")
   das.pprint(cs)
   cs.dataRange = (100, 146)
   cs.dataRange.expand(102, 150)
   cs.set_media("./source.mov")
   cs.set_clip_offsets(1, -1)
   das.pprint(cs)
   print("-- write (2)")
   das.write(cs, "./out.tl")
   c = das.copy(cs)
   das.pprint(c)
   for k, v in c.iteritems():
      print("%s = %s" % (k, v))
   os.remove("./out.tl")


def test_mixin2():
    class Fn(das.mixin.Mixin):
        @classmethod
        def get_schema_type(klass):
            return "timeline.ClipSource"

        def __init__(self, *args, **kwargs):
            super(Fn, self).__init__()

        def _copy(self):
            print("Fn._copy")
            return self

        def pprint(self):
            das.pprint(self)

    class Fn2(das.mixin.Mixin):
        @classmethod
        def get_schema_type(klass):
            return "timeline.ClipSource"

        def __init__(self, *args, **kwargs):
            super(Fn2, self).__init__()

        def echo(self):
            print("From Fn2 Mixin")

    class Fn3(das.mixin.Mixin):
        @classmethod
        def get_schema_type(klass):
            return "timeline.Range"

        def __init__(self, *args, **kwargs):
            super(Fn2, self).__init__()

        def echo(self):
            print("From Fn3 Mixin")

    data = das.make_default("timeline.ClipSource")
    try:
        data.pprint()
    except Exception, e:
        print(str(e))
    das.mixin.bind([Fn, Fn2], data)
    das.mixin.bind(Fn2, data)
    das.mixin.bind(Fn, data)
    try:
        das.mixin.bind(Fn3, data)
    except Exception, e:
        print(str(e))
    data.pprint()
    c = data._copy()
    c = das.copy(data)
    das.mixin.bind(Fn2, c, reset=True)
    c.echo()
    try:
        c.pprint()
    except Exception, e:
        print(str(e))


def name_conflicts():
   print("=== Name conflict resolution ===")
   d = das.make_default("conflicts.DictMethod")
   das.pprint(d)
   print("keys = %s" % d.keys)
   print("_keys() -> %s" % d._keys())
   print("values = %s" % d.values)
   print("_values() -> %s" % d._values())
   print("items() -> %s" % d.items())
   for k, v in d.items():
      print("%s = %s" % (k, v))
   das.pprint(d)
   d._clear()
   das.pprint(d)


def do_shopping():
   def make_item(name, value):
      item = das.make_default("shopping.item")
      item.name = name
      item.value = value
      return item

   b = das.make_default("shopping.basket")
   b.items.append(make_item("carottes", 110))
   b.items.append(make_item("meat", 320))
   das.pprint(b)
   for c in ["yen", "euro", "dollar"]:
      print("%f %s(s)" % (b.value_in(c), c))


if __name__ == "__main__":
   args = sys.argv[1:]
   nargs = len(args)

   funcs = {"print_types": print_types,
            "test_mixin1": test_mixin1,
            "name_conflicts": name_conflicts,
            "test_mixin2": test_mixin2,
            "do_shopping": do_shopping}

   if nargs == 0:
      print("Please specify function(s) to run (%s or all)" % ", ".join(funcs.keys()))
      sys.exit(0)

   if "all" in args:
      for f in funcs.values():
         f()
   else:
      for arg in args:
         f = funcs.get(arg, None)
         if f is None:
            print("Ignore non-existing function '%s'" % arg)
         else:
            f()
