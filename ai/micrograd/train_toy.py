from nn import MLP, train

"""
 train MLP(3, [4, 4, 1]) on the lecture's 4-example dataset with a manual loop for at least 50 steps:
 zero grads, forward, MSE loss, backward, p.data -= lr * p.grad. Print the loss every 10 steps.
"""

mlp = MLP(3, [4, 4, 1])
xs = [
    [2.0, 3.0, -1.0],
    [3.0, -1.0, 0.5],
    [0.5, 1.0, 1.0],
    [1.0, 1.0, -1.0]
]
ys = [1, -1, -1, 1]

train(xs, mlp, ys, 0.1, 100)
