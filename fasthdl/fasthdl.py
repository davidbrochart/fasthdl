import asyncio
import inspect
from typing import Any, Optional


class Wire:

    d: Any = None

    driver: Optional["Module"] = None

    def __init__(self, name=None):
        self.name = name

    async def compute(self) -> bool:
        recomputed = False
        if self.driver:
            recomputed = await self.driver.compute()
        return recomputed


class Reg:

    d: Any = None
    q: Any = None

    def clock(self):
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
                p2 = [p for p in m2.resources.ports.values() if isinstance(p, str)]
                for p1 in [
                    p for p in m1.resources.ports.values() if isinstance(p, str)
                ]:
                    if p1 in p2:
                        w = Wire(name=p1)
                        m1.resources.set_arg(p1, w)
                        m2.resources.set_arg(p1, w)

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
            output.driver = self.module

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
    def __init__(self, func, args, kwargs):
        self.func = func
        self.resources = Resources(func, args, kwargs, self)
        self.computed = False

    async def run(self, clocks=1):
        for i in range(clocks):
            self.clock()
            await self.compute()

    async def compute(self) -> bool:
        recomputed = False
        inputs_changed = any(
            await asyncio.gather(*(i.compute() for i in self.resources.inputs.values()))
        )
        do_compute = not self.computed or inputs_changed
        if do_compute:
            self.func(*self.resources.args, **self.resources.kwargs)
            self.computed = True
            recomputed = True
        for m in self.resources.modules.values():
            await m.compute()
        return recomputed

    def clock(self):
        for m in self.resources.modules.values():
            m.clock()
        for r in self.resources.registers.values():
            r.clock()
        self.computed = False

    def __getitem__(self, name):
        return self.resources[name]

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getattribute__("resources")[name]


def module(func):
    def wrapper(*args, **kwargs):
        return Module(func, args, kwargs)

    return wrapper
