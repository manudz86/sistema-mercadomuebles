#!/usr/bin/env python3
"""Extrae las imagenes de paginas puntuales de un PDF.

Uso:  venv/bin/python3 scripts/pdf_extraer_imgs.py <pdf> <dir_salida> <pag> [pag ...]
"""
import os
import sys

from pypdf import PdfReader

MIN_BYTES = 50_000   # ignorar iconos/logos chicos


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    pdf, destino = sys.argv[1], sys.argv[2]
    pags = [int(a) for a in sys.argv[3:]]
    os.makedirs(destino, exist_ok=True)

    r = PdfReader(pdf)
    for p in pags:
        try:
            imgs = list(r.pages[p - 1].images)
        except Exception as e:
            print(f'pag {p}: error {e}')
            continue
        for im in imgs:
            if len(im.data) < MIN_BYTES:
                continue
            ext = os.path.splitext(im.name)[1].lower() or '.bin'
            out = os.path.join(destino, f'pag{p}_{os.path.basename(im.name)}')
            with open(out, 'wb') as fh:
                fh.write(im.data)
            print(f'  {out}  ({len(im.data):,} bytes, {ext})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
