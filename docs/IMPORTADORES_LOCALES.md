# Importadores de bibliotecas locales

Los adaptadores se usan desde Python. La interfaz gráfica importa JSON bibliográfico general y consulta catálogos ya preparados; no exporta cuentas de Apple, Amazon o Kobo.

```python
from pkm.applebooks import import_snapshot as import_applebooks
from pkm.kindle import import_snapshot as import_kindle
from pkm.kobo import import_metadata as import_kobo

# Trabajar sobre una copia del catálogo PKM, nunca sobre la biblioteca original.
# import_applebooks('data/pkm.sqlite', 'private/applebooks.sqlite')
# import_kindle('data/pkm.sqlite', 'private/kindle.sqlite')
# import_kobo('data/pkm.sqlite', 'private/kobo-metadata.json')
```

Apple Books requiere ZBKLIBRARYASSET y las columnas declaradas en pkm.applebooks.FIELDS. read_snapshot devuelve referencias y agrupaciones de series separadas; las muestras se identifican explícitamente.

Kindle requiere ZBOOK. Interpreta contenedores plist como datos sin instanciar clases archivadas. read_snapshot devuelve referencias y registros incompletos por separado. No exporta pedidos, cuentas, posiciones ni anotaciones.

Kobo recibe una lista JSON con las claves declaradas en pkm.kobo.FIELDS. Los metadatos proceden de content: expiration_status corresponde a ___ExpirationStatus y has_account es un indicador booleano, nunca el identificador de usuario. No incluir cuentas, claves, enlaces de descarga ni anotaciones. normalize_metadata separa referencias, revisión pendiente y estadísticas, y descarta capítulos con BookID. Los estados desconocidos quedan fuera de la búsqueda. La preparación de ese JSON no está automatizada por la interfaz.

Los importadores son aditivos, no sincronizadores. Una referencia retirada o cuyo acceso cambie en el origen requiere conciliación explícita; un snapshot no garantiza disponibilidad actual. No se fusionan obras entre plataformas por similitud de título. No se copian contenidos de libros ni se eluden protecciones.

La búsqueda admite referencias y recursos de Drive, Dropbox, Apple Books, Kobo y Kindle. Una URL vacía indica que no se ha verificado un enlace de apertura.

La tabla privada security_exclusions(source, source_key, reason) bloquea recursos con la misma fuente y clave en búsquedas y apertura de enlaces. No sustituye al antivirus. El repositorio no incluye exclusiones personales ni archivos bloqueados.

## Validación

36 pruebas sintéticas cubren importación, idempotencia, actualización del índice, validación, preservación de orígenes, privacidad, muestras, revisión pendiente, búsqueda entre fuentes y exclusiones.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
python examples/demo.py
python examples/demo_unified.py
```

Los catálogos y exportaciones personales permanecen fuera de Git. Compartir copias cerradas en una ubicación privada y comprobar el acceso autorizado de cada proyecto; no hay sincronización automática ni acceso automático entre chats.
