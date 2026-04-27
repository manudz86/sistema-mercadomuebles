"""
procesar_competencia.py
Procesa el CSV crudo del scraper de competencia y genera el CSV procesado
listo para el panel /admin/competencia-scraper.

CSV de entrada (del scraper Windows):
    tienda, categoria, titulo, precio, cuotas, envio, url, fecha

CSV de salida:
    tienda, tipo, modelo, medida, almohadas, cuotas_si, precio,
    sku_match, titulo_orig, url, fecha

Uso:
    python3 procesar_competencia.py competencia_completo.csv competencia_procesado.csv
"""
import re, csv, sys

# ============================================================================
# REGLAS DE MODELO — orden por especificidad (primero que matchea gana)
# ============================================================================
REGLAS_MODELO = [
    # Exclusive y variantes
    (['exclusive doble pi'], 'Exclusive Pillow'),                  # incluye typo "Doble Pilllow"
    (['exclusive europillow', 'exclusive euro pillow'], 'Exclusive Europillow'),
    (['exclusive ep '], 'Exclusive Europillow'),
    (['exclusive pillow', 'exclusive c/pillow', 'exclusive con pillow'], 'Exclusive Pillow'),
    (['exclusive'], 'Exclusive'),
    # Renovation
    (['renovation europillow', 'renovation euro pillow'], 'Renovation Europillow'),
    (['renovation pillow', 'renovation c/pillow'], 'Renovation Europillow'),  # publicaciones dicen "Pillow" pero corresponde al Europillow
    (['renovation'], 'Renovation'),
    # Sublime
    (['sublime europillow', 'sublime euro pillow'], 'Sublime Europillow'),
    (['sublime pillow', 'sublime c/pillow'], 'Sublime Europillow'),
    (['sublime'], 'Sublime'),                          # sin match (no se trabaja)
    # Doral
    (['doral pillow top', 'doral pillow', 'doral c/pillow', 'doral con pillow'], 'Doral Pillow'),
    (['doral'], 'Doral'),
    # Resto
    (['compac plus'], 'Compac Plus'),                  # sin match
    (['compac'], 'Compac'),
    (['princess'], 'Princess'),
    (['soñar', 'sonar'], 'Soñar'),
    (['tropical'], 'Tropical'),
    (['especial de lujo', ' lujo'], 'Lujo'),           # sin match
    (['platino'], 'Platino'),                          # sin match
    (['clasico plus', 'clásico plus'], 'Clasico Plus'),
    (['clasico', 'clásico'], 'Clasico'),
    (['infantil', 'cuna'], 'Infantil'),
    (['bajo cama'], 'Bajo Cama'),
]


# Upgrades cuando el título contiene "pillow" en cualquier parte y se detecta
# el modelo base. Útil para títulos donde el modelo y "pillow" están separados
# por otras palabras (ej. "Doral Resortes Pillow 180 X 200", "Renovation Espuma C/pillow").
UPGRADES_PILLOW = {
    'Doral':      'Doral Pillow',
    'Exclusive':  'Exclusive Pillow',     # Manu: si dice "Pillow" sin "Euro/EP" → Pillow
    'Renovation': 'Renovation Europillow',  # Manu: no existe Renovation Pillow puro
    'Sublime':    'Sublime Europillow',     # Manu: no existe Sublime Pillow puro
}


def extraer_modelo(titulo):
    t = titulo.lower()
    # Normalizar "c/ pillow" / "c / pillow" -> "c/pillow"
    t = re.sub(r'c\s*/\s*pillow', 'c/pillow', t)
    for patrones, modelo in REGLAS_MODELO:
        for p in patrones:
            if p in t:
                # Upgrade si el modelo es base y aparece "pillow" en otro lugar del título
                if modelo in UPGRADES_PILLOW and 'pillow' in t:
                    # Caso especial Exclusive: distinguir Pillow de Europillow
                    if modelo == 'Exclusive':
                        if ('europillow' in t or 'euro pillow' in t
                                or re.search(r'\bep\b', t)):
                            return 'Exclusive Europillow'
                        return 'Exclusive Pillow'
                    return UPGRADES_PILLOW[modelo]
                return modelo
    return 'DESCONOCIDO'


