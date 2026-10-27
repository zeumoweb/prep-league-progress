import random
from engine import Value


class Neuron:
    def __init__(self, nin): # number of inputs
        self.w = [Value(random.uniform(-1, 1)) for _ in range(nin)]
        self.b = Value(random.uniform(1, -1))

    def __call__(self, x):
        out = sum([wi*xi for (wi, xi) in zip(self.w, x)], self.b)
        result = out.tanh()
        return result


    def parameters(self):
        return self.w + [self.b]


class Layer:
    def __init__(self, nin, nout):
        self.neurons = [Neuron(nin) for _ in range(nout)]

    def __call__(self, x):
        outs = [n(x) for n in self.neurons]
        return outs[0] if len(outs) == 1 else outs

    def parameters(self):
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    def __init__(self, nin, nouts):
        size = [nin] + nouts # nin is the first input layer and nouts define subsequent layers
        self.layers = [Layer(size[i], size[i + 1]) for i in range(len(nouts))]

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

    def parameters(self):
        return [p  for layer in self.layers for p in layer.parameters()]


def train(inputs, mlp: MLP, y, learning_rate, iteration):
    # forward pass
    ypred = []
    for i in range(iteration):
        ypred = [mlp(x) for x in inputs]
        loss = sum([(yi - ypi)**2 for (yi, ypi) in zip(y, ypred)])

        # backward pass
        for p in mlp.parameters():
            p.grad = 0

        loss.backward()

        # update values
        for p in mlp.parameters():
            p.data += -learning_rate*p.grad

        if i%10 == 0:
            print(f"Current loss value is {loss}")











