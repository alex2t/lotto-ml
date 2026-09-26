# Open Issues — Irish Lotto ML System

**Maintained by:** Claude Opus 5
**Last updated:** 2026-09-26
**Scope:** the single record of outstanding defects.

Sections 1-5 are **open**: defects by severity, then improvements not yet started. Section 6 lists
improvements already done. Items carried from the retired code review keep
their original IDs (C-nn / N-n); items found later are numbered F-n, and an ID is never reused.
Appendix A is the resolved list. Appendix B keeps the full C-5 write-up for reference.

**Keeping this file true.** The Priority summary lists **open items only** — a resolved ID never
appears in it. When a defect is found: give it the next free F-n, add a row to the Priority summary,
and write a section with file:line evidence. When one is fixed: delete its summary row, renumber the
remaining sections, add it to the Appendix A table, and write up the root cause and the measured
effect. A fix is not finished until this file says so.

**Improvements are tracked the same way.** Planned work that is not a defect also gets the next
free F-n, a Priority summary row with severity `Improvement`, and its own section. When done, it
moves to section 6 (Improvements done). Nothing open lives only in a list or in `plan.md`.

---

## Priority summary

A new defect takes the next free `F-n`, a row in this table in severity order, and a section
with file:line evidence.

None open as of 2026-09-26.

F-37 was withdrawn on review, 2026-09-19: the `max()` calls it cited run over dicts filled in draw
order, so ties resolve the same way on every run. It is not reused.

---

## 3. Low severity defects

None open.

---

## 6. Improvements done

Kept for the record; each is complete and covered by tests.

- **2026-09-26 - F-75, Streamlit was public on the VPS, around the proxy.** The base
  `docker-compose.yml` publishes `streamlit-web` on `8501:8501` for the PC, and
  `docker-compose.prod.yml` never mentioned the service, so `docker compose up -d` on the VPS
  published it on `0.0.0.0:8501` - plain HTTP with none of Caddy's headers, reachable at
  `http://<vps-ip>:8501` while `vps.md` said nothing public pointed at it. Shown with
  `docker compose config`, which listed `streamlit-web ('0.0.0.0', '8501')` for both the
  two-file and the Hostinger deploy. Docker publishes ports through its own iptables rules, so a
  host firewall such as ufw does not close it. **Fixed**: the production overlay overrides the
  port to `127.0.0.1:8501:8501`; for the side-by-side week it is reached with
  `ssh -L 8501:127.0.0.1:8501 <vps>`. The PC's base file is unchanged (still `0.0.0.0:8501`).
  `tests/test_docker_stack.py::test_streamlit_is_not_public_on_the_vps` failed before and passes
  now; `vps.md` 3.4 adds the external `curl` on 8501 that must fail.

- **2026-09-26 - F-74, `vps.md`'s update procedure could not run after the first draw.** It
  said `git pull` then rebuild. On the VPS the receiver appends each draw to
  `data/irish500.csv` and the engine rewrites `data/*.json`, all tracked in git, so from the
  first rebuild the clone has local changes to files the next pull also changes, and git
  refuses the pull ("Your local changes to the following files would be overwritten"). Not
  reproduced on the server - it follows from git's rule and from which files the receiver
  writes. **Fixed** in `vps.md` section 5: `git checkout -- data/` before `git pull`, with why it
  loses nothing (n8n commits each draw to GitHub before it posts it, and the engine regenerates
  the artifacts from the pulled CSV on the next start), and never committing from the VPS.

- **2026-09-25 - F-72, the rebuild receiver took a known date as proof it had the draw.**
  `handle_draw()` decided a post was already in the file with `draw["date"] != newest` and
  never compared the numbers, so a post for 2026-09-21 with `15,24,29,30,3,38` (the row holds
  31) was answered `200 already had it` - the same as the true draw - and n8n, which counts that
  as success, would have sent no failure email for a misread draw. Shown on a copy of `data/`
  before the fix. **Fixed** in `rebuild_webhook.py`: when the date is the newest row's,
  `row_numbers()` reads that row and a difference in any main number or the bonus answers
  `409 {"state": "conflict", "in_csv": ..., "posted": ...}`; nothing is written and nothing is
  rebuilt, stale artifacts included, since which side is right is not known. The same draw in
  another order is still `already had it`. `tests/test_rebuild_webhook.py`
  `test_a_known_date_with_other_numbers_is_a_conflict_not_a_success` (a main number, the bonus)
  failed before the fix with 200 and passes after; `test_a_known_draw_in_another_order_is_still_the_same_draw`
  holds the other side. 35 receiver tests pass.

- **2026-09-25 - F-73, the example secrets file had no line for the rebuild secret.** The
  receiver reads `REBUILD_SECRET` raw from `secrets.env` and refuses to start below 16
  characters, but `secrets.env.example` listed only the admin, session and OpenRouter values.
  **Fixed**: the example now carries `REBUILD_SECRET=` with its generator command.
  `tests/test_docker_stack.py::test_the_rebuild_secret_comes_from_secrets_env_and_the_example_lists_it`
  failed on the missing line and passes now; it also holds that the secret reaches
  `rebuild-receiver` only through the raw `env_file`, never `environment:`.

- **2026-09-25 - F-70, the scenario table's caption described a statistic it does not count.**
  The Statistics tab captioned `lotto_odds_results.json` `scenarios` "How often a number that came
  up N times in a window came up again in the next draw". `drawpick.py:350-362` writes something
  else: for each scenario in `lotto_analysis/config/config.py` `SCENARIOS` (2 times in 5 draws, 3 in
  6, 4 in 10, 8 in 25), the share of windows of consecutive draws, all seven balls counted, in
  which some number came up exactly that many times, each number's windows kept from overlapping
  (`pattern_analyzer.process_pattern_analysis`). Nothing in it looks at the next draw - the 64.5%
  for "2 in 5" would be an absurd repeat rate for one draw. **Fixed** while rebuilding the tab as
  collapsible cards: the card is "Repeats inside a window", its rows read "2 times in 5 draws", and
  its explanation says what a window is. `frontend/test/statistics.test.ts` asserts the row label
  and that its share equals `hit_count / total_windows`.

- **2026-09-24 - F-68, the chat panel (`nextStep/chat.md`).** A panel on every page answers
  questions about what the site shows, through four layers: 57 hand-written answers
  (`frontend/lib/chat/prepared.ts`), twelve data intents reading `lib/data/` (`intents.ts`), a
  response cache keyed on the artifacts' mtime (`cache.ts`), and last, `openai/gpt-oss-120b` on
  Cerebras through OpenRouter (`openrouter.ts`), handed the page's fact sheet (`context.ts`) and
  never asked to compute. All four spending limits of chat.md 5 are in `budget.ts` and the route;
  every model answer passes the `ADVICE` scan (`guard.ts`) before it is shown, which is why it
  does not stream. The `ADVICE` list moved into one file, `frontend/lib/advice.json`, read by the
  source scan, the rendered scan, the system prompt and the guard. Without `OPENROUTER_API_KEY`
  the model layer is off and nothing else changes.

  Covered by `frontend/test/chat-layers.test.ts` (every prepared entry answers its own question,
  route weighting, each intent against its reader), `frontend/test/chat-model.test.ts` (each
  limit fired once, the guard once per banned word, cache and mtime invalidation, the key-less
  path, no network), `frontend/test/e2e/chat.spec.ts` (desktop and mobile), and
  `tests/test_docker_stack.py::test_the_openrouter_key_comes_from_secrets_env_not_interpolation`.
  The e2e run caught that the nav's new button pushed a 412px phone's page to 443px; the nav is
  tighter below the `sm` breakpoint.

- **2026-09-21 - F-63, a six-number line was scored against a seven-ball spread.**
  `lotto_odds_results.json` `draw_range` bins `max(numbers) - min(numbers)` over **all seven**
  balls: the 19 Sep 2026 draw records 42 there, while its six main numbers span 34. The Phase 4
  shape card computed a line's spread over its six numbers and looked the band up in that
  distribution, so a wide line was told it was more ordinary than it is - the seven-ball
  distribution puts 31.1% of draws in 40-45, the six-ball one 23.5%. The Statistics chart had the
  same figures under the caption "the spread of the six main numbers".

  This is F-59's shape a second time: a six-ball value read against a seven-ball distribution. It
  did not announce itself the way F-59 did, because the band keys are shared - it returned a
  plausible wrong number instead of nothing.

  **Found by a test rather than by reading.** `frontend/test/ranged.test.ts` recounts every
  distribution from the draw history and asserts it matches the artifact over the whole history.
  It failed on the spread by 1.41 percentage points, which is what sent me to the analyzer.

  **Fixed** the same way as F-59, upstream: `hmc_analyzer.py` already computed the six-ball metrics
  and was discarding the range, so it now stores `draw_range_6` per draw,
  `generate_draw_range_analysis` takes which key to bin, and `drawpick.py` writes
  `lotto_odds_results.json` `draw_range_6` beside `draw_range`. `spreadBandShares()` reads it.
  Covered by `tests/test_number_pairs.py::test_the_six_ball_spread_is_written_beside_the_seven_ball_one`,
  which asserts adding a seventh ball can only widen a span, and by the agreement test that found it.

- **2026-09-21 - F-59 and F-60, the six-ball hot/medium/cold distribution.**
  `validate_hmc_pattern` counted the player's **six** numbers into a pattern like `3-0-3` and looked
  it up in `lotto_odds_results.json` `hmc`, which is over **seven** balls: every key in it sums to 7.
  A six-ball key sums to 6, so the lookup never matched, `.get('percentage', 0)` supplied the
  default and the "never observed" branch ran for **every possible line**, taking 80 of 100 points
  off each one. Measured before the fix: `3-0-3`, `4-0-2`, `6-0-0` and `2-3-1` all reported
  `Very rare pattern (never observed)`, score 20/100.

  **Fixed upstream, which closed F-60 with it.** `hmc_analyzer.py` already had each draw's pre-draw
  categories in its loop, so it now counts the main-six pattern beside the seven-ball one and
  `drawpick.py` writes it as `lotto_odds_results.json` `hmc_6`. The Prediction Validator reads
  `odds_data['hmc_6']` - no default - and `frontend/lib/data/hmc.ts` reads the same block instead of
  aggregating the distribution itself, which is what F-60 was about.

  **Measured after.** The four lines above now report 4.81%, 5.61%, 0.80% and 5.61% and score 100,
  100, 60, 100 - the check distinguishes lines instead of answering the same thing every time. The
  artifact's counts match what the front end had been computing independently from the draw history
  (`4-1-1` 13.03%, `2-2-2` 11.82%, `3-1-2` 11.42%): two implementations agreeing.

  **One test changed, deliberately.**
  `test_validator_verdict_describes_typicality_not_a_chance_of_winning` required the line
  `1, 2, 3, 4, 5, 6` to score under 60. That threshold only held while every line was losing 80
  points, so it was calibrated on the defect. It is now
  `test_validator_separates_a_typical_line_from_an_extreme_one`, asserting the ordering and the
  failing checks rather than a number: the typical line scores 100, the run of six scores 70, and
  the two checks that object to it are sum and spread. The wording assertions - no advice, the
  equal-chance sentence, the verdict vocabulary - are unchanged and still run on both lines.
  `tests/test_site_wording.py` also gained
  `test_hmc_check_compares_a_line_with_the_six_ball_distribution`, which asserts the two key sets
  sum to 6 and 7 and that no line is told "never observed".

- **2026-09-21 - F-61, the engine could call its own output stale.**
  `test_verify_artifacts_accepts_files_written_by_this_run` failed twice in full-suite runs on a
  loaded machine and passed on its own, which looked like flakiness. It was not.

  **Root cause, measured.** `verify_artifacts` rejected an artifact whose `st_mtime < run_started`.
  Both are doubles built from the same clock but rounded differently, so a file written immediately
  after `run_started` can report an mtime **2.384185791015625e-07 seconds earlier** - exactly
  2^-22, a double-rounding artefact. Over 6000 write-and-compare cycles this happened 534 times
  (~9%); over 300 cycles on an idle machine it happened 0 times, which is why the first
  investigation found nothing and nothing was changed on that guess.

  In production the gap is seconds to minutes, so a real run was never affected; the exposure was
  the boundary itself, where a file written in the same clock tick as the start of the run could be
  reported STALE and exit the engine non-zero.

  **Fixed** with `MTIME_TOLERANCE_SECONDS = 1.0` in `drawpick.py`: a file is stale only if its
  mtime is more than a second before the run started. An artifact left from an earlier run is hours
  old, so the check still does its job (F-43). Covered by
  `test_verify_artifacts_accepts_a_file_written_in_the_same_clock_tick`, which asserts the exact
  2.4e-7 case, and by the earlier-run test, now offset clear of the tolerance.

- **2026-09-21 - F-62, the site could not be built without the artifacts.**
  `frontend/app/layout.tsx` read the draw history to put "N draws on file, back to X" in the footer.
  A root layout is used by every route including the error pages Next prerenders at build time, and
  `data/` is a runtime mount that does not exist while the image builds, so
  `docker compose build nextjs-web` failed: `Error occurred prerendering page "/_not-found"`,
  `ENOENT: no such file or directory, stat '/data/lotto_draw_history.json'`. It passed locally only
  because a developer's `../data` is there.

  **Fixed** by making the layout read nothing: the footer carries the equal-chance sentence, which is
  a constant, and the draw count moved to the home page, which has the history anyway. Covered by
  `tests/test_docker_stack.py::test_the_site_builds_without_the_artifacts` and proved by building
  with `DATA_DIR` pointed at a directory that does not exist.

- **2026-09-21 - F-58, the admin login could not work in Docker.**
  `docker-compose.yml` passed the account through `environment: ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH:-}`.
  A bcrypt hash is `$2b$12$<22-char salt><31-char hash>`, and compose expands `$name` inside an
  interpolated value. The `$<salt>` run was read as a variable name and expanded to nothing, so a
  hash `$2b$12$SALT/HASH` reached the container as `$2b$12/HASH` - the cost marker and the whole
  salt gone - and `bcrypt.compare` returned false for the correct password. (No real hash is quoted
  here: it is the hash of a live password, and an offline attack on it is exactly what a public
  repository would enable.) Every login answered 401 and the data bundle was unreachable from the
  container - found by the owner, who had no login button and no download.

  **Two faults, one symptom.** There was also no `.env` at all (the container had only been started
  with inline shell variables), and `.env` was in neither `.gitignore` nor `.dockerignore`, so the
  first `git add -A` would have committed the admin hash and the session secret.

  **Fixed.** The service takes the file with
  `env_file: [{path: secrets.env, required: false, format: raw}]` - `format: raw` disables
  interpolation, `required: false` keeps the public site starting without an admin account, since one
  account's failure must never take the site down.

  **The file is `secrets.env`, not `.env`** (refined the same day, while building Phase 4). Compose
  also reads `.env` for its own variable substitution in the compose file, so a bcrypt hash sitting
  there printed `WARNING: The "xoaC9..." variable is not set` on every `docker compose` command -
  the same expansion, one layer up. `.env` now holds only `UID`/`GID`; `secrets.env` holds the
  account. Both are gitignored and dockerignored, and `.env.example` and `secrets.env.example`
  document each.

  **Verified** in the running container: the hash arrives byte-identical to the file, login returns a
  131-character session cookie, the download returns 200 with 30 entries, and a wrong password still
  returns 401. `tests/test_docker_stack.py` gained
  `test_admin_secrets_are_passed_without_interpolation` and `test_the_env_file_is_not_committed_or_shipped`.

