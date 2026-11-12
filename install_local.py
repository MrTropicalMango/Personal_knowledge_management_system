"""Install this dependency-free module into the active virtual environment."""
from pathlib import Path
import shutil
import sys
import sysconfig

if sys.prefix == sys.base_prefix:
    raise SystemExit('Activa primero el entorno virtual del proyecto.')
root = Path(__file__).resolve().parent
source = root / 'src/pkm'
destination = Path(sysconfig.get_paths()['purelib']) / 'pkm'
shutil.copytree(source, destination, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'Instalado en {destination}. Usa: python -m pkm --help')
