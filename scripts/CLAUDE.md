# scripts/

Standalone utilities. **None of these run as part of `drawpick.py` or `quickpick.py`.**

| File | Role |
|:--|:--|
| `scrape_lotto.py` | fetches Irish National Lottery results; the only thing here that writes `data/irish500.csv`. Covered by `../tests/test_scraper_sources.py` |
| `train_with_all_features.py` | demonstration of the full training pipeline with SMOTE, feature selection and tuning all enabled. Not the production path |

## Reading README.md in this folder

`README.md` is long and predates several changes. Two cautions:

- It does not mention `scrape_lotto.py` at all.
- Its "Example Output" blocks are illustrative, not captured runs. The numbers in them (AUC 0.69,
  Top-7 0.43) are **not** this system's actual metrics - the real models sit at chance, AUC close to 0.50.
  Check `model_metrics/model_comparison.csv` for real figures.

## Rules

- After adding a draw with `scrape_lotto.py`, the pipeline must be re-run: `python drawpick.py` then
  `python quickpick.py`, then `/lotto-verify`.
- `train_with_all_features.py` enables options the production configs deliberately leave off. Do not
  copy its settings into `ml_lotto/config.py` without measuring - several of them hand capacity back
  to the models.
