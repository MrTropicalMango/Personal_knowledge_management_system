# Personal Knowledge Management System

### Local-first bibliographic data engineering · MVP v0.1.0

A small, working Python pipeline for importing bibliographic JSON, keeping a local catalog consistent, and finding references through SQLite full-text search.

**Python 3.11+ · SQLite FTS5 · No third-party runtime dependencies · 8 automated tests**

> **Status:** functional MVP under active development. This is a command-line application. Broader source integrations and AI-assisted retrieval are future work.

## Why this project

A bibliographic catalog needs more than an import button: repeat imports must not create duplicates, changed records must refresh search results, and personal library data must stay separate from shareable code. This MVP implements and tests those foundations before adding a user interface or AI features.

## What works today

| Capability | Implemented behavior |
| --- | --- |
| JSON import | Accepts bibliographic objects and Zotero-style API envelopes |
| Validation | Checks the entire input before opening the destination database |
| Repeat imports | Uses `(source, key)` identity to keep existing records unchanged |
| Updates | Refreshes metadata and the search index for an existing identity |
| Full-text search | Searches titles and creators, including accent-insensitive matching |
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

No background synchronization, cloud service, or automatic connection to a personal library is used by the importer.

## Quick start

Requires Python 3.11 or later with SQLite FTS5. From the repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python install_local.py
python examples/demo.py
```

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

- **8 automated tests:** import and idempotence; FTS updates; validation without altering an existing catalog; duplicate input keys; API envelopes and library namespaces; malformed input; source/destination separation; read-only search without database creation.
- **Synthetic demo:** 10 initial imports, zero duplicate inserts on repetition, one metadata update, and search-index verification.
- **Local Zotero integration check:** 9 real references verified for titles, creators, dates, title/creator search, and repeat-import behavior. Only aggregate results are described here; the references and test database are not included.

Run the tests against the source code:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Validated locally on macOS arm64 with Python 3.13.5 and SQLite 3.45.3. No CI workflow or broader platform compatibility verification is claimed.

## Input contract and current limits

The input is a UTF-8 JSON list. Each record requires a nonempty string `key` and `title`; optional fields include `creators`, `date`, `DOI`, and `itemType`. Creator names may use `firstName`/`lastName` or `name`. API objects may wrap metadata in `data`.

- Identity is library/source plus key; there is no DOI/title matching across different keys.
- Repeated keys within one input file are rejected.
- The importer loads the complete JSON file in memory.
- Search treats query words literally and combines them with AND; it does not search attachments or document full text.
- BibTeX, RIS, keyless CSL JSON, attachment import, live library synchronization, a graphical interface, and AI retrieval are not implemented.

## Privacy and repository boundaries

`data/` (except its empty placeholder), databases, `.venv/`, local reports, and private files are ignored by Git. The importer does not write back to Zotero. Explicitly inspect any real input before importing it: the full supplied record is retained in the local database.

The GitHub repository is private. Linking to it does not grant visitors access. The demo and documentation are designed to be shared using fictional records only.

## Repository guide

```text
src/pkm/                         Import, search, and command-line interface
examples/demo.py                 Self-checking synthetic demonstration
examples/references.synthetic.json  Ten fictional bibliographic records
tests/test_catalog.py            Eight automated tests
docs/DEMO.md                     Walkthrough and captured demo output
install_local.py                 Offline installation into an active venv
data/                           Local catalogs; excluded from version control
```
