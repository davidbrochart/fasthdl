from fasthdl import module, In, Out, Reg, Wire


@module
def sub_module0(
    # I/O
    in0: In,
    out0: Out,
):
    if in0.d is None:
        out0.d = None
    else:
        out0.d = 2 * in0.d


@module
def sub_module1(
    # I/O
    reset: In,
    out0: Out,
    # internal
    reg0=Reg(),
):
    if reset.d == 1:
        reg0.d = 0
    elif reg0.q is not None:
        reg0.d = reg0.q + 1
    out0.d = reg0.q


reset = Wire()


@module
def top_module(
    m0=sub_module0(in0="cnt"),
    m1=sub_module1(reset, "cnt"),
):
    pass
