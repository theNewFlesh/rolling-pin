import bar.baz as baz


def mod_func_1(a, b, c):
    return a * b + c


class Foo():
    def __init__(self, kiwi):
        self.kiwi = kiwi

    def do_instance_thing(self, a, b):
        def recurse(items):
            if isinstance(items, list):
                return items
            for item in items:
                recurse(item)
        return recurse([a, b])

    @staticmethod
    def do_static_thing(taco):
        return mod_func_1(baz(taco))