- **2026-09-21 - F-57, build and run the Next.js image.**
  Phase 3 wrote `Dockerfile.web`, the `nextjs-web` service and `docker-compose.dev.yml` on a day
  Docker Desktop was down, so the image had never been built. `tests/test_docker_stack.py` covers
  the wiring only - a file-copy or permission fault inside the image would have surfaced first on
  the VPS in Phase 5. Built and exercised on Docker 29.8.0:

  - `docker compose build nextjs-web` succeeds; the image is 385 MB and `/app/data` inside it is
    empty, so no artifact is baked in.
  - The container runs as `uid=1000(node)`, not root, and a write to `/app/data` is refused -
    `Read-only file system`.
  - Served from the container: the home page, `/api/schedule`, `/api/draws`, a login (401 on a wrong
    password) and the zip download - 30 entries, `irish500.csv` included, the 4.4 MB draw history
    among them. `/api/download/data` is 401 without a session.
  - `docker compose up -d nextjs-web` with no `--no-deps` ran the engine first and started the site
    only after it exited 0, which is what F-45's `service_completed_successfully` is for. The
    container's rebuild changed three lines of `data/` against the host's run - two `generated_date`
    and one `analysis_date` - so F-46's rounding holds across platforms; the artifacts were restored
    with `git checkout -- data/`.
  - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up nextjs-web` builds the `deps`
    stage and runs `next dev` against the same read-only artifacts.

- **2026-09-19 - F-24, delete the ML code for features no model uses.**
  After F-21 no model used any C-5 full-history feature, but every run still built them for all 47
  numbers and the engine copied them into training rows as static values. Deleted from `ml_lotto/`
  only: `features/long_term_patterns.py`, `features/window_saturation.py`, their wiring in
  `extractor.py` and `quickpick.py`, the engine's `static_feat` lines, the `window_saturation_penalty`
  copy in `bonus_to_main_features.py`, five loader functions nothing else called
  (`load_range_spread_analysis`, `load_odd_even_analysis`, `load_sum_contribution_analysis`,
  `load_long_term_patterns`, the deprecated `load_statistics_analysis`) and the
  `LONG_TERM_PATTERN_WEIGHTS` / `LONG_TERM_PATTERNS_JSON` constants. The engine now produces 65 keys
  per number, down from 73; every name the six configs request is still produced.

  **The website is untouched by design.** `drawpick.py`, `data/*.json`, `view/` and `app.py` are
  unchanged: four of the six source files are read by dashboard pages, and the other two are draw
  facts the Next.js site may show. `quickpick.py` still loads the three `*_validated.json` files for
  its scipy summary.

  **Measured.** `lottery_picks.txt` identical to the committed version; all six models +0.0000 on
  val AUC and Top-7 against the committed `model_comparison.csv`. All 8 dashboard pages rendered
  headless with Streamlit `AppTest`: no exceptions, no error boxes, and identical element counts
  before and after. 135 real tests pass. The legacy print-script
  `tests/test_unified_bonus_to_main_features.py` (now `demos/demo_unified_bonus_to_main_features.py`,
  C-17b) asserted `window_saturation_penalty` was present;
  it now asserts the feature is *not* carried through when the input contains it, with its counts
  corrected (12 -> 11 base, 22 -> 21).

  **Note.** A baseline taken during this work was spoiled: the then print-script
  `tests/test_train_with_all_features.py` overwrote `model_metrics/model_comparison.csv` with mock
  models. The comparison above is against the committed file. Fixed in C-17b - the script is now
  `demos/demo_train_with_all_features.py` and writes to a temp directory.

- **2026-09-19 - F-19, steer lines away from popular combinations.**
  Expected *payout* is not uniform even when probability is: birthday numbers (<=31), calendar
  patterns and arithmetic sequences are heavily played and share prizes more often. Steering toward
  numbers >=32 does not change the chance of winning; it lowers the chance of sharing a prize. This
  repo has no ticket-sales data, so that benefit cannot be measured here. (An earlier note said the
  sum and odd rules push toward popular combinations; checked 2026-09-19, they barely steer - they
  pass 95% and 81% of all lines.)

  **Done 2026-09-19 - the data, on the dashboard.** `drawpick.py` Phase 6
  (`distribution_analyzer.analyze_high_number_distribution`) writes, into
  `lotto_distribution_stats.json`, how many draws had 0-6 main numbers >= 32, with a fair draw's share
  alongside. The Statistics page shows the breakdown on its own; the Prediction Validator also shows it
  for any line the user types in, information only.
  Over the 497 analysed draws:

  | Numbers >= 32 | Draws | Share | Fair draw |
  |--:|--:|--:|--:|
  | 0 | 32 | 6.44% | 6.86% |
  | 1 | 112 | 22.54% | 25.32% |
  | 2 | 182 | 36.62% | 35.16% |
  | 3 | 130 | 26.16% | 23.44% |
  | 4 | 35 | 7.04% | 7.88% |
  | 5 | 5 | 1.01% | 1.26% |
  | 6 | 1 | 0.20% | 0.07% |

  Draws follow the fair-draw shares; 2 is the most common count and 3+ happens in 34%.

  **Tried and reverted: "at least 3 numbers >= 32" in selection.** It worked (all three lines met it)
  but skewed the lines: it rules out 67% of all lines and squeezes half of each into a 16-number range,
  which raises the share of lines with a consecutive pair from 53% to 55% and the share whose pair sits
  in 32-47 from 20% to 44% - all three generated lines had one (42-43, 39-40, 32-33). "At least 2"
  leaves consecutive pairs at their natural rate (51%) and still excludes the most birthday-heavy lines
  (0-1 high numbers).

  **Decided 2026-09-19, from the dashboard data: a per-model floor.** `min_high_numbers` in each model
  config - Models 1 and 2: at least 2 numbers >= 32 (71% of past draws had 2+); Model 3: no floor, its
  probabilities decide. A floor, not a target: a model may pick more. One constraint in
  `ilp_selection.solve_line` over the whole ticket; not in `validate_line`, since it differs per model.

  Picks: Model 1 unchanged `[5, 13, 15, 24, 42, 43]` (already 2); Model 2 `[6, 8, 9, 23, 31, 39]` ->
  `[6, 9, 23, 31, 38, 39]` (8 -> 38); Model 3 `[7, 22, 32, 38, 40, 47]` -> `[10, 19, 22, 32, 40, 47]`,
  moved only because Model 2 now holds 38 (it still has 3 high numbers unforced). Lines disjoint.
  Tests (`test_selection_invariants.py`): the floor is enforced in a world whose scores favour 1-31,
  is a floor not a target, and counts pre-assigned numbers; removing the constraint fails two.

- **2026-09-19 - F-18, is the freshness pattern worth enforcing? Kept; change freeze lifted.**
  Enforcing a bin pattern can only help if a number's freshness bin changes its chance of being
  drawn, so that was tested directly instead of the two-line backtest first proposed (60 draws, noise
  ~ +/- 0.27 matches - it could only have seen a huge effect). `analysis/freshness_hit_rate.py`: for
  draws 5..496, each number's bin as it stood before the draw - the engine's `min(recent_4, 2)`,
  identical to the serving `current_freshness_bin` selection enforces (`last_4`, C_max 2) - against
  whether it was a main ball. Rule fixed before running: chi-square p < 0.05 keeps the mechanism,
  otherwise its enforcement is deleted.

  | Bin | Exposures | Hits | Hit rate | Expected hits |
  |--:|--:|--:|--:|--:|
  | 0 | 11,714 | 1,499 | 0.1280 | 1,495.4 |
  | 1 | 8,526 | 1,045 | 0.1226 | 1,088.4 |
  | 2 | 2,884 | 408 | 0.1415 | 368.2 |

  chi2 = 6.94, dof 2, **p = 0.031 - keep**. The excess is in bin 2 (drawn 2+ times in the last 5
  draws): +11% over its share. Checked not to be a data artifact: 497 draws on 497 distinct dates, no
  duplicated draw, consecutive-draw overlaps match a fair draw (3 shared numbers 13 times vs 9.8
  expected, 4+ never).

  **Read it with care.** p = 0.031 is weak - one test in twenty passes at that level by chance - and
  the effect is small: one bin-2 number per line is worth about +0.015 expected matches. The rule said
  keep, so the mechanism stays and the freeze is lifted by its own condition. Re-run the script as
  draws accumulate; it takes seconds. If p rises above 0.05, delete the enforcement - the decision was
  made on this evidence, and it should follow the evidence.
- **2026-09-18 - F-17, label-permutation check: no model has an edge.**
  `ml_lotto/models/permutation_check.py`, run as `python quickpick.py --permutation-check 20`. Each
  main model is trained once on real labels and 20 times with the training labels shuffled within
  each draw (hit counts kept, number-outcome link destroyed), through the exact production pipeline
  - features, selection, tuning, calibration - and every run is scored on the real validation
  labels. The rule was fixed before running: an edge needs p < 0.05, i.e. beating all 20 shuffled
  runs.

  | Model | Real val AUC | Shuffled: mean +/- sd (range) | Shuffled >= real | p |
  |:--|--:|:--|--:|--:|
  | Momentum Specialist | 0.5011 | 0.4967 +/- 0.0151 (0.454-0.522) | 9 / 20 | 0.476 |
  | Jackpot Optimizer | 0.5257 | 0.5066 +/- 0.0163 (0.483-0.551) | 2 / 20 | 0.143 |
  | Complexity Explorer | 0.5074 | 0.4891 +/- 0.0132 (0.471-0.532) | 2 / 20 | 0.143 |
  | Conservative Pool Generator | 0.5118 | 0.4928 +/- 0.0119 (0.470-0.516) | 1 / 20 | 0.095 |

  No model passes. Model 1 sits mid-null; the best, Model 4, is beaten by 1 of 20 shuffled runs. The
  shuffled sd of 0.012-0.016 independently confirms the +/- 0.031 noise floor. Four real AUCs above
  their null means is not evidence either: the models share one validation window, so the four are
  not independent draws. The answer to "is there any edge?" is no, as expected for a fair draw -
  further model tuning has nothing to find. To support this, `trainer.build_main_datasets()` was
  extracted and `train_model(output_dir=None)` writes no artifacts. Tests:
  `tests/test_permutation_check.py`.
- **2026-09-18 - Wheel the Model 4 pool.** `ml_lotto/prediction/wheel.py` covers every 3-subset of the
  pool's top 8 with 4 lines (C(8,6,3) = 4): 3+ winners in the top 8 guarantees a match-3, which
  happens in ~5.3% of draws. Written to `lottery_picks.txt` as `Wheel Line 1-4`, guarded by
  `tests/test_wheel.py`. A guarantee over the whole 20 does not fit a 4-8 line budget - even "all 6
  winners in the pool" needs more than 8 lines and fires in 0.36% of draws. It is not an edge and
  does not reduce blanks: 4 unrelated lines catch a match-3 in ~7.2% of draws.
- **2026-09-18 - MILP selection**. `ml_lotto/prediction/ilp_selection.py` replaces
  greedy picking and the filter repair pass with `scipy.optimize.milp`: HMC quotas, the reachable
  freshness target and the ticket rules are constraints, so a line meets all of them or the solver
  raises. Not a prediction change - it removed a defect surface (F-14).

---

## Reality check

All six models are measured out-of-sample on the same 60-draw hold-out, and all six sit at chance -
validation AUC close to 0.50, every difference inside the 2 SE noise floor (~0.031 AUC, ~0.227 Top-7
AvgCaught). That is the correct answer for a fair draw. The worst train/validation gap was once 0.383
(C-15b); the alarm is ~0.1. Figures are in `model_metrics/model_comparison.csv`, with a dated example
in `docs/metrics.md` - they are not repeated here, so a new draw never makes this file stale.

Read the scoreboard in this order: AUC, PR-AUC lift and per-draw Top-K lift first, since they are
threshold-free; the precision / recall / F1 columns last, because maximising F1 at a ~15% positive
rate parks the threshold near the base rate by construction.

No defect is open. The Phase 1 Docker stack and the artifacts it writes were reviewed on
2026-09-20 (F-43 to F-47, all resolved).

---

## Appendix A — Resolved

Every item below was fixed and verified against the live pipeline.

| ID | Issue | Fixed in |
|:--|:--|:--|
| F-71 | The first e2e tests of a full run timed out now and then on the owner's PC; closed as a test-only effect of browser load, not a site defect | nothing changed - see the write-up |
| F-67 | A parity test required every drawn ball to move `recent_4` or `days_since_last`; a bonus ball drawn two days after its last appearance moves neither, so the suite failed on the current data | `tests/test_walk_forward_parity.py` |
| F-69 | The freshness bin, pattern and top-pattern tests measured against a uniform spread, so `lotto_freshness_patterns_validated.json` reported "freshness bias detected" (p 1.9e-160) for what a fair draw produces | `lotto_analysis/analyzers/freshness_pattern_analyzer.py`, `tests/test_freshness_fair_draw.py` |
| F-75 | Streamlit was published on the VPS at `0.0.0.0:8501`, plain HTTP around the proxy | `docker-compose.prod.yml`, `tests/test_docker_stack.py`, `nextStep/vps.md` 3.4 |
| F-74 | `vps.md` updated the server with a bare `git pull`, which git refuses once the receiver has written `data/` | `nextStep/vps.md` section 5 |
| F-73 | `secrets.env.example` had no `REBUILD_SECRET` line, so a `secrets.env` made from it gave a receiver that exited at start | `secrets.env.example`, `tests/test_docker_stack.py` |
| F-72 | The rebuild receiver matched a posted draw by date alone, answering `200 already had it` to a known date with other numbers | `rebuild_webhook.py`, `tests/test_rebuild_webhook.py` |
| F-70 | The Statistics tab captioned the scenario table "came up again in the next draw"; it counts N-draw windows in which some number came up T times | `frontend/lib/guide/statistics.ts`, `frontend/lib/data/statistics.ts`, `frontend/test/statistics.test.ts` |
| F-66 | lottery.ie heads the most recent draw `aria-label="Last draw, ..."` and only the older ones `"Draw, ..."`, so both parsers skipped exactly the draw being scraped: the n8n workflow emailed `only the archive has 2026-09-21` while the row was on both pages, and the Python scraper never cross-checked the newest draw | `nextStep/n8n.md`, `scripts/scrape_lotto.py`, `tests/test_scraper_sources.py`. One source is now `one_source`, which takes the same path as `ok` - same row, same CSV contract check, same commit - and does not retry, since a late site and a blind parser are indistinguishable from inside the node. `verified: false`, the subject line and the commit message are what mark a row nothing cross-checked |
| F-65 | The receiver decoded `drawpick.py`'s log with the locale codec, so the engine's emoji killed the reader thread on Windows and a rebuild that had succeeded was reported as a crash | `rebuild_webhook.py`, `tests/test_rebuild_webhook.py` |
| F-64 | The rebuild receiver ran `drawpick.py` on whatever CSV was already on the VPS, and nothing put the new draw there - every webhook regenerated the same artifacts from unchanged input, and a retried n8n execution paid for a second pointless run | `rebuild_webhook.py`, `tests/test_rebuild_webhook.py`, `nextStep/lottodraw.md`, `nextStep/n8n.md`, `nextStep/vps.md` |
| F-63 | A six-number line's spread was compared with a seven-ball distribution, overstating how ordinary a wide line is | `lotto_analysis/analyzers/hmc_analyzer.py`, `lotto_analysis/utils/output_generator.py`, `drawpick.py`, `frontend/lib/scoring/line.ts` |
| F-59 | A six-ball hot/medium/cold pattern was looked up in a seven-ball distribution, so every line was told its pattern had never been observed | `lotto_analysis/analyzers/hmc_analyzer.py`, `drawpick.py`, `view/pages/prediction_validator.py` |
| F-60 | The six-ball pattern distribution was aggregated in the front end instead of written by the engine | `frontend/lib/data/hmc.ts` |
| F-61 | `verify_artifacts` could call the engine's own fresh artifact stale, over a 2.4e-7 second float rounding | `drawpick.py`, `tests/test_pipeline_completeness.py` |
| F-62 | The root layout read an artifact, so the image build failed prerendering `/_not-found` with data/ absent | `frontend/app/layout.tsx`, `components/layout/Footer.tsx` |
| F-58 | Compose interpolated the `$` in the bcrypt hash, so the admin login failed with 401 in every container | `docker-compose.yml`, `.gitignore`, `.dockerignore` |
| F-57 | The Next.js image and its compose service existed only on paper - never built, never started | `Dockerfile.web`, `docker-compose.yml`, `docker-compose.dev.yml` |
| F-56 | n8n.md 3.6 tested the scraped date for string equality with the CSV's top row, so a date that was older but already present was reported as new - a duplicate row inserted out of order | `nextStep/n8n.md` 3.6 |
| F-55 | n8n.md 3.6 read the current CSV with an unguarded `split` chain, so a GitHub 404 threw and lost a draw that had passed every validation | `nextStep/n8n.md` 3.6 |
| F-54 | n8n.md 3.5 capped retries with a counter in workflow static data that never reset, so after three lifetime attempts the workflow would give up on every future draw silently | `nextStep/n8n.md` 3.5 |
| F-53 | n8n.md 3.4 downgraded a draw rejected by `buildDraw()` to `not_published`, making a malformed published result indistinguishable from no result | `nextStep/n8n.md` 3.4 |
| F-52 | n8n.md 3.4 computed `httpErrors` and never routed on it, so a dead fetch was reported as `not_published` and the email blamed the lottery site | `nextStep/n8n.md` 3.4 |
| F-51 | n8n.md 3.4 claimed the Code node never throws but had no `try`/`catch`; a thrown Code node ends the execution with no email at all | `nextStep/n8n.md` 3.4 |
| F-50 | n8n.md monitoring check 5 gated Phase 2B on parser notes about rejected Plus rows, which neither page produces - the archive table carries the main draw only | `nextStep/n8n.md` 6 |
| F-49 | n8n.md wired both HTTP nodes into one Code node input, which n8n runs once per incoming branch - two executions and two emails per draw | `nextStep/n8n.md` 3 |
| F-48 | n8n.md specified error output on both HTTP nodes while its Code node read the failed item from the main output, so a fetch failure would have thrown instead of emailing | `nextStep/n8n.md` 3.2 |
| F-46 | Artifact floats differed between platforms although the engine versions were pinned | `lotto_analysis/utils/serialization.py`, 14 `json.dump` sites |
| F-47 | A failed data load printed an error and exited 0, so the stack started on stale data | `drawpick.py` |
| F-45 | Docker plumbing: junk files from `echo >>`, no service ordering, unowned bind mount | `scripts/docker_*.bat`, `docker-compose.yml`, both Dockerfiles, `.dockerignore` |
| F-44 | Every artifact rewritten CRLF -> LF on each host/container alternation, and unpinned engine dependencies | `.gitattributes`, `requirements-engine.txt` |
| F-43 | The data engine swallowed a failed phase and reported SUCCESS on stale artifacts | `requirements-engine.txt`, `hmc_success_analyzer.py`, `drawpick.py` |
| C-1 | SMOTE destroyed calibration (2 distinct probabilities across 47 numbers) | `config.py`, `trainer.py` |
| C-2 | Tie-breaks decided picks, in opposite directions in two modules | `constraints.py`, `pool_generator.py`, `selection.py`, `bonus_predictor.py` |
| C-3 | Walk-forward windows disagreed with the serving JSON | `walk_forward.py`, `drawpick.py` |
| C-4 | Eight serving features frozen at draw #100 | `rolling_stats.py`, `quickpick.py` |
| C-5 | Full-history constant features in the training matrix | `config.py`, `trainer.py` (Appendix B) |
| C-6 | `days_since_last` moved with wall-clock time | `extractor.py` |
| C-7 | Sum and range filters advertised but not implemented | `filters.py` |
| C-8 | Bonus ball could duplicate a main number | `quickpick.py` |
| C-9 | Soft diversity penalty disabled while the hard lockout stayed | `config.py`, `selection.py` |
| C-10 | No validation set for the main models | `config.py` |
| C-11 | `pick_from_hmc_pool` returned 1 number for a request of 0 | `selection.py` |
| C-12 | Safety top-up could duplicate a pre-assigned number | `selection.py` |
| C-13 | Streamlit autofill inert; CSV assumed newest-first | `post_draw_analysis.py` |
| C-14 | Scraper had no fallback source and accepted any game sharing the draw date | `scrape_lotto.py` |
| C-15a | Feature engine rebuilt 5x per run; O(N^2) gap-list memory | `walk_forward.py`, `trainer.py`, `bonus_trainer.py`, `bonus_to_main_trainer.py`, `quickpick.py` |
| F-42 | Bonus-to-Main predictor returned a bare `[]` where callers unpack a 2-tuple | `bonus_to_main_predictor.py` |
| F-39 | `validate_line` counted odd balls over 7 numbers while sum and span used the main 6 | `filters.py` |
| F-41 | Bonus-to-Main selected `category`, a string every row turned into a constant 0.0 | `config.py`, `bonus_to_main_features.py` |
| F-36 | A bonus ball repeated inside the 10-draw window was counted from its oldest appearance | `bonus_window.py` |
| F-38 | Odd/even affinity tested each number against 0.5 and validated all 24 odd numbers; overall test expected 50/50 | `odd_even_analyzer.py`, `statistics.py` |
| F-35 | Post Draw Analysis parsed `data/irish500.csv` itself for the latest draw | `post_draw_analysis.py` |
| F-40 | Bonus-to-Main model was served a dict built from the extractor and JSON profiles, not the engine rows it was trained on | `bonus_to_main_trainer.py`, `bonus_to_main_predictor.py`, `bonus_to_main_features.py`, `bonus_window.py`, `quickpick.py` |
| F-34 | Main models were served the extractor's row, not the row they were trained on: gap statistics, `freshness_bin` interactions and `has_consecutive_partner` differed | `walk_forward.py`, `quickpick.py` |
| F-33 | A draw's recent-bonus list ends with its own bonus; three bonus statistics read it as the pre-draw window | `bonus_analyzer.py`, `draw_history.py` |
| F-32 | Bonus-to-main transition rate divided by bonus appearances with no 10-draw window | `bonus_to_main_analyzer.py` |
| F-29 | Sum alerts used hard-coded mean/std from a key that never existed; the volatility alert could never fire | `anomaly_detector.py`, `pattern_comparison.py`, `prediction_validator.py` |
| F-31 | The "significant trend" flag ran Kendall's tau on a smoothed rolling series and flagged 61% of numbers on fair draws | `advanced_pattern_analyzer.py` |
| F-30 | Number Insights graded numbers STRONG PICK / AVOID and rewarded "overdue"; bonus balls were called likely to come up, from a 10/47 baseline | `number_insights.py`, `draw_history.py`, `prediction_validator.py`, `bonus_to_main_analyzer.py`, `generate_bonus_to_main_json.py` |
| F-28 | Pattern Comparison, Trigger Periods, the anomaly alerts and the manual graded lines strong / weak / risky and quoted false frequencies | `pattern_comparison.py`, `trigger_analysis.py`, `anomaly_detector.py`, `prediction_validator.py`, `statistics.py`, `dashboard-manual.md` |
| F-26 | Prediction Validator told players "Play with confidence" and "Regenerate numbers" | `prediction_validator.py` |
| F-27 | Pattern Comparison classified past draws with today's hot/medium/cold | `pattern_comparison.py` |
| F-25 | Pattern Comparison read `main_numbers`, a key the draw history never had - it never found a match | `hmc_analyzer.py`, `pattern_comparison.py`, `anomaly_detector.py` |
| F-7 | Two `analysis/` scripts read `last_14`, a window that has never existed | `bonus_to_main_analysis.py`, `feature_stability_scorer.py` |
| C-17b | Eleven feature-discovery print-scripts sat in `tests/`; one was broken, one overwrote the real metrics | moves them to `demos/`; `pytest.ini` |
| F-21 | Bonus-to-Main trained on a C-5 full-history feature computed from last-draw categories | `config.py`, `window_saturation.py`, `bonus_to_main_trainer.py` |
| C-6b | Training dated rows at their own draw; serving dated them at the last draw | `extractor.py`, `walk_forward.py`, `quickpick.py` |
| F-22 | Next-draw date ignored the 2026 move to Mon/Wed/Sat draws | `walk_forward.py` |
| F-23 | `days_since_bonus` was served from the wall clock | `timing.py`, `quickpick.py` |
| F-6 | Ensemble code was unreachable, and each entry point was broken | deletes `ensemble.py`, `ensemble_predict.py`, `analysis/ensemble.py`; `config.py`, `quickpick.py` |
| F-20 | Bonus prediction 2 claimed category diversity it never applied | `bonus_predictor.py` |
| F-5 | A too-small bonus pool crashed with a bare IndexError; the registered divide-by-zero was unreachable | `bonus_predictor.py` |
| F-16 | Diversity penalty applied twice; the configured percentage barely mattered | `ilp_selection.py`, `predictor.py` (deletes `penalties.py`) |
| F-15 | Config feature names the serving path never produces were dropped silently | `config.py`, `extractor.py` |
| C-15b | Tree models memorised the training set (train/val AUC gap 0.383) | `config.py`, `hyperparameter_tuning.py` |
| C-16 | Non-deterministic feature column order | `extractor.py` |
| F-1 | Freshness target sized for 7 balls while a line has 6 slots | `freshness_analyzer_7_numbers.py`, `constraints.py`, `drawpick.py` |
| F-2 | Bonus and bonus-to-main models had no validation split | `quickpick.py`, `bonus_trainer.py`, `bonus_to_main_trainer.py`, `trainer.py` |
| F-3 | Decision threshold tuned and scored on the same validation rows | `model_metrics.py` |
| F-4 | Probability array built conditionally while every consumer indexed it positionally | `predictor.py` |
| F-10 | Dead look-ahead guard printed a false reassurance; contradictory split constant | `hmc_analyzer.py`, `lotto_analysis/config/config.py` |
| F-13 | Freshness target could be unreachable for a model's HMC ratio, and missed it silently | `constraints.py`, `predictor.py` |
| F-14 | Filter repair overrode the diversity penalty and reported the pre-repair pattern | `ilp_selection.py` (replaces `selection.py`, `rebalance_line`) |
| F-8 | Freshness target was consulted for ordering then discarded; bin 0 absorbed every slot | `selection.py` |
| F-9 | Serving features fell back to 0 for a column the model was trained on | `predictor.py`, `bonus_predictor.py` |
| F-11 | HMC categorization measured days against wall-clock today | `hmc_categorization_analyzer.py` |
| F-12 | `max(set(...), key=list.count)` tie-break was non-deterministic | `bonus_to_main_analyzer.py`, `generate_bonus_to_main_json.py` |
| N-1 | Serving row was stale by one draw | `walk_forward.py`, `quickpick.py` |
| N-1b | `draws_since_bonus` was exactly inverted | `walk_forward.py` |
| N-3 | Top-K computed globally instead of per draw; overfit gap zero by construction | `model_metrics.py` |
| N-4 | Bonus-pool tie-break non-deterministic | `bonus_predictor.py` |
| N-5 | Two models could be assigned the same bonus ball | `quickpick.py` |
| — | `total_count` train/serve window mismatch | `drawpick.py` |
| — | Pipeline crashed at shutdown on the Tk matplotlib backend | `model_metrics.py`, `trend_analyzer.py` |
| — | Interaction thresholds: phantom features, vacuous splits, empty cells, mismatched recency | `feature_interaction_analyzer.py`, `interaction_thresholds.py` |
| — | Duplicate interaction script overwriting pipeline output | `feature_interaction_explorer.py` |
| — | main-6 / all-7 split corrupting the freshness selection target | `drawpick.py`, `walk_forward.py` |

The write-ups below run roughly newest first. Each explains a root cause of the kind that comes back; the
original reports are in git history.

### F-71 - Closed without a change: e2e timeouts on a loaded PC

Found 2026-09-25; closed 2026-09-26 on the owner's decision.

**What it was.** A few Playwright tests - the navigation test, then the chat tests - timed out
now and then at the start of a full run and passed when rerun. The note recorded here blamed a
cold server. **That was wrong.** Measured on a freshly started standalone server, the first
request to each destination takes 0.1-0.45s and `/api/chat` 0.04s - nowhere near a 10s timeout.
A global setup that warmed every destination before the tests (tried 2026-09-26) did not stop
it: the next full run still failed two chat tests.

**What it is.** Browser load on the PC. The same suite with 4 workers instead of 2 failed 50 of
204 tests and took 17 minutes; with 2 it fails 0-2 per run. A starved browser clicks the chat
button before the page has hydrated, the click does nothing and the panel never opens.

**Why closed.** It affects only the e2e suite on the owner's PC, where several Chromes share
one machine. The hosted site is not involved: the server is fast from its first request, and
each visitor uses their own device. The one real-world echo is a tap in the first moment of
a page load on a slow phone, which is normal for a server-rendered React site. If the suite
ever needs to be quiet, the fix is for a test to wait for hydration before clicking - not a
warm-up and not a longer timeout.

### F-67 - A parity test's assertion could not hold for every draw

Found 2026-09-24 while running the full suite for the chat panel; fixed 2026-09-26.

**Root cause.** `test_serving_row_changes_when_a_draw_is_added` required each of the seven balls
of the newest draw to change `recent_4` or `days_since_last` in the serving row. It failed with
`drawn number 11 did not move`: 11 was a main number on 2026-09-19 and the bonus on 2026-09-21.
`recent_4` counts the main six only, so the bonus appearance does not raise it, and
`days_since_last` counts to the next draw date - 2 days before (19 to 21 Sep), 2 days after (21 to
23 Sep). The engine was right; neither feature has to move. The suggestion recorded here when it
was found - keep `recent_4` for the main six - would have been wrong too: `recent_4` is a sliding
window, and a main ball that was also a main ball in the draw leaving the window nets zero.

**Fix.** The test asserts what must always hold: `total_count` is counted over all seven balls
from the first draw, so the newest draw raises it by exactly one for each ball it drew, bonus
included, and by zero for every other number. This is stricter than the old check, which
allowed any number of other changes.

**Measured.** `tests/test_walk_forward_parity.py` 19/20 -> 20/20. The new assertion still fires on
the failure it guards: a serving row built with `extract_features_at_draw(N-1)`, stale by one
draw, is caught.

### F-69 - The freshness tests measured against a uniform spread

Found 2026-09-25 while choosing figures for the chat panel's freshness answer; fixed 2026-09-26.

**Root cause.** A drawn ball's freshness bin is how many of the 5 preceding draws had it among the
main six. `freshness_pattern_analyzer.py` tested the bins against a third of the 3,500 balls each,
the 26 observed patterns against 1/26 each, and the most common pattern against 1/26. A fair
draw is none of those: 5 draws hold at most 30 of the 47 numbers, so half the drawn balls are
in C0 by chance alone. All three tests flagged, and `bin_distribution_test` said "freshness bias
detected" at p 1.9e-160. The same "random baseline counted the same way" mistake as F-30 and
F-38. The pattern test also dropped patterns that never occurred, so its expectation did not
cover every outcome.

**Fix.** `fair_pattern_probabilities()` computes each pattern's chance in a fair draw exactly:
each preceding draw hits a given k of the 7 balls with chance C(40, 6-k)/C(47, 6), and a hit
moves a ball up one bin. Its per-bin share is Binomial(5, 6/47): C0 50.4%, C1 37.0%, C2+ 12.5%.
The bin test and the pattern test compare with it (patterns a fair draw expects fewer than 5
times pooled into one cell). The top-pattern test first compared the winner with its own
chance, and on fair histories flagged 25%: three patterns are almost equally likely (12.7%,
12.2%, 11.4%) and the one that comes out on top is chosen after looking. It is now tested as a
maximum - the chance that any pattern reaches that count, bounded by the sum of their binomial
tails.

**Measured.** On 40 simulated fair histories of 500 draws, through the real
`freshness_analyzer_7_numbers` path: before, the bin, pattern and top-pattern tests flagged
100%, 100%, 100%; after, over 200 histories, 4.0%, 4.5%, 5.5%. On the real draws: bin test p
1.9e-160 -> 0.076, pattern test 5.0e-95 -> 0.34, top pattern 4.1e-19 -> 0.56. None flags.

**Effect on the ML layer: none beyond rounding.** `validated_weights` was set from the top pattern
only when the pattern and top-pattern tests both flagged; it is now uniform and marked
unvalidated, so `calculate_freshness_category_features` falls back to `top_pattern_dist` from
`lotto_7_number_freshness_results.json` - the same top pattern, 4/7, 2/7, 1/7. The
`freshness_c*_weight` values differ by at most 4.3e-13, the 12-digit rounding the old weights took
through the JSON (F-46). The site never read this file.

**Tests.** `tests/test_freshness_fair_draw.py`: each of the three tests flags at most 15% of 40
fair histories and the weights are almost never marked validated; the bin chance is the binomial;
every pattern's chance matches 20,000 simulated draws within a point; a history where every draw
repeats two balls of the one before is flagged by the bin and pattern tests.

### F-47 - A failed data load exited 0

Found 2026-09-20 while testing the F-45 service ordering; fixed the same day.

**Root cause.** `main()` in `drawpick.py` handled `FileNotFoundError`, a `ValueError` from
`load_lotto_data`, an out-of-range `FRESHNESS_WINDOW_INDEX` and an empty draw list by printing an
error and `return`ing, which exits 0. Verified against `HEAD`: run with no `data/irish500.csv`, the
old file prints "ERROR: CSV file 'data/irish500.csv' not found" and exits **0**. The F-45
`depends_on: service_completed_successfully` reads that exit code, so the dashboard would have
started on whatever artifacts were already on the volume - the F-43 failure mode by another route.

**Fix.** All four sites `sys.exit(1)`.

**Measured.** With `data/irish500.csv` moved aside, `docker compose up -d streamlit-web` now ends
`service "data-engine" didn't complete successfully: exit 1`, and `docker ps` shows no container.
Before the fix the same run would have started the dashboard.

**Tests.** `tests/test_pipeline_completeness.py`, `test_a_missing_csv_exits_non_zero`: runs
`drawpick.py` in an empty directory and asserts a non-zero exit. It fails on the old file.

### F-46 - Pinned versions did not make the artifacts platform-independent

Found 2026-09-20 measuring the F-44 fix; fixed the same day.

**Root cause.** With `requirements-engine.txt` pinned to exactly the versions the owner's PC runs and
the same BLAS on both sides (`scipy-openblas 0.3.30`), a host run and a container run still disagreed
in the last digits of every scipy p-value - the Windows and manylinux wheels are different builds.
Measured over the same `data/irish500.csv`, ignoring `generated_date` and `analysis_date`: host vs
host 0 lines, host vs container 8 files and 146 lines, all `p_value` or `p_value_adjusted`, for
example `lotto_odd_even_validated.json` `0.683682015990339` -> `0.6836820159903383`. Pinning removes
version drift; it cannot remove this.

**Fix.** `lotto_analysis/utils/serialization.py` holds `round_floats(obj, digits=12)`, which rounds
every float in a nested structure to 12 **significant** digits - not decimal places, which would
flush a p-value of 1.99e-307 to zero - and leaves ints, bools and strings alone. All 14 `json.dump`
calls in the pipeline wrap their payload in it: the twelve analyzers in `lotto_analysis/analyzers/`,
`lotto_analysis/utils/output_generator.py:write_json_file` and `analysis/bonus_analysis.py`. Twelve
digits is far below any threshold the repo tests and far above the precision these figures carry.
`drawpick.py`'s expected-artifact list moved to the module-level `EXPECTED_ARTIFACTS` so a test can
read it.

**Measured.** After the change, host run vs host run **0 differing lines**, and host run vs container
run **0 differing lines** (`docker compose run --rm data-engine`), apart from the date fields.
`quickpick.py` retrained on the rounded artifacts: every model's validation AUC and Top-7 AvgCaught
moved by +0.0000 against the pre-change `model_comparison.csv`.

**Tests.** `tests/test_artifact_rounding.py`, 25 tests: the two measured host/container values land
on the same rounded value; a 1.99e-307 p-value survives; ints, bools, strings and `None` are
unchanged; and each of the 22 JSON artifacts is checked float by float for no more than 12
significant digits, which catches a writer that skips the helper.

### F-45 - Docker stack plumbing: junk files, no service ordering, unowned volume

Found 2026-09-20, reviewing the Phase 1 Dockerization; fixed the same day.

**Root cause.** Four small defects, all in the Phase 1 plumbing.

- `cmd` reads `>>` as append-to-file, so `echo >> Step 1/2: ...` wrote a file called `Step` and
  printed nothing. Three lines across `scripts/docker_start.bat` and `scripts/docker_stop.bat` had
  it; the `.sh` and `.ps1` scripts quote their strings and were unaffected.
- `docker-compose.yml` expressed the engine-before-web ordering only inside the start scripts, so a
  bare `docker compose up` started both at once and Streamlit could read a half-written artifact.
- Both Dockerfiles create uid 1000 and `chown -R` at build time, but the `./data:/app/data` mount
  replaces that directory at runtime with the host directory's ownership. Docker Desktop masks it;
  the VPS will not.
- `.dockerignore` did not exclude `data/`, so ~24 artifacts and the draw CSV were sent to both build
  contexts although neither Dockerfile copies them.

**Fix.** The three `echo` lines print `[Step 1/2]` and `[Done]` instead of redirecting, and the two
junk files (`Step`, `Docker`) were deleted. `streamlit-web` gets
`depends_on: { data-engine: { condition: service_completed_successfully } }`; the start scripts
already run the engine themselves and check its exit code, so their `docker compose up` now passes
`--no-deps` and the engine still runs exactly once. Both Dockerfiles take `ARG UID` / `ARG GID`
(default 1000), passed from `docker-compose.yml` as `${UID:-1000}`, with the `chown -R 1000:1000 data`
alternative recorded in the compose header and in `plan.md` Phase 5. `.dockerignore` excludes `data/`.

**Measured.** `docker compose build` rebuilds both images; `docker compose up -d streamlit-web` runs
the engine to completion and only then starts the dashboard. With `data/irish500.csv` moved aside the
engine exits 1, `up` exits 1 and no container is left running (that exit code needed F-47).
`scripts\docker_start.bat` and `scripts\docker_stop.bat` print their step lines and create no files:
`git status` shows nothing new in the repo root.

**Tests.** `tests/test_docker_stack.py`, four tests: no `echo` line in either `.bat` contains a
redirect; `streamlit-web` waits for `service_completed_successfully`; both Dockerfiles take the uid
as a build arg and both services pass it; `.dockerignore` excludes `data/` and neither image copies
it.

### F-44 - A container run rewrote every artifact, masking the real diff

Found 2026-09-20, reviewing the Phase 1 Dockerization; fixed the same day.

**Root cause.** Two independent sources of churn. `json.dump` writes `\n` in text mode, which becomes
CRLF on Windows and stays LF in the Linux container, and the repo had no `.gitattributes` - so every
line of every artifact was "changed" on each alternation, 306,770 in `lotto_draw_history.json` alone.
Separately `requirements-engine.txt` pinned nothing (`pandas>=2.0.0`), so the image resolved different
builds from the host's.

**Fix.** `.gitattributes` marks `data/**/*.json`, `data/**/*.csv` and `data/**/*.txt` as
`text eol=lf`, so both platforms store and check out LF, and the tree was renormalised once with
`git add --renormalize data/`. `requirements-engine.txt` pins all five packages with `==`, matched to
the owner's venv on 2026-09-20.

**Measured.** A real container run (`docker build -f Dockerfile.data_engine`, then
`docker run -v ./data:/app/data`) now writes 24/24 artifacts and exits 0. Ignoring `generated_date`
and `analysis_date`, two host runs differ in 0 lines and a host run and a container run in 146 lines
across 8 files, against ~325k lines before. `git diff` over `data/` after a host run shows the real
content change alone, not the whole file.

**Not fixed by this.** Those 146 lines are last-digit p-value differences that survive identical
pinned versions and the same BLAS - see F-46, raised from this measurement.

**Tests.** `tests/test_pipeline_completeness.py`: `git check-attr` reports `eol: lf` for the tracked
JSON, CSV and text artifacts, and every line of `requirements-engine.txt` pins with `==`.

### F-43 - The data engine wrote 22 of 24 artifacts and still exited 0

Found 2026-09-20, reviewing the Phase 1 Dockerization; fixed the same day.

**Root cause.** Three failures lined up. `requirements-engine.txt` listed `pandas`, `scipy`, `numpy`
and `statsmodels` but not `scikit-learn`, which `hmc_success_analyzer._learn_feature_weights()`
imports inside the function - a lazy import is invisible to a dependency list built by reading the
top of each file. Its `except ImportError` returned `{'error': 'scikit-learn not available'}`, the
same silent-default class the repo forbids, so `hmc_recommendation_analyzer.py:32` raised `KeyError`
on `normalized_weights`. Phase 16's `except Exception` printed "System will continue without HMC
recommendations" and the run carried on, leaving `lotto_hmc_recommendations.json` and `.txt`
unwritten. The completeness check then passed because it tested `Path(...).exists()`: both files were
still on the mounted volume from the host run of 09-19 23:28.

**Fix.** `scikit-learn>=1.3.0` added to `requirements-engine.txt`; the `ImportError` fallback deleted
so a missing dependency raises; the Phase 16 handler re-raises after naming the phase; and the
completeness check extracted as `drawpick.verify_artifacts(expected_files, run_started)`, which
compares each artifact's mtime with the start of the run and exits 1 on a stale file as well as a
missing one. `run_started = time.time()` is taken at the top of `main()`.

**Measured.** `python drawpick.py` exits 0 with 24/24 artifacts fresh, and
`lotto_hmc_success_patterns_validated.json` `learned_weights` again carries `raw_coefficients`,
`normalized_weights`, `model_accuracy` and `intercept` in place of the error stub. `python
quickpick.py` exits 0; no model metric moved - nothing in `ml_lotto/` reads the Phase 16 artifacts.

**Tests.** `tests/test_pipeline_completeness.py`, six tests: the engine requirements list
`scikit-learn`; `_learn_feature_weights` raises `ImportError` with `sklearn` masked instead of
returning the stub; the Phase 16 handler contains `raise` and no "will continue" line;
`verify_artifacts` accepts a file written by this run, and exits 1 on a missing one and on one whose
mtime predates the run.

### F-42 — Bonus-to-Main predictor returned `[]` instead of its 2-tuple

Raised by Antigravity, 2026-09-19; the evidence was accurate.

**Root cause.** `generate_bonus_to_main_predictions` returns `(selected, top_6_data)`, but its
empty-window guard returned a bare `[]` (there since the original bonus-to-main commit `f491afd`, and
kept unchanged through the F-40 rewrite). `quickpick.py` unpacks two names, so the guard produced
`ValueError: not enough values to unpack (expected 2, got 0)` - reported instead of the real problem.
Latent: the branch needs ten consecutive draws with no bonus ball, and all 498 draws have one, so it
has never fired.

**Fix.** It raises `ValueError` naming the real fault, rather than returning `([], [])`, which would
let a run continue and silently write no bonus-to-main picks. Same rule as F-5, where a pool too small
for the request raises.

**Measured.** `quickpick.py`: metrics and picks identical - the branch is unreachable on this data.

**Tests.** `tests/test_bonus_predictor.py`, `test_empty_bonus_window_raises`: an empty window raises
`ValueError`. It failed on the old code, which returned instead.

**Not a defect.** The same report called the branch's emoji `print` a `UnicodeEncodeError` risk on
Windows. `drawpick.py:8` and `quickpick.py:20` already `sys.stdout.reconfigure(encoding='utf-8',
errors='replace')`, and a redirected `drawpick.py` run exits 0. Only a script importing these modules
directly is exposed, which no supported entry point does.

### F-39 — `validate_line` counted odd balls over seven numbers

**Root cause.** `validate_line` documented "a sorted list of 6-7 numbers". Sum and span sliced
`numbers[:6]`, but the odd count ran over every number given. A 7-number line whose 6 main numbers
hold 4 odd, with an odd bonus, counted 5 odd and failed `odd_even_balance` - a rule its ticket meets.
Latent: every caller passed 6 numbers, so no generated ticket was ever misjudged.

**Fix.** The ticket rules are about the 6 main numbers, so `validate_line` takes exactly `LINE_SIZE`
of them and raises on any other length, rather than slicing one part of the input and not another.
The bonus ball is not a ticket-rule input.

**Measured.** `quickpick.py`: metrics and picks identical - nothing in generation calls it.
`/lotto-verify` validates all three tickets as before.

**Tests.** `tests/test_selection_invariants.py`,
`test_validate_line_takes_exactly_the_six_main_numbers`: a valid 6-number line passes, and 7, 5 and 0
numbers each raise. It failed on the old code, which returned a verdict for all three.

### F-41 — Bonus-to-Main trained on `category` as a constant 0.0

**Root cause.** `BONUS_TO_MAIN_MODEL_CONFIG` listed `'category'`, whose value is the string 'hot',
'medium' or 'cold'. `bonus_to_main_row()` - and the two loops it replaced in F-40 - turned any
non-numeric value into 0.0, so the column was 0.0 in every training and serving row. A feature that
never varies is a bug, and the other tests missed it because their `produced` fixture drops
`category`.

**Fix.** `'category'` removed from the config; `bonus_to_main_row()` now indexes `float(row[f])` and
raises on a non-numeric value rather than substituting 0.0. The engine still carries `category`, which
is what the interaction features read.

**Measured.** The model fits 33 columns instead of 34. Every metric and every pick is identical, as an
all-zero column under L1 must be: it had zero weight.

**Tests.** `tests/test_no_constant_features.py`, `test_no_selected_feature_is_a_string`, over all six
configs: no model selects a feature whose engine value is not a number. It failed for Bonus-to-Main on
the old code.

### F-36 — A repeated bonus ball was counted from its oldest appearance

**Root cause.** `bonus_window_positions()` (`ml_lotto/utils/bonus_window.py`) walked the last 10 draws
oldest to newest and skipped a ball it had already seen, so a ball that was the bonus twice kept the
older position. `draws_since_bonus` then said 9 for a ball that had been the bonus in the most recent
draw. A 10-draw window averages ~9.2 distinct balls, so a repeat is common. Training and serving read
this one function since F-40, so both were wrong the same way - not a parity break, a feature that did
not mean what its name said.

**Fix.** Drop the "already seen" guard: the loop runs oldest to newest, so overwriting leaves the most
recent appearance. One change covers training and serving.

**Measured.** `quickpick.py`: the four main models and the Bonus Ball model are unchanged
(+0.0000 on every metric). Bonus-to-Main validation AUC 0.4997 -> 0.5124 and Top-7 AvgCaught +0.0167,
both well inside the 2 SE noise floor of 0.031 AUC and 0.227 - not a result, and it stays at chance.
Its picks reordered (31 now first, at 0 draws since bonus); the main lines are identical.

**Tests.** `tests/test_bonus_window.py`, two new tests: a ball that was the bonus in the oldest and
the newest of ten draws is 0 draws ago, not 9; and the window holds the last 10 draws only. The first
failed on the old code.

### F-38 — Odd/even affinity validated every odd number on a biased test

**Root cause.** `odd_even_analyzer.py` labels a draw "odd" when it has at least as many odd numbers as
even, then tested each number's share of odd draws against 0.5 (`stats.binomtest(..., 0.5)`). A
draw containing an odd number already has one odd ball, so for an odd number the fair-draw chance is
0.827, for an even one 0.543 - never 0.5. With FDR correction applied, all 24 odd numbers plus 46
were still "statistically validated", and the Statistics page marked them so, under text calling an
affinity above 0.75 a "strong preference". The overall chi-square expected 50/50 odd balls where the
pool holds 24 odd of 47. On simulated fair draws the old test gave p < 0.05 for 261 of 470 numbers.

**Fix.** `chance_of_odd_draw(number, max_number, draw_size)` is the hypergeometric chance that a fair
draw containing the number is an odd draw; each number is tested against its mean chance over its
draws, and `chance_affinity_score` is written beside `affinity_score`. `preferred_type` is 'odd' or
'even' only for a share that differs from chance after FDR, else 'neutral'. The overall test expects
24/47 odd and writes `expected_odd_percentage`. The Statistics page shows a Chance column, says a fair
draw's balls are 51.1% odd, and takes the count of numbers that differ from chance from the artifact.

**Measured.** `drawpick.py`: only `lotto_odd_even_validated.json` changed (three others by timestamp
only). Validated numbers 25 -> 0; raw p < 0.05 for 4 of 47 (about the 5% chance gives); number 1's
share 0.820 against chance 0.827. Overall p 0.534 -> 0.588. `quickpick.py`: picks identical, every
validation AUC identical - nothing in the ML layer reads the per-number results.

**Tests.** `tests/test_odd_even_affinity.py` (new, 6 tests): on 10 x 498 simulated fair draws about 5%
of numbers have p < 0.05 and FDR validates at most 2 (old: 261 and 254); the stated chance matches
20,000 simulated draws within 0.01; a number whose draws are forced odd is still validated; every
number drawn equally often gives chi-square 0; the Statistics page renders with the Chance column and
without "strong preference" or "50/50". Four of the six failed on the old code.

### F-35 — Post Draw Analysis read the draw CSV

**Root cause.** `view/pages/post_draw_analysis.py` had its own `load_latest_draw_from_csv()`, which
parsed `data/irish500.csv` - trying three date formats and swallowing every exception - to show the
latest draw and fill the Autofill inputs. Every other page reads `data/*.json`, which is what lets the
Next.js site replace Streamlit without the CSV; this page would have broken there. The CSV and the
JSON agreed on the latest draw, so nothing showed wrong.

**Fix.** `load_latest_draw()` takes the last date from `data_loader.get_sorted_draw_dates(
load_draw_history())` and reads `main_numbers` and `bonus_number` with `[...]`. The "no draw found"
branches went with it: `load_draw_history()` stops the page if the file is missing.

**Measured.** Autofill fills 2026-09-16's draw (4, 7, 19, 20, 35, 42 / bonus 31), as before. No module
under `view/` names `irish500` any more.

**Tests.** `tests/test_draw_history_numbers.py`, two new tests: clicking Autofill (Streamlit
`AppTest`) fills the newest draw in `lotto_draw_history.json`, and no `view/**/*.py` names
`irish500`. The second failed on the old code.

### F-40 — Bonus-to-Main model was served a different row from the one it was trained on

**Root cause.** Training built each row from the engine - `extract_features_at_draw(t)[num]` with
`is_in_bonus_window` and `draws_since_bonus` overridden. Serving scored `bonus_to_main_features_dict`,
built in `bonus_to_main_features.py` from the extractor's row and `lotto_bonus_to_main_patterns.json`.
The two rules were written out twice, in the trainer and in the predictor, and read different dicts.
Against the engine's next-draw row, for the 10 numbers in the current bonus window: the transition
weights (`category_multiplier`, `freshness_multiplier`, `timing_decay_weight`,
`composite_transition_score`) differed on 10/10, the gap statistics on 10/10, `freshness_bin` and its
interactions on 3-8/10 (served as 0, as in F-34), the freshness triples on 4/10. The predictor also
read each column with `.get(fname, 0.0)`.

**Fix.** One row rule and one window rule, shared. `bonus_to_main_row()` in
`bonus_to_main_features.py` builds a row from an engine row and the number's window position;
`bonus_window_positions()` in `ml_lotto/utils/bonus_window.py` gives the window for a history. The
trainer applies them at each draw `t` (history cut at `t`); the predictor applies them to
`base_engine.with_base_features(bonus_to_main_features_dict).extract_features_for_next_draw()` and
the full history - the same engine view the trainer uses. The predictor's silent `.get` is gone:
a column the row lacks raises.

**Measured.** Training unchanged: validation AUC and Top-7 +0.0000 against the post-F-34 baseline.
The served probabilities also did not move (the same six, 7.3% to 6.3%). The fitted model (L1,
C = 0.005) gives weight almost only to `gap_variance` and `total_count`, and the old path already
served both correctly - `gap_variance` from `rolling_stats.py`, `total_count` parity-tested. The
~20 corrected columns currently have zero weight; they would have mattered as soon as the
regularisation or the feature set changed.

**Tests.** `tests/test_walk_forward_parity.py`, `test_bonus_to_main_serves_the_row_it_was_trained_on`:
with the history cut at the last draw `t`, the rows the predictor scores (captured by a recording
model) equal the trainer's rows for draw `t`, number for number.

### F-34 — Main models were served a different row from the one they were trained on

**Root cause.** A training row is built by `build_main_dataset` (`walk_forward.py`): the engine's
point-in-time value for every feature it computes, the base features only for the rest. The serving
row was `extract_features_from_hmc_json()`'s output, passed straight to `generate_predictions`,
`generate_all_picks` and `generate_pool_picks`. Where the two computed the same name differently, the
models were fitted on one value and served another:

- `appearance_volatility`, `gap_consistency_score`, `max_gap_ratio` came from
  `lotto_advanced_patterns.json` - calendar-day gaps, detrended - where training uses draw-index gaps.
  Different on 47/47 numbers (number 1: volatility 0.8127 trained vs 0.836 served, max gap ratio
  4.498 vs 3.75). `gap_consistency_score` is in all four main models.
- The extractor never set `freshness_bin`, and `interactions.py` reads it with `.get('freshness_bin', 0)`,
  so every served `*_x_freshness_bin_interaction` and freshness triple was computed at bin 0:
  `recent_4_x_freshness_bin_interaction` differed on 23/47 numbers, `triple_hot_0_very_recent` on 15.
- `has_consecutive_partner` used `recent_4 >= 1` for a hot neighbour, training the hot category:
  3/47 numbers differed.

`test_walk_forward_parity.py` compared only six named features, none of these.

**Fix.** `PointInTimeFeatureEngine.extract_serving_rows()` builds the next-draw row the way a
training row is built - `{**base_features[num], **point_in_time[num]}` - and `quickpick.py` passes
`base_engine.with_base_features(features_dict).extract_serving_rows()` to predictions, picks and the
pool. The extractor's row is still the base, so a feature the engine does not compute is served the
same full-history value it was trained on. Training is unchanged.

**Measured.** Validation metrics identical to the pre-fix baseline (every AUC and Top-7 change
+0.0000), as expected - only the served row changed. The picks changed: all three model lines and the
Model 4 wheel. `/lotto-verify`: all checks pass.

**Tests.** `tests/test_walk_forward_parity.py`, two new tests: the served row equals the training row
on every column any main model trains on, and the gap statistics, `freshness_bin` and
`has_consecutive_partner` come from the engine. Both fail on the old code.

**Not covered here.** The Bonus Ball model was already served by the engine (`quickpick.py:587`).
The Bonus-to-Main model had the same defect, fixed separately as F-40.

### F-33 — Bonus statistics read a list that ends with the draw's own bonus

**Root cause.** `hmc_analyzer.py` stores each draw's `recent_bonus_numbers` after the draw, so it ends
with that draw's bonus (498 of 498 draws) - correct as the window for the next draw, which serving
reads. `bonus_analyzer.py` read it as the window *before* the draw in two places. The repeat statistic
(`recent_bonus_exclusion.was_bonus_last_10`) therefore found every bonus in its own list: rate 1.0.
The recency effect behind `predicted_bonus_score` did the same, giving a "penalty" of 1.0 / 0.2128 =
4.7 that multiplied every recent bonus ball's score - all ten sat at the 1.0 cap, top of the ranking.
Nothing reads `predicted_bonus_score`, so no model or page was affected. All three bonus statistics
also used 10/47 as chance, assuming 10 distinct balls; a 10-draw window averages 9.22, so chance is
19.6%. That alone made `main_from_recent_bonus` read a 0.92 "boost" for what is 1.00. The Draw History
page showed the same list as "Last 10 Bonus Numbers", so a draw's own bonus was always highlighted.

**Fix.** `pre_draw_bonus_window(sorted_draws, idx)` returns the previous draw's list; the repeat
statistic and the recency effect use it, and all three statistics take chance as the window's
distinct balls / 47. The stored list keeps its meaning - serving needs it. Draw History shows the
previous draw's list as "Last 10 Bonus Balls Before This Draw".

**Measured.** `drawpick.py`: only `lotto_bonus_analysis.json` changed - repeat rate 1.0 -> 0.183
(expected 0.196, p = 0.25), `main_from_recent_bonus` boost 0.92 -> 1.00, `recency_penalty` 4.7 ->
0.93, and the 10 capped `predicted_bonus_score`s dropped. `quickpick.py`: picks identical, largest
metric change 1.2e-5. Draw History renders with `AppTest`, no exceptions or error boxes.

**Tests.** `tests/test_bonus_window.py` (new, 5 tests): the pre-draw window equals the previous 10
draws' bonus balls on the real data; on 3,000 simulated fair draws the repeat rate matches chance, the
main boost is 0.95-1.05 and the recency penalty 0.85-1.15 (old code: 1.0, 0.92, 4.7); Draw History's
latest table shows the previous draw's list.

### F-32 — Transition rate divided by bonus balls that could not yet transition

**Root cause.** `bonus_to_main_analyzer.py` counted transitions only for bonus balls with 10 draws
after them (`range(len(sorted_draws) - 10)`) but divided by every bonus appearance, including the
last 10. Overall that read 364/498 = 73.09% instead of 364/488 = 74.59%, and each number that was a
recent bonus ball had its per-number rate understated (e.g. 0.5556 -> 0.625). It made bonus balls look
slightly *below* chance (74.48%) - the mirror of F-30's false boost.

**Fix.** Profiles count `eligible_bonus_appearances` (with a full 10-draw window) and divide by it,
overall and per number; `total_bonus_appearances` still counts every appearance for the pages. The
standalone `analysis/generate_bonus_to_main_json.py` counted inside the loop and was already right.
The remaining "3.48x boost" text went too: the Bonus-to-Main config description and trainer
docstring, the class-weight comment (the 3.5 weight was set from that boost; kept, unmeasured), a
print in `generate_bonus_to_main_json.py`, and a "3.42x lift" in `analysis/validate_bonus.py` -
`main_from_recent_bonus` in the artifact shows 0.92.

**Measured.** `drawpick.py`: `overall_transition_rate` and `base_rate` 0.7309 -> 0.7459 - the
figure measured independently for F-30 - and `boost_factor` 0.98 -> 1.00; 10 per-number rates changed.
`quickpick.py`: picks identical and Bonus-to-Main metrics bit-identical, although its
`historical_transition_rate` column held the new values (22 distinct in training). Probed: L1 at
C = 0.005 keeps 2 of its 34 coefficients, so that feature has none - the constrained capacity working.

**Tests.** `tests/test_bonus_transition_baseline.py` 3 -> 4: in a 40-draw history where every bonus
ball is a main number in the next draw, the rate is 1.0 overall and per number (the old code: 0.75).

### F-29 — Sum alerts used hard-coded figures; the volatility alert could never fire

**Root cause.** `view/utils/anomaly_detector.py` and `view/pages/pattern_comparison.py` read
`summary_statistics.mean/std` from `lotto_sum_contribution_validated.json`; the file keeps them under
`overall_distribution`. `.get(..., 144.87)` / `.get(..., 30.4)` hid the miss, so both always used
constants (real today: 145.95 / 30.71). The bands moved: a line summing 237 was "Very unusual" (past
the constant 3 SD of 236.1; the real one is 238.1), and Pattern Comparison called a sum of 206-207
unusual (constant range 84-206; real 85-207). The volatility alert needed 4 numbers at
`appearance_volatility >= 1.5`; the highest of the 47 is 1.16 and only one is >= 1.15, so no line
could fire it. The whole detector loaded files with `except FileNotFoundError: {}` and read with
`.get` defaults, and loaded two artifacts no check used.

**Fix.** The detector loads the four artifacts it uses with direct access - a missing file or key
raises - and reads the sum statistics from `overall_distribution`; every check reads its fields
directly. Pattern Comparison does the same. The volatility check is removed rather than re-thresholded:
at the page's own "High" band (>= 1.15) only one number qualifies, so it still could not fire, and
the values (0.69-1.16) are what gap regularity looks like in a fair draw. With it went the `info`
alert level, its only source, and the validator's always-zero "Note" counter.

**Measured.** Sum 237: "Very unusual" -> "Unusual", quoting mean 146.0 instead of 144.9. Pattern
Comparison, sum 207: typical range 84-206 -> 85-207. `AppTest`: Prediction Validator and Pattern
Comparison render with no exceptions or error boxes.

**Tests.** `tests/test_anomaly_detector.py` (new, 4 tests): the sum alert quotes the artifact's mean;
237 is "Unusual", not "Very unusual"; Pattern Comparison's typical range is the artifact's mean +- 2
SD; every `_check_` method fires on at least one line built from the current data. All 4 failed on the
old code; the last names `_check_extreme_volatility`.

### F-31 — The "significant trend" flag flagged most numbers on fair draws

**Root cause.** `advanced_pattern_analyzer.py` set `trend_is_significant` from Kendall's tau on the
last 50 points of a rolling 10-draw frequency, smoothed with a Savitzky-Golay filter. Neighbouring
points of that series share most of their data, so they are not independent, and the test's p-values
were far too small: 32 of 47 real numbers were "significant", and on simulated fair draws the function
flagged 285 of 470 (61%) where p < 0.05 allows about 5%. It also flagged trends with no older window
to compare. The flag was shown as Trend on Number Insights and Post Draw Analysis and as the Trending
Up / Down filter and lists on Trigger Periods ("statistically significant (p < 0.05)").

**Fix.** `trend_is_significant` is Fisher's exact test on the raw counts the trend compares - draws
with the number in the last 50 against the 50 before - false when there is no older window. The
smoothed `appearance_trend` value, which the ML layer reads, is unchanged. Number Insights' profile
shows the trend again (F-30 had left it out); Trigger Periods states the test and that about 2 of the
47 numbers are flagged by chance; the manual and `docs/ml-concepts.md` describe the real method.

**Measured.** Simulated fair draws, 20 x 47 numbers: 3.3% flagged (was 53-70% per run).
`drawpick.py` re-run: only `trend_is_significant` changed - 31 numbers True -> False - and
`statistically_significant_trends` 32 -> 1 (number 42; ~2.4 expected by chance). `quickpick.py`
re-run: picks identical, largest metric change 1.3e-6. Number Insights for 42 and Trigger Periods
render with `AppTest`: no exceptions, no error boxes.

**Tests.** `tests/test_trend_significance.py` (new, 4 tests): 0.5-6% flagged across 470 fair numbers
(the old code: 61%); a real change (2 -> 25 appearances in 50 draws) is flagged; nothing is flagged
with fewer than 100 draws. Three of the four failed on the old code; the real-change test passes on
both, as it should.

### F-30 — Number Insights graded numbers as picks; bonus balls were called due

**Root cause.** Two claims with one shape: a number's past predicts its next draw. Number Insights
scored each number 0-100 as STRONG PICK / GOOD PICK / NEUTRAL / AVOID, adding 25 for an "overdue"
gap (> 1.5x its average) and calling a number "OVERDUE!" - the gambler's fallacy; every number has
the same 6/47 chance each draw. Draw History said recent bonus balls "are likely to appear in main
draw soon" and advised including 1-2, because 74% of bonus balls come up as main numbers within 10
draws. That figure is real but is chance: any number does it 1 - (41/47)^10 = 74.5% of the time
(bonus 74.59%, numbers not drawn 74.37%, p = 1.0). It looked like a signal because
`bonus_to_main_analyzer.py:460` used 10/47 = 21.3% as the random rate - one ball per draw instead of
six - and wrote `boost_factor: 3.44` into the artifact. The Prediction Validator scored a line lower
unless it held a "transition candidate" (past rate > 0.65), the same claim. The demo that "showed"
74% hard-codes `transition_rate: 0.74` as mock input.

**Fix.** Kept as a neutral profile, as the owner chose. Number Insights: the Recommendation score is
replaced by a Profile - a list of what stands out (recent vs historical frequency, regime shift, gap
vs average, recent bonus appearance, last-5 count), no score, no verdict, and a caption that every
number has a 6 in 47 chance. The gap is stated as longer than usual / about usual / came up recently,
with "a long gap does not make a number due"; it now runs to the latest draw, not `datetime.now()`
(the F-11 rule). The Bonus→Main rate is shown next to the fair-draw rate. The trend line is left out
of the profile - its significance flag is broken (F-31). Draw History: "Recent Bonus Balls and the
Main Draw" shows the rate next to the fair-draw rate from the artifact and lists every number that
was a bonus ball in the last 150 days, with no rate filter and no tip. Validator: the check counts
any number that was a bonus ball in the last 150 days - 99.6% of past draws had one, so it is a
typicality check - with no transition-rate filter. Analyzer: `expected_random = 1 - (1 - 6/47)**10`,
also in `analysis/generate_bonus_to_main_json.py`. Manual, `lotto_analysis/analyzers/CLAUDE.md`
and the old `analysis/bonus_to_main_model_recommendation.md` updated.

**Measured.** `drawpick.py` re-run: the only artifact change is `expected_random_rate` 0.2128 ->
0.7448 and `boost_factor` 3.44 -> 0.98. `quickpick.py` re-run: picks identical, largest metric change
3.4e-5 (run noise; floor 0.031). Number Insights (the latest bonus ball and the longest-gap number)
and Draw History render with `AppTest`: no exceptions, no error boxes. A dead branch went with the
score: it read `days_since_bonus`, a key the artifact never had, so its +15 never applied.

**Tests.** `tests/test_bonus_transition_baseline.py` (new, 3 tests): on 3,000 simulated fair draws
the analyzer's random rate is 1 - (41/47)^10 and its boost 0.95-1.05 (the old code reports 3.5 on
fair draws); the validator scores a line with a recent low-rate bonus ball as typical (the old one
scored it 70). `tests/test_site_wording.py` 10 -> 13: Number Insights for the latest bonus ball and
the longest-gap number, and Draw History, carry no pick / avoid / overdue / candidate / strategy
wording and show the chance rate. All new tests failed on the old code.

### F-28 — Other pages graded lines strong, weak or risky, and quoted false frequencies

**Root cause.** The same assumption as F-26 - that a line's shape changes its chance - ran through
the rest of the site. Pattern Comparison graded a line STRONG / GOOD / MODERATE / WEAK PATTERN with
"Pattern Strengths" and "has NEVER won". Trigger Periods ended its sum check with a "Validation
Confidence: HIGH/MEDIUM/LOW" and called sums "Realistic" / "Unrealistic". The anomaly alerts, shown
on the Prediction Validator, said "risky", "Consider diversification", "Balanced selections have much
higher success rates", and that repeating a past line is "astronomically unlikely" - it is exactly as
likely as any other. Two of their figures were false: all-odd/all-even "<0.5% of draws" is 2.0%
(10 of 498), and 1 or 5 odd "~5%" is 18.9%. The manual carried all of it, plus a strategy section
("ride the wave", "surprise wins", "Contrarian value picks").

**Fix.** Wording only; no score, threshold or alert condition changed. Pattern Comparison: "How
Typical Is This Shape", verdicts Very typical / Typical / Less typical / Unusual shape, lists "Common /
Less common in past draws", and an equal-chance caption. Trigger Periods: typical / uncommon / never
seen before, no confidence verdict. Anomaly detector: every detail describes past draws, with no
advice and no hard-coded percentage; the repeat alert says a repeat is as likely as any line. The
validator shows alert counts as Very unusual / Unusual / Note, without red error boxes. "Realistic"
became "typical" or "common" on the validator and Statistics pages. `docs/dashboard-manual.md`: the
Trigger Periods, Statistics, Freshness, Validator, Pattern Comparison and Key Concepts sections, the
workflow and the Tips section rewritten to describe, not advise; its odd/even shares are now the
measured 79% / 19% / 2%. `view/pages/CLAUDE.md` gains the rule "Describe, never advise".

**Measured.** Rendered with `AppTest` - Prediction Validator, Pattern Comparison, Trigger Periods
(sidebar numbers) and Statistics: no exceptions, no error boxes.

**Tests.** `tests/test_validator_wording.py` renamed `tests/test_site_wording.py`, 3 -> 10 tests:
Pattern Comparison and Trigger Periods rendered with a typical and an unusual line; six lines, derived
from the data, that fire nine of the ten alert kinds (volatility cannot fire - F-29) with no advice in
any; no percentage in the odd/even alerts; the repeat alert says "as likely". All 10 failed on the
code before F-26. Number Insights and Draw History are F-30.

### F-26 — Prediction Validator told players to play or regenerate

**Root cause.** The page scores five checks on a line (odd/even, sum, HMC, bonus transition, range
spread) - a measure of how much the line resembles past draws. Its verdicts read that score as a
chance of winning: "RECOMMENDED - Play with confidence!", "NOT RECOMMENDED - Regenerate numbers",
grades "Excellent" / "Risky" / "Poor", a legend ending "definitely regenerate", a "High Risk" badge on
critical alerts, "Suggested Improvements" and "statistically sound". In a fair draw every line is
equally likely to win; the page itself said so in the high-numbers check.

**Fix.** Wording only, in `view/pages/prediction_validator.py`; the score and its thresholds are
unchanged. Verdicts: "Typical of past draws" / "Somewhat typical" / "Unusual next to past draws", no
longer shown as success/warning/error colours for the two lower bands. Grades: A+ Very typical, A
Typical, B Fairly typical, C Less typical, D Unusual. The intro, a caption under the score and the
legend state that the score is resemblance, not a chance of winning. "Recommendations / Suggested
Improvements" became "What Makes It Less Typical", offered only "if you want one". Range spread
Good/Fair/Poor became Wide/Moderate/Narrow; bonus candidates are "recent", not "high-probability".
The validator part of `docs/dashboard-manual.md` matches.

**Measured.** Rendered with `AppTest`: 5, 12, 23, 31, 38, 44 scores 84 (A Typical) and 1-6 scores 54
(D Unusual), no exceptions, none of the advice phrases on either page. Same scores as before.

**Tests.** `tests/test_site_wording.py` (new, 3 tests): for a line scoring >= 80 and one < 60,
and for the empty page with the legend, no "play with confidence", "recommended", "regenerate",
"risk", "improvement", "statistically sound", "excellent" or "poor", and the page says every line is
equally likely to win. All 3 failed on the old page. Added to `verify.py`. The same language on
other pages is F-28.

### F-27 — Pattern Comparison classified past draws with today's hot/medium/cold

**Root cause.** `get_hmc_pattern(numbers, trigger_data)` classifies numbers with
`lotto_trigger_periods.json`, whose categories are dated at the latest draw. The page used it for the
player's line - correct - and also for every historical draw in `find_similar_draws` and the "HMC
Pattern Frequency" count, which is not: a past draw's pattern is the categories in force *before* it.
Numbers just drawn are hot today, so recent draws looked all-hot (16 Sep 2026: shown 6H-0M-0C,
pre-draw 3H-3M-0C). 459 of 498 draws had the wrong pattern. A number missing from the JSON was also
silently counted as medium by a `.get(..., 'medium')` default.

**Fix.** `view/pages/pattern_comparison.py`: new `get_draw_hmc_pattern(draw)` counts the main 6 of
`winning_numbers_details` (stored pre-draw, `is_bonus` false); both historical uses call it.
`get_hmc_pattern` stays for the player's line only and reads the category by direct key, so an
unknown number raises. `find_similar_draws` lost its now-unused `trigger_data` argument. No artifact
changed - the draw history already carried the pre-draw categories.

**Measured before/after.** Pattern Comparison for 9, 14, 20, 22, 26, 29 (the 14 Sep 2026 draw, today
6H-0M-0C): HMC Pattern Frequency 26/498 -> 4/498 (draws that really were 6H before the draw);
the 14 Sep draw itself now shows its pre-draw 4H-1M-1C and ranks 2nd at 80.0% instead of 1st at 100%,
because a line typed in today is classified with today's categories. Odd/even 112/498 unchanged.
Rendered headless with `AppTest`: no exceptions or error boxes.

**Tests.** `tests/test_draw_history_numbers.py`, 4 -> 7 tests. New: every historical match carries
the HMC counted from the draw's separate `categories_pre_draw` lists, summing to 6 (failed on 459 draws
with the old page); the latest draw is 6H by today's categories but keeps its pre-draw pattern; an
unknown number in the player's line raises (the old page returned it as medium). **Changed:** the F-25
test "a past draw comes back with the top similarity" queried with the draw's numbers classified by
today's categories. That premise is what F-27 removes - a past draw's own HMC is now pre-draw - so it
queries with the draw's own pre-draw pattern and asserts 100% similarity, stricter than "top".

### F-25 — Pattern Comparison read a key the draw history never had

**Root cause.** `view/pages/pattern_comparison.py:155,174,330,333` and
`view/utils/anomaly_detector.py:310` read `main_numbers` and `bonus_number` from
`data/lotto_draw_history.json`. No entry has ever had them (0 of 498; also absent in the version
committed with the page, `70f053c`, 2025-11-23) - the balls are in `winning_numbers_details`. The
`.get('main_numbers', [])` default gave every draw an empty list, so `find_similar_draws` skipped all
498: every line, even a real past draw typed in exactly, got "No similar historical draws found", and
the Pattern Frequency section never rendered. The Prediction Validator's "exact same numbers drawn
recently" alert compared against `[]` and could never fire.

**Fix.** In the website's API, not the page: `hmc_analyzer.py` now writes `main_numbers` (the 6, in
draw order) and `bonus_number` into each draw-history entry - what the Next.js site will need too. The
pages read both with direct key access, so a missing field raises. `drawpick.py` and `quickpick.py`
re-run.

**Measured before/after.** Pattern Comparison for 9, 14, 20, 22, 26, 29 (the 14 Sep 2026 draw):
0 matches -> 15, itself first at 100%; Pattern Frequency now renders (26/498 HMC, 112/498 odd/even).
The validator on the 16 Sep draw now raises "Pattern Repetition: Exact same numbers drawn on
2026-09-16". `lotto_draw_history.json` only gained the two fields; the other three changed files differ
only in `generated_date`. Picks identical and metrics +0.0000 - the models never read these fields.

**Tests.** `tests/test_draw_history_numbers.py` (new, 4 tests): every entry has 6 distinct main numbers
in 1-47 and a separate bonus; both agree with `winning_numbers_details`; Pattern Comparison returns the
latest and the earliest past draw with the top similarity score. All 4 failed with `KeyError` on the
old data. Added to `verify.py`.

### F-7 — Two analysis scripts read a window that has never existed

**Root cause.** `analysis/bonus_to_main_analysis.py:109,121` and `analysis/feature_stability_scorer.py:82`
read `recent_counts.get('last_14', 0)`. `SCENARIOS` (`lotto_analysis/config/config.py`) has windows
5/6/10/25, so the draw history holds only `last_4`, `last_5`, `last_9` and `last_24` - checked in
`data/lotto_draw_history.json` on 2026-09-19. The `.get(..., 0)` default turned the missing key into
a constant: every `recent_14` in their output was 0.

**Fix.** Pointed both at `last_24` and renamed the field `recent_24` (a column named `recent_14`
holding a 25-draw count would mislead), including the feature lists that name it. The window keys are
now read with `[...]`, so a missing window raises instead of defaulting to 0. Regenerated their
outputs in `data/analysis/` (`bonus_to_main_analysis.json`, `lotto_feature_stability.json`,
`lotto_feature_stability_rankings.csv`, `lotto_core_feature_set.json`); these are read by nothing in
the pipeline, the models or the website.

**Measured before/after.** `bonus_to_main_analysis.json`: `recent_14` was 0 in 100/100 rows;
`recent_24` now ranges 0-6. The outputs were last generated 2025-11-17, so the rerun also takes in
every draw since. Checked in passing: the Bonus Ball model's `recent_14` is fine - the engine computes
it point-in-time in training (0-5) and serving (0-4); the `.get('recent_14', 0)` in
`bonus_features.py:210` is a dead default the engine overrides.

**Tests.** None: both are standalone exploratory scripts outside the pipeline. The 135 real tests pass.

### C-17b — Feature-discovery scripts sat in `tests/` as if they were tests

**Root cause.** Eleven scripts written to explore features as they were built (from November 2025)
had a `test_` prefix and lived in `tests/`, so pytest collected them next to the 13 real test files.
Checked 2026-09-19: six had no assertion at all, and the other five asserted only shape on mock data
(`is not None`, `'best_params' in`, `len > 0`) - nothing the real tests do not cover better. One was
broken (`test_interactions.py` read `feature_medians`, renamed `feature_thresholds` in `3f2d3aa`).
One wrote real output: `test_train_with_all_features.py` overwrote
`model_metrics/model_comparison.csv` with two mock models, which spoiled a baseline during F-24.
Because of them, `pytest tests/` could not be run bare.

**Fix.** Moved, not deleted - the owner may mine them for facts to show on the site. `git mv` of all
11 to `demos/demo_*.py` (history kept), run as `python -m demos.<name>` from the root. Fixed the
broken one; the overwriting one now writes to a temp directory; removed two dead
`sys.path.insert(0, '/home/user/lotto-ml')` lines. Added `pytest.ini` (`testpaths = tests`), so a
bare `pytest` runs exactly the 13 real files. New `demos/CLAUDE.md`, imported from the root one.

**Measured before/after.** Before: `tests/` held 24 files, 11 not tests; `test_interactions.py`
exited 1. After: `tests/` holds the 13 real files; `pytest` collects 135 tests and passes in ~30 s;
all 11 demos exit 0 as modules (1-32 s each) and leave `git status` unchanged - nothing written to
`model_metrics/` or `data/`.

**Tests.** No behaviour changed, so none added. The 135 real tests and `/lotto-verify` pass.

### F-21 — Bonus-to-Main trained on a C-5 full-history feature

**Root cause.** Six places read `category` from `lotto_trigger_periods.json`, dated at the last draw
rather than the draw being predicted. Traced 2026-09-19, only one reached a model:

| Site | Reaches a model? |
|:--|:--|
| `long_term_patterns.py:79,172` | no - `lt_*` removed from every config in C-5 |
| `window_saturation.py:357,423` | no - `get_saturation_explanation`, `get_saturation_statistics` had no callers |
| `bonus_to_main_trainer.py:228` | no - `extract_bonus_to_main_features_for_number` had no callers |
| `window_saturation.py:245` | **yes** - `window_saturation_penalty`, in `BONUS_TO_MAIN_MODEL_CONFIG` |

Re-dating that category would not have made the feature correct. `window_saturation_penalty` is one
of the C-5 full-history features: in training every row gets the same per-number value
(`walk_forward.py:356`, `static_feat`), estimated over the whole timeline including the validation
window. C-5 removed it from the four main models, but its guard test only checked those four, so
Bonus-to-Main kept it.

**Fix.** Removed `window_saturation_penalty` from `BONUS_TO_MAIN_MODEL_CONFIG`. Deleted the three
functions with no callers. The remaining last-draw category reads feed only features no model uses;
deleting those is F-24.

**Measured before/after.** Bonus-to-Main val AUC 0.4979 -> 0.4978, train/val gap 0.0331 -> 0.0332,
Top-7 unchanged - all far inside the noise floor, consistent with the L1 penalty (C=0.005) having
kept almost no weight on it. Every other model +0.0000. `lottery_picks.txt` identical.

**Tests.** `tests/test_no_constant_features.py::test_the_removed_c5_features_stay_out_of_the_auxiliary_models`
checks both auxiliary configs against the C-5 list (now `C5_REMOVED`, shared with the main-model
test). It failed on Bonus-to-Main before the config change.

### C-6b, F-22, F-23 — The serving row was dated differently from the training rows

**Root cause.** Every training row counts days to its own draw's date; the main models are served
from `extractor.py`, which counted to a different date. Three defects, one cause - no single serving
date:

- **C-6b.** `extractor.py` counted `days_since_last` to the latest draw (14 Sep), the engine to the
  estimated next draw. Measured on 2026-09-19: every one of the 47 served values was 3 days short of
  the training convention, and 4 numbers (2, 37, 41, 46) were served as hot at 12 days where training
  would call them medium at 15. `category` came from the JSON, dated at the last draw.
- **F-22.** The engine's next-draw estimate was last draw + median gap over all history (3 days).
  Irish Lotto added Monday draws in September 2026 (Mon/Wed/Sat), so after Mon 14 Sep it gave Thu
  17 Sep - not a draw day - instead of Wed 16 Sep.
- **F-23.** `calculate_days_since_bonus` counted to `datetime.now()` (`timing.py:32`), so Model 3's
  `days_since_bonus` input changed with the day `quickpick.py` ran.

**Fix.** One serving date, `engine.next_draw_date`: the first day after the last draw on a weekday
used by the latest 6 draws (`walk_forward.next_draw_date()`). `quickpick.py` builds the engine
before any serving feature and passes the date to `extract_features_from_hmc_json(reference_date=)`
and `calculate_days_since_bonus(draws, reference_date)`; both now require it. `category` is derived
by the shared `walk_forward.hmc_category()` in the engine and the extractor.

**Measured before/after.** Extractor vs engine serving row: `days_since_last` differed by 3 on 47/47
numbers and `category` on 4/47; now 0/47 on both, and on `days_since_bonus`. Picks changed, as they
should: Model 1 `[5, 13, 15, 24, 42, 43]` -> `[5, 13, 20, 27, 38, 42]`, Model 2
`[6, 9, 23, 31, 38, 39]` -> `[8, 9, 23, 31, 39, 40]`, Model 3 `[10, 19, 22, 32, 40, 47]` ->
`[6, 10, 19, 22, 32, 47]`. Validation metrics unchanged (+0.0000 on every model): training and
validation rows were always dated correctly; only the serving row moved.

**Tests.** `tests/test_walk_forward_parity.py`: `test_next_draw_date_follows_the_current_schedule`
(Wed/Sat and Mon/Wed/Sat cases), and `test_extractor_serving_row_matches_the_engine` on
`days_since_last`, `category` and `days_since_bonus`. Putting the extractor's date back to the last
draw fails the first two.

### F-6 — Ensemble code was unreachable, and each entry point was broken

**Root cause.** Ensembling was added (commit `85d3c41`, 2025-11-21) to combine the four main models
by vote, but never wired into `quickpick.py`. Checked 2026-09-19, every way in was broken as well
as unreachable:

- `ml_lotto/prediction/ensemble.py` (341 lines, majority/threshold/weighted/unanimous voting) was
  imported only by a demo script and legacy print-scripts.
- `scripts/ensemble_predict.py`: `main()` printed two warnings and returned 0 - it never called
  the voting code.
- `ENSEMBLE_MODE = True` in `config.py` only printed a banner claiming "Each model runs 15x with
  different seeds"; nothing reran anything.
- `scripts/train_with_all_features.py` voted on `val_proba.argsort()` - row positions in the
  validation table, not lotto numbers 1-47.
- `analysis/ensemble.py` reran `quickpick.py` with seeds 42..56 by rewriting `ml_lotto/config.py`
  in place (a crash mid-run left the source modified), left `lottery_picks.txt` and
  `model_metrics/` from the last seed rather than 42, had a 120 s timeout against a ~108 s run, and
  read only Models 1-3.

Beyond the defects, the method cannot help here: averaging cancels independent errors of models
that carry signal, and every model sits at chance (F-17).

**Fix.** Deleted `ml_lotto/prediction/ensemble.py`, `scripts/ensemble_predict.py`,
`analysis/ensemble.py`, and the print-scripts `tests/test_ensemble.py` and
`tests/test_ensemble_predict.py`. Removed `ENSEMBLE_MODE`, `ENSEMBLE_RUNS` and the unused
`_CURRENT_RANDOM_SEED` from `config.py` and the banner branch from `quickpick.py` (the deterministic
seed path is now the only one). Stripped the voting step from `scripts/train_with_all_features.py`
and `tests/test_train_with_all_features.py`. About 1,300 lines removed; recoverable from git.

**Measured before/after.** `lottery_picks.txt` identical apart from its timestamp; metrics
unchanged against the baseline. Nothing removed was on the path that produces either.

**Tests.** None added - this deletes code rather than changing behaviour. The 127 real tests pass;
`grep` finds no remaining import of the deleted modules or flags.

### F-20 — Bonus prediction 2 claimed category diversity it never applied

**Root cause.** `ml_lotto/prediction/bonus_predictor.py` chose prediction 2 with
`cat != used_categories` - a string compared to a set, always true - so it took the second-highest
probability whatever its category, while the log printed "Category diversity". Prediction 3 used
`not in` and was correct. Found 2026-09-19 while fixing F-5.

**Fix.** `cat not in used_categories`. The rule the docstring describes now holds: prediction 2 is
the best number from a different hot/medium/cold category than prediction 1, and prediction 3 from
a category not used yet, so the three span all three categories when the pool allows.

**Measured before/after.** In a case where the top two share a category (47 and 46 both cold), the
old code returned `[47, 46, 45]` - two colds - and the fix returns `[47, 45, 44]`, one of each. The
real run is unchanged, `[45, 10, 19]` (cold, medium, hot): its top two already differed. Picks and
metrics identical; bonus probabilities are at chance, so this is about what the output claims, not
about odds.

**Tests.** `tests/test_bonus_predictor.py::test_three_picks_span_three_categories_when_the_top_two_share_one`
fails on the old comparison and passes on the fix.

### F-5 — A too-small bonus pool crashed with a bare IndexError

**Root cause.** The register said `assign_bonus_to_models` divides by zero on an empty list and that
`generate_bonus_predictions` could return fewer picks than requested. Reproduced 2026-09-19 with a
stub model: the second claim is false. With a pool of 0, 1 or 2 numbers after recent-bonus
exclusions, `generate_bonus_predictions` raised `IndexError: list index out of range` itself
(`available_pool[0]`, `available_pool[i]`, `candidates[0]`), so an empty list never reached
`assign_bonus_to_models` - the division by zero was unreachable from `quickpick.py`. The real defect
was an unchecked precondition failing with an unexplained error. In practice the pool is never thin:
the bonus window is a `deque(maxlen=10)` (`walk_forward.py:145`), so at most 10 numbers are excluded
and at least 37 remain.

**Fix.** `generate_bonus_predictions` raises `ValueError` naming the pool size and the request when
the pool is smaller than `num_predictions`. The fix the register proposed - return `{}` and let the
`None` handling take over - was not applied: it is a silent default, and would have produced a run
with no bonus ball and no error.

**Measured before/after.** Pools of 0/1/2: `IndexError` before, `ValueError` with a message after.
Pool of 3 and the real pipeline: unchanged. No metric or pick can move - the guard is never reached
with a 10-draw window.

**Tests.** `tests/test_bonus_predictor.py` (new, 6 tests): pools of 0, 1 and 2 raise `ValueError`
(the three fail on the old code with `IndexError`); a pool of exactly 3 uses all of it; with the
widest real exclusion (10 numbers) the three picks are distinct and none excluded; every model gets
one of the predictions.

### F-16 — The diversity penalty was applied twice

**Root cause.** `predictor.py` scaled each number used by an earlier line down by the model's
`diversity_penalty` (25-40%, rank-aware, `penalties.py`), then `solve_line` also charged a flat 1 per
such number. The flat cost dominated, so the configured percentages only ordered reused numbers
among themselves when one was unavoidable - a config advertising "30% soft penalty" was in effect a
near-hard rule. Model 4's key was never read at all. The greedy picker had the same stack; the ILP
carried it over.

**Fix.** One mechanism: the flat cost, now `PENALTY_COST = LINE_SIZE`. Scores are probabilities
below 1, so two lines' sums differ by less than 6 and the cost is exactly lexicographic - fewest
reused numbers first, then best probability - whatever the probability spread. The cost of 1 relied
on spreads being small. The solver gets raw probabilities. Deleted: `penalties.py`, the four
`diversity_penalty` keys, `SHOW_DETAILED_PENALTIES` and the rank-aware explanation display. The run
now prints how many numbers each line avoids and any it had to reuse.

**Measured before/after.** Picks unchanged - `[5, 13, 15, 24, 42, 43]`, `[6, 8, 9, 23, 31, 39]`,
`[7, 22, 32, 38, 40, 47]`, still disjoint - which confirms the percentage was not affecting the
result. Metrics untouched: selection does not feed training.

**Tests.** `tests/test_selection_invariants.py`: in a random and four skewed score worlds, the
unpenalised optimum is penalised and the solver must match a brute-force lexicographic optimum.
Dropping the cost to 0.1 fails two of the five.

### F-15 — Config feature names were dropped silently

**Root cause.** `expand_feature_selection` (`ml_lotto/features/extractor.py`) kept a config name only
`if item in all_features` and skipped anything else without a word. A run with every call
instrumented found two such names: `recent_14` in Models 1, 2 and 3 (the walk-forward engine
produces it, the main serving path has no 15-draw window) and `category` in `BONUS_MODEL_CONFIG`
(the bonus dataset excludes the raw category string; the model uses `category_weight`). Model 1's
comments also misdescribed its config: "~17 features" for 25, `recent_4` as "last 4 draws" for 5, and
an empty `# CONSTRAINTS` block.

