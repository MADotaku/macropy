
import sys
import imp
import ast
from ast import *
from macroscopy.core.core import *
from util import *



class Placeholder(AST):
    def __repr__(self):
        return "Placeholder()"


def expr_macro(func):
    Macros.expr_registry[func.func_name] = func


def block_macro(func):
    Macros.block_registry[func.func_name] = func


expr.__repr__ = lambda self: ast.dump(self, annotate_fields=False)
stmt.__repr__ = lambda self: ast.dump(self, annotate_fields=False)


def splat(node):
    """Extracts the `lineno` and `col_offset` from the given node as a dict.
    meant to be used e.g. through Str("omg", **splat(node)) to transfer the old
    `lineno` and `col_offset` to the newly created node.
    """
    return {"lineno": node.lineno, "col_offset": node.col_offset}


def interp_ast(node, values):
    def v(): return values

    def func(node):
        if type(node) is Placeholder:
            val = v().pop(0)
            return ast_repr(val)
        else:
            return node
    x = Macros.recurse(node, func)
    return x


@singleton
class Macros(object):
    expr_registry = {}
    block_registry = {}



    def recurse(self, node, func):
        if type(node) is list:
            return flatten([
                self.recurse(x, func)
                for x in node
            ])
        elif isinstance(node, AST):
            node = func(node)
            print type(node)

            if type(node) is list:
                return self.recurse(node, func)
            else:
                for field, old_value in iter_fields(node):
                    old_value = getattr(node, field, None)
                    new_value = self.recurse(old_value, func)
                    setattr(node, field, new_value)
                return node
        else:
            return node


class MacroLoader(object):
    def __init__(self, module_name, txt, file_name):
        self.module_name = module_name
        self.txt = txt
        self.file_name = file_name

    def load_module(self, module_name):
        """see http://www.python.org/dev/peps/pep-0302/ if you don't know what
        a lot of this stuff is for"""

        try:
            if module_name in sys.modules:
                return sys.modules[module_name]

            a = expand_ast(ast.parse(self.txt))

            code = compile(a, module_name, 'exec')

            mod = imp.new_module(module_name)
            mod.__file__ = self.file_name
            mod.__loader__ = self

            exec code in mod.__dict__

            sys.modules[module_name] = mod
            return mod
        except Exception, e:
            print e
            pass


def expand_ast(node):

    def macro_search(node):


        if      isinstance(node, With) \
                and type(node.context_expr) is Name \
                and node.context_expr.id in Macros.block_registry:

            return Macros.block_registry[node.context_expr.id](node)

        if      isinstance(node, BinOp) \
                and type(node.left) is Name \
                and type(node.op) is Mod \
                and node.left.id in Macros.expr_registry:

            return Macros.expr_registry[node.left.id](node.right)


        return node
    node = Macros.recurse(node, macro_search)

    return node

@singleton
class MacroFinder(object):
    def find_module(self, module_name, package_path):
        if module_name in sys.modules:
            return None

        if "macroscopy" in str(package_path):
            try:
                (file, pathname, description) = imp.find_module(module_name.split('.')[-1], package_path)
                txt = file.read()

                return MacroLoader(module_name, txt, file.name)
            except Exception, e:
                pass




sys.meta_path.append(MacroFinder)


