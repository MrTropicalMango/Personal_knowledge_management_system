# Catálogos enriquecidos: Zotero y Google Drive

El catálogo distingue entre una referencia bibliográfica y un archivo disponible. Una misma obra puede tener varias ubicaciones o versiones; la similitud de títulos no basta para fusionarlas.

## Tablas de consulta

- `references_catalog` y `references_fts`: referencias importadas desde JSON bibliográfico.
- `drive_bibliography`: `drive_id`, `title`, `authors`, `url`, `metadata_status`. Puede conservar también evidencia de extracción en columnas adicionales.
- `drive_search`: tabla FTS5 con `drive_id UNINDEXED`, `title`, `authors`, `topics`; usa el tokenizador `unicode61 remove_diacritics 2`.

`pkm.unified` abre la base en modo de solo lectura y combina ambas fuentes. Alterna resultados entre ellas antes de aplicar el límite para que una no oculte a la otra. Los catálogos sin tablas Drive siguen funcionando.

## Procedencia y límites

`metadata_status` debe indicar si el título y el autor proceden del nombre del archivo, metadatos internos o una revisión bibliográfica. Los metadatos PDF pueden contener valores incorrectos o nombres de programas. La versión y la edición deben comprobarse por separado.

El campo `topics` permite buscar marcadores, navegación EPUB o texto de índices extraídos. No equivale a búsqueda de todo el texto de los libros. Conserva el número físico de página PDF separado de la numeración impresa y registra el alcance de cada lectura.

Los PDF escaneados, protegidos o dañados pueden necesitar OCR, una contraseña autorizada o reparación. No se eluden contraseñas ni DRM. No encontrar un índice en las primeras páginas no prueba que el documento carezca de él.

## Demostración sin biblioteca personal

```sh
python examples/demo_unified.py
```

La demostración crea una base temporal con referencias ficticias de ambas fuentes, comprueba una consulta por tema y elimina su propia base al salir. No accede a Drive ni Zotero y no descarga libros.

## Instantánea local de Zotero

`scripts/import_complete.py` lee la API de Zotero Desktop en `127.0.0.1:23119`, con Zotero abierto y su API local habilitada. Recorre las bibliotecas accesibles y sus colecciones, excluyendo adjuntos, notas, anotaciones y papelera. Verifica estabilidad de versiones, recuentos, idempotencia e integridad de SQLite. Los registros sin título se conservan con una marca explícita y el valor original.

```sh
python scripts/import_complete.py
```

La salida se guarda exclusivamente bajo `data/`, con permisos locales restringidos. El script no escribe en Zotero. Revisa la política de privacidad de tu dispositivo antes de guardar metadatos personales en una carpeta sincronizada.

Las exportaciones a Drive deben ser copias cerradas del catálogo, nunca una base activa editada por varios proyectos simultáneamente. Cada proyecto necesita una conexión autorizada para consultar los archivos privados; no hay acceso automático entre chats ni sincronización automática.