**Fix.** The four dead names are removed from the configs, Model 1's comments corrected, and
`expand_feature_selection` now raises `ValueError` on a name that is neither a keyword nor an
available feature. The bonus model's `recent_14` stays - it is produced on both of its paths.

**Measured before/after.** No model's features changed - Model 1 25, Model 2 16, Model 3 26, Model 4 5,
bonus 32 columns, identical to before - because the names were never reaching a model. Picks
unchanged; the largest metric move is 1.9e-5 in Model 2's overfit gap, run-to-run noise.

**Tests.** `tests/test_no_constant_features.py` expands every main config against the engine's
features, so an unknown name now fails it; a new test asserts the raise directly. A full
`quickpick.py` run exercises all six configs against the serving features.

### C-15a — The feature engine was rebuilt five times per run

**Root cause.** Each trainer built its own `PointInTimeFeatureEngine` because the engine carried its
static `base_features_dict` (main, bonus, bonus-to-main) alongside the draw state, so a different
dict meant a new engine. Measured 2026-09-18 on a full `quickpick.py` run: 5 constructions - main
trainer, bonus trainer twice (train and validation datasets), bonus serving row, bonus-to-main
trainer - at ~0.5 s each. Separately, `_precompute_timeline_state` snapshotted every number's full
gap list at every draw: 843,204 stored gaps, 12.8 MB retained per engine.

