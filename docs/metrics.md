# Metrics

How the six models are evaluated, what the numbers currently are, and how to tell a real improvement
from noise.

Computed by `ml_lotto/models/model_metrics.py` during `quickpick.py`. Written to `model_metrics/`.

## Current results

From `model_metrics/model_comparison.csv`, run of 2026-09-19 (598 draws, latest 16 Sep 2026).
Validation window is the last **60 draws** for every model.

| Model | Val AUC | Overfit gap | Top-7 caught | Top-7 expected | Top-7 lift | PR-AUC lift | Calib. error |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Bonus Ball Predictor | 0.551 | 0.002 | 0.13 | 0.15 | 0.90 | 1.91 | 0.008 |
| Conservative Pool Generator | 0.531 | 0.026 | 1.17 | 1.04 | 1.12 | 1.07 | 0.016 |
| Jackpot Optimizer | 0.531 | 0.078 | 0.95 | 0.89 | 1.06 | 1.08 | 0.013 |
| Complexity Explorer | 0.519 | 0.029 | 1.23 | 1.04 | 1.18 | 1.08 | 0.016 |
| Bonus-to-Main Transition | 0.500 | 0.029 | 1.08 | 1.01 | 1.07 | 0.99 | 0.072 |
| Momentum Specialist | 0.496 | 0.024 | 1.18 | 1.04 | 1.14 | 1.02 | 0.015 |

**Read this table correctly.** AUC 0.50 is a coin flip. Every model sits between 0.496 and 0.551,
and Top-7 lift is 0.90-1.18 against an expected baseline of ~1.04 numbers caught. Adding one draw
moved every figure by less than the noise floor below - the values drift, the conclusion does not. The
Bonus-to-Main model has a PR-AUC lift **below 1.0**, meaning it is fractionally worse than the base
rate.

This is the correct result. Irish Lotto is a fair draw: past draws carry no information about future
ones, so a model that found real signal would be evidence of a bug, not a breakthrough. The system's
value is in the analysis, the constraint satisfaction and the ticket construction - not in beating
the odds.

## The noise floor

Over 60 validation draws, the 2 SE noise band is approximately:

- **AUC: +/- 0.031**
- **Top-7 AvgCaught: +/- 0.227**

A change smaller than that is not a result. Do not report it as an improvement and do not tune
against it. Two models differing by 0.02 AUC are indistinguishable.

## The permutation check

`python quickpick.py --permutation-check 20` retrains each main model 20 times with its training
labels shuffled within each draw - the exact production pipeline with nothing to learn - and scores
every run on the real validation labels. Results go to `model_metrics/permutation_check.json`.

Run 2026-09-18 (F-17), rule fixed beforehand: an edge needs p < 0.05, i.e. beating all 20 shuffled
runs.

| Model | Real val AUC | Shuffled: mean +/- sd (range) | Shuffled >= real | p |
|:--|--:|:--|--:|--:|
| Momentum Specialist | 0.5011 | 0.4967 +/- 0.0151 (0.454-0.522) | 9 / 20 | 0.476 |
| Jackpot Optimizer | 0.5257 | 0.5066 +/- 0.0163 (0.483-0.551) | 2 / 20 | 0.143 |
| Complexity Explorer | 0.5074 | 0.4891 +/- 0.0132 (0.471-0.532) | 2 / 20 | 0.143 |
| Conservative Pool Generator | 0.5118 | 0.4928 +/- 0.0119 (0.470-0.516) | 1 / 20 | 0.095 |

**No model has an edge.** Every real AUC sits inside the range noise produces. The shuffled runs
spread with sd 0.012-0.016, so 2 sd is 0.024-0.033 - an independent confirmation of the +/- 0.031
floor above. Re-run it after any change that claims to add signal.

## The metrics, and why each one is here

**AUC-ROC** - probability the model ranks a random drawn number above a random undrawn one. 0.5 is
chance. The headline number, but nearly uninformative on its own at these magnitudes.

**Accuracy is deliberately not the headline.** Roughly 7 of 47 numbers are drawn, so a model that
predicts "never drawn" scores ~85% accuracy while catching nothing. Ignore accuracy.

**PR-AUC, with baseline and lift** - precision-recall area, compared against the base rate
(~0.149 for 7-of-47, ~0.128 for the main-6-only model). Lift is the ratio. More honest than AUC for
a heavily imbalanced target. Lift below 1.0 means worse than guessing.

**Top-K accuracy** (`calculate_topk_accuracy`, K = 7, 10, 15, 20) - of the K highest-ranked numbers,
how many were actually drawn. This is the metric that matches how the system is used, since a ticket
is a small set of numbers. `Top-7 AvgCaught` is the mean caught per draw; `Top-7 Expected` is what
random selection would catch; `Top-7 Lift` is the ratio.

**Hit rate** (`calculate_hit_rate`) - fraction of validation draws where at least one of the top K
was drawn.

**Calibration error** - mean absolute gap between predicted probability and observed frequency.
Below 0.05 is good, above 0.1 means the probabilities are not trustworthy as probabilities. All main
models are currently under 0.025; the Bonus-to-Main model at 0.072 is the weakest.

**Overfit gap** - train AUC minus validation AUC. Currently 0.002-0.078.

## The overfit gap is the number to watch

Because AUC cannot meaningfully improve on a fair draw, the only way to move it is to let a model
memorise the training set. That shows up as the gap widening, not as a better validation score.

**A gap above ~0.1 means capacity was handed back to a model.** The narrow `algorithm_params` in
`ml_lotto/config.py` and the constrained grids in `ml_lotto/models/hyperparameter_tuning.py` exist
to prevent this, and `tests/test_model_capacity.py` enforces it. Widening either one alone
reintroduces the problem through the back door.

## Files produced

Per model in `model_metrics/`: `<name>_roc_curve.png`, `<name>_pr_curve.png`,
`<name>_calibration.png`, and `<name>_tuning_results.json` for the tuned models. Across models:
`model_comparison.csv` (the scoreboard) and `model_comparison_chart.png`.

All regenerated by `quickpick.py`. Do not hand-edit them.

## Claiming an improvement

1. `cp model_metrics/model_comparison.csv /tmp/baseline.csv`
2. Make the change, re-run the pipeline.
3. `python .claude/skills/lotto-verify/verify.py --baseline /tmp/baseline.csv`

If the move is inside the noise floor, the change did not help. Say so plainly rather than reporting
it as a gain.
