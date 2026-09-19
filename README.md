# Lotto ML System - Irish Lotto

A playful way to pick an Irish Lotto line (6 from 47, plus a bonus ball), backed by real draw
history, and a machine-learning sandbox built to learn how to code well with AI.

## Two projects, one data layer

**The website - pick your line for fun.** A dashboard for players who would rather build their own
line than take a random quick pick. It shows the facts behind past draws - which numbers are hot,
medium or cold, how odd and even numbers split, which balls were recently a bonus, how many numbers
of 32 or above a typical draw holds - and leaves the choice to you. It never promises a better
chance of winning: in a fair draw every line is equally likely. The aim is simply to make picking a
line more fun. Built in Streamlit today; a React version with spinning, game-like pickers is planned.

**The ML layer - a learning project.** Six models (logistic regression, random forest, XGBoost,
CatBoost and two auxiliary models) trained on the same history to generate picks. They are for my
own use, and their real purpose is the engineering: walk-forward training with no look-ahead,
train/serve parity checks, calibrated metrics, and an integer-programming line selector.

**`drawpick.py` feeds both.** It turns the draw history into ~24 JSON files that the website displays
and the models train on.

## The honest result

All six models score at chance - validation AUC 0.50-0.55. A label-permutation test confirms it:
retrained 20 times on shuffled results, no model beat its shuffled versions. That is the correct
answer for a fair lottery, and the project treats it as one. The one statistical signal found so far
is small: numbers drawn two or more times in the last five draws came up about 11% more often (p = 0.03, weak).

## How it is built

The project started over a year ago as vibe coding, with no real technique, and grew by trial and
error. It has since been rebuilt around the practices from Ed Donner's Udemy course
[AI Coder: Complete Claude Code & Coding Agents Course](https://www.udemy.com/course/ai-coder-from-vibe-coder-to-agentic-engineer/):

- **A `CLAUDE.md` in every substantial folder**, holding the rules that must stay true there - so an
  AI agent working in that folder starts from the invariants instead of rediscovering them.
- **`issue.md`**, one register of every known defect and planned improvement, with file:line
  evidence, severity and the fix history.
- **`review.md`**, the architecture overview and roadmap.
- **A verification skill** (`/lotto-verify`) that runs the tests, checks train/serve parity and
  validates every generated ticket after each change.
- **Evidence before change** - a decision rule fixed before an experiment runs, measured
  before/after on every fix, and no claim made without the data behind it.

## Quick start

```bash
python drawpick.py     # build the data from data/irish500.csv
python quickpick.py    # train the models, write lottery_picks.txt
streamlit run app.py   # open the website
```

`python scripts/scrape_lotto.py` adds new draws. Re-run `drawpick.py` after it.

## Layout

| Path | What |
|:--|:--|
| `lotto_analysis/`, `drawpick.py` | statistics over the draw history -> `data/*.json` |
| `view/`, `app.py` | the website (8 pages) |
| `ml_lotto/`, `quickpick.py` | features, models, line selection |
| `tests/` | the real tests - see `tests/CLAUDE.md` for which files they are |
| `docs/` | reference: metrics, features, models, JSON files, dashboard manual |

## Next

- React front end with game-like line pickers.
- Automated pipeline: scrape each draw, rebuild the data, refresh the site.
