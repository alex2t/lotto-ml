# scripts/

Standalone utilities. **None of these run as part of `drawpick.py` or `quickpick.py`.**

| File | Role |
|:--|:--|
| `scrape_lotto.py` | fetches Irish National Lottery results; the only thing here that writes `data/irish500.csv`. Covered by `../tests/test_scraper_sources.py` |
| `post_draw.py` | posts one draw to the rebuild receiver, signed exactly as n8n signs it - the owner's test of the POST before n8n is wired (`../nextStep/whatleft.md` section 2). Standard library only |
| `train_with_all_features.py` | demonstration of the full training pipeline with SMOTE, feature selection and tuning all enabled. Not the production path |
| `docker_start.*`, `docker_stop.*` | the Docker launchers for Linux/macOS (`.sh`), PowerShell (`.ps1`) and cmd (`.bat`). Each runs the data engine, checks its exit code, then starts both front ends with `--no-deps` - Streamlit on 8501 and the Next.js site on 3000, which run side by side until the cutover in `nextStep/web.md` section 8 |

## Reading README.md in this folder

`README.md` is long and predates several changes. Two cautions:

- It does not mention `scrape_lotto.py` at all.
- Its "Example Output" blocks are illustrative, not captured runs. The numbers in them (AUC 0.69,
  Top-7 0.43) are **not** this system's actual metrics - the real models sit at chance, AUC close to 0.50.
  Check `model_metrics/model_comparison.csv` for real figures.

## Rules

- **`echo >> text` in a `.bat` is a file redirect, not an arrow.** `cmd` takes the first word as a
  filename and writes the rest into it, silently - three of these wrote `Step` and `Docker` into the
  repo root and printed nothing (F-45). Write `echo [Step 1/2] ...`. `tests/test_docker_stack.py`
  rejects any `>` on an `echo` line.
- **The launchers run the engine themselves**, so their `docker compose up` passes `--no-deps`; the
  `depends_on: service_completed_successfully` in `docker-compose.yml` is there for a bare
  `docker compose up`. Both rely on `drawpick.py` exiting non-zero when it fails (F-43, F-47).
- After adding a draw with `scrape_lotto.py`, the pipeline must be re-run: `python drawpick.py` then
  `python quickpick.py`, then `/lotto-verify`.
- `train_with_all_features.py` enables options the production configs deliberately leave off. Do not
  copy its settings into `ml_lotto/config.py` without measuring - several of them hand capacity back
  to the models.