**Fix.** Two parts.
- `with_base_features()` returns a shallow view sharing the precomputed state and swapping only the
  base features. `quickpick.py` builds one engine and passes it to all three trainers and the bonus
  serving row as `base_engine`.
- Gap lists are replaced by running moments `(count, sum, sum of squares, max)`; variance is
  `(n*ss - s^2) / n^2` over exact integers.

**Measured before/after.** Constructions 5 -> 1; engine time 2.43 s -> 0.49 s of a ~120 s run.
Memory per engine 12.8 MB -> 5.1 MB. Feature output for every draw 0..N compared value by value:
1,683,420 identical, 25,218 differing by at most 5.7e-14 (float rounding in the four gap-derived
features only), 0 real differences. Picks unchanged; the largest metric move is 1.1e-5 in Model 2's
overfit gap, run-to-run noise.

**Tests.** `tests/test_walk_forward_parity.py`: gap variance, CV and max ratio checked against numpy
over the gaps recomputed from the draw history; a view shares state and equals a freshly built
engine. Both fail when the variance formula or the view is broken.

**Not changed.** `build_walk_forward_dataset` / `trainer.build_training_dataset` still build their
own engine; only `scripts/train_with_all_features.py` and a legacy print-script call them.

### F-14 — The filter repair overrode the diversity penalty and reported a stale pattern

