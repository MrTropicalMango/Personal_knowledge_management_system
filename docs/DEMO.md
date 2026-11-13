# Synthetic demonstration

A short walkthrough of the bibliographic pipeline, suitable for a portfolio presentation or screen recording. All records and creator names in the fixture are fictional.

## Run

From the repository folder, after creating and activating `.venv`:

```sh
python install_local.py
python examples/demo.py
```

No network connection or Zotero session is needed. Every run uses a new temporary database. No existing catalog is opened, overwritten, or removed. The demo updates a temporary copy of the input and checks that the original fixture remains unchanged.

## Walkthrough (about 90 seconds)

1. **Problem:** repeated bibliographic imports can produce duplicates and stale search results.
2. **Import:** load ten fictional references from `examples/references.synthetic.json` into SQLite.
3. **Repeat:** run the same import and verify zero new inserts and ten unchanged records.
4. **Search:** query titles with `aprendizaje` and creators with `ejemplo`; both return ten records.
5. **Update:** change one title to “Robótica sintética: demostración de actualización” in a temporary file and import it.
6. **Verify:** search `robotica` without the accent; the updated record appears. The old title search now returns nine records, while the catalog still contains ten.
7. **Privacy:** the demo exits and deletes only its own temporary directory. The source fixture and personal library remain untouched.

## Captured successful output

Verified locally on November 12, 2026, with Python 3.13.5 and SQLite 3.45.3 on macOS arm64:

```text
PKM | Synthetic demonstration
Data: 10 fictional records. No Zotero connection. No network requests.
1. First import:      10 inserted
2. Repeat import:      0 inserted; 10 unchanged
3. Title search:      10 results for "aprendizaje"
4. Creator search:    10 results for "ejemplo"
5. Update one title:   1 updated; 9 unchanged
6. Accent-free search: 1 result for "robotica"
7. Final catalog:     10 records; source file unchanged
PASS | All checks passed. Temporary database removed on exit.
Fixture SHA-256: 9b8e21492266d22708be21668bc66957f16bc106d68687509bd7427d53068790
```

The script raises an error and returns a nonzero exit status if a check fails. This transcript is evidence of the local run, not a CI badge or performance benchmark.

## Explore the actual data and CLI

```sh
python -m pkm import-json examples/references.synthetic.json --db data/demo.sqlite --source synthetic-demo
python -m pkm search aprendizaje --db data/demo.sqlite --limit 2
```

These commands keep a demonstration database under `data/`, which is excluded from Git. The automated demo above instead removes its temporary database after each run.
