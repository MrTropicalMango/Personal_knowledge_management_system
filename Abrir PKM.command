#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print 'No se encontró el entorno .venv del proyecto.'
  read '?Pulsa Intro para cerrar.'
  exit 1
fi
.venv/bin/python launch_gui.py
result=$?
if (( result != 0 )); then
  print 'PKM no pudo abrirse. Revisa el mensaje anterior.'
  read '?Pulsa Intro para cerrar.'
fi
exit $result
