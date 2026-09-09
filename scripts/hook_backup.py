#!/usr/bin/env python3
"""Hook PreToolUse: copia a backups/ cualquier archivo ANTES de que se edite.

Reemplaza el `cp -a ... backups/` manual: el backup deja de depender de que
alguien se acuerde y pasa a ser automático. Nunca bloquea la edición: si algo
falla, sale en silencio con código 0.

Se configura en .claude/settings.local.json:
    "hooks": {"PreToolUse": [{"matcher": "Edit|Write|NotebookEdit",
              "hooks": [{"type": "command", "command": "..."}]}]}
"""
import sys
import os
import json
import shutil
from datetime import datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUPS = os.path.join(APP_DIR, 'backups')
# no tiene sentido respaldar esto
EXCLUIR_DIRS = (os.path.join(APP_DIR, 'backups'), os.path.join(APP_DIR, 'venv'),
                os.path.join(APP_DIR, '__pycache__'), os.path.join(APP_DIR, '.git'))
MAX_BYTES = 25 * 1024 * 1024   # no copiar archivos enormes (CSV/JSON de datos)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get('tool_input') or {}
    ruta = ti.get('file_path') or ti.get('notebook_path') or ''
    if not ruta:
        return 0
    ruta = os.path.abspath(ruta)
    if not os.path.isfile(ruta):
        return 0                      # archivo nuevo: no hay nada que respaldar
    if any(ruta.startswith(d + os.sep) for d in EXCLUIR_DIRS):
        return 0
    try:
        if os.path.getsize(ruta) > MAX_BYTES:
            return 0
        os.makedirs(BACKUPS, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        destino = os.path.join(BACKUPS, f'{os.path.basename(ruta)}_{ts}.bak')
        if not os.path.exists(destino):
            shutil.copy2(ruta, destino)
    except Exception:
        pass                          # jamás frenar la edición por el backup
    return 0


if __name__ == '__main__':
    sys.exit(main())
