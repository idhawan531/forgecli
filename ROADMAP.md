# ForgeCLI Roadmap

Goal: a scaffolder Ikshit actually reaches for. Deterministic core that always
works, with an optional Copilot layer on top.

## The problem this roadmap solves

Today `"a rest api for short links"` and `"a rest api for cat photos"` generate
byte-identical files apart from one title string. The description picks a template
and is then only ever used as a string literal. "One sentence in, a running project
out" isn't true yet.

## The central idea: a Spec in the middle

Don't wire description → files. Put a structured `Spec` between them:

```
description ──▶ extract ──▶ Spec ──▶ render ──▶ project
                              │                    │
                         (editable)          --enhance ──▶ Copilot CLI ──▶ tests ──▶ iterate
```

The Spec is what makes the layered approach work, because both layers consume the
same object:

- The **deterministic extractor** fills it from the description. Always works, no
  network, fully testable.
- **`--enhance`** passes it to Copilot as *structured context* — a far better prompt
  than the raw sentence ever was.
- **You** can edit it by hand, which is the difference between a demo and a tool.

```python
@dataclass
class Field:   name: str; type: str; optional: bool = False
@dataclass
class Entity:  name: str; plural: str; fields: list[Field]
@dataclass
class Spec:
    project_name: str
    description: str
    template_key: str
    entities: list[Entity]
    addons: list[str]
```

---

## Milestone 1 — Make the description matter

The one that closes the gap. Everything else is optional; this isn't.

### F1 — Spec extraction

```
Create src/forgecli/spec.py with Field, Entity and Spec dataclasses (see ROADMAP.md
for the shape) and a function `extract_spec(description, template_key, name=None) -> Spec`.

Entity extraction, heuristic and deterministic — no LLM calls:
- Strip leading stopwords and verbs ("a", "the", "build", "create", "simple",
  "minimal", "for", "that", "tracks", "manages").
- Find the head noun phrase after "for"/"of"/"to track"/"to manage", else the last
  noun phrase in the sentence. "a rest api for short links" -> "short links";
  "a react dashboard for tracking daily habits" -> "daily habits".
- Singularise and PascalCase it for the entity name ("short links" -> Link, dropping
  adjectives; "daily habits" -> Habit). Hand-roll the pluralisation rules for the
  common cases (s, es, ies, y->ies) rather than adding a dependency.
- Always give every entity an `id: int` field, plus `name: str` as a default.
- Infer extra fields from words present in the description: url/link -> `url: str`;
  date/daily/weekly/schedule -> `created_at: datetime`; price/cost/amount ->
  `amount: float`; done/complete/status -> `completed: bool`; count/score/total ->
  `count: int`.
- Never return zero entities — fall back to a single generic `Item` entity.

Add tests in tests/test_spec.py covering at least 12 real descriptions across all
three templates, including the zero-match fallback and multi-word adjective noun
phrases.
```

### F2 — `forgecli plan`

```
Add a `forgecli plan "<description>"` command that runs template selection and
extract_spec and prints the resulting Spec as a Rich tree — template, entities,
and each entity's fields with types — WITHOUT writing any files.

Add a `--spec-out <path>` option that also writes the Spec to a YAML file.
Add PyYAML as a dependency. Add tests asserting plan writes no files to disk.
```

### F3 — `--spec-file`

```
Add a `--spec-file <path>` option to `generate` that loads a Spec from YAML and
skips extraction entirely. When given, --template and the description argument
become optional (make `description` an optional argument that is required only when
--spec-file is absent, with a clear error if both are missing).

Validate the loaded YAML against the Spec dataclasses and fail with a readable
message naming the offending field, not a traceback.
```

This gives the real workflow, and it's the bit that makes ForgeCLI a tool rather
than a toy:

```bash
forgecli plan "a rest api for short links" --spec-out spec.yaml
$EDITOR spec.yaml          # fix what the heuristics got wrong, add fields
forgecli generate --spec-file spec.yaml
```

### F4 — Templates consume the Spec

```
Rewrite the three templates to render from Spec.entities instead of substituting
the description string.

fastapi_api:
- models.py.j2 — a Pydantic BaseModel per entity, with the spec's fields and types
- routers/{{ entity.plural }}.py.j2 — one router per entity with full CRUD over a
  module-level dict, proper 404s, and response models
- main.py.j2 — includes each router
- test_{{ entity.plural }}.py.j2 — TestClient tests per entity covering create,
  list, get, 404, and delete

rich_tui:
- A Rich table view over a list of the primary entity, with seeded example rows
  derived from the field types

vite_react:
- One list component and one add-form component per entity, with useState storage

Jinja must loop over entities — generating for a two-entity spec has to produce two
routers and two test files. Add a test asserting exactly that.
```

**After Milestone 1**, `"a rest api for short links"` produces a `Link` model, a
`/links` router with working CRUD, and passing tests against it. That is a real tool.

---

## Milestone 2 — Daily-use ergonomics

Deliberately ahead of the Copilot layer: this is the tier that decides whether you
actually reach for it, and it is cheap.

