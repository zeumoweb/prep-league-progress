import random
from pathlib import Path

import torch
import torch.nn.functional as F

# Read words
words = Path(__file__).with_name("names.txt").read_text().splitlines()

chars = ["."] + sorted(set("".join(words)))
stoi = {char: i for i, char in enumerate(chars)}
itos = {i: char for i, char in enumerate(chars)}
block_size = 3  # number of previous characters used to predict the next one


def build_dataset(words):
    X, Y = [], []
    for w in words:
        context = [0] * block_size
        for ch in w + ".":
            ix = stoi[ch]
            X.append(context)
            Y.append(ix)
            context = context[1:] + [ix]

    X = torch.tensor(X)
    Y = torch.tensor(Y)
    return X, Y


# 80/10/10 train/dev/test split
random.seed(0)
random.shuffle(words)
n1 = int(0.8 * len(words))
n2 = int(0.9 * len(words))
Xtr, Ytr = build_dataset(words[:n1])
Xdev, Ydev = build_dataset(words[n1:n2])
Xtest, Ytest = build_dataset(words[n2:])
print(f"train {tuple(Xtr.shape)}, dev {tuple(Xdev.shape)}, test {tuple(Xtest.shape)}")

# Parameters
G = torch.Generator().manual_seed(0)
C = torch.randn((27, 10), generator=G, requires_grad=True)
W1 = torch.randn((30, 200), generator=G, requires_grad=True)
b1 = torch.randn(200, generator=G, requires_grad=True)
W2 = torch.randn((200, 27), generator=G, requires_grad=True)
b2 = torch.randn(27, generator=G, requires_grad=True)
params = [W1, W2, b1, b2, C]
print(f"parameters: {sum(p.nelement() for p in params)}")


def forward(X):
    emb = C[X]
    h = torch.tanh(emb.view(emb.shape[0], 30) @ W1 + b1)
    return h @ W2 + b2


# Train with minibatches of 32
for i in range(100000):
    ix = torch.randint(0, Xtr.shape[0], (32,))
    loss = F.cross_entropy(forward(Xtr[ix]), Ytr[ix])
    for p in params:
        p.grad = None
    loss.backward()
    lr = 0.1
    for p in params:
        p.data += -lr * p.grad

print(f"last minibatch loss: {loss.item():.4f}")


# Evaluate loss on each split
@torch.no_grad()
def split_loss(X, Y):
    return F.cross_entropy(forward(X), Y).item()


print(f"train loss: {split_loss(Xtr, Ytr):.4f}")
print(f"dev loss:   {split_loss(Xdev, Ydev):.4f}")
print(f"test loss:  {split_loss(Xtest, Ytest):.4f}")

# Sampling
with torch.no_grad():
    for _ in range(20):
        out = []
        context = [0] * block_size
        while True:
            logits = forward(torch.tensor([context]))
            probs = F.softmax(logits, dim=1)
            indx = int(torch.multinomial(probs, num_samples=1, generator=G).item())
            out.append(itos[indx])
            context = context[1:] + [indx]
            if indx == 0:
                break

        print(f"Name: {''.join(out)}")