# ============================================================================
# MEDIDA
# ============================================================================
def _norm(a, b):
    if a > b:
        a, b = b, a
    if 60 <= a <= 200 and 180 <= b <= 220:
        return f"{a}x{b}"
    return None


def extraer_medida(titulo):
    """
    Devuelve tupla (medida, origen).
    origen: 'explicita' si vino con regex AxB clara, 'inferida' si vino de 
    King/Queen/plaza/etc., 'desconocida' si no se pudo extraer.
    """
    t = titulo.lower()
    # 1. Formato metros: "1.50x1.90", "1,50x1,90"
    m = re.search(r'(\d)[.,](\d{2})\s*x\s*(\d)[.,](\d{2})', t)
    if m:
        a = int(m.group(1)) * 100 + int(m.group(2))
        b = int(m.group(3)) * 100 + int(m.group(4))
        r = _norm(a, b)
        if r: return (r, 'explicita')
    # 2. Formato cm AxB
    for m in re.finditer(r'(\d{2,3})\s*(?:cm|cms)?\s*x\s*(\d{2,3})', t):
        r = _norm(int(m.group(1)), int(m.group(2)))
        if r: return (r, 'explicita')
    # 3. Formato cluster ML "190 cm - 80 cm"
    m = re.search(r'(\d{2,3})\s*cm\s*-\s*(\d{2,3})\s*cm', t)
    if m:
        r = _norm(int(m.group(1)), int(m.group(2)))
        if r: return (r, 'explicita')
    # 4. Tamaños nombrados (King, Queen, etc.) - INFERIDO
    if 'súper king' in t or 'super king' in t:
        return ('200x200', 'inferida')
    if 'súper queen' in t or 'super queen' in t:
        return ('160x200', 'inferida')
    if 'king size' in t or re.search(r'\bking\b', t):
        return ('180x200', 'inferida')
    if re.search(r'\bqueen\b', t):
        return ('160x200', 'inferida')
    # 5. Plaza sin medida - INFERIDO
    if re.search(r'2\s*(?:plazas?\s*y\s*media|1/2\s*plazas?|½\s*plazas?)', t):
        return ('160x200', 'inferida')
    if re.search(r'2\s*plazas?', t):
        return ('140x190', 'inferida')
    if (re.search(r'1\s*(?:1/2|½)\s*plazas?', t)
            or re.search(r'1\s*plazas?\s*y\s*media', t)
            or 'plaza y media' in t or 'plaza media' in t):
        return ('100x190', 'inferida')
    if re.search(r'1\s*plazas?', t):
        return ('80x190', 'inferida')
    # 6. Una sola dimensión "X cm" - INFERIDO
    m = re.search(r'\b(\d{2,3})\s*cm\b(?!\s*x)', t)
    if not m:
        m = re.search(r'(?<![x.,\d/])(\b\d{2,3}\b)(?![x\d])', t)
    if m:
        x = int(m.group(1))
        if 70 <= x <= 100:
            return (f"{x}x190", 'inferida')
        if x in (130, 140, 150):
            return (f"{x}x190", 'inferida')
        if 160 <= x <= 200:
            return (f"{x}x200", 'inferida')
    return ('?', 'desconocida')


# ============================================================================
# ALMOHADAS
# ============================================================================
def extraer_almohadas(titulo):
    t = titulo.lower()
    m = re.search(r'(?<![.,\d])(\d+)\s*alm', t)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 6:
            return n
    if re.search(r'(?<![.,\d])\balmohada\b', t) and 'almohadas' not in t:
        return 1
    return 0


