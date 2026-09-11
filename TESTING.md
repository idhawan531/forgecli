# Testing ForgeCLI

Work top to bottom. Anything marked **[GAP]** has never actually been executed by
anyone — those are where the bugs are.

Assumes `cd ~/AIAgents/forgecli` and an activated venv unless stated otherwise.

---

## 1. Automated suite

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

Expect 20 passed, ruff clean. This covers the CLI surface and the generator, but
**nothing here ever runs a generated project** — that's sections 4-6.

---

## 2. Clean-install test (verifies the packaging fix)

The bug this catches: templates living outside the package so a non-editable install
ships without them.

```bash
rm -rf /tmp/fc-clean /tmp/fc-venv
python3 -m venv /tmp/fc-venv
/tmp/fc-venv/bin/pip install .          # note: no -e
/tmp/fc-venv/bin/forgecli templates
/tmp/fc-venv/bin/forgecli generate "a rest api for short links" -o /tmp/fc-clean
ls /tmp/fc-clean/*/
```

**Pass:** three templates listed, project generated with main.py, README.md,
requirements.txt, test_main.py, .gitignore, .github/workflows/ci.yml.
**Fail:** `FileNotFoundError` or an empty template directory → package data isn't
shipping.

---

## 3. Selection, flags and errors

```bash
forgecli --help
forgecli generate --help
forgecli templates
```

Auto-selection — check the panel names the expected template and keywords:

| Command | Expect |
|---|---|
| `forgecli generate "a rest api for short links" -o /tmp/t` | `fastapi_api`, matched: api, rest |
| `forgecli generate "a react dashboard for habits" -o /tmp/t` | `vite_react`, matched: react, dashboard |
| `forgecli generate "a terminal pomodoro timer" -o /tmp/t` | `rich_tui`, matched: terminal |
| `forgecli generate "something completely unrelated" -o /tmp/t` | `fastapi_api`, matched: none (fallback) |
| `forgecli generate "a web service" -o /tmp/t` | tie → `fastapi_api`, matched: none |

Flags and errors:

```bash
forgecli generate "anything" -o /tmp/t --name my-custom-name   # folder = my-custom-name
forgecli generate "a rest api" -o /tmp/t -t rich_tui           # override wins, no auto panel
forgecli generate "a rest api" -o /tmp/t -t nonsense           # exit 1, lists valid keys
forgecli generate "" -o /tmp/t                                 # exit 1, "must not be empty"
forgecli generate "   " -o /tmp/t                              # exit 1, same
echo $?                                                         # confirm the exit codes
```

Collision handling — run the same command three times:

```bash
forgecli generate "collision test" -o /tmp/t
forgecli generate "collision test" -o /tmp/t
forgecli generate "collision test" -o /tmp/t
ls /tmp/t | grep collision     # expect collision-test, collision-test-1, collision-test-2
```

Naming (the Phase 0 fix) — this must NOT produce a 60-character folder:

```bash
forgecli generate "A minimal URL shortener API with FastAPI and in-memory storage" -o /tmp/t
```

Unicode and punctuation shouldn't crash:

```bash
forgecli generate "café / naïve — api (v2)" -o /tmp/t
```

Prompt log — check `prompts_log.md` gains one entry per run, under Part 2, with the
template name and the suggested next prompts.

---

## 4. **[GAP]** Does the generated FastAPI project actually run?

```bash
forgecli generate "a rest api for short links" -o /tmp/run --run-tests
cd /tmp/run/*/
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload &
sleep 3
curl -s localhost:8000/ ; echo
open http://127.0.0.1:8000/docs     # Swagger UI should render
kill %1
```

**Pass:** JSON response, docs page loads.

---

## 5. **[GAP]** Does the generated React project actually run?

This is the one I'd bet on failing — see the note at the bottom.

```bash
forgecli generate "a react dashboard for habits" -o /tmp/run
cd /tmp/run/*/
npm install
npm test          # <-- expect this to FAIL today
npm run dev       # open the URL it prints; heading should be your description
```

**Pass:** `npm test` reports 1 passing test, dev server renders the description as
an `<h1>`.

Then the flag that depends on it:

```bash
forgecli generate "a react dashboard for habits" -o /tmp/run2 --run-tests
```

**Pass:** the summary panel says `Tests: Passed` and that is true.
**Fail:** it says Passed while `npm test` in section 5 failed → the flag is lying.

---

## 6. **[GAP]** Does the generated Rich TUI project actually run?

```bash
forgecli generate "a terminal pomodoro timer" -o /tmp/run
cd /tmp/run/*/
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
.venv/bin/python -m pytest -q
```

---

## 7. Graceful degradation

Missing toolchain — the CLI must skip, not crash:

```bash
# temporarily hide npm
PATH=/usr/bin:/bin forgecli generate "a react app" -o /tmp/t --run-tests
```

**Pass:** "Skipped tests: missing toolchain", exit 0.

Timeout — verify the 120s guard exists by reading `_run_template_tests` in
`src/forgecli/cli.py`; to exercise it, temporarily set a template's `test_command`
to `python -c "import time; time.sleep(999)"` and confirm it is killed and reported.

Unwritable output directory:

```bash
mkdir -p /tmp/ro && chmod 500 /tmp/ro
forgecli generate "anything" -o /tmp/ro        # expect a clean error, not a traceback
chmod 755 /tmp/ro
```

---

## 8. CI

```bash
gh run list --limit 5
gh run view --log-failed
```

Or check the Actions tab. The matrix is 3.9 / 3.11 / 3.12; the smoke step runs
`--run-tests` on fastapi_api, so section 4 failing means CI fails too.

---

## 9. Cleanup

```bash
rm -rf /tmp/t /tmp/run /tmp/run2 /tmp/fc-clean /tmp/fc-venv
git checkout prompts_log.md      # discard entries from testing
```

---

## Known issue to confirm first

`vite.config.js.j2` has no `test` block, so Vitest runs in its default **node**
environment. `@testing-library/react`'s `render()` needs a DOM, so `npm test` on a
generated React project should fail with something like `document is not defined`.

The earlier verification only asserted that `package.json` *contained* the right
strings — the test was never executed. Confirm in section 5, then fix:

```
In the vite_react template's vite.config.js.j2, add a `test` block to the defineConfig
call setting environment to "jsdom" and globals to true, so Vitest can run
@testing-library/react's render(). Then generate a project from the vite_react
template, run `npm install && npm test` in it, and confirm the test actually passes
before reporting done — do not verify by inspecting package.json contents.

Separately, App.jsx.j2 and App.test.jsx.j2 interpolate {{ description }} directly
into JSX and into a JS double-quoted string. Escape it properly so a description
containing a double quote, brace or backslash cannot produce invalid JSX. Add a test
generating a project from a description containing " and { and assert the output parses.
```
