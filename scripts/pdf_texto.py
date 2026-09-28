#!/usr/bin/env python3
"""Extrae texto de un PDF (solo lectura).

Uso:
    venv/bin/python3 scripts/pdf_texto.py <archivo.pdf>              # indice de paginas
    venv/bin/python3 scripts/pdf_texto.py <archivo.pdf> 3 9          # paginas 3 a 9
    venv/bin/python3 scripts/pdf_texto.py <archivo.pdf> --buscar doral
"""
import sys

from pypdf import PdfReader


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    ruta = sys.argv[1]
    r = PdfReader(ruta)
    n = len(r.pages)

    if '--buscar' in sys.argv:
        termino = sys.argv[sys.argv.index('--buscar') + 1].lower()
        print(f'Buscando {termino!r} en {n} paginas\n')
        for i, pg in enumerate(r.pages, 1):
            try:
                t = pg.extract_text() or ''
            except Exception:
                continue
            if termino in t.lower():
                primera = next((l.strip() for l in t.splitlines() if l.strip()), '')
                print(f'  pag {i:>3}: {primera[:90]}')
        return 0

    nums = [a for a in sys.argv[2:] if a.isdigit()]
    if len(nums) >= 2:
        desde, hasta = int(nums[0]), int(nums[1])
    elif len(nums) == 1:
        desde = hasta = int(nums[0])
    else:
        print(f'{n} paginas. Primera linea de cada una:\n')
        for i, pg in enumerate(r.pages, 1):
            try:
                t = pg.extract_text() or ''
            except Exception:
                t = ''
            lineas = [l.strip() for l in t.splitlines() if l.strip()]
            print(f'  {i:>3}: {" | ".join(lineas[:3])[:110]}')
        return 0

    for i in range(desde, min(hasta, n) + 1):
        print(f'\n{"="*70}\nPAGINA {i}\n{"="*70}')
        try:
            print(r.pages[i - 1].extract_text() or '(sin texto)')
        except Exception as e:
            print(f'(error: {e})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