# ============================================================================
# PACK — detectar publicaciones de múltiples unidades (Pack X2, etc.)
# ============================================================================
def extraer_pack(titulo):
    """Retorna cantidad de unidades del pack. Default: 1 (no es pack)."""
    t = titulo.lower()
    # "Pack X2", "Pack 2", "Pack X 2", "PackX2"
    m = re.search(r'\bpack\s*x?\s*(\d+)', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 6:
            return n
    # "Combo 2 Colchones", "2 Colchones"
    m = re.search(r'(\d+)\s*colch[oó]n(?:e?s|es)\b', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 6:
            return n
    return 1


# ============================================================================
# PRECIO Y CUOTAS
# ============================================================================
def parsear_precio(s):
    """'659.000' -> 659000. '1.130.000' -> 1130000."""
    if not s:
        return None
    s = s.replace('.', '').replace(' ', '').strip()
    try:
        return int(s)
    except ValueError:
        return None


def parsear_financiacion(s):
    """
    Parsea el campo 'cuotas' del scraper y devuelve tupla (cuotas_si, cuotas_simple).
    - cuotas_si: cantidad de cuotas s/i (string vacío si no aplica)
    - cuotas_simple: '1' si es Cuota Simple/Cuota Promocionada, '0' si no
    
    Ejemplos:
      'Mismo precio 6 cuotas de \\n$...'    -> ('6', '0')
      '6 cuotas de \\n$...'                 -> ('', '0')   (con interés, sin s/i)
      'Cuota promocionada en 24 cuotas...'  -> ('', '1')   (Cuota Simple)
    """
    if not s:
        return ('', '0')
    s_low = s.lower()
    # Cuota Simple / Cuota Promocionada (interés bajo subvencionado por el vendedor)
    if 'cuota promocionada' in s_low or 'cuota simple' in s_low:
        return ('', '1')
    # Cuotas sin interés
    if 'mismo precio' in s_low:
        m = re.search(r'(\d+)\s*cuotas', s, re.IGNORECASE)
        if m:
            return (m.group(1), '0')
    return ('', '0')




# ============================================================================
# REGLAS DE MODELO ALMOHADA — orden por especificidad
# ============================================================================
REGLAS_MODELO_ALM = [
    # Sin match (no se trabajan)
    (['triángulo', 'triangulo', 'apoya espalda', 'princess'], 'Triangulo'),
    # Modelos visco con marca premium (cervical y clásica)
    (['visco cervical renovation', 'visco cerv renovation', 'renovation'], 'Renovation'),
    (['visco sublime', 'sublime'], 'Sublime'),
    # Dual va PRIMERO porque títulos como "Almohada Inteligente Viscoelástica Cannon Dual Confort"
    # tienen "viscoelástica" antes que "dual" y caerían a Clasica si no priorizamos Dual.
    (['dual refreshing', 'dual confort', 'dual'], 'Dual'),
    # Modelos visco básicos
    (['visco cervical', 'visco cerv', 'viscoelástica cervical', 'viscoelastica cervical'], 'Cervical'),
    (['visco clasica', 'visco clásica', 'viscoelástica clásica', 'viscoelastica clasica',
      'viscoelástica inteligente', 'viscoelastica inteligente',
      'inteligente clasica', 'inteligente clásica',
      'inteligente viscoelástica', 'inteligente viscoelastica',
      'visco', 'viscoelástica', 'viscoelastica', 'inteligente'], 'Clasica'),
    # Cervical sin visco = NO es la de Manu
    (['cervical'], 'Cervical_no_visco'),
    # Modelos por nombre
    (['exclusive'], 'Exclusive'),
    (['doral'], 'Doral'),
    (['platino', 'vellón', 'vellon'], 'Platino'),
]


def extraer_modelo_almohada(titulo):
    t = titulo.lower()
    for patrones, modelo in REGLAS_MODELO_ALM:
        for p in patrones:
            if p in t:
                return modelo
    return 'DESCONOCIDO'


# ============================================================================
# MEDIDA ALMOHADA
# ============================================================================
DEFAULT_MEDIDA_ALM = {
    'Cervical':         '65x35',
    'Cervical_no_visco':'65x35',
    'Renovation':       '57x37',
    'Sublime':          '62x40',
    'Clasica':          '62x40',
    'Dual':             '70x50',
    'Exclusive':        '70x40',
    'Triangulo':        '50x41x29',
    'Platino':          '70x40',  # default cuando no se ve la medida
    'Doral':            '70x50',  # default cuando no se ve la medida
}


def extraer_medida_almohada(titulo, modelo):
    t = titulo.lower()
    # 1. Triángulo: 50x41x29 (formato 3D)
    m = re.search(r'\b0?(\d{2,3})\s*x\s*0?(\d{2,3})\s*x\s*0?(\d{2})\b', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        # Filtrar caso visco con grosor: 62x40x12 → ignorar el grosor, devolver 62x40
        if int(m.group(3)) <= 15 and a >= 50 and b >= 30:
            return f"{a}x{b}"
        return f"{m.group(1)}x{m.group(2)}x{m.group(3)}"

    # 2. AxB con o sin "cm" intermedio: 70x40, 70cm x 40cm, 070x040
    m = re.search(r'0?(\d{2,3})\s*(?:cm)?\s*x\s*0?(\d{2,3})(?!\d)', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 30 <= a <= 110 and 25 <= b <= 60:
            return f"{a}x{b}"

    # 3. Default por modelo si no se encontró
    if modelo in DEFAULT_MEDIDA_ALM:
        return DEFAULT_MEDIDA_ALM[modelo]

    return '?'


# ============================================================================
# PACK ALMOHADA — patrones más variados que en colchones
# ============================================================================
def extraer_pack_almohada(titulo):
    t = titulo.lower()
    # "X10", "X 6", "PackX2", "Pack X 4"
    m = re.search(r'(?:pack\s*)?x\s*(\d{1,2})\b', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 20:
            return n
    # "Combo 2 Almohadas", "Pack 2 Almohadas", "2 Almohadas"
    m = re.search(r'(?:combo|pack)?\s*(\d{1,2})\s*almohadas\b', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 20:
            return n
    # "por 2 unidades"
    m = re.search(r'por\s+(\d{1,2})\s+unidad', t)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 20:
            return n
    # "Combo Dos Almohadas" / "Combo Tres Almohadas"
    palabras_num = {'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6}
    for word, n in palabras_num.items():
        if re.search(rf'\b{word}\s+almohadas?\b', t):
            return n
    return 1



# ============================================================================
# SKU_MAP — basado en queries reales de productos_base + productos_compuestos
# ============================================================================
def construir_sku_map():
    mapa = {}
    todas = ['80x190', '90x190', '100x190', '140x190', '150x190',
             '160x200', '180x200', '200x200']

    def add_full(modelo, prefijo_c, prefijo_s, medidas):
        for med in medidas:
            n = med.split('x')[0]
            if prefijo_c:
                mapa[('colchon', modelo, med)] = f'{prefijo_c}{n}'
            if prefijo_s:
                mapa[('sommier', modelo, med)] = f'{prefijo_s}{n}'

    add_full('Doral', 'CDO', 'SDO', todas)
    add_full('Doral Pillow', 'CDOP', 'SDOP',
             ['140x190', '150x190', '160x200', '180x200', '200x200'])
    add_full('Exclusive', 'CEX', 'SEX', todas)
    add_full('Exclusive Pillow', 'CEXP', 'SEXP', todas)
    add_full('Renovation', 'CRE', 'SRE', todas)
    add_full('Renovation Europillow', 'CREP', 'SREP', todas)
    add_full('Sublime Europillow', 'CSUP', 'SSUP',
             ['140x190', '150x190', '160x200', '180x200', '200x200'])

    for med in ['80x190', '90x190', '100x190', '140x190']:
        n = med.split('x')[0]
        mapa[('colchon', 'Princess', med)] = f'CPR{n}20'
        mapa[('sommier', 'Princess', med)] = f'SPR{n}20'

    for med in ['80x190', '90x190', '100x190', '140x190']:
        n = med.split('x')[0]
        mapa[('colchon', 'Soñar', med)] = f'CSO{n}'
        mapa[('sommier', 'Soñar', med)] = f'SSO{n}'

    # Tropical: SOLO colchón en 80, 90, 100 (no hay sommier ni 130+ en BD)
    for med in ['80x190', '90x190', '100x190']:
        n = med.split('x')[0]
        mapa[('colchon', 'Tropical', med)] = f'CTR{n}'

    # Compac: SOLO colchón en 80, 100, 140, 160 (sufijo _DEP)
    for med in ['80x190', '100x200', '140x190', '160x200']:
        n = med.split('x')[0]
        mapa[('colchon', 'Compac', med)] = f'CCO{n}_DEP'

    # ALMOHADAS (Manu trabaja: Platino 70x40, Doral 70x50, Exclusive 70x40,
    # Cervical 65x35, Clasica 62x40, Sublime 62x40, Renovation 57x37, Dual 70x50)
    mapa[('almohada', 'Platino',    '70x40')] = 'PLATINO'
    mapa[('almohada', 'Doral',      '70x50')] = 'DORAL'
    mapa[('almohada', 'Exclusive',  '70x40')] = 'EXCLUSIVE'
    mapa[('almohada', 'Cervical',   '65x35')] = 'CERVICAL'
    mapa[('almohada', 'Clasica',    '62x40')] = 'CLASICA'
    mapa[('almohada', 'Sublime',    '62x40')] = 'SUBLIME'
    mapa[('almohada', 'Renovation', '57x37')] = 'RENOVATION'
    mapa[('almohada', 'Dual',       '70x50')] = 'DUAL'

    return mapa


SKU_MAP = construir_sku_map()


def matchear_sku(tipo, modelo, medida):
    return SKU_MAP.get((tipo, modelo, medida), '')


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================
COLUMNAS_OUT = ['tienda', 'tipo', 'modelo', 'medida', 'medida_origen',
                'almohadas', 'cuotas_si', 'cuotas_simple', 'precio', 'pack',
                'sku_match', 'titulo_orig', 'url', 'fecha']


def procesar(in_path, out_path):
    rows_out = []
    with open(in_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            titulo = r['titulo']
            cat = r['categoria'].lower()
            if cat.startswith('almohada'):
                tipo = 'almohada'
            elif cat.startswith('colchon'):
                tipo = 'colchon'
            else:
                tipo = 'sommier'

            precio = parsear_precio(r['precio'])
            cuotas_si, cuotas_simple = parsear_financiacion(r['cuotas'])

            if tipo == 'almohada':
                modelo = extraer_modelo_almohada(titulo)
                medida = extraer_medida_almohada(titulo, modelo)
                medida_origen = 'explicita'  # almohadas no tienen "King/Queen/plaza"
                almohadas = 0
                pack = extraer_pack_almohada(titulo)
            else:
                modelo = extraer_modelo(titulo)
                medida, medida_origen = extraer_medida(titulo)
                almohadas = extraer_almohadas(titulo)
                pack = extraer_pack(titulo)

            sku = matchear_sku(tipo, modelo, medida)

            rows_out.append({
                'tienda': r['tienda'],
                'tipo': tipo,
                'modelo': modelo,
                'medida': medida,
                'medida_origen': medida_origen,
                'almohadas': str(almohadas),
                'cuotas_si': cuotas_si,
                'cuotas_simple': cuotas_simple,
                'precio': str(precio) if precio else '',
                'pack': str(pack),
                'sku_match': sku,
                'titulo_orig': titulo,
                'url': r['url'],
                'fecha': r['fecha'],
            })

    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_OUT)
        w.writeheader()
        w.writerows(rows_out)

    return rows_out


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python3 procesar_competencia.py CSV_CRUDO CSV_PROCESADO")
        sys.exit(1)
    rows = procesar(sys.argv[1], sys.argv[2])
    total = len(rows)
    match = sum(1 for r in rows if r['sku_match'])
    s_si = sum(1 for r in rows if r['cuotas_si'])
    s_simple = sum(1 for r in rows if r.get('cuotas_simple') == '1')
    print(f"Total filas:      {total}")
    print(f"Match con SKU:    {match} ({match*100//total}%)")
    print(f"Sin match:        {total - match}")
    print(f"Con cuotas s/int: {s_si}")
    print(f"Con Cuota Simple: {s_simple}")
    print(f"OK -> {sys.argv[2]}")
