"""Train a micrograd MLP on make_moons until training accuracy is at least 95%.

Setup follows the micrograd repo demo, adapted to this engine (tanh units, no ReLU):
MLP(2, [16, 16, 1]), labels mapped to -1/+1, MSE loss plus a small L2 penalty, full-batch
gradient descent with a decaying learning rate.
"""

import random

from sklearn.datasets import make_moons

from nn import MLP

SEED = 1337
MAX_STEPS = 200
TARGET_ACCURACY = 0.95
ALPHA = 1e-4  # L2 regularisation strength


def load_data():
    X, y = make_moons(n_samples=100, noise=0.1, random_state=SEED)
    labels = [1.0 if label == 1 else -1.0 for label in y]  # {0, 1} -> {-1, +1}
    return [list(map(float, row)) for row in X], labels


def loss_and_accuracy(model, xs, ys):
    scores = [model(x) for x in xs]
    data_loss = sum((score - y) ** 2 for score, y in zip(scores, ys)) * (1.0 / len(ys))
    reg_loss = ALPHA * sum(p * p for p in model.parameters())
    accuracy = sum((score.data > 0) == (y > 0) for score, y in zip(scores, ys)) / len(ys)
    return data_loss + reg_loss, accuracy


def main():
    random.seed(SEED)
    xs, ys = load_data()
    model = MLP(2, [16, 16, 1])
    print(f"MLP with {len(model.parameters())} parameters, {len(xs)} training points")

    for step in range(MAX_STEPS):
        loss, accuracy = loss_and_accuracy(model, xs, ys)
        if step % 10 == 0:
            print(f"step {step:3d}  loss {loss.data:.4f}  accuracy {accuracy:.0%}")
        if accuracy >= TARGET_ACCURACY:
            break

        for p in model.parameters():
            p.grad = 0
        loss.backward()

        learning_rate = 1.0 - 0.9 * step / MAX_STEPS  # decays from 1.0 to 0.1
        for p in model.parameters():
            p.data -= learning_rate * p.grad

    print(f"final: step {step}  loss {loss.data:.4f}  training accuracy {accuracy:.0%}")
    return accuracy


if __name__ == "__main__":
    main()