- **F5 — Add-ons.** `--with docker,precommit,devcontainer,makefile`, rendered from
  `templates_data/_addons/` and layered onto any template.
- **F6 — `forgecli.toml`.** `~/.config/forgecli/config.toml` plus a per-directory
  override: default output dir, author name, default add-ons, default template.
- **F7 — Custom template paths.** A `template_paths` config key so your own
  templates live outside this repo and survive a `git pull`. **This is the feature
  that makes it yours** — see the note at the bottom.
- **F8 — Git init.** `--git/--no-git`, defaulting on: `git init` plus an initial
  commit in the generated project.
- **F9 — `--dry-run`.** Rich tree of what would be written, writing nothing.
- **F10 — `forgecli doctor`.** Check for python, node, npm, git, copilot; report
  which templates and flags are currently usable on this machine.

---

## Milestone 3 — The Copilot layer

- **F11 — `--enhance`.** After scaffolding, shell out to `copilot -p "<prompt>"`
  inside the generated folder, with a prompt built from the Spec plus the template's
  `next_prompts`. Detect `copilot` on PATH; if absent, print a clear skip message and
  exit successfully — the deterministic path must never depend on it.
- **F12 — `--enhance --fix`.** Run the template's tests; on failure feed the failing
  output back to Copilot and retry, up to `--max-iterations` (default 3). Stop on
  pass, on iteration limit, or if two consecutive iterations produce no file changes.
- **F13 — Session transcript.** Every Copilot invocation, its prompt, a diff summary
  and the test result appended to `.forgecli/session.json` and summarised into
  `prompts_log.md`. The prompt log stops being decorative and becomes a byproduct of
  real work.

---

## Milestone 4 — If it earns it

Only worth doing if you're still using the tool in a month.

- `forgecli new-template <key>` — reverse-engineer a template from an existing
  project folder (copy the tree, replace the project name with `{{ project_name }}`)
- `forgecli replay <n>` — re-run generation n from the log
- Interactive Textual mode when run with no arguments
- PyPI release

---

## Explicitly not doing

- **Web gallery mode** (from the original plan) — a second app to build and host
  that nobody visits. The terminal is the product.
- **Scraping X for other entries** — that was contest-shaped, and the contest turned
  out to be a random draw.
- **Multi-agent orchestration** — complexity with no payoff at this size.
- **Cookiecutter compatibility** — you'd be maintaining someone else's spec forever.

---

## The thing that would actually get you using it

`fastapi_api`, `vite_react` and `rich_tui` are fine demos, but they aren't what you
repeat. Your repetitive work is RPA process design, draw.io diagrams and client
decks — and a template doesn't have to generate an app.

A `templates_data/` entry is just a folder of Jinja files. It could equally be:

- a UiPath REFramework project skeleton with your standard config, folder layout and
  exception handling
- a client engagement doc set — FDS skeleton, assumptions register, test-script
  workbook stub, folder structure named for the client
- an RPA flow-diagram starter with the standard shapes and naming already in place

With **F7** those live in your own private folder and `forgecli generate` becomes
the front door to work you genuinely do every few weeks. That is the difference
between a portfolio repo and a tool.

### Decision: build the engagement doc set

Of the three, this is the one to prototype. Reasoning:

- **UiPath REFramework skeleton — ruled out.** Studio already ships REFramework as a
  built-in template, so you'd be rebuilding something you get for free. And .xaml is
  verbose XML; Jinja-templating it is painful for little gain.
- **Flow-diagram starter — weak.** The hard part of a diagram is the content, not
  the empty file. A blank starter saves you a couple of minutes at most.
- **Engagement doc set — the real one.** You run many concurrent engagements, each
  one opens with the same folder tree and the same set of document stubs, nothing
  currently does it for you, and it is all text — exactly what a file-tree templater
  is good at. It is the only one of the three where the boilerplate is genuinely
  repeated and genuinely unautomated.

It also fits the Spec model cleanly: for this template the "entities" are robots or
processes, so `--spec-file` drives per-robot folders and per-robot document stubs.

```
engagement_docs/
├── {{ client }}-{{ project_slug }}/
│   ├── 01-requirements/
│   │   ├── assumptions-register.md.j2
│   │   └── requirements-log.md.j2
│   ├── 02-design/
│   │   ├── fds-{{ project_slug }}.md.j2        # section skeleton only
│   │   └── flow-diagrams/.gitkeep
│   ├── 03-build/
│   │   └── {{ entity.name }}/                   # one folder per robot
│   │       └── build-notes.md.j2
│   ├── 04-test/
│   │   └── test-scripts-{{ entity.name }}.md.j2
│   ├── 05-deploy/
│   │   └── deployment-checklist.md.j2
│   └── README.md.j2                             # client, scope, robots, status
```

Treat that tree as a first sketch, not a spec — you know what your engagements
actually need and the first version should be a copy of whatever your last one
looked like. Which is what **F11** (`forgecli new-template` from an existing folder)
is for: point it at your tidiest past engagement and let it derive the template,
rather than typing one out.

So the order becomes: Milestone 1, then F11 pulled forward to derive this template
from a real engagement folder, then F5-F7 designed around it.
