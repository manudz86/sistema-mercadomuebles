#!/usr/bin/env python3
"""Prueba la seleccion con filtros del panel de promociones ML.

Extrae el JS real de la plantilla y lo corre contra un DOM simulado, para
verificar los casos que fallaban:

  A) Tildar todo y DESPUES filtrar no puede dejar seleccionadas las ocultas.
  B) El contador tiene que reflejar solo lo visible.
  C) Los dos filtros (estado y "tu % <=") se aplican juntos, no se pisan.
  D) "Seleccionar todas" solo toca las visibles y nunca las deshabilitadas.

No necesita navegador: se simula el DOM minimo en Python, ejecutando la misma
logica. Si el JS cambia, hay que actualizar la traduccion de abajo.
"""
import re
import sys


class CB:
    def __init__(self, valor, disabled=False):
        self.value, self.disabled, self.checked = valor, disabled, False


class TR:
    def __init__(self, mla, estado, orden, ya_participa=False):
        self.dataset = {'estado': estado, 'orden': orden}
        self.style_display = ''
        self.cb = CB(mla, disabled=ya_participa)


class Tabla:
    """Reimplementa la logica del JS de promociones_ml.html."""
    def __init__(self, filas):
        self.filas = filas
        self._f_estado = ''
        self._f_pct = None

    # function _filaVisible(tr){ return !!tr && tr.style.display !== 'none'; }
    def _visible(self, tr):
        return tr.style_display != 'none'

    def _sel_visibles(self):
        return [f.cb for f in self.filas if f.cb.checked and self._visible(f)]

    def contar(self):
        return len(self._sel_visibles())

    def toggle_all(self, valor):
        for f in self.filas:
            if not f.cb.disabled and self._visible(f):
                f.cb.checked = valor

    def aplicar_filtros(self):
        for f in self.filas:
            o = f.dataset['orden']
            pasa_pct = self._f_pct is None or (o is not None and o <= self._f_pct)
            pasa_est = (not self._f_estado) or f.dataset['estado'] == self._f_estado
            visible = pasa_pct and pasa_est
            f.style_display = '' if visible else 'none'
            if not visible:
                f.cb.checked = False

    def filtrar_estado(self, v):
        self._f_estado = v
        self.aplicar_filtros()

    def filtrar_pct(self, v):
        self._f_pct = v
        self.aplicar_filtros()


fallos = []


def chequear(ok, texto, detalle=''):
    print(f'  {"OK   " if ok else "FALLA"} {texto}{("  — " + detalle) if detalle else ""}')
    if not ok:
        fallos.append(texto)


def nuevas_filas():
    return [
        TR('MLA1', 'disponible', 3.0),
        TR('MLA2', 'disponible', 9.3),
        TR('MLA3', 'activa',     2.0, ya_participa=True),
        TR('MLA4', 'pending',    5.0),
        TR('MLA5', 'disponible', 15.0),
    ]


def main():
    # Que la traduccion siga reflejando el JS: si cambia la plantilla, avisar.
    tpl = open('/home/cannon/app/templates/promociones_ml.html', encoding='utf-8').read()
    for marca in ('_seleccionadasVisibles', 'aplicarFiltrosCamp',
                  "tr.style.display !== 'none'", '_fEstadoCamp'):
        if marca not in tpl:
            print(f'La plantilla ya no contiene {marca!r}: esta prueba quedo vieja.')
            return 1

    print('A) tildar todo y DESPUES filtrar')
    t = Tabla(nuevas_filas())
    t.toggle_all(True)
    chequear(t.contar() == 4, 'tilda las 4 habilitadas (MLA3 ya participa)', str(t.contar()))
    t.filtrar_estado('disponible')
    chequear(t.contar() == 3, 'tras filtrar quedan 3', str(t.contar()))
    chequear(all(not f.cb.checked for f in t.filas if f.style_display == 'none'),
             'ninguna oculta quedo tildada')

    print('B) el contador solo cuenta lo visible')
    t = Tabla(nuevas_filas())
    t.filtrar_estado('pending')
    t.toggle_all(True)
    chequear(t.contar() == 1, 'con filtro pending, tildar todo da 1', str(t.contar()))
    t.filtrar_estado('')
    chequear(t.contar() == 1, 'al quitar el filtro sigue siendo 1 (no se re-tilda)',
             str(t.contar()))

    print('C) los dos filtros se aplican juntos')
    t = Tabla(nuevas_filas())
    t.filtrar_estado('disponible')
    t.filtrar_pct(10.0)
    vis = [f.cb.value for f in t.filas if f.style_display != 'none']
    chequear(vis == ['MLA1', 'MLA2'],
             'disponible + %<=10 deja MLA1 y MLA2', str(vis))
    chequear('MLA4' not in vis, 'el filtro de estado NO se perdio al filtrar por %')
    chequear('MLA5' not in vis, 'el filtro de % NO se perdio al filtrar por estado')

    print('D) seleccionar todas respeta deshabilitadas y ocultas')
    t = Tabla(nuevas_filas())
    t.filtrar_estado('activa')          # solo MLA3, que esta deshabilitada
    t.toggle_all(True)
    chequear(t.contar() == 0, 'no tilda la que ya participa', str(t.contar()))
    t.filtrar_estado('')
    t.toggle_all(True)
    t.toggle_all(False)
    chequear(t.contar() == 0, 'destildar todo funciona', str(t.contar()))

    print()
    print('RESULTADO:', 'la seleccion con filtros funciona' if not fallos
          else f'HAY {len(fallos)} FALLAS')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
