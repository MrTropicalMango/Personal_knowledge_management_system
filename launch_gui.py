"""Launch the native interface while preserving the project virtual environment."""
import os
from pathlib import Path
import sys

if sys.prefix == sys.base_prefix:
    raise SystemExit('Usa el Python de .venv para abrir la interfaz.')
framework = Path(sys.base_prefix) / 'python.app/Contents/MacOS/python'
if sys.platform == 'darwin' and framework.is_file() and not os.environ.get('PKM_GUI_FRAMEWORK'):
    env = os.environ.copy()
    env['PYTHONEXECUTABLE'] = sys.executable
    env['PKM_GUI_FRAMEWORK'] = '1'
    os.execve(str(framework), [str(framework), str(Path(__file__).resolve()), *sys.argv[1:]], env)
from pkm.gui import launch
pointer = Path(__file__).resolve().parent / 'data/current_catalog.txt'
db = pointer.read_text().strip() if pointer.exists() else None
launch(db if db and Path(db).is_file() else None)
