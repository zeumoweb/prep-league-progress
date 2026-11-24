import torch
import torch.nn.functional as F
import matplotlib.pyplot as plt

words = open("./names.txt", "r").read().splitlines()
N = torch.zeros((27, 27), dtype=torch.int32)

chars = ["."] + sorted(set("".join(words)))
stoi = {char: i for i, char in enumerate(chars)}
itos = {i: char for i, char in enumerate(chars)}

for word in words:
    word = "." + word + "."
    for char1, char2 in zip(word, word[1:]):
        N[stoi[char1], stoi[char2]] += 1


# plt.figure(figsize=(16, 16))
# plt.imshow(N, cmap="Blues")
# for i in range(27):
#     for j in range(27):
#         charstr = itos[i] + itos[j]
#         plt.text(j, i, charstr, ha="center", va="bottom", color="gray")
#         plt.text(j, i, str(N[i, j].item()), ha="center", va="top", color="gray")
# plt.show()

P = (N + 1).float() # smoothing
P /= P.sum(dim=1, keepdim=True)
G = torch.Generator().manual_seed(2147483647)


# loss function using counting of bigrams
logprob = 0
count = 0
for word in words:
    word = "." + word + "."
    for char1, char2 in zip(word, word[1:]):
        logprob += torch.log(P[stoi[char1], stoi[char2]])
        count += 1

nll = -logprob
print(f"{nll=} Average {nll/count}")

# Implementation using neural network and backpropagation
xs, ys = [], []

for word in words:
    word = "." + word + "."
    for char1, char2 in zip(word, word[1:]):
        xs.append(stoi[char1])
        ys.append(stoi[char2])

xs = torch.tensor(xs)
ys = torch.tensor(ys)
xenc = F.one_hot(xs, num_classes=27).float()  # pylint: disable=not-callable
W = torch.randn((27, 27), generator=G, requires_grad=True)
print(f"Number of bigrams samples {xs.nelement()}")
probs = torch.Tensor([])
# gradient descent
for _ in range(100):
    # forward pass
    logits = (xenc @ W)
    counts = logits.exp()
    probs = counts/counts.sum(dim=1, keepdim=True) # soft max function to help output probabilities
    loss = -probs[torch.arange(xs.nelement()), ys].log().mean()  + 0.01*(W**2).mean() # negative log likelihood
    W.grad = None
    loss.backward()
    assert W.grad is not None
    with torch.no_grad():
        W -= 50 * W.grad

G = torch.Generator().manual_seed(2147483647)

# Sampling Using Count
print("Count Sampling")
for i in range(10):
    out = []
    indx = 0

    while True:
        p = P[indx]
        indx = int(torch.multinomial(p, num_samples=1, replacement=True, generator=G).item())
        out.append(itos[indx])
        if indx == 0:
            break
    print("".join(out))

G = torch.Generator().manual_seed(2147483647)

print("Neural Network Sample")
for i in range(10):
    out = []
    indx = 0

    while True:
        xenc = F.one_hot(torch.tensor([indx]), num_classes=27).float() # pylint: disable=not-callable
        logits = xenc @ W
        # normalize
        counts = logits.exp()
        p = counts / counts.sum(dim=1, keepdim=True)
        indx = int(torch.multinomial(p, num_samples=1, replacement=True, generator=G).item())
        out.append(itos[indx])
        if indx == 0:
            break
    print("".join(out))
