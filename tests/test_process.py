from fasthdl import module, Reg, X


def test_process(capfd):
    @module
    def counter(r=Reg()):
        if r.q is X:
            r.d = 0
        else:
            r.d = r.q + 1

    m = counter()

    def process0(m):
        while m.r.d != 2:
            yield
        print(f"process0 {m.cycle_i=}, {m.r.d=}")
        for _ in range(2):
            yield
        print(f"process0 {m.cycle_i=}")

    def process1(m):
        while True:
            print(f"process1 {m.cycle_i=}")
            for _ in range(3):
                yield

    m.attach(process0(m))
    m.attach(process1(m))

    m.run(6)

    out, err = capfd.readouterr()
    assert (
        out == "process1 m.cycle_i=0\n"
        "process0 m.cycle_i=3, m.r.d=2\n"
        "process1 m.cycle_i=3\n"
        "process0 m.cycle_i=5\n"
    )
