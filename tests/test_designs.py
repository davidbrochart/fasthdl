import asyncio

from designs.design0 import top_module, reset


def test_design0():
    m = top_module()

    reset.d = 1
    asyncio.run(m.run())
    assert m.m1.out0.d is None
    reset.d = 0
    for i in range(10):
        asyncio.run(m.run())
        assert m.m0.out0.d == 2 * i
