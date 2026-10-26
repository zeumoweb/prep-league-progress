"""Tests for micrograd part 1: the Value class and backprop.

Hand-checked gradients for each operation, plus Karpathy's two sanity checks that compare
against PyTorch. Run with:  python -m pytest -q
"""

import math

import pytest

from engine import Value

TOL = 1e-6


def approx(x):
    return pytest.approx(x, abs=TOL)


# ---------------------------------------------------------------------------
# Forward pass
# ---------------------------------------------------------------------------
class TestForward:
    def test_add_mul(self):
        a, b = Value(2.0), Value(-3.0)
        assert (a + b).data == -1.0
        assert (a * b).data == -6.0

    def test_mixed_with_plain_numbers(self):
        a = Value(2.0)
        assert (a + 1).data == 3.0
        assert (1 + a).data == 3.0
        assert (a * 3).data == 6.0
        assert (3 * a).data == 6.0
        assert (a - 1).data == 1.0
        assert (1 - a).data == -1.0
        assert (-a).data == -2.0

    def test_pow_div(self):
        a = Value(4.0)
        assert (a**2).data == 16.0
        assert (a**0.5).data == approx(2.0)
        assert (a / 2).data == approx(2.0)
        assert (2 / a).data == approx(0.5)

    def test_tanh(self):
        assert Value(0.0).tanh().data == approx(0.0)
        assert Value(1.0).tanh().data == approx(math.tanh(1.0))

    def test_new_value_starts_with_zero_grad(self):
        assert Value(5.0).grad == 0


# ---------------------------------------------------------------------------
# Gradients of each operation
# ---------------------------------------------------------------------------
class TestBackward:
    def test_output_grad_is_one(self):
        a = Value(3.0)
        out = a * 2
        out.backward()
        assert out.grad == 1

    def test_add_grad(self):
        a, b = Value(2.0), Value(-3.0)
        (a + b).backward()
        assert a.grad == approx(1.0)
        assert b.grad == approx(1.0)

    def test_mul_grad(self):
        a, b = Value(2.0), Value(-3.0)
        (a * b).backward()
        assert a.grad == approx(-3.0)   # d(ab)/da = b
        assert b.grad == approx(2.0)    # d(ab)/db = a

    def test_pow_grad(self):
        a = Value(3.0)
        (a**3).backward()
        assert a.grad == approx(27.0)   # 3 * a^2

    def test_div_grad(self):
        a, b = Value(6.0), Value(2.0)
        (a / b).backward()
        assert a.grad == approx(0.5)     # 1/b
        assert b.grad == approx(-1.5)    # -a/b^2

    def test_sub_and_neg_grad(self):
        a, b = Value(5.0), Value(3.0)
        (a - b).backward()
        assert a.grad == approx(1.0)
        assert b.grad == approx(-1.0)

    def test_tanh_grad(self):
        a = Value(0.5)
        a.tanh().backward()
        assert a.grad == approx(1 - math.tanh(0.5) ** 2)

    def test_chain_rule_through_several_ops(self):
        a = Value(2.0)
        b = a * 3          # 6
        c = b + 1          # 7
        d = c * c          # 49, dd/da = 2c * 3 = 42
        d.backward()
        assert a.grad == approx(42.0)


# ---------------------------------------------------------------------------
# Gradient accumulation (a node used more than once)
# ---------------------------------------------------------------------------
class TestAccumulation:
    def test_same_value_added_to_itself(self):
        a = Value(3.0)
        (a + a).backward()
        assert a.grad == approx(2.0)

    def test_same_value_multiplied_by_itself(self):
        a = Value(3.0)
        (a * a).backward()
        assert a.grad == approx(6.0)

    def test_value_used_in_two_branches(self):
        a = Value(-2.0)
        b = Value(3.0)
        d = a * b          # -6
        e = a + b          # 1
        f = d * e          # -6
        f.backward()
        assert a.grad == approx(-3.0)   # b*e + d = 3 - 6
        assert b.grad == approx(-8.0)   # a*e + d = -2 - 6

    def test_pow_of_reused_value_accumulates(self):
        a = Value(2.0)
        (a**2 + a).backward()
        assert a.grad == approx(5.0)    # 2a + 1


# ---------------------------------------------------------------------------
# The neuron from the lecture: o = tanh(x1*w1 + x2*w2 + b)
# ---------------------------------------------------------------------------
def test_lecture_neuron():
    x1, x2 = Value(2.0), Value(0.0)
    w1, w2 = Value(-3.0), Value(1.0)
    b = Value(6.8813735870195432)
    n = x1 * w1 + x2 * w2 + b
    o = n.tanh()
    o.backward()
    assert o.data == approx(0.7071067)
    assert n.grad == approx(0.5)
    assert x1.grad == approx(-1.5)
    assert w1.grad == approx(1.0)
    assert x2.grad == approx(0.5)
    assert w2.grad == approx(0.0)


# ---------------------------------------------------------------------------
# Compare against PyTorch (Karpathy's micrograd sanity checks)
# ---------------------------------------------------------------------------
torch = pytest.importorskip("torch")


def test_sanity_check_against_torch():
    x = Value(-4.0)
    z = 2 * x + 2 + x
    q = z.tanh() + z * x
    h = (z * z).tanh()
    y = h + q + q * x
    y.backward()

    xt = torch.tensor([-4.0], dtype=torch.double, requires_grad=True)
    zt = 2 * xt + 2 + xt
    qt = zt.tanh() + zt * xt
    ht = (zt * zt).tanh()
    yt = ht + qt + qt * xt
    yt.backward()

    assert y.data == approx(yt.item())
    assert x.grad == approx(xt.grad.item())


def test_more_ops_against_torch():
    a = Value(-4.0)
    b = Value(2.0)
    c = a + b
    d = a * b + b**3
    c = c + c + 1
    c = c + 1 + c + (-a)
    d = d + d * 2 + (b + a).tanh()
    d = d + 3 * d + (b - a).tanh()
    e = c - d
    f = e**2
    g = f / 2.0
    g = g + 10.0 / f
    g.backward()

    at = torch.tensor([-4.0], dtype=torch.double, requires_grad=True)
    bt = torch.tensor([2.0], dtype=torch.double, requires_grad=True)
    ct = at + bt
    dt = at * bt + bt**3
    ct = ct + ct + 1
    ct = ct + 1 + ct + (-at)
    dt = dt + dt * 2 + (bt + at).tanh()
    dt = dt + 3 * dt + (bt - at).tanh()
    et = ct - dt
    ft = et**2
    gt = ft / 2.0
    gt = gt + 10.0 / ft
    gt.backward()

    assert g.data == approx(gt.item())
    assert a.grad == approx(at.grad.item())
    assert b.grad == approx(bt.grad.item())
