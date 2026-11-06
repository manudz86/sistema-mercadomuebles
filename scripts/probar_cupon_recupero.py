#!/usr/bin/env python3
"""Prueba crear_cupon_recupero SIN tocar la base (get_db simulado):
copia los datos de la plantilla, 1 uso / 1 por cliente, reintenta si el código
choca, y no crea nada con plantilla vencida o inexistente."""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, '/home/cannon/app')
os.chdir('/home/cannon/app')
os.environ['CANNON_SIN_SCHEDULER'] = '1'
from dotenv import load_dotenv  # noqa: E402
load_dotenv('/home/cannon/app/config/.env')
import pymysql  # noqa: E402
import tienda_bp as T  # noqa: E402

fallas = 0


def check(cond, msg):
    global fallas
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    fallas += 0 if cond else 1


class FakeDB:
    def __init__(self, plantilla, choques=0):
        self.plantilla, self.choques, self.inserts, self.commits = plantilla, choques, [], 0

    def cursor(self):
        return FakeCur(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


class FakeCur:
    def __init__(self, db):
        self.db, self._r = db, None

    def execute(self, sql, params=()):
        if sql.strip().startswith('SELECT'):
            self._r = self.db.plantilla
        else:
            if self.db.choques > 0:
                self.db.choques -= 1
                raise pymysql.err.IntegrityError(1062, 'Duplicate')
            self.db.inserts.append(params)

    def fetchone(self):
        return self._r

    def close(self):
        pass


vto = date.today() + timedelta(days=2)
pl = {'tipo': 'pct', 'valor': 7, 'minimo_compra': 0, 'fecha_vencimiento': vto}

db = FakeDB(pl)
T.get_db = lambda: db
cod = T.crear_cupon_recupero('recucyber')
check(cod and cod.startswith('RECU-') and len(cod) == 11, f'código único generado ({cod})')
ins = db.inserts[0]
check(ins[1:] == ('pct', 7, 0, vto), 'copia tipo, valor, mínimo y vencimiento de la plantilla')
check(db.commits == 1, 'un solo insert confirmado')

db = FakeDB(pl, choques=2)
T.get_db = lambda: db
check(T.crear_cupon_recupero('RECUCYBER') and len(db.inserts) == 1, 'si el código choca, reintenta con otro')

db = FakeDB(dict(pl, fecha_vencimiento=date.today() - timedelta(days=1)))
T.get_db = lambda: db
check(T.crear_cupon_recupero('RECUCYBER') is None and not db.inserts, 'plantilla vencida: no crea nada')

db = FakeDB(None)
T.get_db = lambda: db
check(T.crear_cupon_recupero('NOEXISTE') is None and not db.inserts, 'plantilla inexistente: no crea nada')

print('\nTODO OK' if not fallas else f'\n{fallas} FALLA(S)')
sys.exit(1 if fallas else 0)
