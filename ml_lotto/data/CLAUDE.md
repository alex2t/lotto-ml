# ml_lotto/data/

`loader.py` (~1.1k lines) - the only place the ML layer reads `data/*.json`.

Loads and validates the artifacts `drawpick.py` wrote: draw history with bias ratios, HMC data,
odds, freshness, distribution stats, bonus analysis, and the seven `*_validated.json` files. Paths
come from `../config.py`, never hard-coded here.

## Rules

- **Validation is strict on purpose.** A missing key must raise, not default. Most defects found in
  this repo were `.get(key, 0)` fabricating a constant for a field that did not exist - a phantom
  column that trains and serves happily while carrying no signal.
- The ML layer reads **only** these JSON files, never `data/irish500.csv`. Adding a draw to the CSV
  changes nothing until `drawpick.py` re-runs.
- `quickpick.py` calls `validate_data_files()` and `validate_loaded_data()` before training. If you
  add an artifact, add it to both.

## After changing anything here

`python quickpick.py`, then `/lotto-verify`.
