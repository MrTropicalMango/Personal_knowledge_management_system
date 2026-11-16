# Interfaz local

La interfaz nativa usa Tkinter y consulta SQLite sin servicios web. Requiere una distribución de Python con soporte Tkinter/Tk. En Linux puede ser necesario instalar el paquete `python3-tk` de la distribución.

## Apertura

Desde la carpeta del repositorio:

```sh
python3 -m venv .venv
source .venv/bin/activate
python install_local.py
python launch_gui.py
```

En macOS también puedes abrir `Abrir PKM.command` desde Finder. El lanzador detecta el ejecutable gráfico de Anaconda y conserva el entorno virtual del proyecto. Si el proceso termina con un error, el acceso de Finder mantiene el mensaje visible.

## Recorrido

1. Usa **Crear catálogo** y elige un archivo nuevo bajo `data/`.
2. Pulsa **Cargar ejemplo sintético** dos veces: la segunda carga debe indicar cero nuevas y diez sin cambios.
3. Busca `aprendizaje` o `ejemplo`.
4. Selecciona un resultado para consultar clave, procedencia y estado de los metadatos.
5. En un catálogo enriquecido, **Abrir fuente** admite enlaces de Google Drive y enlaces locales de Zotero. Los enlaces no conceden permisos de acceso.

**Abrir catálogo** selecciona una base PKM existente. La vista está limitada a 200 resultados por consulta. Los catálogos antiguos de solo referencias siguen siendo compatibles.

## Selección del catálogo privado

Opcionalmente, `data/current_catalog.txt` puede contener la ruta de una base local que se abrirá al iniciar. Este archivo está excluido de Git. Nunca publiques bases, rutas personales ni archivos de biblioteca junto con el código.

## Verificación

El recorrido original de creación, carga repetida y búsqueda fue confirmado manualmente en macOS. Las consultas conjuntas se comprobaron mediante pruebas automatizadas y la ventana actualizada fue inspeccionada con filas de ambas fuentes. No se declara una prueba gráfica automatizada completa de los diálogos o del botón que abre enlaces.