**Root cause.** `pick_line_hybrid()` chose numbers first and checked the ticket rules afterwards;
a failing line went to `filters.rebalance_line()`, which swapped numbers by raw probability. Two
consequences, both visible in the 2026-09-18 run:

- **The penalty was bypassed.** Model 3's line `[10, 22, 32, 38, 40, 47]` failed odd/even (1 odd).
  The repair swapped 22 for 9 - the rank-1 penalised number for Model 3 (35%) and already on Model 2's
  line `[6, 8, 9, 23, 31, 39]` - because it ranked replacements on unpenalised `probabilities`.
- **The printed pattern could be stale.** `pattern_str` was built before the repair phase ran
  (old `selection.py`, pattern built above `# PHASE 3: Filter validation`), so `Achieved Pattern`
  described the pre-repair line whenever a repair happened.

**Fix.** Replaced by `ilp_selection.solve_line()`: one `scipy.optimize.milp` solve with the HMC
quotas, the reachable freshness target, the sum/odd/span rules (on the whole ticket, pre-assigned
included) and a 1-per-number penalty cost. `selection.py` and `rebalance_line` are deleted. The
pattern is computed from the returned line.

**Measured before/after.** Models 1 and 2 are unchanged (`[5, 13, 15, 24, 42, 43]`,
`[6, 8, 9, 23, 31, 39]`) - the greedy line was already the optimum. Model 3 goes from
`[9, 10, 32, 38, 40, 47]` to `[7, 22, 32, 38, 40, 47]`: still 2H/2M/2C and `C0=4, C1=2`, and the
three lines now share no number. Validation metrics are untouched - selection does not feed training.

