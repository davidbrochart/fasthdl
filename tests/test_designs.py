from fasthdl import X
from designs.design0 import top_module, reset


def test_design0():
    m = top_module()

    reset.d = 1
    m.run()
    assert m.m1.out0.d is X
    reset.d = 0
    for i in range(10):
        m.run()
        assert m.m0.out0.d == 2 * i
