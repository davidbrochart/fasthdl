import inspect
from typing import Any, Callable, List, Optional, Generator


class _X:
    def __eq__(self, other):
        return False

    def __neq__(self, other):
        return False

    def __repr__(self):
        return "X"

    # unary operators
    def __neg__(self):
        return X

    def __pos__(self):
        return X

    def __abs__(self):
        return X

    def __invert__(self):
        return X

    def __complex__(self):
        return X

    def __int__(self):
        return X

    def __float__(self):
        return X

    def __round__(self):
        return X

    def __trunc__(self):
        return X

    def __floor__(self):
        return X

    def __ceil__(self):
        return X

    # binary operators
    def __add__(self, other):
        return X

    def __radd__(self, other):
        return X

    def __sub__(self, other):
        return X

    def __rsub__(self, other):
        return X

    def __mul__(self, other):
        return X

    def __rmul__(self, other):
        return X

    def __matmul__(self, other):
        return X

    def __rmatmul__(self, other):
        return X

    def __truediv__(self, other):
        return X

    def __rtruediv__(self, other):
        return X

    def __floordiv__(self, other):
        return X

    def __rfloordiv__(self, other):
        return X

    def __mod__(self, other):
        return X

    def __rmod__(self, other):
        return X

    def __divmod__(self, other):
        return X

    def __rdivmod__(self, other):
        return X

    def __pow__(self, other):
        return X

    def __rpow__(self, other):
        return X

    def __lshift__(self, other):
        return X

    def __rlshift__(self, other):
        return X

    def __rshift__(self, other):
        return X

    def __rrshift__(self, other):
        return X

    def __and__(self, other):
        return X

    def __rand__(self, other):
        return X

    def __or__(self, other):
        return X

    def __ror__(self, other):
        return X

    def __xor__(self, other):
        return X

    def __rxor__(self, other):
        return X


X = _X()


class Wire:

    d: Any
    _name: Optional[str]
    _driver: Optional["Module"]

    def __init__(self, name: Optional[str] = None):
        self.d = X
        self._name = name
        self._driver = None

    def _compute(self) -> bool:
        """Compute the wire's value.
        Returns `True` if a computation was effectively triggered (and the value may have changed),
        `False` otherwise.
        """
        recomputed = False
        if self._driver:
            recomputed = self._driver._compute()
        return recomputed


class Reg:

    d: Any
    q: Any

    def __init__(self):
        self.d = X
        self.q = X

    def _tick(self):
        self.q = self.d


class In(Wire):
    pass


class Out(Wire):
    pass


class Resources:
    def __init__(self, func, args, kwargs, module):
        spec = inspect.getfullargspec(func)
        if spec.defaults:
            defaults = {
                spec.args[i - len(spec.defaults)]: v
                for i, v in enumerate(spec.defaults)
            }
        else:
            defaults = {}
        for k in kwargs.keys():
            if k not in spec.args:
                raise RuntimeError(f"{k} not in module {func.__name__}")
        self._args = {k: v for k, v in zip(spec.args, args)}
        absent_ports = {}
        for i, k in enumerate(spec.args):
            if not (k in kwargs or k in self._args.keys() or k in defaults.keys()):
                absent_ports[k] = Wire()
        self.func = func
        self.kwargs = dict(kwargs, **absent_ports)
        self.module = module
        self.argnames = spec.args
        self.update_ports()
        self.modules = {
            self.argnames[-len(defaults) + i]: m
            for i, m in enumerate(defaults.values())
            if isinstance(m, Module)
        }
        self.registers = {
            self.argnames[-len(defaults) + i]: r
            for i, r in enumerate(defaults.values())
            if isinstance(r, Reg)
        }

        for m1 in self.modules.values():
            for m2 in [m for m in self.modules.values() if m != m1]:
                p2 = [p for p in m2._resources.ports.values() if isinstance(p, str)]
                for p1 in [
                    p for p in m1._resources.ports.values() if isinstance(p, str)
                ]:
                    if p1 in p2:
                        w = Wire(name=p1)
                        m1._resources.set_arg(p1, w)
                        m2._resources.set_arg(p1, w)

    def update_ports(self):
        self.inputs = {
            k: self._args[k] if k in self._args else self.kwargs[k]
            for k, v in self.func.__annotations__.items()
            if v == In
        }
        self.outputs = {
            k: self._args[k] if k in self._args else self.kwargs[k]
            for k, v in self.func.__annotations__.items()
            if v == Out
        }
        self.ports = dict(self.inputs, **self.outputs)
        for output in [o for o in self.outputs.values() if not isinstance(o, str)]:
            output._driver = self.module

    def set_arg(self, name, value):
        if name in self._args.values():
            i = list(self._args.values()).index(name)
            k = list(self._args.keys())[i]
            self._args[k] = value
        else:
            i = list(self.kwargs.values()).index(name)
            k = list(self.kwargs.keys())[i]
            self.kwargs[k] = value
        self.update_ports()

    @property
    def args(self):
        return tuple(self._args.values())

    def __getitem__(self, name):
        if name in self.ports:
            return self.ports[name]
        if name in self.registers:
            return self.registers[name]
        if name in self.modules:
            return self.modules[name]
        raise KeyError


class Module:

    _func: Callable
    _resources: Resources
    _computed: bool
    _cycle_i: int
    _processes: List[Generator[None, None, None]]

    def __init__(self, func, args, kwargs):
        self._func = func
        self._resources = Resources(func, args, kwargs, self)
        self._computed = False
        self._cycle_i = 0
        self._processes = []

    @property
    def cycle_i(self):
        return self._cycle_i

    def run(self, cycle_nb=1):
        for _ in range(cycle_nb):
            for process in self._processes:
                try:
                    next(process)
                except StopIteration:
                    self._processes.remove(process)
            self._compute()
            self._tick()
            self._cycle_i += 1

    def _compute(self) -> bool:
        recomputed = False
        inputs_changed = any(i._compute() for i in self._resources.inputs.values())
        do_compute = not self._computed or inputs_changed
        if do_compute:
            self._func(*self._resources.args, **self._resources.kwargs)
            self._computed = True
            recomputed = True
        for m in self._resources.modules.values():
            m._compute()
        return recomputed

    def _tick(self):
        for m in self._resources.modules.values():
            m._tick()
        for r in self._resources.registers.values():
            r._tick()
        self._computed = False

    def attach(self, process):
        self._processes.append(process)

    def __getitem__(self, name):
        return self._resources[name]

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getattribute__("_resources")[name]


def module(func):
    def wrapper(*args, **kwargs):
        return Module(func, args, kwargs)

    return wrapper