**Tests.** `tests/test_selection_invariants.py`, rewritten for the solver (19 tests): every
constraint met, the line equals a brute-force optimum in a random and four filter-stressing score
shapes, pre-assigned numbers fixed and filters applied to the whole ticket, penalties avoided when
possible but never shortening the line, infeasibility raises. Disabling any one constraint in the
solver fails at least two tests.

### F-13 — The freshness target could be unreachable for a model's HMC ratio

**Root cause.** `target_pattern` came from `get_optimal_pattern_distribution()` and the hot/medium/
cold counts from `ml_lotto/config.py`, with nothing reconciling them. The freshness bins are not
spread evenly across HMC categories - measured 2026-09-17, every bin 1 and bin 2 candidate was hot
(hot 7/16/7, medium 7/0/0, cold 10/0/0) - so a line can hold at most as many non-bin-0 numbers as it
has hot slots. Model 3 has 2 hot slots against a target wanting 3 non-bin-0, and was therefore
unsatisfiable by construction. It missed silently, and the miss looked like a selection failure.

**Fix.** `constraints.reachable_pattern()` computes what a model can actually achieve from its HMC
quotas and the live pool composition, allocating scarce bins first and drawing on the most
constrained category first - the same ordering `selection.pick_line_hybrid` uses, so the result is
attainable rather than optimistic. `predictor.py` passes that to selection and prints the shortfall:

```
Target unreachable for this HMC ratio, using {0: 4, 1: 2, 2: 0} (C0: 3 -> 4, C2: 1 -> 0)
```

**Measured before/after.** Picks are unchanged - `[5, 13, 15, 24, 42, 43]`, `[6, 8, 9, 23, 31, 39]`,
`[9, 10, 32, 38, 40, 47]` - because the reachable pattern is what selection already achieved after
F-8. The change makes the constraint visible and attributable, not different.

Validated against the three known outcomes: `reachable_pattern` predicts `{0:3,1:2,2:1}`,
`{0:3,1:2,2:1}` and `{0:4,1:2,2:0}`, matching all three lines exactly, Model 3's shortfall included.
A feasibility calculation that disagreed with what selection produces would be worse than none.
Slot conservation checked across all 28 hot/medium/cold splits summing to 6: no mismatches.

**What this does not do.** Model 3 still cannot place 3 non-bin-0 numbers; that is arithmetic, not a
bug. Two alternatives were rejected: deriving a per-model target from the freshness data would mean
each model chases a different pattern, which is no longer the observed distribution the target
represents; and changing the HMC ratios would be tuning the models to satisfy a mechanism whose value
is unestablished.

**Resolved by F-18 (2026-09-19): kept.** Freshness bins do differ in hit rate (p = 0.031), so the
target and `reachable_pattern` stay. See section 7.

### F-8 — The freshness target was consulted for ordering, then discarded

**Root cause, two parts.** `pick_from_hmc_pool` ranked the freshness bins **once** per HMC category
and then drained the top bin until the slot count was met. Bin 0 holds 24 of 47 candidates, so it
never ran out and the loop never reached bin 1. The target was a sort key, not a constraint.

Fixing the ranking alone was **not sufficient**, and the first attempt made Line 3 worse. The second
part is call order. Every bin 1 and bin 2 candidate is hot (see F-13); medium and cold can supply
only bin 0. Picking hot first spent the bin 0 quota on the one category that could have supplied the
scarce bins, after which medium and cold overshot bin 0 because they had nowhere else to go.

**Fix.** Re-rank the bins before every pick, so each slot goes to the bin with the largest unmet gap,
and take the HMC categories **most-constrained-first**, so a category that can only supply one bin
claims its quota before the flexible category spends it. `freshness_counts` is shared across the
three calls, so the target applies to the line rather than per category. HMC categories are disjoint,
so the reordering changes only which bins get claimed, never which numbers a category may use.

**Measured before/after** (target `C0=3, C1=2, C_GE_2=1`):

| Line | Before | Ranking fix only | Both fixes |
|:--|:--|:--|:--|
| 1 Momentum Specialist | C0=6, C1=0 | C0=5, C1=1 | **C0=3, C1=2, C_GE_2=1** |
| 2 Jackpot Optimizer | C0=6, C1=0 | C0=5, C1=1 | **C0=3, C1=2, C_GE_2=1** |
| 3 Complexity Explorer | C0=4, C1=2 | C0=6, C1=0 | C0=4, C1=2 |

Two lines now hit the target exactly. Line 3 has only 2 hot slots and therefore at most 2 non-bin-0
numbers, so `C0=4, C1=2` is its structural optimum - see F-13, which is the open half of this.

All three lines still pass the ticket filters unrepaired (sums 142/116/176, spans 38/33/38, odd
counts 4/4/2). A side effect worth noting: bin 0 concentration was itself *causing* filter failures -
in a controlled reproduction the old code produced an all-bin-0 line that was 6 odd / 0 even, failed
`odd_even_balance`, and had to be repaired, which scrambled the freshness distribution further. The
two mechanisms were working against each other.

**Tests.** Verified with a controlled reproduction on a pool deliberately skewed like the real one
(bin 0 oversupplied): the old code returns `{0:2, 1:3, 2:0}` plus a repaired number and fails the
filters, the new code returns `{0:3, 1:2, 2:1}` and passes. The existing 79 pass. Model metrics are
unchanged and cannot change - selection is downstream of them.

**Not answered.** Whether enforcing the target is worth anything. `model_comparison.csv` scores the
models, not the selection, so it cannot settle this; it needs a backtest of generated lines against
actual draws. If the freshness pattern carries no signal the mechanism should be deleted rather than
fixed, and F-13 disappears with it.

### F-9 — Serving features fell back to 0 for a column the model was trained on

