# Personal Knowledge Management System

Importador bibliográfico local v0.1.0, desarrollado desde cero. 

## Preparación

Requiere Python 3.11 o posterior con SQLite FTS5.

```sh
python3 -m venv .venv
source .venv/bin/activate
python install_local.py
```

## Uso

Desde esta carpeta:

```sh
source .venv/bin/activate
python -m pkm import-json examples/references.synthetic.json --db data/demo.sqlite --source demo
python -m pkm search aprendizaje --db data/demo.sqlite
python -m unittest discover -s tests -v
```

Repetir la importación conserva las referencias sin duplicarlas. Los cambios para una misma clave actualizan el registro y el índice de búsqueda.

## Formato y límites

Entrada: lista JSON UTF-8 de objetos con `key` y `title` obligatorios. Admite `creators` (firstName/lastName o name), `date`, `DOI`, `itemType`, y envolturas API con `data`. Conserva el objeto original en SQLite. No admite todavía BibTeX, RIS, CSL JSON sin key, adjuntos o sincronización con bibliotecas.

La identidad es `(source, key)`. Use un `--source` distinto por biblioteca; no hay deduplicación entre claves diferentes por DOI o título. Las claves repetidas dentro del mismo archivo se rechazan. La entrada completa se valida antes de abrir el destino; las escrituras del lote son transaccionales. La búsqueda literal opera sobre títulos y creadores, ignorando acentos.

## Privacidad y entorno

Sin dependencias de ejecución externas; SQLite y unittest forman parte de Python. El entorno `.venv` está aislado. No hay llamadas de red ni acceso automático a Zotero. Solo se lee el JSON indicado y se escribe la base de destino. `data/`, bases de datos y `.venv/` están excluidos de Git. Los ejemplos son sintéticos.

Instalación sin descargas: activa `.venv` y ejecuta `python install_local.py`. Se copia el módulo al entorno virtual. Repite este comando después de editar `src/pkm`. También se incluye `pyproject.toml` para instalación convencional con pip cuando las herramientas de empaquetado estén disponibles. La instalación verificada usa el método sin descargas.
