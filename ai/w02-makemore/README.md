# Week 2: makemore part 1, count and neural bigram models

Prep League task `w02-tue-ai-1`: the bigram character model from Zero to Hero lecture 2, built two ways on `names.txt` (32,033 names, 228,146 bigrams), with all code typed by hand.

- **Code:** `main.py` (the card suggests `ai/w02-makemore/bigram.py`; same content, different path)
- **Count model NLL:** 2.4544
- **Neural model NLL:** 2.4750 (0.021 from the count model, inside the 0.05 target)

```bash
python main.py   # run from this folder; needs torch and matplotlib
```

## Count model
1. Wrap each name in `.` (start and end token) and count every bigram into a 27x27 tensor `N`.
2. Add +1 smoothing so unseen bigrams (102 of them, such as `jq`) get a small probability instead of 0, which would make their log-likelihood infinite.
3. Normalise each row with `P.sum(dim=1, keepdim=True)`. `keepdim=True` keeps the shape (27, 1) so each row is divided by its own total; without it, broadcasting divides columns instead.
4. Average negative log-likelihood over all 228,146 training bigrams: **2.4544**.

## Neural model
- **Input:** one-hot encode each first character (228,146 x 27).
- **Model:** one 27x27 weight matrix `W`, initialised with `torch.randn`. `logits = xenc @ W`, then softmax (`exp`, then normalise rows) gives next-character probabilities.
- **Loss:** average NLL of the correct next character, plus `0.01 * (W**2).mean()` regularisation.
- **Training:** 100 steps of full-batch gradient descent with learning rate 50, using torch autograd.
- **Result:** data NLL **2.4750**, or 2.4901 including the regularisation term.

### Why the two models agree
- A one-hot input times `W` selects one row of `W`, so row `i` of `W` holds the log-counts for "what follows character `i`". After softmax it plays the same role as row `i` of `P`.
- The regularisation term pulls `W` toward zero, which makes each row more uniform. That is the neural equivalent of +1 smoothing; a larger coefficient acts like adding more fake counts.

## Samples
Both samplers use `torch.Generator().manual_seed(2147483647)`, reseeded before each model.

| Count model | Neural model |
|---|---|
| cexze. | cexze. |
| momasurailezitynn. | momasurailezityha. |
| konimittain. | konimittain. |
| llayn. | llayn. |
| ka. | ka. |
| da. | da. |
| staiyaubrtthrigotai. | staiyaubrtthrigotai. |
| moliellavo. | moliellavo. |
| ke. | ke. |
| teda. | teda. |

9 of 10 names are identical, which shows both models learned the same bigram table. The one difference comes from the neural model being slightly off the count table (100 training steps plus regularisation), so one random draw late in name 2 landed on a different character.

## Bug found during review
- **Neural sampling read the wrong row.** The first version sampled from `probs[indx]`, but `probs` has one row per training example (228,146 x 27), not one per character. Row 0 happened to be correct (the first bigram starts with `.`), and every later step used an unrelated example, producing names like `kd.` and `nmr.`.
- **Fix:** run the model on the current character, `onehot(indx) @ W` then softmax, which is the same as `softmax(W[indx])`.

## What I'd note in an interview
- Bigram NLL of about 2.45 is the baseline every later makemore model must beat.
- Counting and gradient descent reach the same answer here because a one-hot linear layer is just a lookup table. The neural approach is the one that scales once the context is longer than one character.