**Root cause.** `[feat.get(col, 0) for col in features_for_model]`, where `features_for_model` is the
exact column list the pipeline was fitted on. A column absent from the serving dict - a renamed
feature, an analyzer that stopped emitting a key, a `drawpick.py` run that did not happen - would be
served as a constant 0 to every number, and the model would apply a coefficient fitted on real values
to a column that no longer exists. Nothing prints; train/serve parity breaks silently. Same
`.get(key, 0)` pattern that produced the phantom `total_count` and `recent_14` columns.

**A second site was found during the fix.** F-9 recorded only
`ml_lotto/prediction/predictor.py:60`, because it was written from the F-4 investigation, which
touched that line. `ml_lotto/prediction/bonus_predictor.py:51` carried the identical pattern and had
never been examined. Both are fixed; fixing only the recorded one would have been the "changed one
side only" failure the parity contract exists to prevent.

**Fix.** `feat[col]` at both sites, so a missing column raises where it happens. Each carries a
comment saying why `.get(col, 0)` is wrong there, since the bare indexing otherwise looks like an
oversight waiting to be "hardened".

**Measured before/after.** Verified no column is missing before making it raise: 0 missing across all
five models with named feature lists (13, 9, 21, 5 and 20 columns) x 47 numbers. After the change
`quickpick.py` exits 0 with no `KeyError`, picks are unchanged
(`[2, 4, 5, 27, 42, 43]`+45, `[6, 23, 37, 39, 41, 46]`, `[9, 10, 32, 38, 40, 47]`+19) and all six
model AUCs are unchanged (0.5074 / 0.5011 / 0.5118 / 0.5257 / 0.4979 / 0.5454).

**Tests.** No new test. The change converts a silent wrong answer into a loud failure; asserting it
would mean constructing a serving dict with a column removed, which tests Python's `KeyError` rather
than this system. The existing 79 pass, and `test_walk_forward_parity.py` remains the real guard -
it checks the columns actually agree.

### F-11 — HMC categorization measured days against wall-clock today

**Root cause.** `hmc_categorization_analyzer.calculate_days_since_date()` used `datetime.now()` as
the reference, while the rest of the layer references the most recent draw
(`frequency_analyzer.calculate_days_since_last_hit`). Three call sites were affected
(`calculate_category_anova`, `calculate_pairwise_comparisons`, `calculate_threshold_validation`).

`data/lotto_hmc_categorization_validated.json` therefore changed **every calendar day** with no new
draw and no code change. Observed: the copy committed 2026-09-17 (generated on the 16th) had
`hot.min = 2.0`; a re-run on the 17th gave `3.0`, every statistic +1, `std_dev` byte-identical — the
signature of a moving reference rather than changed data.

There was a second effect, not noticed when the defect was logged. `suggested_thresholds` is read
against `HMC_HOT_THRESHOLD = 13` / `HMC_COLD_THRESHOLD = 27`, which are **draw-relative**. The
validated thresholds were on a clock-relative scale, so the two drifted further apart the longer the
gap since the last draw. They are now on the same basis.

**Fix.** Added `latest_last_seen(hmc_data)`, which derives the reference from the most recent
`last_seen` in the data, and made `calculate_days_since_date(date_str, reference)` take it
explicitly. Computed once per function and passed at all three call sites. No `datetime.now()`
remains in the path.

**Measured before/after** (run 2026-09-17, last draw 2026-09-14, so a -3 day shift):

| Category | Before (clock) | After (last draw) |
|:--|:--|:--|
| hot | mean 8.133, min 3, max 15 | mean 5.133, min 0, max 12 |
| medium | mean 21.857, min 19, max 26 | mean 18.857, min 16, max 23 |
| cold | mean 59.400, min 33, max 124 | mean 56.400, min 30, max 121 |

`std_dev` byte-identical (`4.150058855696763`) and `p_value` identical (`1.2947678031855394e-13`),
confirming a pure constant shift with the ANOVA verdict unchanged. `hot.min` is now 0, the correct
answer for a number drawn in the most recent draw. `suggested_thresholds` 8.0/19.0 -> 5.0/16.0.
Picks and all six model metrics unchanged.

**Tests.** No new test. The defect only reproduces across a calendar day boundary, so a meaningful
regression test would have to inject a reference date; the fix removes the clock from the path
entirely, which `grep -n "datetime.now()"` over the module now confirms. Covered by the existing 79.

---

### F-12 — A tie-break over a set made an artifact non-deterministic

**Root cause.** `max(set(values), key=values.count)` at four sites -
`bonus_to_main_analyzer.py:128,136` and `generate_bonus_to_main_json.py:122,128`. `max()` returns the
first maximal element in iteration order, and set iteration order varies between processes under
hash randomisation (`sys.flags.hash_randomization` is 1). On a tie the winner changed run to run, so
`data/lotto_bonus_to_main_patterns.json` differed between identical runs, dirtying the working tree
and masking real diffs. It already cost time during the F-10 verification, where a genuine
comparison had to be separated from this noise.

**Fix.** `sorted()` around the set at all four sites, so ties resolve to the first candidate in
sorted order. Each site carries a comment stating the call is load-bearing - this class has now
recurred three times (C-2, N-4, F-12) and an uncommented `sorted()` reads as removable noise.

**Measured before/after.** Three `drawpick.py` runs under `PYTHONHASHSEED` 1, 2 and 12345 now produce
a byte-identical artifact (`bbc69db8bd522d90b9da4b689c5a0ffc`); before the fix the same file varied
between runs at a fixed seed.

Three values changed and are now pinned. All five numbers that had ever varied were verified to be
genuine ties, so no majority is overruled:

| Number | Counts | Tied | Now |
|--:|:--|:--|:--|
| 2 | hot 4, cold 4, medium 4 | three-way | cold |
| 6 | cold 3, medium 3, hot 2 | cold/medium | cold |
| 21 | cold 2, medium 2, hot 1 | cold/medium | cold |
| 1 | hot 7, medium 7, cold 2 | hot/medium | hot |
| 40 | medium 4, hot 4, cold 3 | hot/medium | hot |

Picks and all six model metrics unchanged.

**Tests.** No new test. Reproducing it requires a subprocess with a forced `PYTHONHASHSEED`, since
hash randomisation is fixed within a process - a same-process test cannot fail. Verified empirically
across three seeds. A permanent guard would be worth adding if this class recurs a fourth time.

### F-10 — The HMC look-ahead guard was dead code printing a false reassurance

**Root cause.** `hmc_analyzer.py` sliced `all_draws[:train_end_index]` to exclude the validation
window from the final HMC category assignment. With `VALIDATION_SPLIT_RATIO = 1.0` in
`lotto_analysis/config/config.py`, `train_end_index` equalled `len(all_draws)`, so the slice excluded
nothing. The guard ran and did nothing while printing `Calculating final categories WITHOUT
look-ahead bias` and `Validation draws excluded: 0`.

The guard was the leftover, not the ratio. `final_categories` is consumed by **serving** only - it
reaches `lotto_trigger_periods.json` via `num_to_category` (`drawpick.py:231`) and
`ml_lotto/features/extractor.py` reads it to build the row for the next draw, where conditioning on
all history is correct. Training never reads it: `walk_forward.py:241-243` derives `category` itself,
point-in-time. The mechanism survived from a design that assumed these categories fed model fitting.

Three numbers also described one concept: the comment said 80/20, the constant was 100/0, and
`ml_lotto/config.py:57` is 85/15. The comment claimed `(matches ml_lotto/config.py)`, which was
false, and acting on it - setting this side to 0.85 - would have changed HMC categorisation for the
last 15% of draws, changed `lotto_trigger_periods.json`, and broken train/serve parity while training
stayed put.

**Fix.** Removed the dead slice and the misleading log lines; `calculate_days_since_last_hit` is now
called on `all_draws` with a comment stating why that is correct and that training does not consume
the value. Removed the now-unused `VALIDATION_SPLIT_RATIO` import from `hmc_analyzer.py` and the
dead constant from `lotto_analysis/config/config.py`, replacing it with a note pointing at
`ml_lotto/config.py` as the only split that exists. **Neither ratio was changed.**

**Measured before/after.** Behaviour-preserving by construction, and verified:

- Category distribution unchanged: Hot=30, Medium=7, Cold=10.
- `data/lotto_trigger_periods.json` byte-identical.
- Isolation test: `drawpick.py` run with the fix applied and with it reverted produced the identical
  hash for every artifact (`c4e8a85...` for `lotto_hmc_categorization_validated.json`). The drift
  against the committed copy predates this change - the committed `data/` was already stale.
- `lottery_picks.txt` Line 1 unchanged: `[2, 4, 5, 27, 42, 43]` + bonus 45.
- All six models unchanged to 4 dp: AUC 0.5074 / 0.5011 / 0.5118 / 0.5257 / 0.4979 / 0.5454, overfit
  gaps 0.0190 / 0.0197 / 0.0511 / 0.0534 / 0.0331 / 0.0051.

**Tests.** No new test - there is no behaviour to assert, the change removes code. Covered by the
existing 79: `test_walk_forward_parity.py` (parity across the artifacts this touches),
`test_no_constant_features.py`, `test_model_capacity.py`. All 79 pass after the change.

**Note for the future.** The system is deliberately **not** 85/15 end to end. ML training holds out
15% (`ml_lotto/config.py`). The analysis layer computes over all draws, which is correct for
serving-time artifacts. Do not "harmonise" them.

### F-1 — The freshness target was sized for 7 balls while a line has 6 slots

**Resolved 2026-09-16.** `lotto_7_number_freshness_results.json` now carries a second
distribution, `distribution_analysis_6_main`, built from the 6 main balls only, and
`get_optimal_pattern_distribution` reads that instead of the 7-ball one. The target went from
`{0:4, 1:2, 2:1}` (sums to 7) to `{0:3, 1:2, 2:1}` (sums to 6) — the genuine mode of the main-ball
distribution, 69 of 497 draws. The function now raises if the key is missing or the target is the
wrong width, rather than silently using a 7-wide one, and `predictor.py` no longer claims a
proportional adjustment it never made. Nine tests in `tests/test_freshness_target.py` cover it.

Generated lines did **not** change on current data: both the old and new targets yield the same
initial bin priority `[0, 1, 2]`, so selection picked identically. The fix removes a real defect and
pins the contract; it did not improve the picks. Investigating that turned up **F-8**.

### F-2 — The bonus and bonus-to-main models trained on 100% of the data

**Resolved 2026-09-17.** `quickpick.py` now calls `calculate_train_val_split(len(all_draws))` once
and passes `training_end_draw` / `validation_start_draw` into both `train_bonus_model` and
`train_bonus_to_main_model`. Both build a chronological validation set, score it with
`calculate_comprehensive_metrics`, and return those metrics; `train_all_models` takes them as
`extra_metrics` and merges them into `compare_models`, so all six models now sit in
`model_metrics/model_comparison.csv` on the same 60-draw hold-out.

`calculate_topk_accuracy` gained a `groups` argument for this. The bonus-to-main model scores only
the numbers in the current bonus window, so its rows per draw vary (9-10, not 47) and the old fixed
reshape would have collapsed the whole validation set into one "draw". Passing the per-row draw
index makes Top-K a real within-draw metric for it.

First out-of-sample numbers for the two models, on 60 validation draws:

| Model | Val AUC | PR-AUC Lift | Top-7 Lift |
|:--|--:|--:|--:|
| Bonus Ball Predictor | 0.461 | 0.90 | 0.67 |
| Bonus-to-Main Transition Predictor | 0.434 | 0.93 | 0.94 |

Same verdict as the four main models — chance, slightly below it here — which is the expected
answer for a fair draw. The point was to be able to see it.

