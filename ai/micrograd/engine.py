import math

class Value:
    "Stores a scalar value and its gradient"

    def __init__(self, data, _children=(), _op=""):
        self.data = data
        self.grad = 0
        self._backward = lambda : None
        self._prev = set(_children)

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(other.data + self.data, (self, other), "+")
        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data*other.data, (self, other), "*")
        def _backward():
            self.grad += out.grad*other.data
            other.grad += out.grad*self.data

        out._backward = _backward
        return out

    def __pow__(self, other):
        assert isinstance(other, (float, int)), "Only support int/float power"
        out = Value(self.data**other, (self,), f"**({other})")
        def _backward():
            self.grad += out.grad*(other*self.data**(other - 1))
        out._backward = _backward
        return out

    def backward(self):
        nodes: list[Value] = []
        visited = set()
        def get_topo_order(node: Value):
            if node not in visited:
                visited.add(node)
                for c in node._prev:
                    get_topo_order(c)
                nodes.append(node)
        get_topo_order(self)
        self.grad = 1
        for n in reversed(nodes):
            n._backward()

    def tanh(self):
        x = self.data
        t = (math.exp(2*x) - 1)/(math.exp(2*x) + 1)
        out = Value(t, (self, ), 'tanh')

        def _backward():
            self.grad += (1 - t**2) * out.grad
        out._backward = _backward

        return out

    def __neg__(self):
        return -1*self

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other): # other - self
        return other + (-self)

    def __rmul__(self, other): # other * self
        return self*other

    def __truediv__(self, other):
        return self*other**-1

    def __rtruediv__(self, other): # other / self
        return self**-1 * other

    def __radd__(self, other):
        return self + other

    def __repr__(self) -> str:
        return f"Value(data={self.data}, grad={self.grad})"




x1 = Value(2)
x2 = Value(0)
w1 = Value(-3)
w2 = Value(1)
b = Value(6.8813735870195432)
x1w1 = x1*w1
x2w2 = x2*w2
x1w1x2w2 = x1w1 + x2w2
n = x1w1x2w2 + b
o = n.tanh()
o.backward()

print('---')
print('o', o.grad)
print('n', n.grad)
print('x2', x2.grad)
print('w2', w2.grad)
print('x1', x1.grad)
print('w1', w1.grad)
