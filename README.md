# Personal Knowledge Management System

### Local-first bibliographic data engineering · MVP v0.2.0

A small, working Python pipeline for importing bibliographic JSON, keeping a local catalog consistent, and finding references through SQLite full-text search.

**Python 3.11+ · SQLite FTS5 · No third-party runtime dependencies · 17 automated tests**

> **Status:** functional MVP under active development. Includes a native local interface and command-line tools. AI-assisted retrieval, automatic synchronization, and study-plan generation remain future work.

## Why this project

A bibliographic catalog needs more than an import button: repeat imports must not create duplicates, changed records must refresh search results, and personal library data must stay separate from shareable code. This MVP implements and tests those foundations, exposes a native local interface, and keeps AI features as future work.

## What works today

| Capability | Implemented behavior |
| --- | --- |
| JSON import | Accepts bibliographic objects and Zotero-style API envelopes |
| Validation | Checks the entire input before opening the destination database |
| Repeat imports | Uses `(source, key)` identity to keep existing records unchanged |
| Updates | Refreshes metadata and the search index for an existing identity |
| Unified search | Searches reference titles/creators and enriched Drive metadata/contents, with accent-insensitive matching |
| Native interface | Opens catalogs, imports JSON, loads synthetic data, searches both sources, and opens verified source URL schemes |
| Local storage | Uses SQLite transactions; preserves each imported source object |
| Privacy | Runs offline; accesses only the explicitly provided input and destination |

## Architecture

```mermaid
flowchart LR
    A[Explicit JSON input] --> B[Validate and normalize]
    B --> C[Transactional import]
    C --> D[(SQLite catalog)]
    D --> E[FTS5 index via triggers]
    E --> F[CLI search]
```

No background synchronization or cloud service is used by the importer. The optional Zotero snapshot script makes explicit local read requests only.

## Quick start

Requires Python 3.11 or later with SQLite FTS5. From the repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python install_local.py
python examples/demo.py
python examples/demo_unified.py
```

Open the native interface with `python launch_gui.py` (requires Tkinter). On macOS, you can also use `Abrir PKM.command`. See [local interface instructions](docs/INTERFAZ_LOCAL.md) and [enriched catalog schema](docs/CATALOGO_ENRIQUECIDO.md).

The local installer copies the module into the active virtual environment without downloading packages. Run it again after editing `src/pkm`. The included `pyproject.toml` also supports conventional pip installation when build tools are available.

## A demonstration you can reproduce

[Demo walkthrough and verified output](docs/DEMO.md) · [Runnable demo](examples/demo.py) · [Synthetic input](examples/references.synthetic.json)

```text
1. First import:      10 inserted
2. Repeat import:      0 inserted; 10 unchanged
3. Title search:      10 results for "aprendizaje"
4. Creator search:    10 results for "ejemplo"
5. Update one title:   1 updated; 9 unchanged
6. Accent-free search: 1 result for "robotica"
7. Final catalog:     10 records; source file unchanged
```

All ten records are fictional. Each run creates a fresh temporary database, checks its results, and removes it on exit. The demo never reads personal catalog data.

## Use the command line

To keep a synthetic catalog for exploration, run from the repository folder:

```sh
python -m pkm import-json examples/references.synthetic.json --db data/demo.sqlite --source synthetic-demo
python -m pkm search aprendizaje --db data/demo.sqlite
python -m pkm search ejemplo --db data/demo.sqlite --limit 5
```

Run the import again to see unchanged-record counts. Use a distinct `--source` for each library. Commands print JSON and return a nonzero exit status on an error.

## Validation evidence

- **17 automated tests:** import and idempotence; FTS updates; validation without altering an existing catalog; duplicate input keys; API envelopes and library namespaces; malformed input; source/destination separation; read-only search without database creation. Additional tests cover interface catalog access, unified results, contents queries, limits, and preservation of database bytes.
- **Synthetic demo:** 10 initial imports, zero duplicate inserts on repetition, one metadata update, and search-index verification.
- **Local Zotero integration check:** 9 real references verified for titles, creators, dates, title/creator search, and repeat-import behavior. Only aggregate results are described here; the references and test database are not included.

Run the tests against the source code:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Validated locally on macOS arm64 with Python 3.13.5 and SQLite 3.45.3. Native-interface behavior was manually checked on macOS. No CI workflow or broader platform compatibility verification is claimed.

## Input contract and current limits

The input is a UTF-8 JSON list. Each record requires a nonempty string `key` and `title`; optional fields include `creators`, `date`, `DOI`, and `itemType`. Creator names may use `firstName`/`lastName` or `name`. API objects may wrap metadata in `data`.

- Identity is library/source plus key; there is no DOI/title matching across different keys.
- Repeated keys within one input file are rejected.
- The importer loads the complete JSON file in memory.
- Search treats query words literally and combines them with AND; it does not search attachments or document full text.
- BibTeX, RIS, keyless CSL JSON, attachment import, live library synchronization, automatic Drive inventory/enrichment from the UI and AI retrieval are not implemented.

## Privacy and repository boundaries

`data/` (except its empty placeholder), databases, `.venv/`, local reports, and private files are ignored by Git. The importer does not write back to Zotero. Explicitly inspect any real input before importing it: the full supplied record is retained in the local database.

The GitHub repository is public for portfolio review. All included example records are fictional; personal library metadata and local test databases remain outside version control.

## Repository guide

```text
src/pkm/                         Import, unified search, native GUI, and CLI
launch_gui.py                    Virtual-environment-aware macOS launcher
scripts/import_complete.py       Read-only local Zotero snapshot
examples/demo.py                 Self-checking synthetic demonstration
examples/references.synthetic.json  Ten fictional bibliographic records
tests/                           Seventeen automated tests
docs/DEMO.md                     Walkthrough and captured demo output
install_local.py                 Offline installation into an active venv
data/                           Local catalogs; excluded from version control
```