Both models now fit 85% of the draws rather than 100%, so the probabilities in `lottery_picks.txt`
changed (bonus top pick 21 -> 10, bonus-to-main #1 27 at 23.0% rather than 33.9%). Main-number
picks are unchanged. The bonus-to-main trainer's duplicated training/validation loop was folded
into one `_build_bonus_to_main_dataset` helper.

### F-3 — The decision threshold was chosen and scored on the same rows

**Resolved 2026-09-17.** `calculate_comprehensive_metrics` now splits the validation window
chronologically on draw boundaries (`split_threshold_tuning_rows`): the earlier 30 draws pick the
F1-maximising threshold, the later 30 carry every threshold-dependent number — accuracy, precision,
recall, F1, both confusion matrices and the classification report. The default-threshold columns
moved to the same held-out half, so the "Default vs Optimal" table compares like with like.
AUC, PR-AUC, Top-K and calibration are threshold-free and still use the whole 60-draw window.

For the bonus-to-main model the split reuses the per-row draw index added for F-2, since its
candidate pool varies by draw; it lands at 281 tuning / 286 reporting rows rather than a clean half.

Effect on the scoreboard — the threshold-free columns are unchanged to the last digit, which is
what confirms only the operating point moved:

| Model | F1 before | F1 after | Recall before | Recall after |
|:--|--:|--:|--:|--:|
| Momentum Specialist | 0.261 | 0.247 | 1.00 | 0.84 |
| Complexity Explorer | 0.261 | 0.254 | 0.90 | 0.86 |
| Conservative Pool Generator | 0.260 | 0.247 | 1.00 | 0.91 |
| Jackpot Optimizer | 0.229 | 0.217 | 0.83 | 0.71 |
| Bonus Ball Predictor | 0.046 | 0.038 | 0.98 | 0.67 |
| Bonus-to-Main Transition Predictor | 0.256 | 0.247 | 1.00 | 0.61 |

Every model's reported F1 fell once the threshold stopped being scored on its own tuning data.
Selection never used these thresholds, so `lottery_picks.txt` is unchanged.

The compounding half of the original report is **not** fixed and was not a defect: maximising F1
at a ~15% positive rate still drives the threshold to roughly the base rate, so recall stays high
and precision stays near the base rate. That is what F1-maximisation does on imbalanced data, and
the columns should still be read after AUC, PR-AUC and Top-K lift, not before them.

`tests/test_threshold_holdout.py` covers it (6 tests): the split is chronological, disjoint and on
draw boundaries, it handles the variable-width bonus-to-main draws, and a model that separates
winners in the tuning half but ranks them last in the reporting half now reports recall 0.0 where
the old code reported 0.50.

### F-4 — The probability array was built conditionally but read positionally

**Resolved 2026-09-17.** `generate_predictions` in `ml_lotto/prediction/predictor.py` now builds one
row per number unconditionally, indexing `features_dict[num]` directly, so the array is
`MAX_NUMBER` long by construction and row *i* is always number *i+1*. A missing number raises a
`KeyError` naming it, at the point where it is missing.

The defect was a disagreement between two halves of the same file: the builder skipped absent
numbers (`if num in features_dict`) while `penalties.py`, `pool_generator.py` and `selection.py` all
read the result as `probabilities[num - 1]`. Demonstrated on a dict missing number 23: the array
comes back 46 long and `probabilities[24 - 1]` returns **number 25's** probability — every number
above the gap shifts down one, silently, with no length check anywhere.

Latent, and confirmed latent before the change: at the point `train_all_models` is called, all 47
numbers are present and no model is missing a single feature column. Re-running the pipeline
produced a `lottery_picks.txt` identical to the previous one apart from its timestamp, which is the
expected result — the fix removes a hazard, it does not change behaviour.

`tests/test_prediction_alignment.py` covers it (3 tests): every number keeps its own probability, a
missing number raises rather than shifting the array, and a `features_dict` built in reverse order
still yields a number-ordered array.

The same four lines still carry `feat.get(col, 0)`, a silent default for a missing *column* rather
than a missing number. That is logged separately as **F-9** rather than folded in here.

### C-14 — The scraper had one source and no main-draw check

**Resolved 2026-09-17.** Both halves of the report are now implemented in
`scripts/scrape_lotto.py`, and the docstring describes what the code does.

**Main-draw verification.** Both result pages carry Lotto Plus 1 and Plus 2 next to the main draw,
sharing its date, and deduplication is by date — so whichever game parsed first won, and nothing
checked which game it was. The two pages need different checks, because they identify the game
differently:

- *Archive table.* The game is in the row's link path (`/irish-lotto/results-...`), and every ball
  carries a class token per game, so a Plus row's balls read `irish-lotto-plus-1`. The parser now
  requires the exact `irish-lotto` token on every ball, and requires the row to hold **exactly one**
  `<ul class="balls">` — with two lists, the link and the balls could refer to different games.
- *lottery.ie.* Verified against the live page: the three games appear in order under repeated
  `Winning numbers` / `Bonus` labels with **no game heading to key on**. The main draw is the first
  pair, and the parser refuses the section if a `Plus` marker appears before it rather than guessing.

**Fallback source.** `parse_lottery_ie` implements the second parser the docstring had advertised
since the beginning. It is used as the data source when the primary yields nothing, and otherwise as
a check on it: dates present in both must carry identical numbers or **nothing is written** and the
run exits non-zero. A date only one source has is not a mismatch — the fallback page holds only the
most recent draws.

Verified against both live sites on 2026-09-17: 76 main draws parsed from the archive, 4 from
lottery.ie, and all 4 shared dates agreed ball for ball.

```
Verified 4 shared date(s) against lottery.ie
Using irish.national-lottery.com. Latest draw: 16 Sep 2026 (Numbers: [4, 7, 19, 20, 35, 42] + Bonus: 31)
Found 1 new draw(s) to add:
  + 16 Sep 2026,04,07,19,20,35,42,31
```

`tests/test_scraper_sources.py` covers it (11 tests) against markup captured verbatim from both
live pages into `tests/fixtures/`. The Plus cases are produced by editing that real markup rather
than inventing a shape the sites do not use: a row retagged `irish-lotto-plus-1` yields no draws, a
row holding two ball lists is dropped while its neighbours survive, the lottery.ie section returns
the Lotto numbers and not Plus 1's, and a reordered section is skipped.

Already fixed earlier: 7-ball uniqueness, date-object deduplication, non-zero exit on failure.

### C-15b — The tree models memorised their training sets

**Resolved 2026-09-17.** Gap 0.383 -> 0.053, validation AUC unchanged within noise.

| | Train AUC | Val AUC | Gap | Top-7 Lift |
|:--|--:|--:|--:|--:|
| before | 0.911 | 0.528 | 0.383 | 1.175 |
| after | 0.579 | 0.526 | **0.053** | 1.119 |

Validation moved -0.003 AUC against a 2 SE noise floor of 0.031, and Top-7 AvgCaught moved well
inside its 0.227 floor. Nothing was gained or lost in predictive terms; the wasted capacity is gone.

**Root cause, and why the obvious fix would have been inert.** `ENABLE_HYPERPARAMETER_TUNING` is
`True` in `quickpick.py:28`, so `MODEL_2_CONFIG['algorithm_params']` is only a starting point —
`get_random_forest_grid(quick=True)` overrode it every run. That grid offered
`max_depth: [5, 10, None]` with no `min_samples_leaf` and no `max_features`, and its CV roc_auc came
out at 0.5103, i.e. chance. A search that cannot tell its candidates apart picks arbitrarily among
them, and it kept landing on `max_depth=10` with `min_samples_leaf=1`. Editing only the config would
have changed nothing that runs.

**Fix.** Both places are constrained: `MODEL_2_CONFIG['algorithm_params']` is now
`max_depth=4, min_samples_leaf=300, max_features=0.5, class_weight='balanced_subsample'`, and both
random-forest grids search only within that envelope (depths 3-6, leaves 100-500, `max_features`
0.3-sqrt). The grid now picks `max_depth=4, min_samples_leaf=500`; 12 fits instead of 24, 38s
instead of 71s.

Measured on the exact Model 2 frames a real run builds (15,839 train / 2,820 val rows). The
selection rule was lowest train/val gap among candidates whose validation AUC did not fall — all
validation differences below are noise:

| Forest | Train AUC | Val AUC | Gap |
|:--|--:|--:|--:|
| depth 10, leaf 1 (the grid winner) | 0.912 | 0.528 | 0.383 |
| depth 6, leaf 50, mf 0.5 | 0.689 | 0.530 | 0.160 |
| depth 6, leaf 100, mf 0.5 | 0.652 | 0.529 | 0.123 |
| depth 5, leaf 200, mf 0.5 | 0.619 | 0.521 | 0.098 |
| depth 4, leaf 300, mf 0.5 | 0.595 | 0.535 | 0.060 |
| depth 4, leaf 500, sqrt | 0.577 | 0.521 | 0.056 |

`lottery_picks.txt` changed: Model 2's line is `[6, 23, 37, 39, 41, 46]` rather than
`[6, 17, 37, 39, 41, 46]` — a different model picks differently. Model 3's line moved 23 -> 17 as a
consequence, which is the cross-model diversity penalty releasing 17 once Model 2 took 23, not a
second change.

`tests/test_model_capacity.py` covers it (4 tests). The behavioural one fits the configured
pipeline on features that carry no information about the label: the constrained forest scores 0.61
on its own training rows, the old one 0.878. The others pin the config and assert no tuning
candidate — quick or extensive — escapes the envelope, since one unconstrained candidate is enough
to bring the memorising model back.

#### The other models — done 2026-09-17, same pass

The report's closing line, "worth reviewing for all four models", is now done. Every model's gap is
at or below 0.054; no validation AUC fell.

| Model | Gap before | Gap after | Val AUC before | Val AUC after |
|:--|--:|--:|--:|--:|
| Jackpot Optimizer (random forest) | 0.383 | 0.053 | 0.528 | 0.526 |
| Complexity Explorer (XGBoost) | 0.165 | **0.019** | 0.507 | 0.507 |
| Bonus-to-Main (logistic) | 0.150 | **0.033** | 0.434 | 0.498 |
| Bonus Ball (logistic) | 0.135 | **0.005** | 0.461 | 0.545 |
| Conservative Pool Generator (CatBoost) | 0.051 | 0.051 | 0.512 | 0.512 |
| Momentum Specialist (logistic) | 0.020 | 0.020 | 0.501 | 0.501 |

**Complexity Explorer.** Same shape of fix as Model 2, in the same two places. Config is now
`max_depth=2, n_estimators=50, learning_rate=0.03, min_child_weight=500, reg_lambda=20`, and both
XGBoost grids search inside that envelope. `scale_pos_weight` is pinned to 1 in the quick grid
because that is the operating point the gap was measured at. The dead `use_label_encoder` parameter
was dropped — XGBoost has ignored it for several releases and warned on every fit.

| Forest of stumps | Train AUC | Val AUC | Gap |
|:--|--:|--:|--:|
| depth 3, min_child_weight 3 (the grid winner) | 0.672 | 0.507 | 0.165 |
| depth 3, mcw 200, lr 0.05, L2 10 | 0.568 | 0.520 | 0.049 |
| depth 2, mcw 300, lr 0.03, L2 20 | 0.545 | 0.515 | 0.030 |
| depth 2, mcw 500, lr 0.03, L2 20, 50 trees | 0.526 | 0.507 | 0.019 |

**The two logistic models needed a different lever, and finding out why mattered.** Sweeping `C`
downward barely moved either gap — 0.135 -> 0.110 for the bonus model across two orders of
magnitude. L2 shrinks coefficients but preserves their ranking, and AUC sees only the ranking, so
L2 cannot reduce a rank-metric gap however hard it is applied. The capacity is in the feature
count: 32 features against 337 positive training rows, and 35 against 462.

The gap is real optimism rather than an unlucky validation window. Refitting the bonus model on the
first 80% of its training window scores 0.614 in-sample, 0.511 on the held-out tail of the *training*
window and 0.503 on the validation window — the drop reproduces on a slice that is not the
validation set.

So both moved to L1, which zeroes features outright: bonus `C=0.05` (5 of 32 features survive),
bonus-to-main `C=0.005` (2 of 35).

**A cost worth knowing about.** The bonus model's probabilities now span 1.9%-2.5%, so all six
entries in `lottery_picks.txt` print as `2.4%`. The ranking behind them is still well defined (241
distinct values across the validation rows) but the displayed figures no longer discriminate. That
is what a model with no signal honestly looks like; if the printed spread matters more than the
gap, `C=0.1` keeps 17 features and a 1.1%-3.5% spread at a gap of 0.096.

**These choices were informed by the same 60 validation draws they are reported on**, so the
validation AUC rises above (bonus +0.084, bonus-to-main +0.064) are not evidence of a better model.
The criterion was the train/val gap, with a guard that validation must not fall; the AUCs remain at
chance, which is the correct answer for a fair draw.

All four main lines and both auxiliary predictions changed in `lottery_picks.txt`, since four of the
six models are different models now.

---

## Appendix B — C-5 full write-up (resolved)

Kept for reference. The analysis below led to the decision to **delete** the seven leaking features
rather than rebuild them point-in-time: removing them moved every validation metric by less than
2 SE while cutting the Jackpot Optimizer's train/val AUC gap from 0.380 to 0.148, so they carried no
signal. Section numbers inside this appendix are the original ones.

### 1. Summary

`PointInTimeFeatureEngine` computes a genuine point-in-time feature row for every historical draw —
that was the whole purpose of `walk_forward.py`. But a subset of features are not computed from the
draw history at all. They are copied out of `base_features_dict`, which holds one value per number
derived from the **entire timeline**, and that same value is written into every training row for
that number.

Two separate mechanisms produce this:

**(A) Explicit static passthrough.** The feature is listed in the `rec` dictionary but its value is
read straight from the static dict. Fourteen features do this, e.g. `walk_forward.py:333`:

```python
'odd_even_json': static_feat.get('odd_even_json', 0.5),
```

**(B) Silent fallback.** The engine never produces the name at all, and the row builder substitutes
the static value without comment — `walk_forward.py:449` (and `:488` for the bonus dataset):

```python
row = {fn: rec.get(fn, static_feat.get(fn, 0)) for fn in all_feature_names}
```

Rev 3 added a warning that prints the (B) names on every run, so the list is at least visible. The
values themselves are unchanged.

---

### 2. Why it matters

These are not innocuous constants. They are **statistics estimated from draw outcomes over the full
dataset, including the validation period**, and then fed back in as inputs.

Take `sum_contribution_json`. Its source, `data/lotto_sum_contribution_validated.json`, stores per
number:

```json
"1": {
  "contribution_score": 0.142923238062531,
  "mean_with": 124.04918032786885,
  "mean_without": 149.0619266055046,
  "appearances": 61,
  "p_value": 1.38896544408424e-09
}
```

`mean_with` is "the average draw sum on draws where number 1 appeared". That is computed from the
outcomes — including the 60 validation draws the model is later scored on. The same is true of
`range_spread_json` (`mean_with` / `mean_without` / `appearances`) and `odd_even_json`
(`affinity_score` conditioned on appearances).

Two distinct consequences:

1. **Target leakage.** A statistic computed from outcomes in the validation window is used as an
   input when predicting that window. Any validation score is therefore optimistic by an unknown
   amount, and cannot be used to compare model variants honestly.
2. **Zero temporal variance.** Because the value never changes across the ~15,800 training rows for
   a given number, the model can only learn a per-number fixed effect from it. It contributes
   nothing to "is this number due *now*", which is the entire question.

A third, separate problem applies to `series_recent` specifically — see §4.

**An honest caveat:** current validation AUC is ≈ 0.50, so this leakage is evidently *not* inflating
results much today. Fixing it is unlikely to change the headline numbers. The reason to fix it is
that until it is fixed, you cannot tell whether a future improvement is real or is the leak talking.

---

### 3. Exact scope — what actually reaches a model

This is narrower than the Rev 2 write-up implied, and worth pinning down before any work starts.

The warning currently prints **23** names, but none of them are selected by
`expand_feature_selection`, so they never enter any model's `X`. They are materialised as DataFrame
columns and then dropped:

```
appearance_count, appearance_trend_raw, appearance_volatility_raw, avg_gap_days,
freshness_c0_weight, freshness_c1_weight, freshness_c2_weight, in_regime_shift,
last_peak_distance, last_trough_distance, lt_category, lt_cold_weight, lt_hot_weight,
lt_medium_weight, lt_statistical_confidence, older_count, peak_count, recent_count,
regime_shifts_detected, std_gap_days, trend_is_significant, trough_count, very_recent_count
```

These are **wasted work, not leakage.**

The features that genuinely reach a trained model — taken from the `Final features (...)` lines of
the last run — are these seven:

| Feature | Source | M1 (15) | M2 (22) | M3 (33) | M4 (8) |
|:--|:--|:-:|:-:|:-:|:-:|
| `odd_even_json` | `lotto_odd_even_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `range_spread_json` | `lotto_range_spread_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `sum_contribution_json` | `lotto_sum_contribution_validated.json` | ✓ | ✓ | ✓ | ✓ |
| `window_saturation_penalty` | `window_saturation.py` over hmc + odds | | ✓ | ✓ | |
| `lt_category_alignment` | `lotto_long_term_patterns.json` | | ✓ | ✓ | |
| `lt_recency_weight` | `lotto_long_term_patterns.json` | | ✓ | ✓ | |
| `series_recent` | `hmc_data['series']` via `extractor.py:305-320` | | | ✓ | |

Proportion of each model's trained feature set that is a full-history constant:

```
Model 1 Momentum Specialist        3 / 15   (20%)
Model 2 Jackpot Optimizer          6 / 22   (27%)
Model 3 Complexity Explorer        7 / 33   (21%)
Model 4 Pool Generator             3 /  8   (38%)
```

And they are not fringe features. From the current `lottery_picks.txt`:

```
Line 3 Complexity Explorer   #1  series_recent           0.0548   <- top feature in the model
Line 2 Jackpot Optimizer    #10  range_spread_json       0.0438
Line 1 Momentum Specialist   #8  sum_contribution_json   0.0163
```

---

### 4. `series_recent` is a different and worse bug

The other six are static statistics that *could* defensibly be per-number constants if they were
estimated in-sample. `series_recent` is not: it is explicitly a **recency window**, and it has been
frozen at one date. `ml_lotto/features/extractor.py:305-320`:

```python
series_total = 0
series_recent = 0
for pattern_name, occurrences in series_patterns.items():
    for occurrence in occurrences:
        series_total += occurrence.get('count', 0)
        end_date = pd.to_datetime(occurrence.get('end_date', ''))
        days_ago = (current_timestamp - end_date).days
        if days_ago <= 60:                      # <-- 60 days before the LATEST draw
            series_recent += occurrence.get('count', 0)
```

`current_timestamp` is the most recent draw date. So for a training row at draw 200 (early 2023),
`series_recent` answers "did this number have a series ending in the 60 days before **September
2026**" — a question about the future, injected into a 2023 row. It is Model 3's single
highest-importance feature.

This one should be fixed first regardless of what is decided about the rest.

---

### 5. Evidence

Reproduced read-only against the live 497-draw history:

```
engine features produced:                                       72
time-invariant across draw 200 vs draw 450:                     18
  (was 20 before Rev 3 fixed avg_days_between_bonus,
   timing_decay_weight and composite_transition_score)

of those 18, actually selected into a model:                     7
of those 18, derived interaction terms built on the others:      4
  recent_14_x_bonus_hit_contribution_interaction
  total_count_x_bonus_hit_contribution_interaction
  total_count_x_recent_14_interaction
  triple_hot_0_recent
silently substituted but never selected (dead columns):         23
```

---

### 6. Fix plan

Four phases. Phases 0 and 1 are small and independently useful; Phase 2 is the real fix; Phase 3
is what makes it stick.

#### Phase 0 — Measure before building anything  *(~1 hour)*

Do not refactor six features on the assumption that they matter. Find out first.

1. Record the current validation block as a baseline (`model_comparison.csv` is already there).
2. Remove the seven names from the four model `features` lists in `ml_lotto/config.py`.
3. Re-run `quickpick.py` and compare Val AUC, PR-AUC lift and Top-7 lift.

Interpretation:

- **Metrics unchanged** (most likely, given AUC ≈ 0.50) → the features carry no signal. Delete them
  and close this issue. No point-in-time implementation needed at all. This is the cheapest good
  outcome and it is genuinely plausible.
- **Metrics drop materially** → the signal is real *or* the leak was doing the work. You cannot tell
  which yet, so proceed to Phase 2 and compare against this measurement.
- **Metrics improve** → they were pure noise plus leak. Delete them.

Phase 0 is reversible, touches one file, and could make Phases 1–2 unnecessary.

#### Phase 1 — Stop the two cheap problems  *(~2 hours)*

Independent of Phase 0's outcome.

1. **Stop materialising the 23 dead columns.** `get_all_feature_names(features_dict)` returns every
   key in the features dict, so the `**adv_feat` / `**lt_feat` splats in `extractor.py:360-375` drag
   23 unused names into every training DataFrame. Build `all_feature_names` from the union of the
   model configs' expanded feature lists instead. Saves 23 × 15,800 cells per dataset build, ×4
   datasets, and removes the misleading warning.
2. **Narrow the Rev 3 warning** to only the names that a model actually selected, so it reports
   leakage rather than unused columns.

#### Phase 2 — Point-in-time implementations  *(the real work, ~1–2 days)*

Only if Phase 0 says the features matter. Every one of these is derivable from the draw sequence the
engine already holds, so they belong in `walk_forward.py` next to the existing prefix-sum machinery
— not in a separate analyzer.

Add to `_precompute_matrices()` the running quantities each feature needs, then read the slice at
`t` in `extract_features_at_draw`.

**`sum_contribution_json`** — "mean draw-sum when this number appears, vs when it does not",
restricted to draws `0..t-1`. Both terms come from two prefix sums:

```
draw_sum[i]                = sum of the 6 main balls in draw i
cum_sum_with[t, num]       = cumsum over i<t of draw_sum[i] * matrix_main[i, num]
cum_count_with[t, num]     = cum_main[t, num]                       (already exists)
cum_sum_all[t]             = cumsum over i<t of draw_sum[i]

mean_with    = cum_sum_with[t,num] / cum_count_with[t,num]
mean_without = (cum_sum_all[t] - cum_sum_with[t,num]) / (t - cum_count_with[t,num])
score        = normalise(mean_with - mean_without)
```

O(1) per number per draw. Guard `t` small / zero appearances with the existing 0.5 default.

**`range_spread_json`** — identical shape, substituting `draw_span[i] = max(main) - min(main)` for
`draw_sum[i]`.

**`odd_even_json`** — affinity is the number's parity weighted by how often that parity wins. Keep a
running count of odd-balls-per-draw over `0..t-1`; the per-number score is a function of the number's
own (fixed) parity and that running rate.

**`window_saturation_penalty`** — `window_saturation.py` computes saturation rates from HMC category
counts. Port it to take a draw-index bound and call it with `t`. Cache per `t` since it is
category-level, not per-number — 3 values per draw, not 47.

**`lt_category_alignment` / `lt_recency_weight`** — from `long_term_pattern_analyzer`. These are
category-level statistics too (alignment of HMC category with realised win rate), so the same
"compute once per `t`, fan out to 47 numbers" trick applies. This is the most involved of the six;
if effort has to be cut, cut here — they appear in two models at modest importance.

**`series_recent` / `series_total`** (§4) — the engine has `self.draw_dates`, so the fix is to
evaluate the 60-day window against `draw_dates[t]` instead of a fixed `current_timestamp`. The series
occurrence list is already in `hmc_data`; filter it by `end_date <= draw_dates[t]` and
`(draw_dates[t] - end_date).days <= 60`. Sort the occurrences once in `__init__` and use
`bisect` to get an O(log n) slice per draw.

> **Convention to preserve:** the serving row uses `t = N` with the estimated next-draw date. Every
> new feature must be reachable at `t = N` or the serving row will KeyError. Rev 3's
> `extract_features_for_next_draw()` is the single entry point — use it.

#### Phase 3 — Lock it in  *(~2 hours)*

1. **Extend `tests/test_walk_forward_parity.py`** with the parity assertion for each newly
   implemented feature: the engine's value at `t = N` must equal the serving JSON's value, 0/47
   mismatches — the same contract `recent_*` and `total_count` are already held to.
2. **Add `tests/test_no_constant_features.py`**: no feature selected by any model config may be
   identical for a given number across draw 200 and draw 450. This test **fails today** with the
   seven names listed in §3, which is the point — it encodes the bug, then passes when it is fixed.
3. **Re-run the Phase 0 comparison** and record the before/after.

---

### 7. Verification that the fix is real

The leak is only genuinely gone when both of these hold:

1. `test_no_constant_features.py` passes.
2. **A label-permutation check**: shuffle `hit` within each draw, retrain, and confirm validation
   AUC collapses to 0.50 ± noise. If a permuted-label model still scores above chance, a feature is
   still carrying outcome information from the validation window and the leak was not closed.

The second check is the one that actually proves it, and it is worth building once — it is the same
harness described in F-17 for answering whether any edge exists at all.

---

### 8. Risks and things not to do

- **Do not "fix" this by deleting the static fallback and letting it raise.** Roughly 23 names would
  immediately KeyError on a legitimate path. Phase 1.1 removes those names first; only then is a
  hard failure safe.
- **Do not change feature semantics silently.** Changing `odd_even_json` from a full-sample score to
  an expanding-window score changes what the model learns. Re-run Phase 0's comparison after each
  feature, not once at the end, or a regression cannot be attributed.
- **Watch the early draws.** An expanding window at `t = 100` has few observations, so
  `mean_without` and friends will be noisy or undefined. Keep the existing neutral defaults (0.5,
  0.0) and prefer them over a wild estimate; `TRAINING_START_DRAW = 100` already gives some burn-in.
- **Do not regenerate the source JSONs per draw.** These are analyzer outputs over the whole file;
  calling `drawpick.py` 400 times is not the fix. The point-in-time versions belong inside the
  engine, computed from the matrices already in memory.
- **Expect no headline improvement.** Validation AUC is at chance. This work makes the measurement
  trustworthy; it is not a performance change, and it should not be reported as one.

---

### 9. Recommendation

Run **Phase 0 first**. Three of the seven features are in every model and the other four are in two
models each, but validation says the models have no skill, so there is a real chance that deleting
all seven changes nothing measurable — in which case the correct fix is deletion and this issue
closes in an afternoon.

Regardless of Phase 0, do **Phase 1** (cheap, removes 23 wasted columns and makes the warning
honest) and fix **`series_recent`** (§4), which is a genuine future-data leak into a 2023 training
row and is Model 3's top feature.

Reserve the full Phase 2 for the case where Phase 0 shows the features carry weight.
