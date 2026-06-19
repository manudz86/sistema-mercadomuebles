"""
tienda_bp.py — Blueprint de la tienda online Mercadomuebles
Rutas:
    GET  /tienda/                    → Home con grilla de productos
    GET  /tienda/producto/<sku>      → Detalle de producto
    POST /tienda/carrito/agregar     → Agregar al carrito (session)
    GET  /tienda/carrito             → Ver carrito
    POST /tienda/carrito/eliminar    → Eliminar item del carrito
    GET  /tienda/datos-envio         → Formulario datos del cliente (antes de MP)
    POST /tienda/checkout            → Crear preferencia MP y redirigir
    GET  /tienda/pago/exito          → Página de éxito
    GET  /tienda/pago/pendiente      → Pago pendiente (con auto-refresh)
    GET  /tienda/pago/error          → Pago fallido
    GET  /tienda/verificar-pago      → API: consulta estado de pago (JSON)
    POST /tienda/webhook/mp          → Webhook Mercado Pago → registra venta y descuenta stock
    GET  /tienda/seguimiento         → Seguimiento de pedido para el cliente
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
import pymysql
import os
import mercadopago
import logging
import json
from datetime import datetime, timezone, timedelta
import uuid
import urllib.parse
import smtplib
import requests as http_requests
import hashlib
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import unicodedata
import re
from utils import log_evento

logger = logging.getLogger(__name__)

tienda_bp = Blueprint('tienda', __name__, url_prefix='/tienda')

@tienda_bp.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now()}


@tienda_bp.context_processor
def inject_nl_popup_desc():
    """Inyecta nl_popup_desc en todos los templates de la tienda."""
    try:
        monto, _ = _get_nl_config()
        texto = '${:,.0f} OFF'.format(monto).replace(',', '.')
    except Exception:
        texto = 'descuento exclusivo'
    return {'nl_popup_desc': texto}


@tienda_bp.context_processor
def inject_hot_event():
    return {'hot_event': get_hot_event()}


def slugify(text):
    """Convierte 'Colchón Cannon Tropical 80x190cm' → 'colchon-cannon-tropical-80x190cm'"""
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text


def get_db():
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'cannon'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'inventario_cannon'),
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
    )
    return conn


def get_mp_sdk():
    token = os.environ.get('MP_ACCESS_TOKEN', '')
    return mercadopago.SDK(token)


def get_mp_sdk_test():
    """SDK de Mercado Pago en modo PRUEBA (sandbox).
    Usa EXCLUSIVAMENTE MP_ACCESS_TOKEN_TEST. Se niega a operar si el token de
    prueba falta o coincide con el de producción, de modo que la página
    /tienda/test-mp nunca pueda generar un cobro real."""
    token_test = os.environ.get('MP_ACCESS_TOKEN_TEST', '').strip()
    token_prod = os.environ.get('MP_ACCESS_TOKEN', '').strip()
    if not token_test:
        raise RuntimeError('MP_ACCESS_TOKEN_TEST no configurado')
    if token_prod and token_test == token_prod:
        raise RuntimeError('MP_ACCESS_TOKEN_TEST coincide con producción: abortado por seguridad')
    return mercadopago.SDK(token_test)

CP_LOCALIDADES = {
    "1407": ["Floresta"],
    "1408": ["Liniers"],
    "1409": ["Mataderos"],
    "1410": ["Villa Luro"],
    "1414": ["Almagro"],
    "1415": ["Villa Crespo"],
    "1416": ["Chacarita"],
    "1419": ["Villa Urquiza"],
    "1420": ["Caballito"],
    "1421": ["Flores"],
    "1423": ["Palermo"],
    "1424": ["Belgrano"],
    "1425": ["Recoleta"],
    "1426": ["Núñez"],
    "1427": ["Saavedra"],
    "1428": ["Belgrano"],
    "1430": ["Villa Devoto"],
    "1431": ["Villa Urquiza"],
    "1432": ["Coghlan"],
    "1433": ["Saavedra"],
    "1434": ["Villa Ortúzar"],
    "1435": ["Agronomía"],
    "1445": ["Floresta"],
    "1446": ["Liniers"],
    "1447": ["Nueva Pompeya"],
    "1449": ["Barracas"],
    "1450": ["La Boca"],
    "1451": ["San Telmo"],
    "1454": ["Boedo"],
    "1455": ["Almagro"],
    "1456": ["Caballito"],
    "1457": ["Flores"],
    "1470": ["Lugano"],
    "1472": ["Villa Lugano"],
    "1474": ["Villa Soldati"],
    "1601": ["Isla Martin Garcia"],
    "1602": ["Florida", "Florida Oeste"],
    "1603": ["Villa Martelli"],
    "1605": ["Carapachay", "Munro", "Villa Adelina"],
    "1607": ["Villa Adelina"],
    "1609": ["Boulogne"],
    "1611": ["Don Torcuato"],
    "1612": ["Ingeniero Adolfo Sourdeaux"],
    "1613": ["Los Polvorines", "Malvinas Argentinas", "Pablo Nogues"],
    "1614": ["Villa De Mayo"],
    "1615": ["Grand Bourg", "Tierras Altas"],
    "1617": ["El Talar", "General Pacheco"],
    "1618": ["Ricardo Rojas", "Troncos Del Talar"],
    "1619": ["Garin", "Maquinista F Savio"],
    "1621": ["Benavidez"],
    "1623": ["Barrio Garin Norte", "Barrio Parque Lambare", "Dique Lujan", "Ingeniero Maschwitz", "La Gracielita", "Punta De Canal"],
    "1625": ["Arroyo Canelon", "Arroyo Las Rosas", "Belen De Escobar", "Campomar Viñedo", "Loma Verde", "Puerto De Escobar", "Villa La Chechela", "Villa Vallier"],
    "1627": ["Matheu", "Zelaya"],
    "1629": ["Almirante Irizar", "Barrio San Alejo", "Champagnat", "Establecimiento San Miguel", "Kilometro 61", "Manzanares", "Pilar", "Pilar Sur", "San Francisco", "Villa Agueda", "Villa Buide", "Villa Santa Maria", "Villa Verde"],
    "1631": ["Villa Rosa"],
    "1633": ["Empalme", "Fatima Estacion Empalme", "Manzone", "Villa Astolfi"],
    "1635": ["Kilometro 45", "Presidente Derqui", "Toro"],
    "1636": ["La Lucila", "Olivos"],
    "1638": ["Vicente Lopez"],
    "1640": ["Acassuso", "Martinez"],
    "1642": ["San Isidro"],
    "1643": ["Beccar"],
    "1644": ["Victoria"],
    "1646": ["San Fernando", "Virreyes"],
    "1647": ["Brazo Largo", "Zona Delta San Fernando"],
    "1648": ["Rincon De Milberg", "Tigre"],
    "1649": ["Zona Delta Tigre"],
    "1650": ["General San Martin"],
    "1651": ["San Andres"],
    "1653": ["Villa Ballester"],
    "1655": ["Jose Leon Suarez"],
    "1657": ["11 De Septiembre", "Churruca", "El Libertador", "Loma Hermosa", "Pablo Podesta", "Remedios De Escalada"],
    "1659": ["Campo De Mayo"],
    "1661": ["Bella Vista"],
    "1663": ["Muñiz", "San Miguel", "Santa Maria"],
    "1664": ["Luis Lagomarsino", "Trujui"],
    "1665": ["Jose C Paz"],
    "1667": ["El Triangulo", "Manuel Alberti", "Tortuguitas"],
    "1669": ["Del Viso", "La Lonja"],
    "1670": ["Nordelta"],
    "1672": ["Villa Lynch"],
    "1674": ["Villa Raffo", "Villa Saenz Peña"],
    "1676": ["Santos Lugares"],
    "1678": ["Caseros"],
    "1682": ["Martin Coronado", "Villa Bosch"],
    "1684": ["Ciudad Jardin Del Palomar", "El Palomar"],
    "1686": ["Hurlingham", "William Morris"],
    "1688": ["Villa Santos Tesei"],
    "1702": ["Ciudadela", "Jose Ingenieros"],
    "1704": ["Ramos Mejia"],
    "1706": ["Haedo", "Villa Sarmiento"],
    "1708": ["Moron"],
    "1712": ["Castelar"],
    "1713": ["Barrio Parque Leloir", "Villa Gobernador Udaondo"],
    "1714": ["Ituzaingo"],
    "1716": ["Libertad"],
    "1718": ["San Antonio De Padua"],
    "1722": ["Merlo"],
    "1723": ["Mariano Acosta"],
    "1727": ["B Los Aromos San Patricio", "B Nuestra Señora De La Paz", "B Sarmiento Don Rolando", "B Sta Catalina Hornero La Loma", "Colonia Hogar R Gutierrez", "Colonia Nacional De Menores", "Elias Romero", "Kilometro 45", "Kilometro 53", "Marcos Paz", "Marcos Paz B Bernasconi", "Marcos Paz B El Martillo", "Marcos Paz B El Moro", "Marcos Paz B El Zorzal", "Marcos Paz B La Lonja", "Marcos Paz B La Milagrosa", "Marcos Paz B Martin Fierro", "Marcos Paz B Urioste", "Zamudio"],
    "1731": ["Villars"],
    "1733": ["Plomer"],
    "1735": ["El Durazno"],
    "1737": ["Kilometro 77", "La Choza"],
    "1739": ["General Hornos", "Hornos", "Parada Kilometro 76", "Santa Rosa"],
    "1741": ["Enrique Fynn", "General Las Heras", "Kilometro 79", "Lozano", "Speratti"],
    "1742": ["Paso Del Rey"],
    "1744": ["Cuartel V", "La Reja", "Moreno"],
    "1746": ["Francisco Alvarez"],
    "1748": ["General Rodriguez", "La Fraternidad", "Las Malvinas"],
    "1752": ["Lomas Del Mirador"],
    "1754": ["San Justo", "Villa Luzuriaga"],
    "1755": ["Rafael Castillo"],
    "1757": ["Gregorio De Laferrere"],
    "1759": ["Gonzalez Catan"],
    "1761": ["20 De Junio", "Pontevedra"],
    "1763": ["Virrey Del Pino"],
    "1765": ["Isidro Casanova"],
    "1766": ["La Tablada"],
    "1768": ["Ciudad Madero"],
    "1770": ["Aldo Bonzi", "Tapiales"],
    "1773": ["Ingeniero Budge"],
    "1774": ["Villa Celina"],
    "1776": ["9 De Abril"],
    "1778": ["Ciudad Evita"],
    "1802": ["Aeropuerto Ezeiza"],
    "1804": ["Canning", "Ezeiza", "La Union"],
    "1806": ["Tristan Suarez"],
    "1808": ["Alejandro Petion", "Francisco Casal", "Vicente Casares"],
    "1812": ["Carlos Spegazzini", "Maximo Paz"],
    "1814": ["Barrio 1 De Mayo", "Cañuelas", "Kilometro 59", "La Costa", "La Garita", "La Leonor", "La Noria"],
    "1815": ["Escuela Agricola Don Bosco", "Kilometro 88", "Uribelarrea"],
    "1816": ["Colonia Santa Rosa", "Los Aromos", "Ruta 205 Kilometro 57", "Ruta 3 Kilometro 75 700", "Villa Adriana"],
    "1822": ["Valentin Alsina"],
    "1824": ["Gerli", "Lanus Este", "Lanus Oeste"],
    "1825": ["Monte Chingolo"],
    "1826": ["Remedios De Escalada"],
    "1828": ["Banfield", "Fiorito"],
    "1832": ["Lomas De Zamora"],
    "1834": ["Temperley", "Turdera"],
    "1836": ["Llavallol"],
    "1838": ["Luis Guillon"],
    "1842": ["El Jaguel", "Monte Grande"],
    "1846": ["Adrogue", "Jose Marmol", "Malvinas Argentinas", "San Francisco Solano", "San Jose"],
    "1847": ["Rafael Calzada"],
    "1849": ["Claypole"],
    "1852": ["Burzaco", "Ministro Rivadavia"],
    "1854": ["Longchamps"],
    "1856": ["Glew"],
    "1858": ["Villa Numancia"],
    "1862": ["America Unida", "Barrio San Pablo", "Barrio Santa Magdalena", "Guernica"],
    "1864": ["Alejandro Korn"],
    "1865": ["El Pampero", "La Argentina", "San Vicente"],
    "1870": ["Avellaneda", "Crucesita", "Gerli", "Piñeyro"],
    "1871": ["Dock Sud"],
    "1872": ["Sarandi"],
    "1874": ["Villa Dominico"],
    "1875": ["Wilde"],
    "1876": ["Bernal Este", "Bernal Oeste", "Don Bosco"],
    "1878": ["Quilmes"],
    "1879": ["Quilmes Oeste"],
    "1881": ["San Francisco Solano", "Villa La Florida"],
    "1882": ["Ezpeleta Este", "Ezpeleta Oeste"],
    "1884": ["Berazategui", "Villa España"],
    "1885": ["Guillermo E Hudson", "Platanos", "Sourigues"],
    "1886": ["Ranelagh"],
    "1888": ["Florencio Varela", "Gobernador Costa", "Santa Rosa", "Villa Brown", "Villa Vatteone", "Zeballos"],
    "1889": ["Bosques"],
    "1890": ["Juan Maria Gutierrez"],
    "1891": ["Ingeniero Allan"],
    "1893": ["Centro Agricola El Pato"],
    "1894": ["El Rincon", "Juan Vucetich Ex Dr R Levene", "Pereyra", "Pereyra Iraola Parque", "Villa Elisa"],
    "1895": ["Arturo Segui", "Los Eucaliptus Casco Urbano"],
    "1896": ["Camino Centenario Km 11500", "City Bell", "Joaquin Gorina"],
    "1897": ["Manuel B Gonnet"],
    "1900": ["La Plata"],
    "1901": ["Angel Etcheverry", "Estacion Moreno", "Lisandro Olmos"],
    "1903": ["Abasto", "Buchanan", "El Peligro", "Estacion Gomez", "Melchor Romero"],
    "1905": ["Jose Ferrari"],
    "1907": ["El Pino", "La Nueva Hermosura", "Ruta 11 Kilometro 23"],
    "1909": ["Arana", "Ignacio Correas"],
    "1911": ["Bme Bavio Gral Mansilla", "General Mansilla", "Kilometro 92"],
    "1913": ["Atalaya", "Cristino Benavidez", "Empalme Magdalena", "Julio Arditi", "Magdalena"],
    "1915": ["Arbuco", "Barrio El Porteño", "Kilometro 103", "Paraje Starache", "Roberto Payro", "Vieytes"],
    "1917": ["La Viruta", "Luis Chico", "Monte Veloz", "Punta Indio", "Veronica"],
    "1919": ["Base Aeronaval Punta Indio"],
    "1921": ["Alvarez Jonte", "Colonia Beethoven", "El Rosario", "La Primavera", "La Talina", "Las Tahonas", "Los Santos Viejos", "Pancho Diaz", "Pipinas", "Piñeiro", "Rincon De Noario"],
    "1923": ["Arroyo Del Pescado", "Arroyo La Maza", "Berisso", "Frigorifico Armour", "La Balandra", "Los Talas", "Palo Blanco"],
    "1925": ["Destileria Fiscal", "Dock Central", "Ensenada", "Fuerte Barragan", "Grand Dock", "Puerto La Plata"],
    "1927": ["Esc Nav Militar Rio Santiago"],
    "1929": ["Base Naval Rio Santiago", "Isla Paulino", "Isla Santiago"],
    "1931": ["Punta Lara"],
    "1980": ["Barrio La Dolly", "Barrio Las Mandarinas", "Brandsen", "Campo Lope Seco", "Doyhenard", "Kilometro 44", "Kilometro 82", "La Posada", "Los Merinos", "Samborombon"],
    "1981": ["Desvio Kilometro 55", "Gobernador Obligado", "Kilometro 58", "Kilometro 70", "Loma Verde", "Oliden"],
    "1983": ["Gomez", "Gomez De La Vega"],
    "1984": ["Domselaar"],
    "1986": ["Altamirano", "Jeppener"],
    "1987": ["Alegre", "Cancha Del Pollo", "Cuartel 2", "Dantas", "Espartillar", "Ranchos"],
    "2000": ["La Ceramica Y Cuyo", "Rosario"],
    "2100": ["Isla Del Charigue"],
    "2101": ["Albarellos", "Monte Flores", "Villa Amelia"],
    "2103": ["Colonia Escribano", "Coronel Bogado", "Juan Bernabe Molina", "Stephenson"],
    "2105": ["Cañada Rica", "Cepeda", "Coronel Dominguez", "El Caramelo", "Estancia La Maria", "La Carolina", "La Vanguardia", "Los Muchachos", "Pereyra Lucena", "Sargento Cabral", "Uranga", "Zamponi"],
    "2107": ["Alvarez", "Estancia San Antonio", "Soldini"],
    "2109": ["Acebal", "Campo Rueda", "Carmen Del Sauce", "Pavon Arriba"],
    "2111": ["Francisco Paz", "Santa Teresa"],
    "2113": ["Peyrano"],
    "2115": ["Colonia Valdez", "La Celia", "La Othila", "Maximo Paz", "Rodolfo Alcorta"],
    "2117": ["Alcorta", "Loma Verde"],
    "2119": ["Arminda", "Bernard", "Estacion Erasto", "Maizales", "Piñero", "Pueblo Muñoz"],
    "2121": ["Perez", "San Sebastian", "Talleres", "Villa America", "Villa Lyly Talleres"],
    "2123": ["Campo Calvo", "Colonia Clodomira", "Coronel Arnold", "Fuentes", "Pujato", "Villa Porucci", "Zavalla"],
    "2124": ["22 De Mayo", "Coronel Aguirre", "Pueblo Nuevo", "Villa Gobernador Galvez", "Villa San Diego"],
    "2126": ["Alvear", "Camino Monte Flores", "Cresta", "Fighiera", "General Lagos", "La Lata", "Pueblo Esther"],
    "2128": ["Arroyo Seco"],
    "2132": ["Aero Club Rosario", "Funes", "Granadero B Bargas", "Liceo Aeronautico Militar", "Links"],
    "2134": ["Roldan"],
    "2136": ["San Geronimo", "San Jeronimo Sud"],
    "2138": ["Carcaraña", "Colonia El Carmen", "Semino"],
    "2142": ["Campo Medina", "Ibarlucea", "Kilometro 323", "La Salada", "Lucio V Lopez", "Luis Palacios", "Salto Grande", "Vicente Echevarria"],
    "2144": ["Campo Horquesco", "Colonia Medici", "Larguia", "Totoras"],
    "2146": ["Classon", "Los Leones", "San Genaro"],
    "2147": ["San Genaro Norte", "Villa Biota"],
    "2148": ["Campo Castro", "Casas", "Centeno", "Las Bandurrias", "Villa Guastalla"],
    "2152": ["Granadero Baigorria", "Paganini"],
    "2154": ["Capitan Bermudez", "Juan Ortiz", "Kilometro 319", "Villa Cassini"],
    "2156": ["Arsenal De Guerra San Lorenzo", "Borghi", "Fabrica Militar San Lorenzo", "Fray Luis Beltran", "Granaderos", "Tte Hipolito Bouchard", "Villa Garibaldi", "Villa Margarita"],
    "2170": ["Candelaria Sud", "Casilda", "Colonia Candelaria", "Colonia La Costa"],
    "2173": ["Campo Pesoa", "Chabas", "La Merced", "Sanford", "Villada"],
    "2175": ["Barlett", "Villa Mugueta"],
    "2177": ["Bigand"],
    "2179": ["Bombal"],
    "2181": ["Los Molinos"],
    "2183": ["Arequito", "La Viuda", "Los Nogales", "Pueblo Arequito"],
    "2185": ["Campo Crenna", "Colonia Toscana Primera", "Colonia Toscana Segunda", "San Jose De La Esquina"],
    "2187": ["Arteaga", "Colonia Lago Di Como"],
    "2189": ["Colonia Los Vascos", "Cruz Alta"],
    "2200": ["Las Quintas", "Pino De San Lorenzo", "Puerto De San Lorenzo", "San Lorenzo"],
    "2201": ["Ricardone"],
    "2202": ["Cerana", "Cullen", "El Transito", "Pueblo Kirston", "Puerto Gral San Martin"],
    "2204": ["Jesus Maria", "Timbues"],
    "2206": ["Campo Paletta", "Oliveros", "Rincon De Grondona"],
    "2208": ["Gaboto", "Maciel", "Puerto Gaboto"],
    "2212": ["Campo Galloso", "Monje"],
    "2214": ["Aldao", "Andino"],
    "2216": ["Campo Raffo", "Colonia Tres Marias", "Serodino"],
    "2218": ["Carrizales", "Clarke"],
    "2222": ["Diaz"],
    "2240": ["Campo Garcia", "Campo Moure", "Carcel Modelo Coronda", "Colonia Corondina", "Coronda"],
    "2241": ["Larrechea"],
    "2242": ["Arijon", "Arocena", "Barrio Caima", "Desvio Arijon", "Puente Colastine", "San Fabian"],
    "2246": ["Barrancas", "Puerto Aragon"],
    "2248": ["Bernardo De Irigoyen", "Campo Brarda", "Campo Carignano", "Campo Genero", "Casalegno", "Irigoyen"],
    "2252": ["Colonia Campo Piaggio", "Galvez"],
    "2253": ["Campo Gimenez", "Gessler", "Loma Alta", "Oroño", "San Eugenio"],
    "2255": ["Campo Rodriguez", "Lopez", "Rigby", "San Martin De Tours"],
    "2257": ["Colonia Belgrano", "Granadero Basilio Bustos", "Wildermuth"],
    "2258": ["Campo Quiñones", "Santa Clara", "Santa Clara De Buena Vista"],
    "2300": ["Colonia Bella Italia", "El Bayo", "Fassi", "Pueblo Terragni", "Rafaela", "Sierra Pereyra", "Tres Colonias"],
    "2301": ["Bella Italia", "Capilla San Jose", "Colonia Castellanos", "Coronel Fraga", "Egusquiza", "Fidela", "Marini", "Presidente Roca", "Ramona", "Saguier", "San Antonio", "Susana", "Vila", "Villa San Jose", "Zanetti"],
    "2303": ["Angelica", "Kilometro 85"],
    "2305": ["Lehmann"],
    "2307": ["Ataliva", "Campo Daratti", "Galisteo"],
    "2309": ["Colonia Reina Margarita", "Humberto Primo", "Reina Margarita", "San Miguel"],
    "2311": ["Adolfo Alsina", "Capivara", "Colonia Maua", "Constanza", "Ituzaingo", "Virginia"],
    "2313": ["Colonia Berlin", "Colonia Ortiz", "Cuatro Casas", "Doce Casas", "Moises Ville", "Mutchnik", "Veinticuatro Casas", "Walvelberg"],
    "2315": ["Estacion Saguier"],
    "2317": ["Casablanca", "Colonia Aldao", "Colonia Bicha", "Colonia Bigand", "Hugentobler", "Rincon De Tacurales", "Santa Eusebia"],
    "2318": ["Aurelia", "Aurelia Norte", "Aurelia Sud"],
    "2322": ["Cabaña El Cisne", "Raquel", "Sunchales"],
    "2324": ["Colonia Tacurales", "Tacural"],
    "2326": ["Bealistock", "Bossi", "Las Palmeras", "Palacios", "Zadockhan"],
    "2340": ["Ceres", "Nueva Ceres"],
    "2341": ["Aromito", "Clavel Blanco", "Colonia Alpina", "Colonia Geraldina", "Colonia Montefiore", "La Elsa", "La Geraldina", "La Marina"],
    "2342": ["Campo El Mataco", "Curupaity", "La Rubia", "Monigotes"],
    "2344": ["Achaval Rodriguez", "Arrufo", "Estancia San Francisco", "Hugentobler", "Los Porongos"],
    "2345": ["Campo Botto", "Colonia Ana", "Villa Trinidad"],
    "2347": ["Colonia Mackinlay", "Colonia Malhman Sud", "Colonia Rosa", "San Guillermo"],
    "2349": ["Colonia 10 De Julio", "Colonia Dos Rosas Y La Legua", "Colonia Maunier", "Colonia Milessi", "Colonia Ripamonti", "Dos Rosas", "Monte Oscuridad", "Suardi"],
    "2352": ["Ambrosetti", "Hersilia"],
    "2354": ["Argentina", "Casares", "Chañar Sunichaj", "Colonia La Victoria", "Colonia Mackinlay", "El Aibal", "El Aspirante", "El Charabon", "El Oso", "El Ucle", "Fortin La Viuda", "Kilometro 735", "La Blanca", "La Carolina", "La Centella", "La Esmeralda", "La Recompensa", "La Romelia", "La Union", "La Victoria", "Las Palmas", "Las Viboritas", "Los Encantos", "Malbran", "Maravilla", "Nueva Trinidad", "Palmas", "Palo Negro", "San Jose", "San Sebastian", "Santa Ana", "Selva", "Tres Lagunas", "Tres Pozos"],
    "2356": ["Alarcon", "Arbol Negro", "Azucena", "Campo Ramon Laplace", "Capilla", "Cleveland", "Colonia Ermelinda", "Colonia Paula", "Doña Lorenza", "El Destino", "El Galpon", "El Solitario", "Guardia Vieja", "Kilometro 764", "La Casimira", "Las Abras De San Antonio", "Las Almas", "Las Delicias", "Libertad", "Los Milagros", "Martin Paso", "Monte Crecido", "Pinto Villa General Mitre", "Punta Del Garabato", "Punta Del Monte", "Quebrachitos", "San Agustin", "San Jose", "San Rufino", "Santa Paula", "Tome Y Traiga"],
    "2357": ["Colonia Santa Rosa Aguirre", "El Huaico", "Estancia El Carmen", "Las Abras", "Las Mostazas", "Las Ramaditas", "Martinez", "Retiro", "Villa Union", "Yaco Misqui"],
    "2400": ["La Milka", "San Francisco", "Villani"],
    "2401": ["Castelar", "Esmeraldita", "Plaza San Francisco", "San Jose Frontera"],
    "2403": ["Bauer Y Sigel", "Campo Torquinston", "Colonia Josefina", "Estacion Josefina", "Jose Manuel Estrada"],
    "2405": ["Colonia Cello", "Santa Clara De Saguier"],
    "2407": ["Campo Clucellas", "Campo Romero", "Campo Zurbriggen", "Estacion Clucellas", "Eustolia", "Kilometro 113", "Plaza Clucellas"],
    "2409": ["Estrada", "Zenon Pereyra"],
    "2411": ["Colonia Santa Rita", "Estacion Luxardo"],
    "2413": ["Colonia Anita", "Colonia Eugenia", "Colonia Iturraspe", "Colonia Prodamonte", "Colonia Valtelina", "Freyre", "La Udine", "Santa Rita"],
    "2415": ["Capilla Santa Rosa", "Colonia Ceferina", "Colonia Gorchs", "Colonia Lavarello", "Colonia Nuevo Piamonte", "Colonia Palo Labrado", "Desvio Boero", "Porteña"],
    "2417": ["Altos De Chipion", "Colonia La Trinchera", "Colonia Udine", "La Paquita", "La Trinchera", "La Vicenta", "Monte Grande"],
    "2419": ["Brinkmann", "Colonia Botturi", "Colonia Vignaud", "Cotagaita", "Seeber"],
    "2421": ["Campo Beiro", "Colonia Beiro", "Colonia Dos Hermanos", "Colonia San Pedro", "Colonia Tacurales", "Los Desagues", "Maunier", "Morteros"],
    "2423": ["Campo Calvo", "Campo La Luisa", "Colonia La Morocha", "Colonia Prosperidad", "Colonia Santa Maria", "Luis Sauze", "Monte Redondo", "Quebracho Herrado"],
    "2424": ["Colonia Cristina", "Colonia El Milagro", "Colonia El Trabajo", "Colonia Marina", "Cristina", "Devoto", "El Trabajo", "Jeanmaire", "Kilometro 531"],
    "2426": ["Campo Boero", "Colonia San Bartolome", "La Francia", "Villa Vieja"],
    "2428": ["Colonia Del Banco Nacion", "El Fuertecito", "Estancia El Chañar", "Estancia La Chiquita", "Estancia La Morocha", "Kilometro 581", "Las Cañitas"],
    "2432": ["Arbol Chato", "Capilla San Antonio", "El Florida", "El Tio", "Los Algarrobitos"],
    "2433": ["Colonia Las Pichanas", "Colonia San Rafael", "La Frontera", "Las Delicias", "Paso De Los Gallegos", "Pozo Del Chaja", "Villa Concepcion Del Tio"],
    "2434": ["Arroyito", "Arroyo De Alvarez", "El Descanso", "La Cortadera", "La Curva"],
    "2435": ["Colonia Coyunda", "La Tordilla", "Pozo Del Chañar", "Tordilla Norte", "Villa Vaudagna"],
    "2436": ["Colonia Arroyo De Alvarez", "Colonia Cortadera", "Colonias", "La Represa", "Plaza Bruno", "Quebrachitos", "Transito"],
    "2438": ["Frontera", "Kilometro 501"],
    "2440": ["Barrio Belgrano Ortiz", "Campo Faggiano", "Sastre"],
    "2441": ["Crispi"],
    "2443": ["Colonia Margarita", "Garibaldi"],
    "2445": ["Cristolia", "Estacion Maria Juana", "Mangore", "Maria Juana", "Pueblo Maria Juana"],
    "2447": ["Los Sembrados", "San Vicente"],
    "2449": ["Avena", "San Martin De Las Escobas"],
    "2451": ["Colonia La Yerba", "Colonia Santa Anita", "Las Petacas", "San Jorge", "Schiffner"],
    "2453": ["Carlos Pellegrini"],
    "2454": ["Cañada Rosquin", "Kilometro 443"],
    "2456": ["Esmeralda", "Kilometro 465", "Kilometro 483", "Traill"],
    "2500": ["Cañada De Gomez", "Cicarelli", "Las Trojas", "Villa La Ribera"],
    "2501": ["Berretta", "Bustinza", "Granja San Manuel", "Maria Luisa Correa", "San Estanislao", "San Ricardo"],
    "2503": ["Villa Eloisa"],
    "2505": ["Campo La Riviere", "Campo Santa Isabel", "Las Parejas"],
    "2506": ["Correa", "Kilometro 49"],
    "2508": ["Armstrong", "Campo Gimbatti", "Campo La Amistad"],
    "2512": ["Campo Charo", "Campo La Paz", "San Guillermo", "Tortugas"],
    "2520": ["La California", "Las Liebres", "Las Rosas"],
    "2521": ["Iturraspe", "Montes De Oca"],
    "2523": ["Bouquet"],
    "2525": ["Flora", "Saira"],
    "2527": ["Colonia San Francisco", "Maria Susana"],
    "2529": ["Piamonte"],
    "2531": ["Landeta"],
    "2533": ["Los Cardos"],
    "2535": ["El Trebol", "Tais"],
    "2550": ["Barrio Belgrano", "Bell Ville", "El Carmen", "Estacion Bell Ville", "San Vicente"],
    "2551": ["Cuatro Caminos", "Villa Los Patos"],
    "2553": ["Justiniano Posse"],
    "2555": ["Campo General Paz", "Ordoñez", "Pueblo Viejo"],
    "2557": ["Idiazabal"],
    "2559": ["Capilla De San Antonio", "Cintra", "Colonia La Leoncita", "Colonia Maschi", "El Paraiso", "Isleta Negra", "Las Overias", "Las Palmeras", "Los Tasis", "Los Ucles", "San Antonio De Litin", "San Pedro"],
    "2561": ["Chilibroste", "Los Molles", "San Eusebio", "Santa Cecilia"],
    "2563": ["El Overo", "La Cajuela", "Monte Castillo", "Noetinger", "San Jose", "San Jose Del Salteño"],
    "2564": ["Monte Leña"],
    "2566": ["San Marcos Sud"],
    "2568": ["Las Lagunitas", "Morrison"],
    "2572": ["Ballesteros", "Ballesteros Sud", "El Triangulo", "Las Merceditas", "Pinas", "San Carlos"],
    "2580": ["Colonia Calchaqui", "Colonia La Muriucha", "El Panal", "Marcos Juarez", "Pueblo Argentino"],
    "2581": ["Colonia 25 Los Surgentes", "Los Surgentes", "Pueblo Carlos Sauveran", "Pueblo Rio Tercero"],
    "2583": ["General Baldissera"],
    "2585": ["Camilo Aldao"],
    "2587": ["Enfermera Kelly", "Inriville", "Saladillo"],
    "2589": ["Monte Buey"],
    "2592": ["Colonia Veinticinco", "General Roca"],
    "2594": ["Barrio La Fortuna", "Colonia El Chaja", "La Reduccion", "Leones", "Villa Elisa"],
    "2600": ["Boca P 25", "Chateaubriand", "Estacion Teodelina", "Rabiola", "San Marcos De Venado Tuerto", "Venado Tuerto"],
    "2601": ["La Chispa", "La Inglesita", "Murphy", "San Francisco De Santa Fe"],
    "2603": ["Chapuy"],
    "2605": ["Otto Bemberg", "Rastreador Fournier", "Santa Isabel"],
    "2607": ["Campo Quirno", "Encadenadas", "Las Encadenadas", "Villa Cañas"],
    "2609": ["Colonia Morgan", "Colonia Santa Lucia", "Maria Teresa"],
    "2611": ["Estacion Christophersen", "Runciman"],
    "2613": ["La Morocha", "San Gregorio"],
    "2615": ["La Gama", "San Eduardo"],
    "2617": ["Sancti Spiritu"],
    "2618": ["Carmen"],
    "2619": ["Kilometro 57"],
    "2622": ["Maggiolo"],
    "2624": ["Arias"],
    "2625": ["Cavanagh", "Desvio Kilometro 57", "Kilegruman", "Latan Hall"],
    "2627": ["Guatimozin", "Pueblo Gambande"],
    "2630": ["Firmat", "Villa Fredrickson", "Villa Regules"],
    "2631": ["Cora", "Durham", "Miguel Torres", "Villa Divisa De Mayo"],
    "2633": ["Chovet"],
    "2635": ["Carlos Dose", "Cañada Del Ucle"],
    "2637": ["Colonia Hansen", "Colonia La Catalana", "Los Quirquinchos"],
    "2639": ["Berabevu", "Campo Nuevo", "Colonia Fernandez", "Colonia Gomez", "Colonia La Palencia", "Colonia La Pellegrini", "Colonia Piamontesa", "Colonia Santa Natalia", "Colonia Valencia", "Cuatro Esquinas", "Godeken", "Santa Natalia"],
    "2643": ["Cafferata", "Chañar Ladeado", "El Cantor"],
    "2645": ["Cap Gral Bernardo O Higgins", "Colonia Italiana", "Colonia La Palestina", "Colonia Progreso", "Corral De Bustos", "Piedras Anchas"],
    "2650": ["Canals", "Colonia La Lola"],
    "2651": ["Aldea Santa Maria", "Colonia Bismarck", "Colonia Bremen", "El Dorado", "El Porvenir", "La Italiana", "Pueblo Italiano"],
    "2655": ["Wenceslao Escalante"],
    "2657": ["Laborde"],
    "2659": ["Colonia Barge", "Matacos", "Monte Maiz"],
    "2661": ["Cortaderas", "Isla Verde"],
    "2662": ["Alejo Ledesma", "Bajo Del Burro", "Colonia Ballesteros", "Colonia Ledesma"],
    "2664": ["Benjamin Gould", "San Meliton"],
    "2670": ["La Carlota"],
    "2671": ["Assunta", "Barreto", "Estancia Las Margaritas", "General Viamonte", "Manantiales", "Pedro E Funes", "Santa Eufemia", "Viamonte"],
    "2675": ["Chazon", "Santa Victoria"],
    "2677": ["Ucacha"],
    "2679": ["Campo Sol De Mayo", "Pascanas"],
    "2681": ["Etruria"],
    "2684": ["Colonia Maipu", "Demarchi", "Los Cisnes", "Olmos"],
    "2686": ["Alejandro Roca"],
    "2700": ["Barrio Trocha", "Campo Buena Vista", "Chacra Experimental Inta", "Fontezuela", "Francisco Ayerza", "Hospital San Antonio De La Lla", "La Cora", "Manantiales Grandes", "Pergamino", "Pueblo Otero", "Santa Rita", "Tambo Nuevo", "Villa Centenario", "Villa Godoy", "Villa Progreso"],
    "2701": ["12 De Agosto", "Aguas Corrientes", "General Gelly", "Haras El Centinela", "Mariano Benitez", "Rancagua", "Santa Teresita Pergamino"],
    "2703": ["Cabo San Fermin", "Carabelas", "Ortiz Basualdo", "Pinzon", "Plumacho", "Roberto Cano"],
    "2705": ["Haras San Jacinto", "Kilometro 36", "Piruco", "Rojas", "Villa Progreso"],
    "2707": ["4 De Noviembre", "El Jaguel", "Guido Spano", "Hunter", "La Nacion", "Las Saladas"],
    "2709": ["Los Indios", "Sol De Mayo"],
    "2711": ["Almacen Piatti", "Colonia La Vanguardia", "Paraje Santa Rosa", "Pearson", "San Federico"],
    "2713": ["Manuel Ocampo"],
    "2715": ["El Socorro", "La Margarita", "La Vanguardia"],
    "2717": ["Acevedo", "Gornatti", "Guerrico", "Juana A De La Peña", "Manantiales"],
    "2718": ["Lierra Adjemiro", "Lopez Molinari", "Maguirre", "Manzo Y Niño", "Mariano H Alfonzo", "Urquiza", "Villa Da Fonte"],
    "2720": ["Caminera General Lopez", "Colon", "El Pelado", "Los Arcos"],
    "2721": ["El Arbolito", "Sarasa"],
    "2722": ["Wheelwright"],
    "2723": ["El Bagual", "Estancia Las Gamas", "Juncal"],
    "2725": ["Hughes", "Merceditas", "Santa Emilia"],
    "2726": ["Labordeboy", "Villa Estela"],
    "2728": ["Melincue", "San Urbano"],
    "2729": ["Carreras"],
    "2732": ["4 De Febrero", "El Jardin", "Elortondo"],
    "2740": ["Almacen La Colina", "Arrecifes", "Cañada Marta", "El Contador", "El Nacional", "La Delia", "La Nelida", "Puente Cañete", "Villa Sanguinetti"],
    "2741": ["El Retiro", "Kilometro 187", "Las Cuatro Puertas", "Marcelino Ugarte", "Salto"],
    "2743": ["Arroyo Dulce", "Berdier", "Los Angeles", "Monroe", "Tacuari", "Villa San Jose"],
    "2745": ["Gahan", "Kenny", "La Invencible"],
    "2747": ["Coronel Isleños", "Ines Indart"],
    "2751": ["Almacen Castro", "Almacen El Cruce", "Colonia La Invernada", "Colonia La Nena", "Colonia La Noria", "Colonia La Reina", "Colonia Laborderoy", "Colonia Los Toldos", "Colonia Stegman", "El Quemado", "La Sarita", "La Violeta"],
    "2752": ["Almacen El Descanso", "Arroyo De Luna", "Campo La Elisa", "Capitan Sarmiento", "Colegio San Pablo", "El Silencio", "Haras Los Cardales", "La Luisa", "Retiro San Pablo"],
    "2754": ["Campo Crisol", "El Carmen", "San Juan", "San Ramon", "Todd", "Viña"],
    "2760": ["Colonia Los Tres Usaris", "Puente Castex", "San Antonio De Areco"],
    "2761": ["Estancia Santa Catalina", "Santa Coloma", "Villa Lia"],
    "2763": ["Flamenco", "Kilometro 102", "Puesto Del Medio"],
    "2764": ["Campo La Nena", "Chenaut", "Duggan", "Gobernador Andonaeghi", "Solis", "Vagues"],
    "2800": ["Arroyo Aguila Negra", "Arroyo Botija Falsa", "Arroyo Negro", "Arroyo Ñacurutu", "Barrio San Jacinto", "Canal Martin Irigoyen", "Frigorifico Las Palmas", "La Pesqueria", "Villa Angus", "Villa Capdepont", "Villa Florida", "Villa Fox", "Villa Massoni", "Villa Mosconi", "Zarate", "Zona Delta Zarate"],
    "2801": ["Alto Verde", "El Tatu", "Escalada"],
    "2802": ["Lomas Del Rio Lujan", "Otamendi"],
    "2804": ["Campana", "El Fenix", "Kilometro 88", "Pasaje Talavera", "Ruta 9 Kilometro 72", "Zona Delta Campana"],
    "2805": ["Arroyo Aleli", "Arroyo Brasilero", "Arroyo Carabelitas", "Arroyo El Ahogado", "Arroyo Ibicuycito", "Arroyo La Paciencia", "Arroyo Las Cruces", "Arroyo Las Rosas", "Arroyo Los Platos", "Arroyo Los Tigres", "Arroyo Pesqueria", "Arroyo Tajiber", "Arroyo Zanjon", "Arroyo Ñacurutu Chico", "Blondeau", "Canal N Alem 1A Sec", "Canal N Alem 2A Sec", "Colonia Delta", "Isla El Dorado", "La Horqueta", "Paraje Palaveroi", "Parana Bravo", "Rio Aguila", "Rio Alferez Nelson Page", "Rio Ceibo", "Rio Parana Guazu", "Rio Pasaje Al Aguila", "Rio Sauce", "Rio Talavera"],
    "2806": ["Las Palmas", "Lima"],
    "2808": ["Atucha"],
    "2812": ["Capilla Del Señor", "Carlos Lemee", "Diego Gaynor", "Exaltacion De La Cruz", "La Lata", "La Rosada", "Orlando", "Pavon", "Villa Preceptor M Robles"],
    "2813": ["Arroyo De La Cruz"],
    "2814": ["Alto Los Cardales", "Los Cardales"],
    "2820": ["Colonia El Potrero", "Colonia Stauwer", "Cuatro Bocas Paraje", "El Nuevo Rincon", "Gualeguaychu", "Kilometro 311", "La Lata", "La Zelmira", "Palavecino", "Pesqueria Diamantino", "Pueblo Nuevo", "Puerto Unzue", "Tres Esquinas", "Villa Antony", "Villa Eleonora", "Villa Lila", "Zona Delta Del Parana"],
    "2821": ["Arroyo Del Cura", "Arroyo Venerato", "Costa Uruguay Norte", "Costa Uruguay Sur", "El Potrero", "Gualeyan", "Pehuajo Norte", "Pueblo General Belgrano", "Rincon Del Gato", "Sarandi", "Villa Del Cerro", "Ñandubaysal"],
    "2823": ["Aero Club Canal", "Arroyo Buen Pastor", "Arroyo Caballo", "Arroyo Principal", "Arroyo Salado", "Arroyo Sanchez Chico", "Arroyo Sanchez Grande", "Arroyo Zapallo", "Canal Principal", "Ceibal", "Ceibas", "Cooperativa Brazo Largo", "El Sauce", "Establecimiento San Martin", "Isla Del Ibicuy", "La Calera", "La Cuadra", "Perdices", "Puente Paranacito", "Puente Ñancay", "Sagastume", "Villa Paranacito"],
    "2824": ["Britos", "Colonia Gdor Basavilbaso", "Colonia Italiana", "Doctor Eugenio Muñoz", "Faustino M Parera", "General Almada", "La Chica", "La Florida", "Villa Faustino M Parera", "Villa Romero"],
    "2826": ["Aldea San Antonio", "Aldea San Juan", "Aldea Santa Celia", "Costa San Antonio", "La Escondida", "Pastor Britos", "Rincon Del Cinto", "San Antonio", "Urdinarrain"],
    "2828": ["Colonia Nueva Montevideo", "Escriña", "Gilbert", "Las Masitas", "Las Rosas", "Los Amigos", "Lucienville 1", "Lucienville 2", "Lucienville 3", "Lucienville 4"],
    "2840": ["Albardon", "Boca Gualeguay", "Buena Vista Paraje", "Chacras", "Cuatro Bocas", "Cuchilla", "El Remance", "Gualeguay", "Hojas Anchas", "Kilometro 306", "Las Bateas", "Monte Redondo", "Primer Distrito", "Puente Pellegrini", "Puerto Barriles", "Puerto Ruiz", "Punta Del Monte", "Rincon Del Nogoya Sur", "Saladero Alzua", "Saladero San Jose", "Santa Marta", "Septimo Distrito"],
    "2841": ["Aldea Asuncion", "Arroyo Cle", "Cuatro Manos", "Gonzalez Calderon", "Kilometro 290", "Kilometro 303", "Lambare", "Las Colas", "Lazo", "San Julian"],
    "2843": ["General Galarza", "Quinto Distrito"],
    "2845": ["Colonia Duportal", "Gobernador Echague", "Gobernador Mansilla", "Sauce Sur"],
    "2846": ["Anahi", "El Empalme Paraje", "Empalme Holt", "Fernandez", "Holt", "Ibicuy", "Islas De Las Lechiguanas", "Kilometro 389", "La Argentina", "Libertador Gral San Martin", "Mazaruca", "Paranacito", "Paso Del Cisnero", "Puerto Constanza", "Puerto Ibicuy", "Puerto Perazzo", "Puerto San Juan"],
    "2848": ["Berisso", "Kilometro 340", "Kilometro 361", "Medanos"],
    "2852": ["Alarcon", "Berisso Desvio Fcgu", "Cuchilla Redonda", "Enrique Carbo", "Irazusta", "La Costa", "Talitas"],
    "2854": ["Dos Hermanas", "Larroque", "Las Mercedes", "Pehuajo Sud"],
    "2900": ["San Nicolas De Los Arroyos"],
    "2903": ["Erezcano"],
    "2905": ["General Rojo"],
    "2907": ["Conesa", "Pujol"],
    "2909": ["Estancias", "Juan G Pujol", "Mutti"],
    "2912": ["La Querencia", "Santa Teresa", "Villa Gral Savio Est Sanchez"],
    "2914": ["Costa Brava", "Villa Ramallo", "Villa Ramallo Est Ffcc"],
    "2915": ["Aguirrezabala", "La Esperanza", "Ramallo"],
    "2916": ["El Jupiter", "El Paraiso", "Haras El Ombu", "Las Bahamas"],
    "2918": ["Empalme Villa Constitucion", "Pavon", "Theobald"],
    "2919": ["Copacabana", "Estacion Villa Constitucion", "Villa Constitucion"],
    "2921": ["Godoy", "Oratorio Morante", "Rueda", "Tres Esquinas"],
    "2930": ["La Buana Moza", "Las Flores", "Ruta 9 Kilometro 169 5", "San Pedro", "Villa Depietri", "Villa Igollo", "Villa Sarita", "Villaigrillo"],
    "2931": ["Isla Los Laureles", "La Matilde", "Oliveira Cesar", "Paname", "Vuelta De Obligado"],
    "2933": ["Colonia Velez", "La Bolsa", "Perez Millan"],
    "2935": ["Algarrobo", "Arroyo Burgos", "Doyle", "El Descanso", "Ingeniero Moneta", "Kilometro 172", "Parada Kilometro 158", "Santa Lucia"],
    "2938": ["Alsina"],
    "2942": ["Baradero", "Estacion Baradero"],
    "2943": ["Ireneo Portela"],
    "2944": ["Rio Tala", "Villa Teresa"],
    "2946": ["El Espinillo", "Gobernador Castro", "Kilometro 184", "Villa Leandra"],
    "3000": ["Barranquitas", "Kilometro 9", "Piquete", "Santa Fe", "Villa Don Bosco", "Villa Maria Selva", "Villa Yapeyu"],
    "3001": ["Alto Verde", "Arroyo Leyes", "Calchines", "Campo Crespo", "Campo Del Medio", "Campo Iturraspe", "Cayasta", "Colastine", "Colastine Norte", "Colonia Mascias", "Colonia Nueva Narciso", "Colonia San Joaquin", "El Laurel", "El Pozo", "Isla Del Porteño", "La Guardia", "La Noria", "Los Cerrillos", "Recreo Sur", "Rincon Norte", "Rincon Potreros", "Ruinas Santa Fe La Vieja", "Saladero Mariano Cabal", "San Joaquin", "San Jose Del Rincon", "Santa Rosa De Calchines", "Villa Viveros", "Vuelta Del Pirata"],
    "3003": ["Colonia Los Zapallos", "Helvecia"],
    "3005": ["Colonia California", "Colonia Francesa", "Colonia San Roque", "Colonia Teresa", "El Ceibo", "El Gusano", "El Para", "Los Cardenales", "Ombu Norte", "San Javier"],
    "3007": ["Empalme San Carlos"],
    "3009": ["El Tropezon", "Franck", "Las Tunas", "San Carlos Norte", "San Jeronimo Del Sauce"],
    "3011": ["Campo Magnin", "Mariano Saavedra", "Sa Pereyra", "San Jeronimo Norte", "San Mariano", "Santa Maria Centro", "Santa Maria Norte"],
    "3013": ["Colonia Matilde", "Coronel Rodriguez", "Estacion Matilde", "Las Higueritas", "San Carlos Centro", "San Carlos Sud"],
    "3014": ["Angel Gallardo", "Arroyo Aguiar", "Ascochingas", "Campo Lehman", "Constituyentes", "Kilometro 28", "Kilometro 35", "Monte Vera", "Nueva Pompeya", "Pompeya", "San Pedro Sur", "Setubal", "Yamandu"],
    "3016": ["San Jose", "Santo Tome", "Villa Lujan"],
    "3017": ["Bajo Las Tunas", "San Agustin", "Sauce Viejo"],
    "3018": ["Candioti", "Iriondo", "Recreo"],
    "3020": ["Campo Santo Domingo", "Kilometro 41", "Laguna Paiva", "Reynaldo Cullen", "San Guillermo"],
    "3021": ["Campo Andino", "El Galpon", "La Clorinda", "Los Hornos", "San Pedro", "San Pedro Norte"],
    "3023": ["Cululu", "Hipatia", "Ingeniero Boasi", "Kilometro 49", "Manucho", "Progreso", "Rincon De Avila", "Sarmiento", "Tomas Alva Edison"],
    "3025": ["Colonia Clara", "La Clara", "Maria Luisa", "Pericota", "Providencia", "Rincon Del Quebracho", "Santo Domingo", "Soledad", "Soutomayor"],
    "3027": ["La Pelada"],
    "3029": ["Colonia Adolfo Alsina", "Elisa", "Jacinto L Arauz"],
    "3032": ["Nelson"],
    "3036": ["Aromos", "Cabal", "Colonia Campo Botto", "Emilia", "Esther", "Lassaga", "Llambi Campbell", "Rio Salado"],
    "3038": ["Cayastacito", "La Sementera"],
    "3040": ["Asuncion Maria", "Avichuncho", "Esquina Grande", "Estancia La Constancia", "Estancia Prusia", "La Capilla", "San Justo", "Vera Mujica"],
    "3041": ["Cacique Ariacaiquin", "Jose Macias", "Los Saladillos", "Mascias", "Ñandubay"],
    "3042": ["Abipones", "Colonia El Ochenta", "Colonia Silva", "La Rosa", "Marcelino Escalada", "Ramayon", "Villa Lastenia"],
    "3044": ["Gobernador Crespo"],
    "3045": ["Campo Zavalla", "Colonia Dolores", "Colonia La Mora", "Colonia La Penca", "La Brava", "San Martin Norte"],
    "3046": ["Arrascaeta", "Campo Berraz", "Colonia Manuel Menchaca", "El Sombrerero", "Fortin Almagro", "Kilometro 95", "La Julia", "Las Cañas", "Las Tres Marias", "Los Olivos", "Miguel Escalada", "Nare", "Nueva Ukrania", "Paikin", "Petronila", "Rincon De San Antonio", "Villa Saralegui"],
    "3048": ["Angeloni", "Colonia Tres Reyes", "Luciano Leiva", "San Bernardo", "Sol De Mayo", "Videla"],
    "3050": ["Calchaqui", "Kilometro 213", "La Hosca", "Los Galpones"],
    "3051": ["Alejandra", "El Pajaro Blanco", "Los Corralitos", "Los Osos"],
    "3052": ["Cañadita", "Colonia La Blanca", "La Criolla"],
    "3054": ["Colonia La Negra", "Fives Lille", "Guaranies", "La Camila", "La Oriental", "Pedro Gomez Cello", "Vera Y Pintado"],
    "3056": ["Campo Coubert", "Colonia La Maria", "Colonia La Nicolasa", "Espin", "La Guampita", "Margarita"],
    "3057": ["Estancia Las Gamas", "Estancia Los Palmares", "Estancia Pavenhan", "La Cigueña", "La Gallareta", "La Sarnosa", "Los Palmares", "Pavenhan"],
    "3060": ["Campo San Jose", "El Amargo", "El Mariano", "El Triangulo", "Estancia Achala", "Estancia La Cigueña", "Fortin Argentina", "Fortin Cacique", "Fortin Charrua", "Fortin Tacuru", "Fortin Tostado", "Independencia", "La Bombilla", "Las Arenas", "Los Charabones", "Sin Pereza", "Tostado"],
    "3061": ["Antonio Pini", "Cabeza De Chancho", "Cuatro Bocas", "El Nochero", "Fortin Atahualpa", "Fortin Seis De Caballeria", "Gregoria Perez De Denis", "Kilometro 389", "Kilometro 421", "Kilometro 468", "Las Chuñas", "Padre Pedro Iturralde", "Pozo Borrado", "San Bernardo", "Santa Margarita", "Tres Pozos", "Villa Minetti"],
    "3062": ["Campo Belgrano", "Desvio Pozo Dulce", "El Cañon", "El Crucero", "El Jardin", "El Once", "El Setenta", "El Simbol", "Fortin Inca", "Guardia Escolta", "La Aida", "La Delia", "La Dora", "La Feliciana", "La Isleta", "La Libia", "La Magdalena", "La Santafecina", "Las Chilcas", "Las Isletas", "Las Mochas", "Las Teresas", "Los Tableros", "Pozo Dulce", "San German", "Tres Lagunas"],
    "3064": ["Bandera", "Colonia Alsina", "Don Pietro", "El Agricultor", "El Candelero", "El Tobiano", "Isla Baja", "La Alemana", "La Dolores", "La Esperanza", "La Eulalia", "La Francisca", "La Hiedra", "La Huerta", "La Pampa", "La Panchita", "La Rosilla", "La Simona", "La Susana", "La Teresa", "Las Aguadas", "Las Gamas", "Los Paraisos", "Nueva Aurora", "Sanavirones", "Santa Catalina", "Selva Blanca"],
    "3066": ["Campo Garay", "Colonia Independencia", "Esteban Rams", "Fortin Alerta", "Kilometro 293", "Logroño", "Portalis"],
    "3070": ["Dho", "El Aguara", "Los Molles", "San Cristobal"],
    "3071": ["Aguara Grande", "Portugalete"],
    "3072": ["La Lucila", "Maria Eugenia", "Ñanducita"],
    "3074": ["Colonia El Simbol", "La Cabral", "La Polvareda", "Las Avispas", "Nueva Italia", "Santurce"],
    "3076": ["Huanqueros", "Kilometro 235", "La Verde", "Laguna Verde"],
    "3080": ["Colonia Pujol", "Esperanza", "La Orilla", "Larrechea", "Paso Vinal", "Pueblo Abc", "Pujato Norte", "Rincon Del Pintado"],
    "3081": ["Cavour", "Colonia La Nueva", "Humboldt", "Humboldt Chico", "Rivadavia"],
    "3083": ["Grutly", "Grutly Norte"],
    "3085": ["Pilar"],
    "3087": ["Felicia", "Nuevo Torino"],
    "3100": ["Avenida Ejercito Parana", "Bajada Grande", "Bañadero Oficial Burgos", "Camino A Diamante Km 1", "Corrales Nuevos", "Isla Lynch", "Oro Verde", "Paracao", "Parana", "Puerto Viejo", "Quintas Al Sud", "Ruta 138 Kilometro 1", "Tiro Federal", "Villa Sarmiento", "Villa Uranga"],
    "3101": ["Aldea Brasilera", "Aldea Protestante", "Aldea Salto", "Aldea San Francisco", "Aldea Spatzenkutter", "Aldea Valle Maria", "Arroyo Jacinto", "Campo Riquelme", "Carrizal", "Colonia Ensayo", "Colonia Palmar", "Costa Grande", "Costa Grande Doll", "Doctor Garcia", "General Alvear", "Isla El Pillo", "Las Cuevas", "Los Gansos", "Molino Doll", "Paja Brava", "Pajonal", "Puente De Las Pencas", "Puente Del Doll", "Puerto Las Cuevas", "Puerto Lopez", "Rincon Del Doll", "San Francisco", "Sanatorio Apeadero Fcgu", "Strobel"],
    "3103": ["Aldea Santafecina", "Colegio Adventista Del Plata", "Sanatorio Adventista Del Plata", "Villa Aida", "Villa Libertador San Martin"],
    "3105": ["Diamante", "Ejido Diamante", "Puerto Diamante"],
    "3107": ["Colonia Avellaneda", "Distrito Espinillo", "San Benito", "Sauce Pinto"],
    "3109": ["Colonia Centenario", "Crucesitas 7 Seccion", "El Ramblon", "Quebracho", "Ramblon", "Seccion Urquiza", "Viale"],
    "3111": ["Almacen Cristian Schubert", "Arroyo Las Tunas", "Arroyo Pancho", "Cañada Grande", "Chañar Maria Grande Primera", "Las Tunas", "Maria Grande Primera", "Puente Del Chañar", "San Martin", "Tabossi"],
    "3112": ["Colonia Loma Negra"],
    "3113": ["Colonia Celina", "Colonia San Martin", "Curtiembre", "La Balsa", "La Balsa Parana", "Paso De La Balza", "Puerto Curtiembre", "San Martin", "Tres Lagunas", "Villa Urquiza"],
    "3114": ["Aldea Grapschental", "Aldea Maria Luisa", "Colonia Maria Luisa", "Colonia Reffino", "Escuela Alberdi", "Establecimiento El Carmen", "Establecimiento El Cimarron", "Establecimiento La Esperanza", "Establecimiento Las Margaritas", "General Racedo", "Kilometro 28", "Tezanos Pinto", "Villa Fontana", "Villa Gob Luis Etchevehere"],
    "3116": ["Aldea Chaleco", "Aldea Cuesta", "Aldea Eigenfeld", "Aldea San Jose", "Aldea San Miguel", "Aldea San Rafael", "Aldea Santa Rosa", "Boca Del Tigre Apeadero Fcgu", "Colonia Merou", "Crespo", "Espinillo Norte", "Kilometro 43", "Kilometro 45", "Los Burgos Apeadero Fcgu"],
    "3117": ["Aldea San Antonio", "El Taller", "Segui"],
    "3118": ["Centro Comunitario Cnia Nue", "Colonia Argentina", "Colonia Crespo", "Colonia Nueva", "Crespo Norte", "Distrito Tala", "Enrique Berduc", "Establecimiento El Tala", "Kilometro 131", "Kilometro 147", "La Picada", "La Picada Norte", "Paso De La Arena", "Paso De Las Piedras", "Puente Carmona", "Ramon A Parera", "Sauce Montrull"],
    "3122": ["Arroyo Corralito", "Cerrito", "Colonia Cerrito", "El Palenque", "General Racedo El Carmen", "Pueblo Moreno"],
    "3123": ["Aldea Santa Maria", "Colonia Rivadavia", "Colonia San Juan", "Pueblo General Paz"],
    "3125": ["Antonio Tomas", "Destacamento General Guemes", "Pueblo Brugo"],
    "3127": ["Alcete", "Hernandarias", "Paso Potrillo", "Puerto Algarrobo", "Puerto Villarruel", "Villa Hernandarias", "Vizcachera"],
    "3128": ["Colonia Berro"],
    "3129": ["Colonia Hernandarias", "Piedras Blancas", "Puerto Viboras"],
    "3132": ["El Pingo", "Kilometro 116"],
    "3133": ["Arroyo Burgos", "Arroyo Maria", "Arroyo Maturrango", "Arroyo Palo Seco", "Barrancas Coloradas", "Colonia Santa Luisa", "Maria Grande", "Maria Grande Segunda", "Santa Luisa", "Sosa"],
    "3134": ["Antonio Tomas Sud", "Colonia Oficial N 4", "Hasenkamp", "La Colmena", "La Juliana", "La Virginia", "Los Naranjos", "Santa Sara"],
    "3136": ["Alcaraz Norte", "Colonia La Gama", "Las Garzas", "Pueblo Bellocq", "Talitas"],
    "3137": ["Alcaraz Sud", "Bañadero Oficial Las Galarzas", "Colonia La Providencia", "El Solar"],
    "3138": ["Alcaraz 2Do", "Colonia Alcarcito", "Colonia Higuera", "Colonia Ougrie", "Costa Del Payticu", "Estancia La Gama", "Los Algarrobos", "Pueblo Arrua Est Alcaraz"],
    "3142": ["Alcaracito", "Bovril", "Colonia Adivinos", "Colonia Avigdor", "Colonia Viraro", "El Corcovado", "Kilometro 160", "La Diligencia", "Primer Congreso", "Pueblo Ellison", "Sir Leonard", "Virano"],
    "3144": ["Alcaraz 1Ro", "Arroyo Del Medio", "Don Gonzalo", "El Gramiyal", "La Encierra", "Sauce De Luna"],
    "3150": ["Algarrobitos 1Ro", "Almirante Iglesias", "Boca Del Tigre", "Crucesitas Urquiza", "Cuarto Distrito", "Distrito El Sauce", "Don Cristobal 1 Seccion", "El Tropezon", "La Corvina", "La Ilusion", "Laurencena", "Montoya", "Nogoya", "Septimo Distrito", "Villa Tres De Febrero"],
    "3151": ["Antelo", "Colonia Angela", "Corrales", "Crucesitas 3 Seccion", "El Pueblito", "Febre", "Gobernador Febre", "Kilometro 148", "La Florencia", "La Loma", "La Maruja A", "Montoya", "Villa Angelica"],
    "3153": ["Kilmetro 165", "Paso Del Abra", "Puente Victoria", "Quebrachitos", "Quinto Cuartel Victoria", "Victoria"],
    "3155": ["Costa Del Nogoya", "Establecimiento Punta Alta", "Laguna Del Pescado", "Pueblito Norte", "Puerta De Crespo", "Puerto Esquina", "Rincon De Nogoya", "Sexto Distrito", "Tres Bocas"],
    "3156": ["Betbeder", "Campo Escales", "Colonia Algarrabitos", "Hernandez", "Tres Esquinas"],
    "3158": ["20 De Septiembre", "Chiqueros", "Colonia La Llave", "La Colina", "La Favorita", "La Llave", "Los Paraisos", "Lucas Gonzalez", "San Lorenzo"],
    "3162": ["Aranguren", "Chilcas", "Don Cristobal 2 Seccion", "Hinojal"],
    "3164": ["Camps", "Colonia Rivas", "Don Cristobal", "General Ramirez", "Isletas", "Isletas Norte", "Pueblito", "Rivas"],
    "3170": ["Alberto Gerchunoff", "Basavilbaso", "Colonia Lucienville", "Colonia N 1", "Colonia N 2", "Colonia N 3", "Colonia N 4", "Kilometro 231", "Linea 24", "Linea 25", "Novibuco Primero", "Pueblo Nuevo", "Tres Aldeas"],
    "3172": ["Kilometro 208", "Rocamora"],
    "3174": ["Altamirano Sud", "Arroyo Obispo", "Cuatro Bocas", "El Chaja", "Estacion Sola", "Hipodromo", "Kilometro 180", "Kilometro 189", "Kilometro 192", "Kilometro 220", "La Ollita", "Las Guachas", "Molino Bob", "Primer Cuartel", "Pueblo Primero", "Puente Obispo", "Rincon De Las Guachas", "Rosario Del Tala", "Sauce Norte", "Segundo Cuartel"],
    "3176": ["Gobernador Sola", "Kilometro 183"],
    "3177": ["Altamirano Norte", "Crucesitas 8 Seccion", "Dist Raices Al Norte", "Dist Raices Al Sud", "Durazno", "Establecimiento San Eduardo", "Establecimiento San Eusebio", "Establecimiento San Francisco", "Gobernador Macia", "Guardamonte", "Kilometro 200", "Kilometro 25"],
    "3180": ["Arroyo Las Tunas", "Diego Lopez", "El Gato", "Federal", "Subcentral Santa Maria"],
    "3181": ["Arroyo Moreira", "Chañar", "Colonia Jorge Fink", "Colonia San Lorenzo", "Jorge Fink", "Paso Duarte", "Paso Sociedad", "Puntas De Moreira", "Villamil"],
    "3183": ["Albariño", "Carpinchoris", "El Embalsado", "Fortuna", "La Hierra", "Laguna Benitez", "Los Conquistadores", "Santa Lucia", "Sauce Norte"],
    "3185": ["Arroyo Garay", "Basualdo", "Colonia Basualdo", "Colonia La Marta", "Colonia Pairiri", "Colonia Tunas", "Costa Arroyo Garay", "Cuatro Bocas", "Fronteras", "La Selva", "La Verbena", "Lomas Blancas", "Paraje Portillo", "Pedro Diaz Colodrero", "Rincon De Tunas", "San Jaime", "San Jaime De La Frontera"],
    "3187": ["Atencio", "Catalotti", "Chañar", "Chircalito", "Correa", "La Esmeralda", "Las Lagunas", "Mac Keller", "Mesa", "Mulas Grandes", "Pajas Blancas", "San Jose De Feliciano", "San Luis San Jose Feliciano", "Tases", "Viboras"],
    "3188": ["Colonia Falco", "Conscripto Bernardi", "El Cimarron", "Estacion Alcaraz", "Loma Limpia", "Villa Perper"],
    "3190": ["Arroyo Hondo", "Banderas", "Centenario Parana", "Colonia Buena Vista", "Colonia Carrasco", "Colonia La Delia", "Colonia Las Gamas", "Colonia Maximo Castro", "Colonia Oficial N 11", "Colonia Oficial N 3", "Curuzu Chali", "Ejido Sud", "El Carmen", "El Diecisiete", "Estancia San Juan", "Isla Curuzu Chali", "Isla La Paz", "Islas Alcaraz", "La Paz", "Ombu", "Paso Medina", "Paso Puerto Augusto", "Picada Beron", "Piloto Avila", "Puerto La Esmeralda", "Puerto Marquez", "Puerto Yunque", "Sarandi Cora", "Tacuaras Yacare", "Yacare", "Yeso", "Yeso Oeste"],
    "3191": ["Arroyo Ceibo", "Bonaldi", "Calandria", "Colonia Fontanini", "Colonia Oficial N 13", "Colonia Oficial N 14", "El Gaucho", "El Rosario", "El Sarandi", "Estacas", "Estaquitas", "Floresta", "Gonzalez", "Las Lagunas", "Las Mulitas", "Las Toscas", "Manantiales", "Martinetti", "Mira Monte", "Montiel", "Palo A Pique", "San Antonio", "San Geronimo", "San Gustavo", "San Juan", "San Ramirez", "San Victor", "Santa Ines", "Santa Maria", "Saucesito", "Villa Boreilo", "Villa Porteña"],
    "3192": ["Colonia Bertozzi", "El Colorado", "El Quebracho", "Paso Garibaldi", "Puerto Cadenas", "Santa Elena"],
    "3194": ["Arroyo Sarandi", "Arroyo Soro", "Guayquiraro", "Paso Telegrafo", "Tres Bocas"],
    "3196": ["Arroyo Vega", "Buena Vista", "Cabral", "Campo Bordon", "Campo Cafferata", "Campo De Carlos", "Campo Morato", "Campo Romero", "Campo San Jacinto", "Chacras Norte", "Chacras Seccion Ejido", "Chacras Sud", "El Carmen", "El Parque", "Esquina", "Estancia Cafferatta", "Estancia El Carmen", "Estancia Laguna Limpia", "Estancia Marquez Lui", "Inga", "Jesus Maria", "La Amistad", "La Casualidad", "La Emilia", "La Isabel", "La Morocha", "Libertad", "Los Flotadores", "Malezal", "Malvinas Norte", "Ombu Solo", "Pueblito", "San Agustin", "San Antonio", "San Fernando", "San Francisco", "San Gustavo", "San Jacinto", "San Juan", "San Roque", "San Vicente", "Santa Catalina", "Santa Cecilia", "Santa Librada", "Santa Rita", "Sarandi", "Villa Cristia"],
    "3197": ["Abra Guazu", "Alejandrina", "Arroyo Saturno", "Boranza", "Colonia Beron De Astrada", "Coronel Abraham Schweizer", "Cuña Suegra", "El Coquito", "El Porvenir", "El Yapu", "Estero Grande", "Estero Sauce", "Estero Yatay", "La Florencia", "La Nena", "La Palmera", "Libertador", "Los Algarrobos", "Los Eucaliptos", "Los Medios", "Los Paraisos", "Paraje Poton", "Paso Algarrobo", "Paso Cejas", "Pueblo Libertador", "Rincon De Sarandy", "San Lorenzo", "San Luis", "San Martin", "Santa Ana", "Santa Isabel", "Toro Chipay"],
    "3199": ["Los Laureles", "Malvinas", "Malvinas Centro", "Malvinas Sur", "Paraje El Carmen"],
    "3200": ["Colonia Los Sauces", "Concordia", "Kilometro 32", "Kilometro 342", "Kilometro 347", "Lesca", "Los Sauer", "Paso Margariños", "Saladero Concordia", "Tablada Norte", "Tablada Oeste"],
    "3201": ["Camba Paso", "Colonia Adela", "Colonia Ayui", "Colonia General Roca", "Colonia Navarro", "Colonia Yerua", "Cueva Del Tigre", "El Martillo", "Embarcadero Ferrari", "Estancia Grande", "Hervidero", "Juan B Monti", "Kilometro 6", "La Rosada", "Las Tejas", "Nueva Escocia", "Puerto Yerua", "Ruta 14 Km 443", "Villa Zorraquin"],
    "3203": ["Arroyo Grande", "Benito Legeren", "Calabacillas", "Clodomiro Ledesma", "Frigorifico Yuqueri", "Kilometro 11", "Kilometro 24", "Kilometro 33", "Pedermar", "Pedernal", "San Gregorio", "Santa Isabel"],
    "3204": ["Ayui Parada", "Chaviyu Colonia Flores", "Colonia Don Bosco", "Colonia La Gloria", "Colonia San Justo", "Estacion Isthilart", "Gualeguaycito", "Kilometro 37", "Kilometro 44"],
    "3206": ["Bella Union Paraje", "Bizcocho", "Chaviyu Parada Fcgu", "Colonia Bizcocho", "Colonia Flores", "Colonia Gualeguaycito", "Colonia La Argentina", "Colonia La Paz", "Colonia Lamarca", "Colonia Santa Eloisa", "Estacion Santa Ana", "Estancia La Floresta", "Estancia San Jose", "Federacion", "Guayaquil", "Kilometro 47", "Kilometro 51", "Lamarca", "Las Peñas", "Monte Chico", "Puerto Algarrobo"],
    "3208": ["Colonia Ensanche Sauce", "Colonia La Matilde", "Santa Ana"],
    "3212": ["Arroyo El Mocho", "Arroyo La Virgen", "Campo Dominguez", "Cnia Justo Jose De Urquiza", "Colonia San Antonio", "Colonia San Bonifacio", "Don Roberto", "El Duraznal", "El Gualeguay", "El Pago Apeadero Fcgu", "El Redomon", "El Refugio", "Kilometro 329", "Kilometro 333", "Kilometro 344", "La Alicia", "La Colorada", "La Criolla", "La Emilia", "La Granja", "La Invernada", "La Nobleza", "La Odilia", "La Querencia", "Loma Negra", "Los Brillantes", "Los Charruas", "Nueva Vizcaya", "Osvaldo Magnasco", "Paso Del Gallo", "Quebracho", "San Buenaventura", "San Jorge", "San Juan La Querencia", "San Pedro", "Tte Primero Brigio Cainzo", "Yaros"],
    "3214": ["Estacion Yerua", "Estacion Yuqueri", "Kilometro 373", "Kilometro 376", "Yerua", "Yuqueri"],
    "3216": ["Arroyo Hondo", "Benitez", "Colonia Campos", "Colonia Curbelo", "Colonia Hebrea", "Colonia La Armonia", "Colonia La Esperanza", "Colonia La Mora", "Colonia La Quinta", "Colonia Oficial N 5", "El Avestruz", "General Campos", "Kilometro 343", "Kilometro 355", "La Perla", "La Quinta", "Las Mochas", "Lucas Noreste", "Mauricio Ribole", "Pueblo Ferre", "Puente De Lucas", "Walter Moss"],
    "3218": ["Arroyo Palmar", "Colonia Lopez", "Colonia Nueva Alemania", "Colonia San Jose", "Kilometro 353", "La Carlota", "San Salvador", "Villaguaycito"],
    "3220": ["Arroyo Manganga", "Arroyo Timboy", "Arroyo Totoras", "Chacras 1A Seccion", "Chacras 2A Seccion", "Chacras 3A Seccion", "Chacras 4A Seccion", "Chircal", "Colonia Barrientes", "Cuatro Bocas", "El Ceibo", "El Chircal", "Este Argentino", "Kilometro 161", "Kilometro 167", "Kilometro 173", "La Florida", "Monte Caseros", "Mota Piedritas", "Paso Esterito", "Paso Vallejos", "San Francisco", "Talleres", "Tres Bocas", "Villa La Florida"],
    "3222": ["Buen Retiro", "Camba Cua", "Casuarina", "Independencia", "Juan Pujol", "Kilometro 120", "Kilometro 134", "La Flor", "Mira Flores", "Mota", "Parada Labougle", "Piedrita", "Pilincho", "Saenz Valiente", "San Antonio", "San Fermin", "San Fernando", "San Salvador", "Santa Magdalena", "Santa Rita", "Santo Domingo", "Tacuabe", "Timboy"],
    "3224": ["Colonia Libertad", "El Porvenir Colonia Libertad", "Estacion Libertad", "Kilometro 182", "La Blanqueada", "La Palma", "San Jose Est Libertad Dp", "San Luis Est Libertad Dp", "San Miguel Estacion Libertad", "Santa Lea", "Santa Marta"],
    "3226": ["Buena Vista", "Colonia Mota", "Kilometro 104", "La Venta", "Mocoreta", "Piedritas", "Puerto Juan De Dios", "San Andres", "San Gregorio"],
    "3228": ["Cabi Monda", "Cañada Del Cerro", "Chajari", "Colonia Alemana", "Colonia Aylman", "Colonia Belgrano", "Colonia Frazer", "Colonia Oficial N 1 La Florida", "Colonia Santa Maria", "Colonia Villa Libertad", "Cooperativa Gral San Martin", "Kilometro 84", "La Fraternidad Y Santa Juana", "Las Catorce", "Los Paraisos", "Mandisovi", "Monte Verde", "San Roque", "Sarandi", "Surst", "Villa Libertad"],
    "3229": ["Colonia Freitas", "Colonia San Ramon", "Colonia Santa Elvira", "Estancia Salinas", "La Florida", "La Soledad", "Tatuti", "Villa Del Rosario"],
    "3230": ["Arbol Solo", "Baygorria", "El Progreso", "Estancia La Carolina", "Estancia Lomatora", "Kilometro 268", "La Amelia", "La Colorada", "La Constancia", "La Elena", "La Haydee", "La Verde", "Los Manantiales", "Los Pinos", "Madariaga", "Mirador", "Nueva Esperanza", "Nueva Palmira", "Ombucito", "Palmar", "Palmita", "Paso De Los Libres", "Paso Rosario", "Quinta Seccion Ombucito", "Quiyati", "Recreo", "Reduccion", "San Carlos", "San Felipe", "San Joaquin", "San Juan", "San Paladio", "San Pedro", "Santa Elisa", "Santa Isabel", "Tres Hojas", "Tristan Chico", "Ñatiu"],
    "3231": ["Colonia Arocena Ina", "Estancia El Porvenir", "Estancia La Arboleda", "Estancia La Loma Alta", "Estancia Los Milagros", "Estancia Pozo Cuadrado", "Estancia San Juan", "Estancia San Solano", "Estancia Soledad", "Mirunga", "San Miguel", "Yapeyu"],
    "3232": ["Cabred", "Guaviravi", "Kilometro 204", "Parada Pucheta", "San Francisco", "San Francisco Guavirari", "San Ignacio", "Santa Emilia", "Santa Rita Parada Pucheta", "Tapebicua", "Yapeyu"],
    "3234": ["Bonpland", "Kilometro 235", "Paso Ledesma", "Rincon De Yaguary", "San Antonio", "San Isidro"],
    "3240": ["Colonia Egido", "Curupi", "Empalme Neild", "Kilometro 279", "Kilometro 284", "Kilometro 285", "Kilometro 288", "Las Pajitas", "Lucas Sur 2Da Seccion", "Paraje Guayabo", "Paso De La Legua", "Villaguay", "Zenon Roca"],
    "3241": ["Campo De Villamil", "Colonia Villaguaycito", "Estacion Raices", "Laguna Larga", "Los Ombues", "Lucas Norte", "Lucas Sur 1Ra Seccion", "Mojones Norte", "Mojones Sur Primero", "Mojones Sur Segundo", "Paso De La Laguna", "Raices Oeste", "Rincon De Mojones", "Rincon Lucas Norte", "Rincon Lucas Sud"],
    "3244": ["Colonia Belga Americana", "Colonia Leven", "Grupo Parrero", "La Amiguita", "La Joya", "Las Moscas", "Libaros", "Linea 19", "Linea 20", "Lionel", "Mac Dougall", "Villaguay Este"],
    "3246": ["Achiras", "Baron Hirsch", "Colonia Achiras", "Colonia Baron Hirsch", "Colonia Carmel", "Colonia Ida", "Colonia Miguel", "Colonia Perliza", "Colonia Sagastume", "Colonia San Manuel", "Colonia Sonenfeld", "Desparramados", "Eben Horoscha", "Grupo Achiras", "Ing Miguel Sajaroff", "La Capilla", "Miguel J Perliza", "Pueblo Dominguez", "Rachel", "Rospina", "Sagastume", "Villa Dominguez"],
    "3248": ["Caraguata", "Colonia Lucrecia", "Estacion Urquiza", "Geribebuy", "Gobernador Urquiza", "Mangrullo", "Santa Anita", "Santa Rosa", "Villa San Marcial"],
    "3252": ["Aldea San Jorge", "Belez", "Campo Moreno", "Clara", "Colonia Belez", "Colonia Carlos Calvo", "Colonia Espindola", "Colonia Feimberg", "Colonia Guiburg", "Colonia La Rosada", "Colonia San Jorge", "Colonia Sandoval", "Colonia Velez", "Kilometro 306", "San Vicente", "Santa Rosa", "Spindola", "Vergara", "Villa Clara"],
    "3254": ["Colonia La Blanquita", "Colonia La Morenita", "Colonia La Pampa", "Colonia San Ernesto", "Jubileo", "Kilometro 325", "La Estrella", "La Pampa", "Las Colonias"],
    "3260": ["Arroyo Molino", "Balneario Pelay", "Colonia Elisa", "Colonia Perfeccion", "Colonia Ubajay", "Concepcion Del Uruguay", "Estacion Uruguay", "Kilometro 108", "Kilometro 112", "Kilometro 115", "La Barraca", "La Goya", "La Sesteada", "La Tigresa", "Paso Del Molino", "Puerto Viejo", "San Justo"],
    "3261": ["Centella", "Colonia Cupalen", "Colonia Elia", "Colonia Luca", "Colonia Oficial N 6", "Colonia Santa Ana", "Colonia Sauce", "Cupalen", "Kilometro 270", "La Maria Luisa", "Los Ceibos", "Puerto Campinchuelo", "Talita", "Tomas Rocamora"],
    "3262": ["Caseros", "Palacio San Jose", "Villa San Justo", "Villa Udine"],
    "3263": ["1 De Mayo", "Centenario La Paz", "Colonia Carmelo", "Colonia Crucesitas", "Colonia Ensanche Mayo", "Colonia Gral Urquiza", "Colonia San Cipriano", "Colonia San Jorge", "Colonia Santa Teresita", "Kilometro 268", "Kilometro 283", "Kilometro 293", "Pronunciamiento", "San Cipriano"],
    "3265": ["Arroyo Caraballo", "Colonia 1 De Mayo", "Colonia Caraballo", "Colonia Elisa", "Colonia Hocker", "Colonia Nueva Norte", "Colonia Nueva Sur", "Colonia San Miguel", "Colonia Tres De Febrero", "Kilometro 305", "Puente De Gualeguaychu", "San Francisco", "Villa Elisa"],
    "3267": ["Cañada De Las Ovejas", "Colonia El Carmen", "Colonia Las Pepas", "Colonia Nueva San Miguel", "Colonia San Ignacio", "Colonia Santa Rosa", "Colonia Vazquez"],
    "3269": ["Arroyo Baru", "Colonia Ambis", "Colonia Baylina", "Colonia Emilio Gouchon", "Colonia F Sillen", "Colonia San Antonio", "Colonia Santa Elena", "Hambis", "Kilometro 311", "Kilometro 337", "Kilometro 344", "La Clarita", "La S Diez Casas", "Pueblo Cazes", "Puntas Del Gualeguaychu", "San Miguel", "San Miguel Nro 2"],
    "3272": ["Arroyo Gena", "Colonia 1 De Mayo", "Colonia Pereira", "Estancia Bella Vista", "Estancia Cnia La Primavera", "Estancia Cnia Santa Elena", "Estancia Cnia Sta Teresa", "Estancia Colonia El Ombu", "Estancia Colonia El Toropi", "Estancia Colonia La Tapera", "Estancia Colonia Peribebuy", "Estancia Colonia San Pedro", "Estancia Colonia Santa Eloisa", "Estancia Colonia Santa Juana", "Estancia El Toropi", "Estancia Los Vascos", "Genacito", "Herrera", "Kilometro 242", "Kilometro 244", "Kilometro 253", "La Calera", "Las Mercedes", "Nicolas Herrera", "Villa Mantero", "Villa San Miguel"],
    "3280": ["Arroyo Urquiza", "Colon", "Kilometro 114", "Kilometro 310", "Kilometro 322", "Kilometro 324", "Kilometro 336", "Kilometro 49", "Kilometro 88", "La Suiza", "Parque Nacional El Palmar", "Puerto Colorado", "Puntas Del Palmar"],
    "3281": ["Calera", "Colonia 5 Ensanche De Mayo", "Colonia Arroyo Urquiza", "Colonia Hughes", "Colonia Nueva Sur", "Ejido Colon", "Fabrica Colon", "Las Achiras", "Liebig", "Pueblo Colorado", "Pueblo Liebig", "Puerto Almiron", "San Anselmo", "Yatay"],
    "3283": ["Colonia Mabragaña", "Colonia San Francisco", "El Brillante", "Kilometro 99", "Perucho Verna", "San Jose"],
    "3285": ["Berduc", "Juan Jorge", "Kilometro 56", "Kilometro 86", "Kilometro 89", "Martiniano Leguizamon", "Palmar", "Pos Pos", "Santa Ines"],
    "3287": ["Aldea San Gregorio", "Arroyo Concepcion", "Cantera La Constancia", "Colonia La Matilde", "Colonia Saenz Valiente", "Establecimiento La Calera", "Establecimiento Los Monigotes", "Isla San Jose", "Kilometro 45", "Kilometro 50", "Palmar Yatay", "Sexto Distrito Colon", "Ubajay"],
    "3300": ["Arroyo", "Don Horacio", "El Reposo", "El Tropezon", "Estancia Itaembe", "Itaembe Mini", "Kilometro 595", "La Milagrosa", "La Rotonda", "Las Vertientes", "Pedro Nuñez", "Posadas", "Puerto Lujan", "Rincon Itaembe", "San Borjita", "San Isidro", "Villa Emilia", "Villa Lanus", "Villalonga"],
    "3302": ["Aguara Cua", "Apipe Grande", "Boqueron", "Buena Vista", "Caa Carai", "Caa Garay", "Cambireta", "Centinela", "Colonia General Uriburu", "Colonia San Antonio", "Colonia Urdaniz", "Costa Guazu", "El Centinela", "El Plata", "Empedrado Limpio", "Estancia San Javier", "Florida", "Garcitas", "Ibiritangay", "Isla Apipe Chico", "Ituzaingo", "La Celeste", "La Hileorica", "Las Animas", "Las Delicias", "Las Tres Hermanas", "Libertad", "Loma Alta", "Loma Negra", "Loma Poy", "Los Gemelos", "Los Laureles", "Los Tres Hermanos", "Ombu", "Paso Tirante", "Pilincho", "Puerto Naranjito", "Puerto Ubajay", "Puerto Valle", "Punta Mercedes", "Rincon Chico", "Rincon Del Rosario", "Salinas", "San Antonio Isla Apipe Grande", "San Isidro", "San Javier", "San Jeronimo", "San Joaquin", "San Jose", "San Juan", "San Julian", "San Pedro", "Sangara", "Santa Ana", "Santa Maria", "Santa Tecla", "Santo Domingo", "Tres Arboles", "Ulajay", "Uriburu", "Villa P Argentina", "Vizcaino"],
    "3304": ["Domingo Barthe", "Fachinal", "Garupa", "Garupa Norte", "Kilometro 577", "Miguel Lanus", "San Andres", "Santa Ines"],
    "3306": ["Aguapey", "Centinela", "Damus", "Kilometro 538", "Kilometro 546", "Manantiales", "Nueva Valencia", "Ojo De Agua", "Parada Leis", "Pindapoy", "Porvenir", "Puente Nacional", "Rincon De Bugres", "San Carlos", "San Jose", "San Juan", "San Juan De La Sierra", "Santo Tomas", "Sierra De San Jose", "Sierras San Juan", "Tororo"],
    "3308": ["Candelaria", "Colonia Profundidad", "Profundidad", "Puerto La Mina", "Sol De Mayo", "Yabebiri", "Yacutinga"],
    "3309": ["Arroyo Tomas", "Bella Vista", "Brazo Del Tacuaruzu", "Campiña Grande", "Capueron", "Cerro Cora", "Colonia Alemana", "Colonia Guarani", "La Invernada", "Las Quemadas", "Nacientes Del Isabel", "Tacuaruzu", "Villa Venecia"],
    "3311": ["Arroyo Isabel", "Colonia Alberdi", "Olegario Victor Andrade"],
    "3313": ["Arroyo Del Medio", "Belgrano", "Campo San Juan", "Cerro Azul", "Colonia Polaca", "Gral Guemes", "Picada Polaca", "Villa Inta"],
    "3315": ["Caa Yari", "Campo Tornquist", "Colonia Caaguazu", "Colonia Taranco", "Dos Arroyos", "El Chaton", "Gobernador Lopez", "Kilometro 26", "Kilometro 78", "Leandro N Alem", "Mecking", "Mojon Grande", "Once Vueltas", "Picada Belgrano", "Picada Bonpland", "Picada Española", "Picada Iglesia", "Picada Libertad", "Picada Pozo Feo", "Picada Rusa", "Picada San Javier", "Picada Sur Mecking", "Villa Libertad"],
    "3316": ["Arroyo Pastora", "Caapora", "Colonia Manuel Belgrano", "Colonia Yabebiri", "Loreto", "Lote 12", "Ruinas De Loreto", "Santa Ana", "Yerbal Mamboreta"],
    "3317": ["Arroyo Magdalena", "Bañado Grande", "Bonpland", "Campiña De Bonpland", "Colonia Almafuerte", "Colonia Aristobulo Del Valle", "Colonia Finlandesa", "Colonia Yacutinga", "Lote 117", "Picada Finlandesa", "Picada Portuguesa", "Picada San Javier", "Picada San Martin", "Rincon De Bonpland", "Timbauba", "Tratado De Paz"],
    "3318": ["Bonpland Norte", "Colonia Martires", "Lote 5"],
    "3322": ["Aparicio Cue", "Arroyo Yabebiri", "Barrancon", "Colonia Domingo Savio", "Colonia Roca Chica", "Colonia San Ignacio", "El Triunfo", "Estacion Experimental De Loret", "Invernada San Ignacio", "La Horqueta", "La Plantadora", "Maria Antonia", "Pastoreo", "Puerto Chuño", "Puerto Nuevo", "Puerto San Ignacio", "Puerto Viejo", "Puerto Yabebiri", "San Ignacio", "Tacuara", "Teyuguare"],
    "3324": ["Gobernador Roca", "Roca Chica"],
    "3326": ["Colonia Leiva", "Colonia Polana", "El 26", "El Destierro", "General Urquiza", "Puerto España", "Puerto Gisela", "Puerto Menochio", "Puerto Naranjito", "Santo Pipo"],
    "3327": ["Colonia Roca", "Corpus", "Hekenan", "Lote 25", "Manis", "Obligado", "Puerto Cazador", "Puerto Doce", "Puerto Hardelaste"],
    "3328": ["Colonia Japonesa", "Colonia Ñacangazu", "Hipolito Yrigoyen", "Jardin America", "La Otilia", "Los Teales", "Oasis", "Ojo De Agua", "Otilia", "Puerto Tabay"],
    "3332": ["Capiovi", "Capivu", "Colonia La Otilia", "Mbopicua", "Puerto Ingeniero Morandi", "Puerto Leoni", "Puerto Mineral", "San Gotardo"],
    "3334": ["3 De Mayo", "Capiovisiño", "Colonia Oro Verde", "Cuña Piru", "Garuhape", "Linea Cuchilla", "Puerto Mbopicua", "Puerto Oro Verde", "Puerto Rico", "Puerto San Alberto", "Puerto Tigre", "Ruiz De Montoya", "San Alberto", "San Miguel", "San Sebastian"],
    "3337": ["Adolfo J Pomar", "Carril De Anta", "Cascuda", "Doradito", "Frigo", "Indumar", "Integracion", "Juan Domingo Peron", "Km 1230", "Km 1246", "Km 1247", "Km1228", "Lapacho", "Loma Pora", "Milagro", "Pueblo Illia", "Sol Naciente"],
    "3338": ["17 De Agosto", "2 De Abril", "El Lapacho", "Fray Luis Beltran", "Km 18", "La Bonita", "Las Flores", "Lechuza", "Manuel Belgrano", "Mariano Moreno", "Picada Mandarina", "Virgen De Lourdes"],
    "3340": ["Boqueron", "Cambal", "Casualidad", "Colonia Gobernador Ruiz", "Colonia Jose R Gomez", "Colonia San Mateo", "Cuay Chico", "Don Maximo", "Estancia Buena Vista", "Estancia Casurina", "Estancia Durruti", "Estancia El Ombu", "Estancia San Mateo", "Estancia San Miguel", "Galarza Cue", "Gobernador Ruiz", "Gomez Cue", "Guay Grande", "Isla San Mateo", "Ita Cua", "Kilometro 442", "Kilometro 459", "Los Bretes", "Nuevo Paraiso", "Paso Concepcion", "Puerto Hormiguero", "Puerto Las Lajas", "Puerto Las Tacuaritas", "Puerto Piedra", "Rincon Mercedes Estancia", "San Antonio", "San Francisco", "San Gabriel", "Santo Tome", "Tablada", "Topador", "Tres Taperas"],
    "3342": ["Aguapey", "Caa Garay Gdor Virasoro", "Caaby Poy", "Carabi Poy", "Cau Garay", "Caza Pava", "Coronel Desiderio Sosa", "El Carmen", "Gobernador Virasoro", "Ibera", "Isla Grande", "Jose Rafael Gomez", "Kilometro 470", "Kilometro 475", "Kilometro 479", "Kilometro 489", "Kilometro 506", "Kilometro 517", "La Criolla", "Las Ratas", "San Alonso", "San Justo", "San Vicente", "Sosa", "Tareiri", "Vuelta Del Ombu"],
    "3344": ["2 De Julio", "Altamira", "Alvear", "Arroyo Mendez", "Batay", "Cambara", "Concepcion", "Cuay Chico", "Cuay Grande", "El Paraiso", "Esfadal", "Espinillar", "Estancia La Loma", "Estancia Las Magnolias", "Estancia Las Tunas", "Florida", "Kilometro 393", "Kilometro 394", "Kilometro 396", "La Blanqueada", "La Chiquita", "La Elsa", "La Elva", "La Loma", "La Loma Torrent", "La Magnolia", "Las Mercedes", "Las Palmas", "Las Palmiras", "Las Palmitas", "Los Arboles", "Malezal", "Mira Flores", "Morica", "Palmita", "Pancho Cue", "Piracu", "Pirayu", "San Jose", "San Juan", "San Pedro", "Santa Ana", "Santa Isabel", "Santa Rita", "Tambo Nuevo", "Tingui", "Torrent", "Tres Capones"],
    "3346": ["Bacacay", "Costa Guaviravi", "Estingana", "Isoqui", "La Cruz", "Los Tres Cerros", "San Gabriel", "Tres Cerros", "Yurucua"],
    "3350": ["Apostoles", "Arroyo Tunitas", "Campo Richardson", "Carrillo Viejo", "Chirimay", "Colonia Apostoles", "Colonia Azara", "Ensanche Este", "Ensanche Norte", "La Capilla", "Las Tunas", "Nacientes Del Tunar", "Puerto Azara", "Rincon De Chimtray", "Tigre", "Villa Errecaborde"],
    "3351": ["Azara", "El Paraiso", "Garruchos", "Lote 117", "Monte Hermoso", "Rincon De Mercedes"],
    "3353": ["Arroyo Santa Maria", "Colonia Santa Maria", "Fraga Cue", "Invernada Chica", "Invernada De Itacaruare", "Invernada Grande", "Isla Argentina", "Itacaruare", "Las Bananeras", "Las Mandarinas", "Los Galpones", "Machadiño", "Picada San Javier", "Rincon De Lopez", "Tres Capones"],
    "3355": ["Arrechea", "Arroyo Persiguero", "Barra Concepcion", "Bretes Martires", "Colonia Capon Bonito", "Colonia Martir Santa Maria", "Colonia San Javier", "Concepcion De La Sierra", "El Persiguero", "Isla San Lucas", "Paso Del Arroyo Persiguero", "Paso Porteño", "Persiguero", "Puerto Concepcion", "Puerto San Lucas", "San Isidro", "San Lucas", "Santa Maria La Mayor", "Santa Maria Martir"],
    "3357": ["Barra Bonita", "Buena Vista", "Colonia Cumanday", "Costa Portera", "Frances", "Guerrero", "Kilometro 26", "Puerto Rosario", "Puerto Ruben", "Puerto Saltiño", "Rincon Del Guerrero", "San Javier", "Tres Esquinas"],
    "3358": ["Cheroguita", "Colonia Liebigs", "Dos Hermanos", "El Rancho", "El Socorro", "Establecimiento La Merced", "Estacion Apostoles", "La Pupi", "La Pupii", "Playadito", "Santa Rosa", "Villa Ortiz Pereira"],
    "3360": ["Arroyo Fedor", "Barra Bonita", "Bayo Troncho", "Doña Maria", "Obera", "Paraje Dos Hermanas", "Picada San Martin", "Pueblo Salto", "San Martin", "Sierra De Oro", "Villa Blanquita", "Villa Sarubbi"],
    "3361": ["Acaragua", "Campana", "Campo Ramon", "Colonia Alberdi", "Colonia Chapa", "Colonia Segui", "Florentino Ameghino", "General Alvear", "Guarani", "Guayabera", "Kilometro 4", "Kilometro 8", "Los Helechos", "Panambi", "Picada Sueca", "Picada Yapeyu", "Samambaya", "Villa Armonia", "Villa Bonita", "Villa Svea", "Yapeyu Centro"],
    "3362": ["1 De Mayo", "Campo Grande", "Campo Viera", "Destacamento Bosques", "Kilometro 17 Ruta 8"],
    "3363": ["25 De Mayo", "9 De Julio", "Alba Posse", "Bartolito", "Campos Salles", "Colonia Alicia", "Colonia Aparecida", "Colonia Aurora", "Colonia El Doradillo", "Colonia El Progreso", "Desplayada", "El Macaco", "El Saltito", "El Saltiño", "Filemon Posse", "Mai Bao", "Puerto Alicia", "Puerto Aurora", "Puerto Insua", "Puerto Londero", "Puerto San Martin", "San Carlos", "San Francisco De Asis", "Santa Rita", "Torta Quemada", "Tres Bocas", "Villa Vilma", "Villafañe"],
    "3364": ["2 De Mayo", "Alta Union", "Aristobulo Del Valle", "Aserradero Echeverria", "Aserradero Piñalito", "Barracon", "Bernardino Rivadavia", "Cainguas", "Capitan Antonio Morales", "Colonia Chafariz", "Colonia Fortaleza", "Colonia Gramado", "Colonia Juanita", "Colonia La Chillita", "Colonia La Gruta", "Colonia La Nueva", "Colonia La Polaca", "Colonia Mondori", "Colonia Paduan", "Colonia Palmera", "Colonia Primavera", "Colonia Puerto Rosales", "Colonia Siete Estrellas", "Comandante Andresito", "Cruce Caballero", "Cruce Londero", "Cuña Pora", "El Soberbio", "El Socorro", "El Tigre", "Fracran", "Fronteras", "Guaibichu", "Kilometro 286", "La Flor", "Las Mercedes", "Lujan", "Mesa Redonda", "Miguel Guemes", "Mocona", "Monteagudo", "Paraiso", "Paraje Lucero", "Pindaiti", "Pindayti", "Pozo Azul", "Puerto Paraiso", "Rio Yabotay", "Salto Encantado", "San Pedro", "San Vicente", "Santa Rosa", "Tobunas", "Villa Don Bosco"],
    "3366": ["Almirante Brown", "Barracon", "Bernardo De Irigoyen", "Campiñas De America", "Campo Alegre", "Colonia El Pesado", "Colonia Tres Marias", "Dos Hermanas", "Integracion", "Paraje Azopardo", "Paraje Estelina", "Paraje Granado", "Paraje Intercontinental", "Paraje Villa Union", "Piray Mini", "Piñalito Norte", "Piñalito Sur", "San Antonio"],
    "3370": ["Planchada Banderita", "Puerto Aguirre", "Puerto Canoas", "Puerto Carolina", "Puerto Iguazu", "Puerto Libertad", "Puerto Paulito", "Puerto Peninsula", "Puerto Uruguay", "Puerto Wanda", "Puerto Yacuy", "Tirica", "Villa Flor"],
    "3371": ["Cabure"],
    "3372": ["Cataratas Del Iguazu"],
    "3374": ["El Porvenir", "Libertad", "Puerto Bemberg", "Puerto Bossetti", "Puerto Errecaborde", "Segunda Zona"],
    "3376": ["Gobernador Lanusse", "Wanda"],
    "3378": ["22 De Diciembre", "Puerto Esperanza"],
    "3380": ["9 De Julio Kilometro 20", "Eldorado", "Kilometro 10"],
    "3381": ["Maria Magdalena", "Piray", "Puerto Delicia", "Puerto Piray", "Santiago De Liniers"],
    "3382": ["Colonia Cunci", "Colonia Delicia", "Colonia Duran", "Colonia Victoria", "Pati Cua", "Puerto El Dorado", "Puerto Mado", "Puerto Paticaa", "Puerto Pinares", "Puerto Victoria", "Villa Roulet"],
    "3384": ["Barrancon", "Citrus", "Colonia Florida", "Colonia Santa Teresa", "Deseado", "El Alcazar", "Estancia Santa Rita", "Guaraypo", "Ita Curuzu", "Kilometro 34", "Kilometro 60", "La Misionera", "La Posta", "Larraque", "Linea De Peray", "Macaca", "Macaco", "Montecarlo", "Puerto Avellaneda", "Puerto Laharrague", "Puerto Paranay", "Villa Ojo De Agua", "Villa Union"],
    "3386": ["Caraguatay", "Paranay", "Puerto Alcazar", "Puerto Caraguatay", "Taruma"],
    "3400": ["Bañado Norte", "Bañado Sur", "Corrientes", "Doctor Felix Maria Gomez", "Parque San Martin", "Villa El Dorado", "Villa Juan De Vera"],
    "3401": ["Arroyo Pelon", "Arroyo Ponton", "Arroyo Solis", "Campo Grande", "Cañada Quiroz", "Colonia Alvarez", "Colonia Maria Esther", "Colonia Matilde", "Costa", "Costa Rio Parana", "El Pelon", "El Pollo", "Ingenio Primer Correntino", "Isla Ibatay", "Juan Ramon Vidal", "Kilometro 13", "Laguna Brava", "Laguna Paiva", "Laguna Soto", "Lomas San Cayetano", "Palmera", "Pampin", "Paso Lovera", "Paso Martinez", "Paso Pesoa", "Ralera Sud", "San Cayetano", "San Jose", "Santa Ana", "Tala Cora", "Villa San Isidro", "Villa Solari"],
    "3403": ["Aguirre Cue", "Aguirre Lomas", "Albardones", "Alta Mora", "Bargone", "Bregain Cue", "Briganis", "Broja Cue", "Campo Grande", "Carabajal", "Caruso Apeadero Fcgu", "Cavia Cue", "Cañada Grande", "Cerrudo Cue", "Colonia Llano", "Costa Grande", "Desaguadero", "El Ponton", "El Vasco", "Empedrado Limpio", "Esquivel Cue", "Garabata", "Garrido", "Gdor Juan Eusebio Torrent", "Herlitzka", "Kilometro 31", "Kilometro 42", "Kilometro 49", "Kilometro 55", "Kilometro 57", "Kilometro 61", "Kilometro 76", "Kilometro 84", "Kilometro 89", "Kilometro 95", "La Eloisa", "Laguna Alfonso", "Las Palmitas", "Lomas De Galarza", "Lomas De Gonzalez", "Lomas Esquivel", "Maloya", "Monte Grande", "Obraje Del Vasco", "Oratorio", "Pueblito Espinosa", "Riachuelito", "Riachuelo Bardeci", "Rincon De Las Mercedes", "San Luis Del Palmar", "Santa Teresa", "Santos Lugares", "Sombrero", "Tiquino", "Tres Cruces", "Tripoli", "Vecindad"],
    "3405": ["Algarrobal Puisoye", "Cañada Grande", "Cerrito", "Colonia Juan Pujol", "Costa Santa Lucia", "Fernandez", "Frontera", "Kilometro 148", "Kilometro 151", "La Flecha", "La Parada", "Loma Alta", "Lomas De Aguirre", "Lomas De Vallejos", "Lomas De Vergara", "Lomas Ramirez", "Lomas Vazquez", "Los Vences", "Maloyita", "Naranjaty", "Obraje Cue", "Ombu Lomas", "Palmar Grande", "Puisoye", "Punta Grande", "Rincon Zalazar", "Rodeito", "Saldana", "Tacuaral", "Talaty", "Tolatu", "Vergara", "Vergara Lomas", "Zapallar"],
    "3407": ["Aguay", "Algarrobales", "Altamora Parada", "Ayala Cue", "Caa Cati", "Capillita", "Chircal", "Colonia Amadei", "Colonia Danuzzo", "Colonia Durazno", "Colonia Florencia", "Colonia San Martin", "Colonia Tacuaralito", "Costas", "El Salvador", "General Paz", "La Jaula", "Loma Villanueva", "Lomas Redondas", "Ntra Sra Del Ros De Caa Cati", "Paso Florentin", "Paso Gallego", "Paso Saldaña", "Rincon De Vences", "Romero", "Rosadito", "San Jose", "San Jose Caacati", "Timbo Cora", "Villa San Ramon", "Zapallos"],
    "3409": ["Arroyo San Juan", "Colonia M Aberastury", "Costa Toledo", "Paso De La Patria", "Puerto Araza", "Puerto Gonzalez", "Rincon", "San Juan"],
    "3412": ["Albardon", "Bedoya", "Buena Vista", "Chilecito", "Ensenada Grande", "Ensenadita", "Guayu", "Isla Ibate", "Mandinga", "Matilde", "Paraje Iribu Cua", "Ramada Paso", "San Cosme", "Santa Rita", "Santo Domingo", "Socorro", "Soledad", "Tuyuti", "Villa Cue", "Villaga Cue", "Yacarey", "Yahape"],
    "3414": ["Abra", "Corsa Cue", "Curuzu", "Ibiray", "Itati", "La Palmira", "La Union", "Mbalguiapu", "San Francisco Cue", "San Isidro", "San Jose", "San Salvador", "Yagua Rocau"],
    "3416": ["Arroyo Ceibal", "Carabajal Este", "Colonia Arrocera", "Colonia Nueva Valencia", "Costa De Arroyo San Lorenzo", "Costa De Empedrado", "Dos Ombues", "El Sombrero", "Garrido Cue", "Kilometro 476", "Kilometro 485", "Kilometro 492", "Kilometro 494", "Kilometro 501", "Kilometro 504", "Kilometro 512", "Kilometro 516", "Manuel Derqui", "Matadero Santa Catalina", "Pehuaho", "Pueblito San Juan", "Real Cue", "Riachuelo", "Riachuelo Sud", "Rincon De Ambrosio", "Rincon De San Lorenzo", "Rincon Del Sombrero", "San Lorenzo", "Seccion Primera San Juan"],
    "3418": ["Bartolome Mitre", "Bernachea", "Cañada Burgos", "Colonia Brougnes", "Empedrado", "Empedrado Limpio", "Kilometro 451", "Kilometro 462", "Lomas De Empedrado", "Mansion De Invierno", "Ocanto Cue", "Pago Poi", "Villa San Juan"],
    "3420": ["Acuña Cue", "Angua", "Arroyo Ambrosio", "Carman", "Casuarinas", "Cnia Oficial Juan Bautista", "Colonia Juan B Cabral", "El Carmen", "Guazu Cora", "Jardin Florido", "Kilometro 406", "Km 425", "La Mansion", "La Querencia", "Lago Arias", "Lauretti", "Lomas", "Lomas Saladas", "Los Lirios", "Mediodia", "Mira Flores", "Muchas Islas", "Pago Arias", "Paraje Augua", "Paso Naranjito", "Paso Naranjo", "Pastores", "Pindoncito", "Rincon San Pedro", "Saladas", "San Emilio", "San Francisco", "San Nicolas", "Santo Domingo", "Soledad", "Sosa Cue"],
    "3421": ["Bajo Guazu", "Batel", "Colonia Dora Elena", "Colonia Lucero", "Colonia Santa Rosa", "Pindo", "San Nicolas", "Santa Rosa", "Tabay", "Tatacua"],
    "3423": ["Arañita", "Batara", "Caiman", "Capilla Cue", "Carambola", "Colonia Jacobo Finh", "Colonia La Habana", "Colonia Tatacua", "Concepcion", "Costa Del Batel", "El Buen Retiro", "El Porvenir", "El Yuqueri", "Estancia San Roberto", "Estancia Santa Maria", "Iguate Pora", "La Angelita", "La Aurora", "La Pepita", "Los Angeles", "Lujambio", "Montevideo", "Nuevo Porvenir", "Palmar", "Paraje Florida", "Paso Iribu Cua", "Paso Lucero", "Porvenir", "San Agustin", "San Francisco", "San Jose", "San Juan", "San Nicanor", "Santa Maria", "Santa Rita", "Sauce", "Tajibo", "Talita Cue", "Tartaguito", "Tres Hermanas", "Virgen Maria", "Yaguaru"],
    "3425": ["Costa Grande", "Loma Alta", "Pago Alegre", "Pago De Los Deseos"],
    "3427": ["Abra", "Arroyito", "Buena Vista", "Campo Cardozo", "Campo Fernandez", "Cardozo Phi", "Chacras", "Chamorro", "Costa", "Costa San Lorenzo", "El Pago", "Francisco Gauna", "La Herminia", "Loma Alta", "Manantiales", "Mburucuya", "Oratorio", "Pasito", "Paso Aguirre", "Potrero Grande", "Punta Grande", "Ramones", "San Antonio", "San Juan", "San Lorenzo", "Santa Ana", "Santa Teresa", "Toros Cora", "Veloso"],
    "3428": ["Estacion Saladas", "Kilometro 431"],
    "3432": ["Bella Vista", "Carrizal", "Cebollas", "Chacras", "El Carrizal", "El Toro Pi", "Estacion Agronomica", "Las Garzas", "Lomas", "Lomas Este", "Macedo", "Martin", "Progreso", "Romero Cuazu", "San Fernando", "Villa Rollet", "Yagua Rincon", "Yuqueri"],
    "3433": ["Carrizal Norte", "Colonia 3 De Abril", "Colonia Progreso", "Raices"],
    "3440": ["Barrio Villa Cordoba", "Colonia Cecilio Echeverria", "Colonia General Ferre", "Colonia Lujan", "Colonia San Eugenio", "Colonia San Jose", "Crucecitas Santa Lucia", "Ferro", "La Pastoril", "Monte Florido", "Naranjito", "Quinta Teresa", "San Eugenio", "Villa Aquino", "Villa Cordoba"],
    "3441": ["Algarrobo", "Cruz De Los Milagros", "Desmochado"],
    "3443": ["Colonia Mendez Bar", "La Bolsa", "Lavalle", "Rincon De Soto", "Saladero San Antonio"],
    "3445": ["9 De Julio", "Algarrobal", "Algarrobo Paraje", "Arroyo Gonzalez", "Arroyo Paiso", "Bajo Grande", "Barrio Algarrobo", "Batal", "Bonete", "Cabana", "Cafarreño", "Cerrito", "Colonia Vedoya", "Costa Batel", "Costa Santa Lucia", "Crucecitas", "El Socorro", "Gobernador Juan E Martinez", "Kilometro 410", "Kilometro 416", "La Celia", "La Matilde", "Laguna Sirena", "Las Matreras", "Leon Cua", "Lomas Floridas", "Los Angeles Del Batel", "Luis Gomez", "Pueblo De Julio", "Puente Batel", "Puerta Ifran", "Saldana 9 De Julio", "San Antonio", "San Luis", "Santa Lucia", "Santa Lucia 9 De Julio", "Vedoya", "Yatay", "Yatayti Calle"],
    "3446": ["Kilometro 374", "Kilometro 387", "La Armonia", "La Lolita", "La Luisa", "Las Lagunas", "Manuel Florencio Mantilla", "San Diego", "San Rafael", "Santa Sinforosa", "Santiago Alcorta", "Seriano Cue", "Yacare"],
    "3448": ["Alamo", "Arroyito", "Balengo", "Caayobay", "Capita Mini", "Caraya", "Cañada Mala", "Isla Alta", "Kilometro 382", "Kilometro 402", "Laguna Avalos", "Laurel", "Manantiales", "Matrera", "Mojon", "Naranjito", "Naranjito San Roque", "Palmira", "Pirra Puy", "Rosado Grande", "Salinas Grande", "San Juan", "San Roque", "San Sebastian", "Santo Tomas", "Tatacua", "Timbo", "Yazuca"],
    "3449": ["Boliche Lata", "Colonia Pando", "Isla Alta", "Juan Diaz", "Santo Domingo"],
    "3450": ["8 De Diciembre", "Alamo", "Arroyo Carancho", "Balengo", "Batel", "Campo Araujo", "Campo Escalada", "Casualidad", "Colonia El Progreso", "Colonia Mercedes Cossio", "Colonia Pucheta", "Colonia Rolon Cossio", "Colonia Sauce", "Corona", "Curtiembre", "El Rosario", "Goya", "Granja Amelia", "Isla Sola", "Ita Curubi", "Laguna Pucu", "Lujan", "Maruchitas", "Paso Coronel", "Paso Santa Rosa", "Ranegas", "Remanso", "Rincon De Gomez", "Rolon Jacinto", "San Dionisio", "San Gregorio", "San Martin", "Santillan", "Soledad", "Tartaria"],
    "3451": ["Batelito", "Colonia Carolina", "Colonia La Carmen", "Colonia Porvenir", "Maruchas", "Mora", "Pago Redondo", "Paso Rubio", "Puerto Goya", "Rincon De Pago", "San Pedro", "Villa Rolon"],
    "3453": ["Ifran", "Isabel Victoria", "Manchita", "Masdeu Escuela 197", "Paranacito", "Punta Ifran", "Ñaembe"],
    "3454": ["Bañado San Antonio", "Buena Esperanza", "Buena Vista", "El Tatare", "El Transito", "Fanegas", "Invernada", "La Carlina", "La Celia", "La Concepcion", "La Cruz", "La Diana", "La Elvira", "Los Ceibos", "Paraje San Isidro", "Paso Bandera", "Paso Los Angeles", "Paso San Juan", "Puente Machuca", "San Alejo", "San Isidro", "San Manuel", "San Marcos", "Tres Bocas"],
    "3460": ["Arroyo Castillo", "Casillas", "Colonia Acuña", "Curuzu Cuatia", "El Ceibo", "El Ñandubay", "Espinillo", "Estancia El Carmen", "Estancia El Chañar", "Estancia Los Paraisos", "Estancia San Julio", "Kilometro 405", "La Cautiva", "La Cañada", "Labory", "Lobory", "Paraiso", "Paso Ancho", "Paso De Las Piedras", "Paso Lopez", "Rincon", "Rincon De Yaguary", "Sarandi", "Siete Arboles", "Tierra Colorada", "Tunitas", "Vaca Cua", "Yaguary"],
    "3461": ["Abo Nezu", "Aguay", "Casualidad", "Colonia Chircal", "Cuarta Seccion Lomas", "El Cerro", "Esperanza", "Estrella", "La Flor", "La Florentina", "La Fortuna", "Las Lomas", "Los Tres Amigos", "Maria", "Nina", "Nueva Granada", "Palmitas", "Paso Tala", "Perugorria", "Puente Avalos", "Rincon Quiroz", "San Pedro", "San Rafael", "Vaca Paso"],
    "3463": ["Aristia", "Arroyo Seco", "Barrancas", "Buena Ventura", "Buena Vista", "Caabi Poi", "Campo Maidana", "Campo Poy", "Cavi Poy", "Cañaditas", "Dos Hermanas", "El Tesoro", "El Tigre", "Estancia Rincon Grande", "Ferret", "La Concepcion", "La Delicia", "La Estrella", "La Fe", "La Garcia", "La Leonor", "La Porteña", "Las Cuchillas", "Las Taperas", "Limas Cue", "Linda Vista", "Loma Alta", "Los Eucaliptos", "Martin Garcia", "Paso Bermudez", "Paso De Mula", "Pujol Bedoya", "Puntas De Francisco Gomez", "Puntas Del Tigre", "Rincon De Animas", "Rincon Del Tigre", "San Jose", "San Luis", "San Luis Cue", "San Martin", "Santa Rosa", "Santa Teresa", "Sauce", "Saucesito", "Seriano Cue", "Soto", "Villa Ortiz", "Villa Soto", "Villa Tesaro"],
    "3465": ["Arroyo Casco", "Capirari", "Capitan Joaquin Madariaga", "Cazadores Correntinos", "Chaquito", "Emilio R Coni", "Guaycuru", "Minuanes", "Pago Largo"],
    "3466": ["Abalo", "Abeli", "Acuña", "Arroyo Horqueta", "Baibiene", "El Loto", "Ibaviyu", "La Blanca", "La Floresta", "La Leontina", "Las Violetas", "San Celestino", "San Juan", "San Vicente", "Santa Juana", "Santa Maria", "Santa Rosa"],
    "3470": ["Arroyo Grande", "Callejon", "Capi Vari", "Capiguari", "Estancia Aguaceros", "Estancia Cerro Verde", "Estancia Gonzalez Cruz", "Estancia Ita Caabo", "Estancia La Calera", "Estancia La Maria", "Estancia Mandure", "Estancia Rosario", "Estancia Santa Cruz", "Estancia Tunas", "Ibira Pita", "Ita Cora", "Ita Pucu", "Itati Rincon", "Kilometro 287 Fcgu", "Kilometro 296", "La Belermina", "Mercedes", "Pasaje Santa Juana", "Paso Mesa", "Pay Ubre Chico", "Piedra Ita Pucu", "Rincon Tranquera General", "Salto Ita Jhase", "Tacural", "Yuqueri"],
    "3471": ["Alen Cue", "Alfonso Lomas", "Boqueron", "Buena Vista", "Colonia Carlos Pellegrini", "San Roquito", "San Salvador", "Tacural Mercedes", "Uguay"],
    "3472": ["Caaguazu", "Capita Mini", "El Cerrito", "El Pilar", "Felipe Yofre", "La Aurora", "La Carlota", "Las Elinas", "Las Rosas", "Naranjito", "Paimbre", "Paso Pucheta", "San Carlos", "San Eduardo", "San Nicolas", "Tarangullo", "Tatare"],
    "3474": ["Chavarria", "El Simbolar", "Estancia Del Medio", "Estancia Las Salinas", "Estero Piru", "La Celina", "Nueva Esperanza", "Oscuro", "Paso Chañaral", "San Antonio", "San Guillermo", "San Pedro", "Santa Irene", "Tacuaritas", "Uruguay", "Yapuca", "Yatay Cora"],
    "3476": ["El Remanso", "Est Solari", "Justino Solari", "Kilometro 261", "La Agripina", "La Estrella", "Maria Del Carmen", "Maria Idalina", "Mariano I Loza Est Solari", "Teblenari"],
    "3480": ["Algarrobal", "Barranqueras", "Blanco Cue", "Colonia Branchi", "Ibahay", "Ita Ibate", "La Loma", "Paraje Barranquitas", "Puesto Lata", "Santa Isabel", "Tilita"],
    "3481": ["Angostura", "Arerungua", "Colonia", "Colonia Romero", "El Palmar", "Estancia La Carmencha", "Estancia Mbota", "Estancia San Antonio", "Isla Tacuara", "Martinez Cue", "Mbarigui", "Palmar", "Palmar Arerungua", "Paso Potrero", "Pirayu", "Rincon", "Ruiz Cue", "San Antonio De Itati", "Tacuaracarendy", "Toro I", "Toro Pichay", "Valencia", "Villa Lujan"],
    "3483": ["Arroyo Balmaceda", "Bastidores", "Casualidad", "Catalan Cue", "Costa Cenisal", "Infante", "Ita Paso", "La Angela", "La Pachina", "Lapacho", "Lomas San Juan", "Loreto", "San Sebastian", "Timbo Paso", "Yta Paso", "Yuqueri", "Ñuruguay"],
    "3485": ["Carandaiti", "Carreta Paso", "Colonia", "Colonia Caiman", "Colonia Gaiman", "Colonia La Union", "Colonia Madariaga", "Colonia San Antonio", "Curupayti", "Curuzu Laurel", "El Carmen", "Ipacarapa", "Los Sauces", "Mboi Cua", "Montaña", "Ombu", "Palma Sola", "San Antonio Del Caiman", "San Miguel", "San Nicolas", "Santa Isabel", "Silvero Cue", "Tacuaral", "Tacuarembo", "Tape Rati", "Veron Cue", "Yatayti Poi", "Yatayti Sata"],
    "3486": ["Villa Olivari"],
    "3487": ["Puesto De Isla"],
    "3500": ["Colonia Florencia", "Colonia Palmira", "La Colonia", "Resistencia", "Tigre", "Tropezon", "Villa Alta", "Villa Barberan", "Villa El Dorado", "Villa Juan De Garay", "Villa Libertad", "Villa Paranacito"],
    "3501": ["Campo De Galnasi", "El Palmar", "La Liguria"],
    "3503": ["Barranqueras", "La Isla", "Puerto Vilelas", "Villa Forestacion"],
    "3505": ["Arroyo Quintana", "Colonia Baranda", "Colonia Benitez", "Colonia Campo Rossi", "Colonia El Pilar", "Colonia Popular", "Coronel Avalos", "Costa Ine", "El Tragadero", "Isla Antequera", "Isla Del Cerrito", "Kilometro 523", "La Evangelica", "La Ganadera", "La Loma", "La Palometa", "La Pilar", "Laguna Beligay", "Los Algarrobos", "Margarita Belen", "Maria Sara", "Pilar", "Puente Ine", "Puente Palometa", "Puerto Antequera", "Puerto Bastiani", "Puerto Tirol", "Punta De Rieles", "Punta Nueva", "Punta Rieles", "San Miguel", "Tres Horquetas", "Villa Jalon"],
    "3507": ["La Eduvigis", "Pampa Almiron", "Selvas Del Rio De Oro"],
    "3509": ["Campo El Bermejo", "Campo Winter", "Colonia Bermejo", "Colonia El Ciervo", "Colonia El Fiscal", "Colonia Esperanza", "Colonia La Filomena", "Colonia Sabina", "Colonia San Antonio", "Colonia Siete Arboles", "Colonia Tres Lagunas", "El 15", "El Perdido", "El Zapallar", "General Jose De San Martin", "Kilometro 39", "Kilometro 42", "Kilometro 48", "Kilometro 59", "Kilometro 62", "Loma Alta", "Loma Florida", "Pampa Chica", "Pampa Larga", "Paraje Las Tablas", "Puerto Zapallar", "Venezuela", "Villa Dos"],
    "3511": ["Colonia Coronel Dorrego", "Colonia Rodriguez Peña", "Kilometro 254", "Los Pozos", "Presidencia Roca"],
    "3513": ["Arbol Solo", "Charadai", "Colonia Codutti", "Colonia Lucinda", "Cote Lai", "El Tupi Kilometro 474", "Estancia El Sabalo", "Estero Redondo", "Fortin Cardoso", "General Obligado", "Kilometro 443", "Kilometro 474", "Kilometro 501", "Kilometro 519", "La Choza", "La Lucinda", "La Negra", "La Raquel", "La Sabana", "La Vicuña", "Las Toscas", "Lote 15 La Sabana", "Lote 9", "Macomitas", "Obraje La Vicuña", "Puesto Cocheri", "Puesto Mendizabal", "Rio Tapenaga"],
    "3514": ["Cacui", "Campo De La Choza", "Campo Echegaray", "Colonia Echegaray", "Colonia Juan Penco", "Colonia Mixta", "Colonia Puente Philipon", "El Obraje", "Fontana", "General Donovan", "Hivonnait", "Kilometro 2 Fcgb", "Kilometro 22", "Kilometro 29", "Kilometro 34", "Kilometro 38", "Kilometro 5", "La Elaboradora", "La Escondida", "La Verde", "Laguna Blanca", "Laguna Escondida", "Lapachito", "Liva", "Lote 48 Colonia Mixta", "Lote 53 Colonia Mixta", "Makalle", "Puente Philippon", "Puente Svritz", "Puerto Vicentini", "Rio Araza", "Vicentini", "Villa Sarmiento"],
    "3515": ["Capitan Solari", "Ciervo Petiso", "Colonia Elisa", "Colonias Unidas", "Ingeniero Barbet", "Kilometro 575", "Kilometro 602", "La Dificultad", "La Pastoril", "Laguna Limpia", "Las Garcitas", "Salto De La Vieja"],
    "3516": ["Basail", "Campo Gola", "Campo Verge", "Colonia Tacuari", "Colonia Urdaniz", "El Bañado", "Estancia La Aurora", "Florencia", "Kilometro 34", "Las Mercedes", "Los Palmares", "Paralelo 28", "Puerto Piracua"],
    "3518": ["Cabral Cue", "Cancha Larga", "Colonia Cabral", "Colonia Rio De Oro", "El 14", "El Lapacho", "El Palmar", "Guaycuru", "La Esperanza", "La Leonesa", "Laguna Patos", "Lapacho", "Las Palmas", "Las Rosas", "Loma Alta", "Pindo", "Puerto Las Palmas", "Punta De Rieles", "Quia", "Ranchos Viejos", "Rincon Del Zorro", "Rio De Oro", "San Fernando", "Tacuari", "Termas Del Cerrito", "Yatay"],
    "3522": ["El Retiro", "Floradora", "General Vedia", "La Magdalena", "Lote 15 Escuela 268", "Lote 16 Escuela 204", "San Carlos", "San Eduardo", "Tres Horquetas"],
    "3524": ["El Campamento", "El Mirasol", "La Posta", "La Rinconada", "Lote 92 La Rinconada", "Mieres", "Puerto Bermejo", "Rio Bermejo", "Solalinde", "Timbo"],
    "3526": ["Cabo Adriano Ayala", "Colonia San Isidro", "Gandolfi", "Gral Ignacio H Fotheringham", "Gral Lucio V Mansilla", "Kilometro 100", "Kilometro 139", "Kilometro 76 Rio Bermejo", "Nuevo Pilcomayo", "Olegario Victor Andrade", "Potrero De Los Caballos", "Puerto Eva Peron", "Velaz", "Villa Escolar"],
    "3530": ["Aldea Forestal", "Campo Feldman", "Colonia El Paraisal", "Colonia General Paz", "Colonia Puente Uriburu", "Cuatro Bocas", "El Tacuruzal", "El Zanjon", "Lote 4 Quitilipi", "Lote 43 Escuela 250", "Pampa La Peligrosa", "Pampa Legua Cuatro", "Picaditas", "Quitilipi", "Reduccion Napalpi", "Villa El Palmar"],
    "3531": ["Colonia Aborigen", "Colonia Blas Parera", "Colonia Pueblo Viejo", "Cuarta Legua 14", "El Palmar", "Guayaibi", "La Matanza", "Napalpi", "Pampa Del Indio", "Pampa Verde", "Santos Lugares"],
    "3532": ["Curandu", "Fortin Aguilar"],
    "3534": ["Colonia El Aguara", "Colonia Gualtieri", "Colonia La Lola", "Colonia Leandro N Alem", "El Totoral", "Kilometro 22", "La Esperanza", "La Soledad", "La Tambora", "Las Lomitas", "Lote 11", "Lote 14", "Lote 23", "Lote 3", "Lote 42", "Machagai", "Pampa Bandera", "Santa Marta", "Tres Palmas"],
    "3536": ["Bocas", "Colonia Coronel Brandsen", "Colonia Herrera", "Colonia Hipolito Vieytes", "Colonia Santa Elena", "Coronel Brandsen", "Cuatro Arboles", "El Curundu", "El Palmar", "El Raigonal", "Fortin Chaja", "Las Banderas", "Lote 4 Colonia Pastoril", "Martinez De Hoz", "Paso Del Oso", "Presidencia De La Plaza"],
    "3540": ["Avanzada", "Cabeza De Tigre", "Colonia Juan Jose Paso", "Colonia La Avanzada", "Colonia Las Avispas", "Colonia Los Ganzos", "Colonia Lote 10", "Colonia Matheu", "Fortin Potrero", "La Manuela", "La Nueva", "La Ofelia", "La Suiza", "La Tapera", "La Viruela", "La Ñata", "Las Golondrinas", "Las Golondrinas Sur", "Las Moreras", "Los Fortines", "Los Gansos", "Lote 10", "Tres Boliches", "Tucuru", "Villa Angela"],
    "3541": ["Campo Las Puertas", "Campo Nuevo", "Colonia El Curupi", "Colonia El Tigre", "Coronel Du Graty", "El Ñandubay", "Gato Colorado", "Kilometro 596", "Pueblo Clodomiro Diaz", "Santa Maria", "Santa Sylvina", "Tres Monjes"],
    "3543": ["Colonia Lote 12", "Colonia Lote 3", "El Esquinero", "El Porvenir", "Enrique Urien", "Haumonia", "Horquilla", "Invernada", "Kilometro 498", "Kilometro 520", "Kilometro 53", "Lote 1", "Lote 12", "Lote 17", "Lote 23 Samuhu", "Lote 24", "Lote 25", "Lote 7", "Lote 8", "Samuhu"],
    "3545": ["Kilometro 525", "Kilometro 530", "Lote 18 Pozo Colorado", "Villa Berthet"],
    "3550": ["Allende", "Cerrito", "El 38", "El 44", "El Bonete", "El Cincuenta", "Paraje Kilometro 12", "Santa Felicia", "Velazquez", "Vera"],
    "3551": ["Campo Monte La Viruela", "Cañada Ombu", "Colmena", "Desvio Kilometro 282", "Desvio Kilometro 392", "Garabato", "Golondrina", "Guaycuru", "Intiyaco", "Kilometro 302", "Kilometro 320", "Kilometro 392", "La Blanca", "La Selva", "La Zulema", "Las Delicias", "Los Amores", "Los Claros", "Los Leones", "Los Tabanos Desvio Km 366", "Ogilvie", "Paraje Tragnaghi", "Pozo De Los Indios", "Pueblo Golondrina", "Toba"],
    "3553": ["Colonia Duran", "Colonia El Toba", "Colonia Sager", "Costa Del Toba", "El Diecisiete", "Fortin Chilcas", "Fortin Olmos", "Paraje 29", "San Roque", "Santa Lucia", "Ñandu"],
    "3555": ["Campo Huber", "La Loma", "Las Palmas", "Los Cuervos", "Romang"],
    "3557": ["Caraguatay"],
    "3560": ["Campo Ubajo", "Colonia El Veinticinco", "Colonia Yaguarete", "La Esmeralda", "Las Anintas", "Las Catalinas", "Las Garsitas", "Reconquista", "Tres Bocas"],
    "3561": ["Avellaneda", "El Carmen De Avellaneda", "El Timbo", "Ewald", "La Vanguardia", "Moussy"],
    "3563": ["Colonia San Manuel", "El Araza", "La Potasa", "La Sarita", "Nicanor E Molinas", "Victor Manuel Segundo"],
    "3565": ["Arroyo Del Rey", "El Tajamar", "Florida", "Kilometro 17", "Kilometro 30", "La Josefina", "San Alberto", "Tartagal"],
    "3567": ["Dest Aeronautico Milit Reconqu", "La Lola", "Los Laureles", "Puerto Reconquista"],
    "3569": ["Barros Pazos", "Berna", "Campo El Araza", "Campo Furrer", "La Celia", "La Diamela"],
    "3572": ["Campo Garabato", "Campo Ramseyer", "Colonia Althuaus", "Colonia Ella", "Colonia Santa Catalina", "El Ricardito", "La Catalina", "Malabrigo"],
    "3574": ["Capilla Guadalupe Norte", "Guadalupe Norte", "Las Garzas"],
    "3575": ["Arroyo Ceibal", "Campo Grande", "Campo Siete Provincias", "Distrito 3 Isletas", "El Ceibalito", "El Tapialito", "Flor De Oro", "Ingeniero Chanourdie", "Lanteri", "Las Siete Provincias", "Los Lapachos", "Santa Ana"],
    "3580": ["Kilometro 408", "Puerto Ocampo", "San Vicente", "Villa Ocampo"],
    "3581": ["Campo Redondo", "Guasuncho", "Isleta", "Kilometro 41", "Kilometro 67", "La Reserva", "Mocovi", "Villa Adela"],
    "3583": ["Isla Tigre", "Villa Ana"],
    "3585": ["El Sombrerito", "Kilometro 403", "Kilometro 421", "La Clarita", "Paul Groussac"],
    "3586": ["Campo Yaguarete", "Ingeniero Garmendia", "Ingeniero Germania", "Las Toscas", "Yaguarete"],
    "3587": ["San Antonio De Obligado", "Tacuarendi"],
    "3589": ["Kilometro 23", "Kilometro 49", "Kilometro 54", "Obraje Indio Muerto", "Obraje San Juan", "Potrero Guasuncho", "Villa Guillermina"],
    "3592": ["Colonia Hardy", "El Rabon", "Puerto Piracuacito"],
    "3600": ["Bahia Negra", "Boca Del Riacho De Pilaga", "Capilla San Antonio", "Cañada Doce", "Colonia Dalmacia", "Colonia Isla Alvarez", "Colonia Isla De Oro", "Colonia Puente Pucu", "Colonia Puente Uriburu", "Formosa", "Guaycolec", "Hospital Rural", "Isla 9 De Julio", "Isla Oca", "La Colonia", "La Florida", "Lote 4", "Mojon De Fierro", "Monte Agudo", "Monte Lindo", "Monteagudo", "Pque Bot Forestal L Tortorelli", "Puerto Dalmacia", "Santa Catalina", "Timbo Pora", "Tres Marias", "Villa Del Carmen", "Villa Emilia"],
    "3601": ["Banco Payagua", "Campo Goreta", "Churqui Cue", "Colonia Aquino", "Colonia Campo Villafañe", "Colonia Cano", "Colonia El Rincon", "Colonia Pastoril", "Comisaria Pte Yrigoyen", "Costa Del Lindo", "Curupay", "El Angelito", "El Arbol Solo", "El Arbolito", "El Gato", "El Olvido", "El Ombu", "El Pindo", "El Silencio", "Esterito", "Fortin Galpon", "Fray Mamerto Esquiu", "Herradura", "Isla Payagua", "Ituzaingo", "La China", "La Esperanza", "La Lucrecia", "La Pasion", "La Picadita", "Los Claveles", "Mayor Edmundo V Villafañe", "Mercedes Cue", "Monte Lindo  Cnia Pastoril", "Presidente Yrigoyen", "Riacho Lindo", "Riacho Ramirez", "San Antonio", "San Cayetano", "San Francisco De Laishi", "Santa Maria", "Sargento Cabral", "Soldado Tomas Sanchez", "Tatane", "Tres Lagunas", "Tres Mojones", "Tres Pocitos"],
    "3603": ["Costa Rio Negro", "El Colorado", "Espinillo", "General Pablo Riccheri", "Hipolito Vieytes", "Kilometro 142", "Kilometro 193", "Kilometro 213", "Kilometro 232", "Las Cañitas", "Racedo Escobar", "Soldado Edmundo Sosa", "Villa Dos Trece"],
    "3604": ["Gran Guardia", "Los Pilagas", "Mariano Boedo", "San Hilario"],
    "3606": ["9 De Julio", "Barrio San Jose Obrero", "Cabo Noroña", "Campo Rigonato", "Casco Cue", "Colonia 5 De Octubre", "Colonia El Alba", "Colonia El Olvido", "Colonia El Zapallito", "Colonia Hardy", "Colonia La Disciplina", "Colonia Palmar Grande", "Colonia Sabina", "Coronel Jose I Warnes", "Costa Salado", "El Algarrobo", "El Bañadero", "El Corralito", "El Guajho", "El Palmar", "El Poi", "El Quebranto", "El Resguardo", "El Salado", "Estancia El Ciervo", "Gendarme Viviano Garcete", "Isla Toldo", "Jose Hernandez", "Kilometro 109", "Kilometro 1695", "La Blanca", "La Esperanza", "La Loma", "La Sirena", "Loma Senes", "Monseñor De Andrea", "Palmar Chico", "Para Todo", "Pilaga Iii", "Pirane", "Rincon Ñaro", "San Camilo", "San Jacinto", "San Simon", "Zorrilla Cue"],
    "3608": ["Agente Argentino Alegre", "Campo Oswald", "Desvio Los Matacos", "El Ñandu", "Estero Grande", "Estero Patiño", "Kilometro 128", "Kilometro 1895", "Laguna Murua", "Palo Santo", "Potrero Norte", "Rincon Ñandu"],
    "3610": ["Barrio San Martin", "Barrio Sud America", "Brigadier General Pueyrredon", "Ceibo Trece", "Clorinda", "El Paraiso", "Estancia Las Horquetas", "Isla De Puen", "Isla Gral Belgrano", "Loma Hermosa", "Parque Nacional", "Primavera", "Punta Guia", "Riacho Negro", "Sol De Mayo", "Virasol"],
    "3611": ["Angostura", "Ayudante Paredes", "Barrio El Porteño", "Bocarin", "Colonia Bouvier", "Curtiembre Cue", "El Pombero", "El Recodo", "Florentino Ameghino", "Garcete Cue", "Gobernador Luna Olmos", "Isla Apando", "Isla Caraya", "Laguna Gallo", "Laguna Naick Neck", "Lucero Cue", "Monte Claro", "Palma Sola", "Pigo", "Presidente Avellaneda", "Puerto Pilcomayo", "Punta Pora", "Riacho He He", "Rodeo Tapiti", "Rozadito", "Salvacion", "San Antonio", "San Juan", "Santa Isabel", "Sgto Mayor Bernardo Aguila", "Toro Paso", "Tres Lagunas", "Tte Gral Juan C Sanchez", "Villa Lucero"],
    "3613": ["Chirochilas", "Colonia Alfonso", "Colonia Jose M Paz", "Frontera", "La Frontera", "Laguna Blanca", "Laguna Ines", "Marca M", "Primera Junta", "Segunda Punta", "Siete Palmas"],
    "3615": ["Apayerey", "Bella Vista", "Buena Vista", "Cataneo Cue", "Chagaday", "Colonia 25 De Mayo", "Colonia Santa Rosa", "El Espinillo", "General Julio De Vedia", "General Manuel Belgrano", "Julio Cue", "La Urbana", "Loma Zapatu", "Loro Cue", "Mision Tacaagle", "Porton Negro", "Puerto San Carlos", "Soldado Heriberto Avalos", "Subtte Ricardo E Masaferro", "Tte Cnel Gaspar Campos", "Villa Gral Manuel Belgrano", "Villa Hermosa", "Villa Real"],
    "3620": ["Alto Alegre", "Andres Flores", "Ballon", "Colonia Alto Tigre", "Colonia Buena Vista", "Colonia Coronel Dorrego", "Comandante Fontana", "Coronel Argentino Larrabure", "El Cogoik", "El Porteño", "Fortin Fontana", "Jose Cancio", "Kilometro 184", "Mayor Marcelo T Rojas", "Nicora", "Nueva Italia", "Rincon Florido", "Saladillo", "Salado", "Soldado Ramon A Arrieta", "Tres Lagunas", "Yunca"],
    "3621": ["Domingo F Sarmiento", "El Porteñito", "Fortin Cabo 1Ro Lugones", "Fortin Sargento 1Ro Leyes", "Kilometro 224", "Las Lolas", "Maestro Fermin Baez", "Posta San Martin 2", "Pozo Navagan", "San Martin 2", "Urbana Vieja", "Villa General Guemes"],
    "3622": ["Bartolome De Las Casas", "Bruchard", "Teniente Brown"],
    "3624": ["Agente Felipe Santiago Ibañez", "Campo Azcurra", "Campo Del Cielo", "Colonia El Catorce", "Colonia El Silencio", "Colonia Guillermina", "Colonia Isla Sola", "Colonia Perin", "Colonia Reconquista", "Colonia Siete Quebrados", "Coronel Enrique Rostagno", "Doctor Carlos Montag", "El Oculto", "Ibarreta", "La Inmaculada", "Lazo Quemado", "Legua A", "Maestra Blanca Gomez", "Soldado Dante Salvatierra", "Soldado Ismael Sanchez", "Subteniente Perin", "Villa Adelaida", "Villa Mercedes"],
    "3626": ["Alolague", "Cabo 1Ro Casimiro Benitez", "Colonia Juan B Alberdi", "Colonia Juanita", "Colonia La Brava", "Colonia La Sociedad", "Colonia San Jose", "Colonia Santa Rosa", "Colonia Tatane", "Colonia Union Escuela", "Coronel Felix Bogado", "El Recreo", "Estanislao Del Campo", "Gabriela Mistral", "Hermindo Bonas", "Juan Jose Paso", "Kilometro 503", "Las Choyas", "Las Mochas", "Loma Clavel", "Los Inmigrantes", "Pato Marcado", "Porteño Viejo", "Ranero Cue", "San Lorenzo", "Saturnino Segurola", "Sgto Ayudante V Sanabria", "Transito Cue", "Tres Pozos"],
    "3628": ["Arbol Solo", "Cmte Principal Ismael St", "El Sauce", "Kilometro 1769", "La Paloma", "Los Esteros", "Paso De Naite", "Posta San Martin 1", "Pozo Del Tigre", "Pozo Verde", "Villa General Urquiza"],
    "3630": ["19 De Marzo", "Bajo Hondo", "Cabo Primero Chavez", "Campo Alegre", "Campo Redondo", "Cnia Aborigen Bme De Las Casas", "Colonia 8 De Septiembre", "Colonia Francisco J Muñiz", "Colonia Los Tres Reyes", "Colonia San Bernardo", "Colonia San Isidro", "Colonia San Pablo", "Colonia Santa Catalina", "Colonia Santoro", "Colonia Villa Rica", "Costa Del Pilcomayo", "El Ceibal", "El Coati", "El Corredero", "El Descanso", "El Mirador", "El Perdido", "El Quebracho", "El Tacuruzal", "El Totoral", "El Yacare", "El Yuchan", "Espinillo", "Fortin Cabo 1Ro Chaves", "Fortin Cabo 1Ro Chavez", "Fortin Guemes", "Fortin La Soledad", "Fortin Pilcomayo", "Isleta", "Kilometro 15", "Kilometro 525", "Kilometro 642", "Kilometro 642 Nav R Bermejo", "La Soledad", "Las Delicias", "Las Lomitas", "Las Saladas", "Los Baldes", "Los Claveles", "Los Suspiros", "Los Tres Reyes", "Nuevo Pilcomayo", "Olegario Victor Andrade", "Paso De Los Tobas", "Paso La Cruz", "Paso Nalte", "Pavao", "Posta Santa Fe", "Posta Sargento Cabral", "Pozo De Las Garzas", "Pozo De Los Chanchos", "Pozo De Navagan", "Pozo El Lecheron", "Pozo Hondo", "Pozo La China", "Pozo La Negra", "Puerto Ramona", "Puesto Aguara", "Punta De Agua", "Quebracho Marcado", "Reduccion Cacique Coquena", "Rio Cue", "San Isidro", "San Martin 1", "San Miguel", "San Ramon", "Santa Rosa", "Sargento Agramonte", "Soldado Ermindo Luna", "Soldado Marcelino Torales", "Suipacha", "Tatu Pire", "Tomas Godoy Cruz", "Tte Cnel Gaspar Campos"],
    "3632": ["El Pimpin", "El Tastas", "General Francisco B Bosch", "Juan Gregorio Bazan", "Kilometro 1695", "Los Chiriguanos", "Matias Gulacsi", "Posta Cambio A Zalazar", "Pozo Del Mortero"],
    "3634": ["Aguas Negras", "Alfonsina Storni", "Alto Alegre", "Bajo Verde", "Campo El Suri", "Capitan Juan Sola", "Colonia Santa Rosa", "El Acheral", "El Aibalito", "El Bordo Santo", "El Bragado", "El Cavado", "El Cañon", "El Corralito", "El Marcado", "El Mojon", "El Palo Santo", "El Paraiso", "El Pilon", "El Pindo", "El Remanso", "El Simbolar", "El Sombrero Negro", "El Surr", "El Yulo", "Ex Fortin Sola", "Ex Posta General Lavalle", "Fortin Media Luna", "Joaquin V Gonzalez", "Jose Manuel Estrada", "La Libertad", "La Manija", "La Media Luna", "La Nobleza", "La Palmita", "La Primavera", "La Represa", "Laguna Yema", "Lamadrid", "Las Avispas", "Las Bolivianas", "Los Galpones", "Los Nidos", "Los Pocitos", "Media Luna", "Miguel Cane", "Mision El Carmen", "Mision Evangelica Lag Yacare", "Poncho Quemado", "Posta Lencina", "Pozo De Las Botijas", "Pozo De Maza", "Pozo De Piedra", "Pozo Del Cuchillo", "Pozo Del Leon", "Reserva Natural Formosa", "Riacho Lindo", "Rio Muerto", "San Antonio", "San Isidro", "Sumayen", "Tres Pozos"],
    "3636": ["Agua Verde", "Bolsa De Palomo", "Buen Lugar", "Caballo Muerto", "Campo Grande", "Carlos Pelegrini", "Carlos Saavedra Lamas", "Cañada San Pedro", "Cnel Miguel Martinez De Hoz", "Doctor Gumersindo Sayago", "Doctor Luis Agote", "El Alambrado", "El Azotado", "El Desmonte", "El Mistolar", "El Potrerito", "El Potrillo", "El Quemado", "El Rosado", "El Totoral", "El Tucumancito", "El Zorro", "Esquinitas", "Florencio Sanchez", "Francisco Narciso De Laprida", "General Enrique Mosconi", "Gobernador Yalur", "Guadalcazar", "Ing Guillermo N Juarez", "Ingeniero Enrique H Faure", "La Florencia", "La Junta", "La Palma Sola", "Las Cañitas", "Las Tres Marias", "Los Chaguancos", "Lote Nro 8", "Maria Cristina", "Media Luna", "Mision El Quebracho", "Mistol Marcado", "Palma Sola", "Palmar Largo", "Palmarcito", "Pescado Negro", "Pozo Cercado", "Pozo De La Yegua", "Pozo De Los Chanchos", "Pozo Del Maza", "Pozo Verde Ing G N Juarez", "Puerto Irigoyen", "Ricardo Guiraldes", "San Isidro", "Santa Teresa", "Selva Maria", "Soldado Alberto Villalba", "Sombrero Negro", "Tte Gral Rosendo N Fra", "Vaca Perdida"],
    "3641": ["Arroyo Seco"],
    "3700": ["Barrio Gral Jose De San Martin", "Barrio Sarmiento", "Colonia Bajo Hondo", "Colonia Jose Marmol", "Kilometro 15", "Pampa Aguado", "Pampa Alegria", "Pampa De Los Locos", "Pampa Galpon", "Pampa Gamba", "Pampa Loca", "Presidencia Roque Saenz Peña"],
    "3701": ["Almirante Brown", "Colonia Bernardino Rivadavia", "Fortin Totoralita Lugar Histor", "La Chaco", "La Chiquita", "La Clotilde", "La Tigra", "Las Cuatro Bocas", "Las Cuchillas Cnia J Marmol", "Lote 10", "Lote 11", "Malbalaes", "Malbalaes Lote 45 Y 46", "Pampa De Las Flores", "Pampa Grande", "San Bernardo"],
    "3703": ["Aleloy", "Cabañaro Pasaje", "Colonia Alelay", "Colonia Velez Sarsfield", "El Boqueron", "El Cuarenta Y Seis", "El Destierro", "El Espinillo", "El Palmar Tres Isletas", "El Treinta Y Seis", "Fortin Lavalle", "Girasol", "Kilometro 841", "Kilometro 855 Estacion", "Kilometro 884", "La Matanza", "La Pobladora", "Ntra Señora De La Concepcion", "Pampa Aguara", "Pampa Alelai", "Pampa El 11", "Pampa El 12", "Pampa Florida", "Pampa Vargas", "Tres Isletas", "Tres Naciones", "Villa Rio Bermejito"],
    "3705": ["10 De Mayo", "Bajo Hondo", "Bajo Verde", "Berlin", "Bolsa Grande", "California", "Campo El Aibal", "Campo El Onza", "Campo Grande", "Campo Overos", "Colonia Cabeza De Buey", "Colonia El Alazan", "Colonia Esperanza", "Colonia Fortuni", "Colonia Indigena", "Colonia Juan Jose Castelli", "Colonia La Florida Chica", "Colonia La Florida Grande", "Colonia Monte Quemado", "Colonia San Antonio", "Comandancia Frias", "Corralito", "Doña Paula", "El 15", "El Aibal", "El Asustado", "El Desierto", "El Pintado", "El Quebrachal", "El Recreo", "El Sauzal", "El Sauzalito", "El Simbolar", "El Viscacheral", "Estancia Loma Alta", "Ex Fortin Arenales", "Ex Fortin Comandante Frias", "Ex Fortin Lavalle", "Ex Fortin Perez Millan", "Ex Fortin Wilde", "Ex Fortin Zelaya", "Fuerte Esperanza", "Juan Jose Castelli", "Kilometro 40", "La Armonia", "La Cañada", "La Costosa", "La Entrada", "La Esperanza", "La Estacion", "La Fidelidad", "La Flojera", "La Gringa", "La Invernada", "La Libertad", "La Media Luna", "La Mora", "La Rinconada", "La Saltarina", "La Soledad", "La Zanja", "Las Blancas", "Las Flores", "Las Hacheras", "Las Maravillas", "Las Vertientes", "Los Barriles", "Los Porongos", "Los Quirquinchos", "Los Tunales", "Lote Ocho", "Manantiales", "Miraflores", "Miramar", "Mision Angelicana", "Mision Nueva Pompeya", "Molle Marcado", "Monte Caseros", "Nueva Poblacion", "Nueva Union", "Palo Marcado", "Pampa Castro", "Pampa El Silencio", "Pampa Los Bedogni", "Pampa Machete", "Pampa Tolosa Chica", "Pampa Tolosa Grande", "Paraje El Colchon", "Paraje El Colorado", "Paso De Los Libres", "Pozo De La Linea", "Pozo De La Mula", "Pozo De La Pava", "Pozo De La Tuna", "Pozo De Las Garzas", "Pozo De Los Suris", "Pozo Del Cincuenta", "Pozo Del Gato", "Pozo Del Gris", "Pozo Del Molle", "Pozo Del Negro", "Pozo Del Tala", "Pozo Del Tigre", "Pozo Del Toro", "Pozo El Chañar", "Pozo La Brea", "Pozo La Osca", "Puerto Lavalle", "Puerto Urquiza", "Reducc San Bernardo De Vertiz", "Reduccion De La Cangaye", "Rosales", "San Agustin", "San Antonio", "San Juancito", "San Lorenzo", "Santa Rita", "Santo Domingo", "Sol De Mayo", "Tartagal", "Tolderias", "Tres Pozos", "Wichi", "Zaparinqui"],
    "3706": ["Avia Terai", "Cnia Agricola Pampa Napenay", "Colonia Mariano Sarratea", "El Catorce", "El Triangulo", "La Mascota", "Lote 34", "Napenay", "Pampa Del Regimiento"],
    "3708": ["Concepcion Del Bermejo", "Pampa Borracho", "Pampa Del Infierno", "Pampa Hermosa", "Pampa Juanita"],
    "3712": ["Belgica", "Campo La Angelita", "Colonia El Peligro", "Coronel Manuel Leoncio Rico", "Desvio Kilometro 1342", "El Aerolito", "El Cabure", "El Perseguido", "El Silencio", "Estados Unidos", "Kilometro 1297", "Kilometro 1314", "Kilometro 1338", "Kilometro 1362", "Kilometro 1380", "Kilometro 1391", "La Angelita", "La Armonia", "La Granja", "Las Perforaciones", "Lavalle", "Los Frentones", "Los Monteros", "Los Pirpintos", "Los Tigres", "Pampa De Los Guanacos", "Pinedo", "Pozo Vil", "Puesto Cordoba", "Puesto Del Medio", "Punta Rieles", "Rio Muerto", "San Horacio", "San Pedro", "Santa Maria", "Urundel"],
    "3714": ["9 De Julio", "Agua Buena", "Atahualpa", "Botija", "Castellin", "Colombia", "El Cañon", "El Cerrito Monte Quemado", "El Guanaco", "El Indio", "El Palmar", "El Palomar", "El Paraiso", "El Valla", "Fierro", "Kilometro 1183", "Kilometro 1210", "Kilometro 1255", "La Aguada", "La Argentina", "La China", "La Firmeza", "La Ilusion", "La Paloma", "La Pinta", "La Providencia", "La Sara", "La Tranquilidad", "La Virtud", "Las Carpas", "Las Delicias", "Las Flores", "Las Perforaciones", "Lorena", "Los Magos", "Los Tigres", "Los Tobas", "Lote 33", "Madre De Dios", "Monte Quemado", "Nueva Esperanza", "Nueva York", "Obraje Los Tigres", "Paaj Pozo", "Palo Blanco", "Pampa Bolsa", "Pampa Cabure", "Pampa El Fosforito", "Pampa El Mangrullo", "Pampa El Mollar", "Pampa Pelado", "Pampa Pereyra", "Pampa Quimili", "Pampa Ralera", "Pampa Virgen", "Paraje Independencia", "Paraje Kilometro 77", "Paraje Ojo De Agua", "Paraje Santa Cruz", "Pozo Hondo", "San Agustin", "San Antonio", "San Jose", "San Luis", "San Martin", "San Telmo", "Santa Agueda", "Santa Elena", "Santa Rosa", "Santa Rosa Copo", "Santa Teresa De Carballo", "Taco Pozo", "Urundel", "Urutau"],
    "3716": ["Campo Largo", "Colonia Malgratti", "Fortin Las Chuñas", "La Cuchilla", "La Flecha", "Pampa Oculta"],
    "3718": ["Amambay", "Corzuela", "Loro Blanco", "Pampa Alsina", "Pampa Cuvalo", "Pampa Grande", "Puesto Carrizo"],
    "3722": ["2 De Mayo", "Campo Zapa", "Colonia Cuero Quemado", "Colonia General Necochea", "Colonia Juan Lavalle", "Curva De Novoa", "Dos Boliches", "El Cajon", "El Estero", "El Oro Blanco", "El Recoveco", "El Recovo", "Las Breñas", "Las Cuchillas", "Las Piedritas", "Los Cerritos", "Los Chinacos", "Pampa Brugnoli", "Pampa Del Cielo", "Pampa Del Huevo", "Pampa Del Tordillo", "Pampa Del Zorro", "Pampa Hermosa", "Pampa Ipora Guazu", "Pampa Mitre", "Pampa San Martin", "Pampa Villordo", "Pampa Zanata", "Pampini", "Pozo Del Indio Estacion Fcgb", "Pueblo Puca"],
    "3730": ["Cabral", "Campo Ferrando", "Cerrito", "Charata", "Colonia Barrera", "Colonia Juan Larrea", "Colonia Schmidt", "El Picaso", "El Puca", "General Necochea", "India Muerta", "Ipora Guazu", "Los Gualcos", "Lote 77", "Pampa Avila", "Pampa Barrera", "Pampa Cejas", "Pampa Del Cielo", "Pampa Flores", "Pampa Sommer", "Pueblo Puca"],
    "3731": ["Arbol Blanco", "Meson De Fierro", "Pampa Cabrera", "Pampa Landriel", "Sachayoj", "Santa Elvira", "Tres Estacas"],
    "3732": ["Colonia Abate", "Colonia Bravo", "Colonia Economia", "Colonia El Triangulo", "Colonia Hamburguesa", "Colonia Necochea Sud", "Colonia Welhers", "El Palmar", "El Triangulo", "General Capdevila", "General Pinedo", "La Economia", "Las Leonas", "Ministro Ramon Gomez", "Palmar Central", "Palmar Norte", "Pampa Dorotier", "Pinedo Central", "Puerta De Leon", "Welhers"],
    "3733": ["Campo El Jacaranda", "Chorotis", "Colonia El Tizon", "Colonia Quebrachales", "Colonia Tañigo", "Hermoso Campo", "Itin", "Kilometro 523", "Tres Mojones", "Venados Grandes", "Zuberbuhler"],
    "3734": ["Campo Moreno", "Colonia Drydale", "Colonia La Maria Luisa", "Colonia La Tota", "El Arbolito", "El Bravo", "El Cuadrado", "El Estero", "El Porongal", "El Puma", "El Saladillo", "Gancedo", "La Cuchilla", "Los Fortines", "Los Quebrachitos", "Viboras"],
    "3736": ["Agua Salada", "Calderon", "Campo Del Cielo", "Campo Del Infierno", "Campo El Rosario", "Dos Represas", "El Urunday", "El Veinte", "Estancia Nueva Esperanza", "Girardet", "Huchupayana", "La Paloma", "Roversi", "Taco Fura", "Tres Mojones"],
    "3740": ["Aibal", "Anchilo", "Barrio Obrero", "Bella Vista", "Campo Limpio", "Cartavio", "Cañada Limpia", "Colonia España", "Colonia Media", "Dolores", "Dos Eulacias", "Dos Hermanas", "El Aibalito", "El Crucero", "El Descanso", "El Fisco", "El Noventa", "El Ojo De Agua", "Estancia La Elsita", "Jardin De Las Delicias", "Juncal Grande", "Kilometro 48", "La Loma", "Laguna Baya", "Los Pensamientos", "Los Puentes", "Maravilla", "Maria", "Minerva", "Nogales", "Paraje El Prado", "Paraje Gauna", "Paraje La Pampa", "Paraje Lilo Viejo", "Paraje Milagro", "Paraje Obraje Maria Angelica", "Paraje Villa Yolanda", "Pirhuas", "Proviru", "Puesto De Mena", "Puma", "Quimili", "Rumi", "Saldivar", "San Jose", "San Nicolas", "Santa Justina", "Tinajeraloj", "Villa Guañuna", "Villa Matilde"],
    "3741": ["Aerolito", "Agustina Libarona", "Alhuampa", "Cejolao", "Doble Tero", "Donadeu", "Dos Eulalias", "El Colorado", "El Fisco", "El Fisco De Fatima", "El Noventa", "El Tanque", "Genoveva", "Granadero Gatica", "Haase", "Hernan Mejia Miraval", "Kilometro 606", "Kilometro 719", "La Curva", "La Marta", "Las Porteñas", "Los Gatos", "Los Milagros", "Los Pecariel", "Los Porteños", "Lote F", "Magdalena", "Morayos", "Octavia", "Otumpa", "Pozo Del Toba", "San Alberto", "San Miguel", "Santa Elena"],
    "3743": ["El Prado", "El Veintisiete", "Estacion Pampa Muyoj", "La Pampa", "Milagro", "Monte Alto", "Obraje Maria Angelica", "Tintina", "Villa Yolanda"],
    "3745": ["Central Dolores", "El 21", "El Hoyo", "Hualo Cancana", "Huilla Catina", "Kilometro 694", "La Chejchilla", "Libertad", "Lilo Viejo", "Patay", "Pozo Castaño", "Puesto Del Medio", "Quilumpa", "Saladillo"],
    "3747": ["Aibalito", "Alberdi", "Campo Gallo", "Estancia La Agustina", "Florida", "Kilometro 20", "La America", "La Fortuna", "Las Carpas", "Monte Verde", "Obraje Iriondo", "Pozo Muerto", "Pozo Salado", "San Antonio", "Yunta Pozo"],
    "3749": ["Agua Blanca", "Bahia Blanca", "Campo Alegre", "Campo Del Aguila", "Campo Verde", "Chainima", "Chañar Pozo", "Cuquero", "Dos Varones", "El Cambiado", "El Colmenar", "El Corrido", "El Oscuro", "El Rosario", "El Simbol", "El Traslado", "El Valle", "El Valle De Oriente", "La Argentina", "La Armonia", "La Cañada", "La Defensa", "La Esperanza", "La Union", "Las Aguilas", "Los Carrizos", "Maidana", "Maravilla", "Nuevo Libano", "Nuevo Lujan", "Palermo", "Parana", "Rivadavia", "San Carlos", "San Juan", "Santa Rosa", "Villa Hazan", "Vinal Pozo"],
    "3752": ["El Mistol", "Kilometro 499", "Nasalo", "Noge", "Pozo Colorado", "Puna", "Quebracho Pintado", "Tobas", "Vilelas"],
    "3760": ["Añatuya", "Barrio La Leñera", "Barrio Villa Fernandez", "Binal Esquina", "Coronel Barros", "El Mataco", "Kilometro 515", "La Encalada", "La Esmeralda", "La Estancia", "Lote 15", "Puni Tajo", "Santa Ana", "Simbol Bajo", "Suncho Pozo", "Tinap Jerayoj", "Veintiocho De Marzo", "Villa Abregu"],
    "3761": ["El Malacara", "Los Linares", "Miel De Palo", "Pozo Herrera"],
    "3763": ["Kilometro 450", "La Simona", "Los Juries", "Obraje Mailin", "Tres Pozos"],
    "3765": ["El Cuadrado", "Kilometro 443 Taboada", "Kilometro 477", "La Balanza", "La Nena", "La Reconquista", "Lote 42", "Tomas Young"],
    "3766": ["3 De Marzo", "Agua Dulce", "Averias", "Gualamba", "Kilometro 433", "Kilometro 454", "La Esmeralda", "Las Flores", "Los Pocitos", "Lote 27 Escuela 286", "Tacañitas"],
    "4000": ["Estacion De Zootecnia B", "Kilometro 180", "Los Pinos B", "San Bernardo B", "San Miguel De Tucuman", "Villa Muñecas", "Villa Zenon Santillan"],
    "4101": ["Agua Negra", "Aguadita", "Alta Gracia De Villa Burruyacu", "Aserradero", "Barrio Diagonal", "Barrio Rivadavia", "Cañada Honda", "Cañada Larga", "Chorrillos", "Colonia Los Hills", "Colonia San Ramon", "Colonia Sarmiento", "Cuchillas", "El Mutul", "El Timbo", "Embalse El Cadillal", "Escuela 107", "Escuela 163", "Escuela 164", "Escuela 210", "Escuela 215", "Escuela 218", "Escuela 219", "Escuela 255", "Escuela 256", "Escuela 299", "Escuela 300 La Picada", "Escuela 350", "Escuela 393", "Escuela 48", "Escuela 59", "Escuela 70", "Escuela Capitan Gaspar De Medi", "Escuela Ee Uu", "Escuela Fortunata Garcia", "Escuela Miguel Azcuenaga", "Escuela Miguel Cervantes", "Escuela Ramon Carrillo", "Estacion Experimental Agricola", "Estacion Superior Agricola", "Granja Modelo", "La Aguadita", "La Cienaga", "La Puerta", "Las Salinas", "Las Talitas", "Las Trancas Tranquitas", "Leo Huasi", "Los Hilos", "Los Nogales", "Los Pocitos", "Los Timbos", "Matul", "Medina", "Nio Villa Padre Monti", "Nogalito", "Nueva Rosa", "Ojo", "Potrerillo", "Puerta De Palavecino", "Puerta Vieja", "Rio Loro", "Sunchal", "Timbo Nuevo", "Timbo Viejo", "Tranquitas", "Tres Sargentos", "Vacahuasi", "Villa De Los Britos", "Villa Padre Monti", "Villa Rosa"],
    "4103": ["Bajo De Raco", "Comuna La Esperanza", "El Cadillal", "El Cuarteadero", "El Duraznito", "El Pelado", "El Tiro Argentino", "El Zanjon", "Gral Anselmo Rojo", "Kilometro 925", "La Falda", "La Manga", "La Picada", "La Ramada", "La Toma", "Lacavera", "Laguna Grande", "Las Cañitas", "Las Moritas", "Los Estanques", "Los Zaragoza", "Luz Y Fuerza", "Monasterio", "Nueva Esperanza", "Pueblo Obrero", "Puesto Cienaga Amarilla", "Rincon", "Tafi Viejo", "Taficillo", "Talleres Nacionales", "Villa Colmena", "Villa La Colmena", "Villa Mitre"],
    "4105": ["Abra Del Tafi", "Anca Juli", "Anfana", "Calimayo", "Camino Del Peru", "Campo Herrera", "Campo Redondo", "Cevil Redondo", "Chasquivil", "Colonia Felipe", "Colonia Los Chasales", "Colonia Tacapunco", "Cuatro Sauces", "Curva De Los Vegas", "El Catorce", "El Ceibal", "El Duraznillo", "El Manantial", "El Nogalito", "El Siambon", "Escuela", "Escuela 113", "Escuela 311", "Escuela Antonio Medina", "Escuela Granaderos De San Mart", "Escuela Otilde De Toro", "Fagsa", "Finca Tina", "Hitachi", "Horco Molle", "Hoyada", "Kilometro 792", "Kilometro 808", "La Banda", "La Bomba", "La Cavera", "La Hoyada", "La Sala", "Las Juntas", "Las Talas", "Las Tipas", "Lomas De Imbaud", "Los Aguirre", "Los Alamos", "Los Alcaraces", "Los Bulacio", "Los Chamicos", "Los Planchones", "Los Vazquez", "Manantial De Ovanta", "Misky", "Mundo Nuevo", "Parada De Ohuanta", "Potrerillo", "Puerto Cochucho", "Raco", "Ruta Provincial 338", "San Alberto", "San Felipe", "San Javier", "San Miguel", "Santa Barbara", "Tecotex", "Tipas", "Villa Angelina", "Villa Carmela", "Villa Nogues", "Villa San Javier", "Yerba Huasi"],
    "4107": ["Aconquija", "Alto De Anfama", "Antama", "Barrio Casino", "Cuatro Gatos", "Higueritas", "Iglesias", "La Cañada Parada", "La Rinconada Parada", "Las Mellizas", "Ojo De Agua", "Pie Del Aconquija", "Puerta San Javier", "Villa Marcos Paz", "Yerba Buena"],
    "4109": ["Alto Nuestra Señora Del Valle", "Banda Del Rio Sali", "Barrio Belgrano", "Ingenio Concepcion", "Ingenio San Juan", "Los Vallistos", "Nuevos Mataderos", "Puente Rio Sali"],
    "4111": ["Aguada", "Bajo Grande", "Bañado Del Valle", "Bilca Pozo", "Campana", "Candelillal", "Carbon Pozo", "Cevilarcito", "Chañar Pago", "Chilcal", "Colombres", "Colonia Agricola", "Colonia Argentina", "Cortaderal", "Cortaderas", "Costa Arroyo Esquina", "El Bracho", "El Cevilar Colombres", "El Cortaderal", "Esquina", "Esquina Del Llano", "Finca Elisa", "Finca Pacara", "Fronteritas", "Gobernador Nouges", "Ingenio Leales", "Juan Posse", "Kilometro 794", "La Aguada", "La Empatada", "La Encantada", "La Fronterita", "Las Mercedes", "Lastenia", "Loma Verde", "Los Bulacio", "Los Camperos", "Los Chañaritos", "Los Porceles", "Los Sueldos", "Los Villagra", "Pacara", "Pacara Pintado", "Pala Pala", "Polito", "Pozo Alto", "Pozo Del Alto", "Puesto Chico", "Quilmes", "Retiro", "Roma", "Rosario Oeste", "San Andres", "San Nicolas", "Santa Felisa", "Santa Rosa De Leales", "Sueldo", "Sueldos", "Villa Fiad"],
    "4113": ["Acostilla", "Avestilla", "Cachi Huasi", "Cachi Yaco", "Cachi Yaco Apeadero Fcgb", "El Carmen", "El Durazno", "El Guardamonte", "El Naranjo", "El Rosario", "Entre Rios", "Gomez Chico", "Las Acostillas", "Las Cañadas", "Leales", "Los Britos", "Los Crespo", "Los Gomez", "Los Herreras", "Los Juarez", "Los Quemados", "Los Romanos", "Lunarejos", "Miguel Lillo", "Noario", "Nueva España", "San Jose De Leales", "Tusca Pozo", "Tusquitas", "Uturungu", "Villa De Leales", "Yatapayana"],
    "4115": ["Agua Azul", "Agua Dulce", "Ahi Veremos", "Barrealito", "Buena Vista", "Camas Amontonadas", "Campo Azul", "Condor Huasi", "El Mollar", "El Naranjito", "El Pavon", "El Suncho", "Establecimiento Las Colonias", "Favorina", "Jusco Pozo", "La Colonia", "La Florida", "Laguna Blanca", "Las Celayas", "Las Colonias", "Las Encrucijadas", "Las Palmitas", "Las Zorras", "Los Chañaritos", "Los Puestos", "Los Villegas", "Los Zelayas", "Mancopa", "Mancopa Chico", "Mixta", "Mojon", "Monte Bello", "Moyar", "Naranjito", "Oran", "Palmitas", "Pirhuas", "Posse Desvio Particular Fcgm", "Puma Pozo", "Punta De Rieles", "Punta Rieles", "Rafaela Pozo", "Romera Pozo", "San Antonio", "Sandis", "Soledad", "Vielos", "Vilca Pozo"],
    "4117": ["Alabama", "Alto De Medina", "Angostura", "Carolinas Bajas", "Cañada De Alzogaray", "Chabela", "Chañar Taqueño", "Chañar Via", "Chañar Viejo", "Delfin Gallo", "El Aserradero", "El Chañar", "El Cochuchal", "El Espinillo", "El Mojon", "El Naranjo", "El Paraiso", "El Portezuelo", "Finca Lopez", "Guzman Estacion Fcgb", "Ingenio La Florida", "La Florida", "Los Godos", "Los Perez", "Luisiana Estacion Fcgm", "Lujan", "Macomita", "Mariño", "Monte Largo", "Moya", "Nuevo Pueblo La Florida", "Paraiso", "Pedro G Mendez", "Portezuelo", "Pozo Hondo", "Puesto De Avila", "San Jose De Macomita", "San Pedro", "Santa Teresa", "Taco", "Taco Palta", "Tambor De Tacuari", "Taquello"],
    "4119": ["Agua Colorada", "Aguas Blancas", "Alto Verde", "Antillas", "Antu Mapu", "Asna Yaco", "Benjamin Araoz", "Benjamin Paz", "Burruyacu", "Calera Aconquija", "California", "Casa Del Alto", "Casales", "Cañada Alegre", "Cañada Angosta", "Cañada De La Cruz", "Cañada De Los Negros", "Chamico", "Chilca", "Chilcas", "Chorrillos", "Churqui", "Colonia Nro 2", "Concepcion", "Cooperativa Agronomica", "Coromama", "Cossio", "Cruz De Abajo", "Descanso", "Desmonte", "El Aserradero", "El Atacal", "El Azul", "El Barco", "El Barrialito", "El Cajon", "El Castoral", "El Chorro", "El Churqui", "El Cruce", "El Establo", "El Frasquillo", "El Interes", "El Jardin", "El Matal", "El Morado", "El Naranjito", "El Obraje", "El Once", "El Porvenir", "El Puestito", "El Rodeo", "El Sinquial", "El Sunchal", "El Tajamar", "El Tipal", "El Triunfo", "El Zapallar", "Esquina", "Estancia El Diamante", "Finca Anchorena", "Finca Cristina", "Finca Piedra Blanca", "Gramilla", "Jaguel", "Juliana", "Kilometro 37", "Kilometro 80", "Kilometro 94", "La Aguita", "La Argentina", "La Banda", "La Calera", "La Cautiva", "La Cañada", "La Corzuela", "La Cruz", "La Cruz De Arriba", "La Fortuna", "La Junta", "La Loma", "La Marta", "La Pola", "La Puerta De Luca", "La Ramada", "La Ramada De Abajo", "La Ruda", "La Sala", "La Soledad", "La Toma", "La Union", "La Verde", "Laguna De Robles", "Las Chacras", "Las Pechosas", "Las Zanjas", "Loma Grande", "Loma Negra", "Los Chorrillos", "Los Eucaliptos", "Los Gonzales", "Los Gonzalez", "Los Pedraza", "Molle Chato", "Nio El Puestito", "Pacara", "Pacara Marcado", "Pacara Pintado", "Palomitas", "Paso De Las Lanzas", "Piedra Blanca", "Piedra Tendida", "Pozo Del Algarrobo", "Puerta Quemada", "Puestito De Arriba", "Puesto Cevil Con Agua", "Puesto De Uncos", "Puesto Villagra", "Punta Del Agua", "Requelme", "Rio Del Nio", "Rodeo Toro", "San Eusebio", "San Geronimo", "San Jose De San Martin", "San Lorenzo", "San Miguel", "San Patricio", "Santa Lucia", "Santa Rosa", "Santos Lugares", "Sinqueal", "Soraire", "Tala Pampa", "Tala Pozo", "Talita Pozo", "Taruca Pampa", "Tierras Blancas", "Toquello", "Totoral", "Tunalito", "Tusca Pampa", "Villa Benjamin Araoz", "Villa Burruyacu"],
    "4122": ["Alizal", "Alurralde", "Aragon", "Benjamin Paz", "Casa Del Alto", "Choromoro", "Chuscha", "Criollas", "Desmonte", "El Cedro", "El Ojo", "Gonzalo", "Huasamayo", "Huasamayo Sud", "Junta", "La Higuera", "Las Criollas", "Las Juntas", "Loma Del Medio", "Mato Yaco", "Posta Vieja", "Potro Yaco", "Puertas", "Puesto Grande", "Rio Vipos", "Rodeo", "Rodeo Del Algarrobo", "Rodeo Grande", "Salamanca", "Salinas", "San Julian Yaco", "San Miguel", "San Vicente", "Sauce Yacu", "Sepultura", "Simbolar", "Tala Yaco", "Tapia", "Ticucho", "Tuna Sola", "Vesubio", "Viaducto Del Toro", "Vipos", "Yaco", "Ñorco", "Ñoreo"],
    "4124": ["Abra El Candado", "Acequiones", "Agua El Simbo", "Agua Rosada", "Agua Salada", "Aguada De Jorge", "Alto De La Angostura", "Alto De Los Gimenez", "Alto La Totora", "Angostura", "Barborin", "Boba Yacu", "Cachi Yaco", "Campo Redondo", "Capilla", "Casas Viejas", "Cañada Del Arenal", "Cervalito", "Chulca", "Corral Viejo", "El Alpizar", "El Arenal", "El Boyero", "El Cadillal", "El Chorro", "El Junquillar", "El Milagro", "El Mistol", "El Molino", "El Mollar", "El Pelado", "El Pelado De Paranillo", "El Porvenir", "El Potrero", "El Pozo", "El Puestito", "El Quebrachal", "El Suncal", "El Talar", "El Zauzal", "Escuela 128", "Escuela 170", "Escuela 171", "Escuela 204", "Escuela 214", "Escuela 216", "Escuela 221", "Escuela 233", "Escuela 265", "Escuela 309", "Escuela 31", "Escuela 341", "Escuela 349", "Escuela 356", "Escuela 362", "Escuela 385", "Escuela 389", "Escuela 392", "Escuela 42", "Escuela 44", "Escuela 45", "Escuela 47", "Escuela Gdor Lopez", "Escuela Hernan Miraval", "Escuela J J Thames", "Escuela Juan Jose Paso", "Estanque", "Hualinchay", "India Muerta", "Kilometro 1340", "Kilometro 847", "La Aguada", "La Banda", "La Cañada", "La Dorita", "La Esquina", "La Laguna", "La Maravilla", "Las Arcas", "Las Botijas", "Las Burras", "Las Cañitas", "Las Pircas", "Las Tacanas", "Las Tipas De Colalao", "Laurel Yaco", "Leocadio Paz", "Los Bordos", "Los Puestos", "Manantiales", "Mimilto", "Miranda", "Molle Yaco", "Monte Bello", "Ovejeria", "Pantanillo", "Perucho", "Pie De La Cuesta", "Pingollar", "Portezuelo", "Pozo Suncho", "Pradera Alegre", "Puesto Varela", "Rearte", "San Carlos", "San Fernando", "San Isidro", "San Jose", "San Pedro De Colalao", "Santa Rita", "Sauzal", "Tacanas", "Taco Llano", "Taco Punco", "Taco Yaco", "Taco Yana", "Tipa Mayo", "Toco Llana", "Toro Loco", "Trancas", "Villa Gloria", "Villa Rita", "Villa Trancas", "Villa Vieja", "Yarami", "Yuchaco", "Zarate"],
    "4126": ["Alem", "Baradero", "Ceibal", "El Brete", "El Cuibal", "El Espinal", "El Jardin", "El Naranjo", "El Sunchal", "El Tala", "El Tala Est R De Los Llanos", "La Asuncion", "La Candelaria", "La Cuesta", "La Cueva", "La Maravilla", "La Poblacion", "Los Mogotes", "Miraflores", "Ovejero", "Potrerillos", "Riarte", "Ruiz De Los Llanos", "Salazar", "San Pedro De Aranda"],
    "4128": ["El Carmen", "El Ceibal", "Escuela 12", "Escuela 130", "Escuela 212", "Escuela 222", "Escuela 243", "Escuela 247", "Escuela 251", "Escuela 253", "Escuela 254", "Escuela 260", "Escuela 324", "Escuela 333", "Escuela 348", "Escuela 39", "Escuela 51", "Escuela De Manualidades", "Escuela De Manualidades Ouanta", "Escuela Dean Salcedo", "Escuela E Canton", "Escuela F N Laprida", "Escuela F Nogues", "Escuela Ignacio Colombres", "Escuela Ing Bertre", "Escuela L Blanco", "Escuela Malvinas", "Escuela Manuel Savio", "La Bolsa", "La Capilla", "Las Moreras", "Lules", "Mercedes", "Potrero De Las Tablas", "Ruta Nacional 157", "Ruta Nacional 38", "Ruta Provincial 301", "Ruta Provincial 338", "Ruta Provincial 380", "San Jose De Lules", "Santa Victoria"],
    "4129": ["Cañada", "Cañada Yerba Buena", "Colonia Maria Elena", "El Obraje", "Ingenio Lules", "La Quebrada", "La Reduccion", "Las Tablas", "Malvinas", "Obraje", "Potrero", "Punta Del Monte", "Quebrada De Lules", "San Jenaro", "San Pablo", "San Rafael"],
    "4132": ["Agua Azul", "Agua Blanca", "Arroyo De La Cruz", "Barrancas Coloradas", "Buen Retiro", "Carrichango", "Colonia Acevedo", "Colonia Bascary", "Colonia Pacara", "Colonia Santa Clara", "Colonia Santa Lucia", "Colonia Santa Rita", "El Cruce", "El Matadero", "El Tropezon", "Escuela 100", "Escuela 124", "Escuela 154", "Escuela 160", "Escuela 197", "Escuela 200", "Escuela 206", "Escuela 257", "Escuela 261", "Escuela 298", "Escuela 321", "Escuela 356", "Escuela 373", "Escuela 63", "Escuela 88", "Escuela Congresales Tucumanos", "Escuela Guillermina Moreira", "Escuela Monte Grande", "Escuela Velez Sarsfield", "Esquina Norte", "Famailla", "Finca Pereyra", "Finca San Luis", "Ingenio La Fronterita", "Invernada", "Kilometro 102", "Kilometro 108", "La Banderita", "La Fronterita", "La Pinta Y La Cuarenta", "Las Banderitas", "Las Mesadas", "Las Ratas", "Las Tres Flores", "Laureles", "Laureles Norte", "Laureles Sur", "Los Sifones", "Nueva Baviera", "Ruta Nacional 157", "Ruta Nacional 38", "Ruta Provincial 322", "Ruta Provincial 334", "Ruta Provincial 380", "San Gabriel Del Monte", "San Jose De Buena Vista", "San Luis", "Sauce Huacho", "Sauce Partido", "Teniente Berdina", "Tres Almacenes"],
    "4133": ["La Banda", "Monte Grande", "Padilla"],
    "4134": ["Acheral", "Aranilla", "Arenilla", "Kilometro 99", "San Gabriel", "San Jose De Flores"],
    "4135": ["Caspinchango", "Duraznos Blancos", "El Mollar", "El Nogalar", "Ingenio Santa Lucia", "La Ramadita", "Las Cienagas", "Los Rodriguez", "Negro Potrero", "Puesto La Ramadita", "Santa Elena", "Santa Lucia", "Santa Monica"],
    "4137": ["Abra Baya", "Abra De La Picaza", "Abra De Yareta", "Abra Del Infiernillo", "Aguada", "Alisos", "Alto Cazadera", "Alto De Los Reales", "Alto Del Huascho", "Alto Del Lampazo", "Alto Los Cardones", "Amaicha Del Valle", "Ampimpa", "Antiguo Quilmes", "Banda", "Campo Blanco", "Campo De Las Gallinas", "Campo De Los Cardones", "Campo De Los Chañares", "Campo Zauzal", "Carapunco", "Casa De Campo", "Casa De Zinc", "Casas Viejas", "Cienaguita", "Corral Blanco", "Corral Grande", "El Antigal", "El Arqueal", "El Carmen", "El Casial", "El Casialito", "El Espinal", "El Infiernillo", "El Lamedero", "El Lamparazo", "El Molle", "El Molle Viejo", "El Pabellon", "El Payanal", "El Potrerillo", "El Pozo", "El Remate", "El Toro", "Escuela 213", "Escuela 217", "Escuela 22", "Escuela 23", "Escuela 28", "Escuela 325", "Escuela 33", "Escuela 336", "Escuela 337", "Escuela 338", "Escuela 340", "Escuela 342", "Escuela 357", "Escuela 37", "Escuela 371", "Escuela 374", "Escuela 379", "Escuela 38", "Escuela 390", "Escuela 50", "Escuela Cnel Ignacio Murga", "Escuela Gob Jose Manuel Silva", "Escuela Manuela Pedraza", "Espiadero", "Esquina Del Valle", "Fuerte Quemado", "Kilometro 1025", "Kilometro 1041", "Kilometro 118", "Kilometro 52", "Kilometro 62", "La Aguadita", "La Angostura", "La Cienaga", "La Combada", "La Lagunita", "La Maravilla", "La Mesada", "La Puntilla", "La Queseria", "La Sala", "La Salamanca", "La Silla", "La Tranca", "La Viñita", "Lamparcito", "Lara", "Las Bolsas", "Las Carreras", "Loma Redonda", "Los Bateones", "Los Colorados", "Los Cordones", "Los Corpitos", "Los Cuartos", "Los Pocitos", "Los Zazos", "Macho Huañusca", "Mesada De Encima", "Molle De Abajo", "Molle Yaco", "Nogalita", "Palo Gacho", "Peña Overa", "Peña Picaza", "Piedras Blancas", "Portezuelo De Las Animas", "Portezuelo De Tomas", "Puesto De Alumbre", "Puesto De Encalillo", "Puesto De Zarzo", "Puesto Viejo", "Rearte", "Rio Blanco", "Salas", "San Carlitos", "San Francisco", "San Jose De Chasquivil", "Tafi Del Valle", "Tio Punco", "Toro Yaco", "Zurita"],
    "4139": ["Agua Amarilla La Hoyada", "Agua Amarilla Pta De Balasto", "Ampajango", "Andalhuala", "Banda", "Buey Muerto", "Campitos", "Casa De Piedra", "Caspinchango", "Cerrillos", "Cerro Colorado", "Chafiñan", "Chañar Punco", "Cienaga", "Corral Viejo", "Desrumbe", "El Arroyo", "El Balde", "El Cajon", "El Calchaqui", "El Cerrito", "El Desmonte", "El Medanito", "El Recreo", "El Tesoro", "El Trapiche", "El Zarzo", "Entre Rios", "Estancia Vieja", "Famabalastro", "Famatanca", "Iapes", "Julipao", "La Campana", "La Hoyada", "La Loma", "La Ollada", "La Quebrada", "La Soledad", "Lampasito", "Las Mojarras", "Loro Huasi", "Los Pozuelos", "Los Saltos", "Medanito", "Ovejeria", "Pajanguillo", "Palo Seco", "Paloma Yaco", "Pie Del Medano", "Punta De Balasto", "San Antonio Del Cajon", "San Jose", "San Jose Banda", "San Jose Norte", "Santa Maria", "Toroyaco", "Totorilla", "Yapes"],
    "4141": ["Agua Salada", "Anchillos", "Anjuana", "Calimonte", "Colalao Del Valle", "El Arbolar", "El Bañado", "El Carrizal", "El Paso", "Fuerte Quemado", "Julipao", "La Cieneguita", "Las Cañas", "Loma Colorada", "Los Chañares", "Macho Rastrojo", "Managua", "Pichao", "Puerta De Julipao", "Puesto De Julipao", "Quilmes", "Quisca Chica", "Quisca Grande", "Rincon De Quilmes", "Tala Paso", "Tio Franco", "Tolombon", "Totorilla", "Totoritas", "Yasyamayo"],
    "4142": ["Alto De Leiva", "Alto Verde", "Aparadero Militar Gral Muñoz", "Aragones", "Aran", "B Zorrilla", "Capitan Caceres", "Casa De Piedra", "Caspichango Viejo", "Chilcar", "Colonia 6", "Colonia Santa Catalina", "Colonia Santa Marina", "Costilla", "El Cercado", "El Churquis", "El Huaico", "El Indio", "El Naranjal", "Escuela", "Escuela 101", "Escuela 121", "Escuela 13", "Escuela 135", "Escuela 139", "Escuela 14", "Escuela 143", "Escuela 144", "Escuela 148", "Escuela 165", "Escuela 202", "Escuela 236", "Escuela 258", "Escuela 281", "Escuela 285", "Escuela 29", "Escuela 290", "Escuela 297", "Escuela 315", "Escuela 319", "Escuela 35", "Escuela 361", "Escuela 380", "Escuela 53", "Escuela Fray M Esquiu", "Escuela Ibatin", "Escuela J Castellano", "Escuela M Ariza", "Escuela Manuel Borda", "Escuela Tambor De Tacuari", "Fin Del Mundo", "Huasa Pampa", "Ibatin", "Ingenio Ñuñorco", "Isla San Jose", "Isla San Jose Sud", "Kilometro 1500", "Kilometro 93", "La Heladera", "La Quinta", "Las Pampitas", "Los Robles", "Los Sosas", "Monteros", "Monteros Viejo", "Oran", "Piedras Coloradas", "Pilco", "Playa Larga", "Pueblo Viejo", "Puesto Los Robles", "Rancho De Cascada", "Rincon Grande", "Ruta Nacional 38", "Santa Catalina", "Santo Domingo", "Soldado Maldonado", "Villa Brava", "Villa Nueva Aguilares", "Yacuchina", "Yonopongo", "Yonopongo Sud", "Zavalia"],
    "4143": ["Independencia", "Ingenio Santa Rosa", "Leon Rouges", "Los Moyes", "Los Reyes", "Los Rojos", "Santa Rosa"],
    "4144": ["Amberes", "La Florida", "Las Higuerillas", "Las Higueritas", "Quinteros 1", "Quinteros 2", "Sargento Moya", "Villa Quinteros"],
    "4145": ["Ingenio La Providencia", "Rio Seco"],
    "4146": ["Barrio Belgrano", "Barrio Textil", "Calera De Chirimayo", "Campo Solco Los Cochamolles", "Carreta Quemada", "Cochamolle", "Concepcion", "Cuesta De Chilca", "El Potrero", "Escuela 115", "Escuela 118", "Escuela 168", "Escuela 17", "Escuela 18", "Escuela 186", "Escuela 19", "Escuela 234", "Escuela 239", "Escuela 268", "Escuela 365", "Escuela 387", "Escuela 6", "Escuela 65", "Escuela 85", "Escuela Almirante Brown", "Escuela Florencio Varela", "Escuela Gregoria Lamadrid", "Escuela Manuel Domingo Bassail", "Escuela Mercedes Pacheco", "Iltico", "Ingenio La Corona", "Ischillon", "Kilometro 66", "Las Cuevas", "Las Pavas", "Lescano", "Los Vega", "Membrillo", "Muyo", "Piedra Grande", "Saladillo", "San Carlos", "San Jose", "Villa Alvear", "Villa Devoto", "Yunca Suma"],
    "4147": ["Alto Las Lechuzas", "Arcadia", "Colonia Fara", "Colonia Juan Jose Iramain", "Colonia Pedro Leon Cornet", "Gastonilla", "Las Faldas", "Los Timbres", "Villa Carolina", "Yalapa"],
    "4149": ["Alpachiri", "Belicha Huaico", "Cochuna", "Costa Del Rio Seco", "El Molino", "El Potrerillo", "El Puesto", "Gastona", "Java", "Jaya", "La Tuna", "Las Animas", "Las Leguas", "Las Lenguas Las Leguas", "Puesto De Los Valdes", "San Ramon", "San Ramon Chicligasta", "Santa Cruz", "Valenzuela"],
    "4151": ["Bajo De Los Sueldos", "Colonia Humaita Primera", "El Milagro", "El Palcara", "El Porvenir", "El Sauzal", "Finca Entre Rios", "Humaita 1", "Humaita 2", "Ingenio La Trinidad", "La Esperanza", "Las Guchas Los Guchea", "Los Arrietas", "Los Guchea", "Medinas", "Molinos", "Rosario Oeste", "Villa La Trinidad", "Yucumanita"],
    "4152": ["Aguilares", "Alto Las Flores", "Arroyo Barriento", "Colonia Marull", "Colonia Naschi", "Colonia Nueva Trinidad", "El Cebil", "Escuela 137", "Escuela 140", "Escuela 176", "Escuela 21", "Escuela 264", "Escuela 274", "Escuela 279", "Escuela 280", "Escuela 287", "Escuela 288", "Escuela 289", "Escuela 320", "Escuela 64", "Escuela 66", "Escuela 67", "Escuela Alfonsina Storni", "Escuela Carlos Pellegrini", "Escuela Domingo Garcia", "Escuela Luis Gianneo", "Huasa Rincon", "Ing Mercedes", "Kilometro 1455", "Los Agudos", "Los Callejones", "Los Ocho Cuartos", "Mercedes", "Monte Redondo", "Monte Rico", "Moras Minucas", "Multiflores", "Nasche", "Potrero De Las Cabras", "Rincon Huasa", "San Miguel", "Santa Isabel", "Santa Rosa"],
    "4153": ["Alto Verde", "Cortaderas", "Cuesta De La Chilca", "El Ceibal", "Rio Chico"],
    "4155": ["Cevil Grande", "Chavarria", "El Rodeo", "Ingenio Santa Ana", "Kilometro 55", "Las Tuscas Tuscal", "Los Lunas", "Santa Ana", "Tuscal", "Villa Clodomiro Hileret", "Villa Vieja Santa Ana"],
    "4157": ["Arroyo Mal Paso", "Cevil Solo", "El Carmen", "El Rincon", "El Tuscal", "Falda De Arcadia", "Ingenio Santa Barbara", "La Tapia", "La Tipa", "Los Agudos", "Los Cordoba", "Los Galpones", "Los Rios", "Los Rizos", "Los Sarmientos", "Mal Paso", "Maria Blanca", "Monte Bello", "Nueva Trinidad", "Posta"],
    "4158": ["Campo De Talamayo", "Casa De Piedras", "Dique Escaba", "El Batiruano", "El Churqui", "El Corralito", "El Divisadero", "El Lamedero", "El Molino", "Escaba", "Escaba De Abajo", "Escaba De Arriba", "Escuela 138", "Escuela 190", "Escuela 26", "Escuela 263", "Escuela 267", "Escuela 307", "Escuela 318", "Escuela 328", "Escuela 352", "Escuela 376", "Escuela 69", "Escuela V Generala", "Fuerte Alto", "Ingenio Marapa", "Juan Bautista Alberdi", "Kilometro 36", "Kilometro 46", "La Calera", "La Invernada", "La Puerta De Marapa", "Las Tablitas", "Los Alamitos", "Los Alisos", "Los Arroyo", "Los Guayacanes", "Marapa", "Naranjo Esquina", "Ruta Nacional 38", "Ruta Provincial 308", "Talamuyo", "Ucuchacra", "Villa Alberdi", "Villa Alberdi Estacion", "Villa Belgrano", "Yaminas", "Yanima", "Yaquilo"],
    "4159": ["Alto El Puesto", "Campo Bello", "Campo Grande", "Escobas", "Gramajos", "Graneros", "Kilometro 29", "Km 12", "La Cañada", "Los Diaz", "Los Gramajo", "Los Gramajos", "Pampa Larga", "San Luis De Las Casas Viejas", "Taco Rodeo", "Ympas", "Zapallar"],
    "4161": ["Alongo", "Campo La Cruz", "Dolavon", "Domingo Millan", "Donato Alvarez", "El Nogal", "El Polear", "Kilometro 10 Fcgb", "Los Bajos", "Los Tres Bajos", "Nueva Esquina", "Palo Blanco", "Sacrificio", "San Francisco"],
    "4162": ["Batiruana", "Boca De La Quebrada", "Cajas Viejas", "Casa Vieja", "El Colcolar", "El Duraznito", "El Jardin", "El Pila", "El Porvenir", "Escuela 125", "Escuela 159", "Escuela 188", "Escuela 24", "Escuela 244", "Escuela 25", "Escuela 282", "Escuela 294", "Escuela 355", "Escuela 363", "Escuela 73", "Escuela 89", "Escuela Joaquin V Gonzalez", "Escuela Mario Bravo", "Escuela Olegario Andrade", "Escuela Pedro Medrano", "Huacra", "Huasa Pampa Sur", "Kilometro 1402", "Kilometro 1412", "Kilometro 1438", "Kilometro 19", "La Cocha", "La Huerta", "La Salvacion", "Las Cejas", "Los Mistoles", "Los Pizarro", "Mistol", "Monte Grande", "Monte Redomon", "Monte Redondo", "Ponzacon", "Potrerillos", "Pozo Cavado", "Puesto Los Robles", "Retiro", "Ruta Nacional 38", "Ruta Nacional 64", "Ruta Provincial 334", "San Ignacio", "Sauce Seco", "Sauce Yaco", "Sauce Yacu", "Tata Yacu", "Villa Nueva"],
    "4163": ["Huasa Pampa Norte", "La Lagunilla", "Puesto Nuevo", "Romerello", "San Jose", "San Jose De La Cocha"],
    "4164": ["Bajastine", "El Bajo", "El Suncho", "La Posta", "Pueblo Nuevo", "Pueblo Viejo", "Puerta Grande", "Rumi Punco", "Suncho Punta"],
    "4166": ["Balderrama", "El Arenal", "Entre Rios", "Kilometro 1220", "Kilometro 1235", "Kilometro 1248", "Kilometro 1256", "Kilometro 5", "Manchala", "Manuel Garcia Fernandez", "Manuela Pedraza", "Puente El Manantial", "Rincon De Balderrama", "Rio Colorado", "Rio Lules", "San Felipe", "San Ramon"],
    "4168": ["Agua Blanca", "Agua Dulce", "Agua Salada", "Amaicha Del Llano", "Anegados", "Bella Vista", "Buena Vista Oeste", "Cachi Huasi", "Cachiyaco", "Camas Amontonadas", "Campana", "Campo Azul", "Campo Redondo", "Candelillal", "Carancho Pozo", "Cañada El Arenal", "Cevilarcito", "Chañar Muya", "Chañar Pozo", "Chañarito", "Colonia El Sunchal", "Colonia Sobrecasa", "El Aguilar", "El Atacat", "El Castoral", "El Ceibal", "El Moyar", "Escuela 1", "Escuela 1 Junta", "Escuela 102", "Escuela 103", "Escuela 104", "Escuela 105", "Escuela 11", "Escuela 114", "Escuela 122", "Escuela 132", "Escuela 145", "Escuela 146", "Escuela 147", "Escuela 153", "Escuela 156", "Escuela 157", "Escuela 174", "Escuela 175", "Escuela 185", "Escuela 192", "Escuela 194", "Escuela 195", "Escuela 207", "Escuela 209", "Escuela 224", "Escuela 226", "Escuela 227", "Escuela 229", "Escuela 231", "Escuela 232", "Escuela 235", "Escuela 238", "Escuela 25 De Mayo", "Escuela 27", "Escuela 272", "Escuela 273", "Escuela 293", "Escuela 323", "Escuela 354", "Escuela 364", "Escuela 370", "Escuela 52", "Escuela 77", "Escuela 78", "Escuela 79", "Escuela 80", "Escuela 81", "Escuela 82", "Escuela Alejandro Heredia", "Escuela Angel Padilla", "Escuela Batalla De Tucuman", "Escuela Cacique Manamico", "Escuela Estanislao Zeballos", "Escuela Gobernador Miguel Nogu", "Escuela Granillo", "Escuela Ignacio Bas", "Escuela La Asuncion", "Escuela M De Pueyrredon", "Escuela P De Mendoza", "Escuela Pedro Echeverry", "Escuela R Rojas", "Estancia La Princesa", "Finca Araoz", "Finca Los Llanos", "Finca Tinta", "Finca Tulio", "Ingenio Bella Vista", "Kilometro 1231", "Kilometro 1240", "Kilometro 1244", "Kilometro 1260", "Kilometro 35", "La Donosa", "La Isla", "La Princesa", "Las Barrancas", "Las Cuatro Esquinas", "Las Juntas", "Las Pirvas", "Los Agudos", "Los Decima", "Los Pocitos", "Los Valdes", "Maria Elena", "Molle Pozo", "Paja Blanca", "Planta De Bombeo De Ypf", "Potrero Grande", "Puertas Grandes", "Ruta Nacional 157", "Ruta Nacional 9", "Ruta Provincial 302", "Ruta Provincial 306", "Ruta Provincial 320", "Ruta Provincial 323", "Ruta Provincial 366", "Ruta Provincial 374", "Ruta Provincial 375", "Santa Clara Sud", "Talilar", "Vizcachera", "Yangallo"],
    "4172": ["Buena Vista", "Campo Volante", "Castillas", "Chilcar", "El Chilcar", "El Jardin", "El Polear", "Escuela 116", "Escuela 126", "Escuela 129", "Escuela 131", "Escuela 133", "Escuela 134", "Escuela 15", "Escuela 16", "Escuela 162", "Escuela 183", "Escuela 193", "Escuela 198", "Escuela 199", "Escuela 20", "Escuela 201", "Escuela 203", "Escuela 237", "Escuela 241", "Escuela 266", "Escuela 269", "Escuela 286", "Escuela 297", "Escuela 317", "Escuela 322", "Escuela 332", "Escuela 345", "Escuela 36", "Escuela 391", "Escuela 41", "Escuela 43", "Escuela 55", "Escuela 68", "Escuela 84", "Escuela 93", "Escuela 94", "Escuela 95", "Escuela 97", "Escuela 99", "Escuela Agueda De Posse", "Escuela Araoz Alfaro", "Escuela Cnel Geronimo Helguera", "Escuela Cornelio Saavedra", "Escuela Gomez", "Escuela Lopez Mañar", "Escuela Lopez Y Planes", "Escuela Lugones", "Escuela Matienzo", "Guemes", "Kilometro 1213", "La Rinconada", "Las Cejas", "Los Diaz", "Macio", "Mascio Pilco", "Mascio Sur", "Mothe", "Pampa Mayo", "Pampa Mayo Noroeste", "San Pedro Martir", "Simoca", "Yerba Buena", "Zanjon Mascio"],
    "4174": ["Ampata", "Ampatilla", "Arocas", "Arroyo Atahona", "Atahona", "Balderrama Sur", "Buena Yerba", "Cejas De Aroca", "Ciudacita", "Consimo", "Corona", "El Durazno", "El Mistolar", "El Mollar", "El Rodeo", "El Tobar", "Ensenada", "Entre Rios", "Estancia Suri Yaco", "Ichipuca", "Ingas", "Kilometro 1185", "Kilometro 1194", "Kilometro 1207", "La Florida", "La Grama", "La Loma", "La Planta", "La Reina", "La Tuna", "Lagarte", "Lazarte", "Loma Grande", "Los Agueros", "Los Aguirre", "Los Amaya", "Los Lescanos", "Los Mendozas", "Los Perez", "Los Trejos", "Lovar", "Maria Luisa", "Monteagudo", "Niogasta", "Palomas", "Palominos", "Planta Compresora Ypf", "Poliar", "Rescate", "Riegasta", "Rio Seco Kilometro 1207", "Rodeo Grande", "San Antonio", "San Antonio De Padua", "San Carlos", "Sandovales", "Sud De Lazarte", "Sud De Sandovales", "Sud De Trejos", "Suriyaco", "Villa Chicligasta", "Yacuchiri"],
    "4176": ["Acos", "Alto Del Puesto", "Alto Verde", "Amimpa", "Amunpa", "Animas", "Arboles Grandes", "Arboles Verdes", "Barrancas", "Barranqueras", "Barrosa", "Campo Alegre", "Casa Santa", "Cañadas", "Chañar", "Dos Pozos", "El Arbolito", "El Barranquero", "El Bañado", "El Campo", "El Mistol", "El Nial", "El Palancho", "El Rodeo", "El Sauzal", "El Vallecito", "Embalse Rio Hondo", "Escuela 123", "Escuela 151", "Escuela 158", "Escuela 172", "Escuela 178", "Escuela 179", "Escuela 180", "Escuela 182", "Escuela 184", "Escuela 187", "Escuela 189", "Escuela 191", "Escuela 245", "Escuela 302", "Escuela 303", "Escuela 306", "Escuela 316", "Escuela 343", "Escuela 346", "Escuela 72", "Escuela 74", "Escuela 75", "Escuela 90", "Escuela 92", "Escuela 96", "Escuela Cap Diego Fco Pereyra", "Escuela Cristobal Colon", "Esquina", "Kilometro 12", "La Brama", "La Concepcion", "La Costa Palampa", "La Esperanza", "La Estrella", "La Loma", "La Soledad", "Laguna Larga", "Lamadrid", "Las Animas", "Las Lomitas", "Las Parritas", "Las Zanjitas", "Los Cercos", "Los Panchillos", "Los Paraisos", "Los Ruiz", "Los Saracho", "Los Sauces", "Los Soraire", "Los Sotelo", "Palma Larga", "Palo Seco", "Palos Quemados", "Pampa Muyo", "Pampa Rosa", "Paso De Los Nievas", "Paso Grande", "Pozo Del Arbolito", "Pozo El Quebracho", "Pozo Verde", "Puesto Belen", "Puesto De Galvanes", "Puesto Los Barraza", "Puesto Los Galvez", "Rio Hondito", "Rumi Cocha", "Ruta Nacional 157", "Ruta Provincial 333", "Ruta Provincial 334", "San Antonio De Quisca", "Sol De Mayo", "Tala Caida", "Tala Sacha", "Villa Pujio"],
    "4178": ["Abra Rica", "Aguadita", "Alabama Nueva", "Alderetes", "Alto Las Lechuzas", "Andres Ferreyra", "Araoz", "Arbol Solo", "Bello Horizonte", "Blanco Pozo", "Boca Del Tigre", "Bracho Viejo", "Cachi Yaco", "Campo El Luisito", "Campo El Mollar", "Campo La Flor", "Casa Rosada", "Cañada De Viclos", "Cejas De Beñachillos", "Cerco Cuatro", "Cevil Pozo", "Cohigac", "Colonia 4", "Colonia 4 De Colombres", "Colonia El Puesto", "Colonia El Tarco", "Colonia La Bonaria", "Colonia La Ortiz", "Colonia La Roca", "Colonia Mercedes", "Colonia Mistol", "Colonia Monteros", "Colonia San Luis", "Colonia San Miguel", "Colonia Santa Rita", "Cruz Alta", "Cruz Del Norte Estacion Fcgm", "El Bagual", "El Cardenal", "El Carmen Puente Alto", "El Cevilar", "El Corte", "El Cruce", "El Cuadro", "El Guayacan", "El Melon", "El Mojon", "El Pacara", "El Pajal", "El Puerto", "El Puesto", "El Quimil", "El Talar", "Empalme Agua Dulce", "Escuela 106", "Escuela 108", "Escuela 109", "Escuela 110", "Escuela 111", "Escuela 12 De Octubre", "Escuela 141", "Escuela 142", "Escuela 220", "Escuela 225", "Escuela 228", "Escuela 270", "Escuela 277", "Escuela 283", "Escuela 284", "Escuela 291", "Escuela 3", "Escuela 308", "Escuela 312", "Escuela 327", "Escuela 329", "Escuela 330", "Escuela 334", "Escuela 335", "Escuela 56", "Escuela 76", "Escuela 86", "Escuela 9", "Escuela Almafuerte", "Escuela Arenales", "Escuela Blas Parera", "Escuela Coronel Roca", "Escuela E De Lucas", "Escuela G De Vega", "Escuela Guido Spano", "Escuela Ingeniero Bascary", "Escuela Jose Colombres", "Escuela Jose Posse", "Escuela Juana Manso", "Escuela N Vergara", "Escuela R J Freyre", "Escuela Santiago Gallo", "Escuela Sargento Cabral", "Escuela W Posse", "Estacion Araoz", "Finca El Ceibo", "Finca Leila", "Guanaco Muerto", "Kilometro 1270", "Kilometro 34", "Kilometro 771", "La Cantina", "La Cornelia", "La Ercilia", "La Favorita", "La Flor", "La Guillermina", "La Media Agua", "La Tala", "Las Cantinas", "Las Palomitas", "Las Piedritas", "Las Talas", "Los Angeles", "Los Gutierrez", "Los Pereyra", "Los Villagra", "Luis Pasteur", "Marta", "Mujer Muerta", "Overo Pozo", "Palmas Redondas", "Pereyra Norte", "Pereyra Sur", "Porvenir", "Potrero De Los Alamos", "Ranchillos", "Ranchillos Viejos", "Rincon De Las Tacanas", "Ruta Nacional 9", "Ruta Provincial 302", "Ruta Provincial 303", "Ruta Provincial 304", "Ruta Provincial 306", "Ruta Provincial 319", "Ruta Provincial 335", "San Ignacio", "San Miguel", "San Miguelito", "San Vicente", "Santa Rita", "Sinquial", "Superintendente Ledesma", "Tacanas", "Tres Pozos", "Viclos", "Villa Recaste"],
    "4182": ["Campo La Flor Los Ralos", "Colmena Lolita", "Colonia Lolita Norte", "Finca Mayo", "Ingenio Los Ralos", "Lolita", "Lolita Nueva", "Los Ralos", "Mayo", "San Pereyra", "Villa Tercera"],
    "4184": ["Animas", "Arbolitos", "Añil", "Bajo Hondo", "Bella Vista", "Blanco Pozo", "Boca Del Tigre", "Bustamante", "Ceja Pozo", "Charco Viejo", "Don Bartolo", "Ea La Verde", "El Cambiado", "El Carbon", "El Churqui", "El Molar", "El Parana", "El Prado", "El Rincon", "Gaspar Suarez", "Humaita", "Huturungo", "Ingenio Cruz Alta", "Isca Yacu", "Isca Yacu Semaul", "Kilometro 781", "Kilometro 784", "Kilometro 794", "La Esperanza", "Las Cejas", "Lopez Dominguez", "Los Ralos", "Poleo Pozo", "Pozo Del Alto", "Pozo Hondo", "Pozo Lerdo", "Pozo Lindo", "Puerta Grande", "Retiro", "San Javier", "San Pedro", "Suncho Pujio", "Superintendente Ledesma", "Tacanas", "Tenene", "Tres Flores", "Tusca Pozo", "Uclar", "Utrunjos", "Viteaca"],
    "4186": ["Cañete", "El Palomar", "El Rincon", "La Libertad", "Lapachitos", "Las Cejas", "Los Godoy", "Los Hardoy", "Los Santillan", "Pozo Lapacho", "San Agustin", "San Carlos", "San Jose", "Santa Luisa", "Santillan", "Tuscal Redondo", "Virginia"],
    "4187": ["Anta Chica", "Arenales", "Bobadal", "Ceja Pozo", "El Arbolito", "El Arenal", "El Bachi", "El Bobadal", "El Cambiado", "El Durazno", "El Gramillar", "El Palomar", "El Puesto Del Medio", "Ensenada", "Escuela 112", "Escuela 118", "Escuela 149", "Escuela 150", "Escuela 152", "Escuela 166", "Escuela 167", "Escuela 173", "Escuela 177", "Escuela 205", "Escuela 208", "Escuela 211", "Escuela 242", "Escuela 246", "Escuela 250", "Escuela 262", "Escuela 275", "Escuela 276", "Escuela 278", "Escuela 292", "Escuela 30", "Escuela 310", "Escuela 313", "Escuela 314", "Escuela 326", "Escuela 331", "Escuela 339", "Escuela 34", "Escuela 344", "Escuela 347", "Escuela 353", "Escuela 366", "Escuela 368", "Escuela 369", "Escuela 375", "Escuela 386", "Escuela 4", "Escuela 5", "Escuela 57", "Escuela 60", "Escuela 61", "Escuela 62", "Escuela 7", "Escuela 83", "Escuela 91", "Escuela Adolfo Alsina", "Escuela Alberto Soldati", "Escuela Alvarez Condarco", "Escuela Campamento El Plumeril", "Escuela Cap Candelaria", "Escuela Caupolican Molina", "Escuela Diego De Villafañe", "Escuela Leo Huasi", "Escuela Manuel Cossio", "Escuela Mariano Salas", "Escuela Pedro Araoz", "Escuela Puestito De Arriba", "Escuela Salvador Alonso", "Garmendia", "Gobernador Piedrabuena", "Ingenio Esperanza", "Isla Mota", "La Costosa", "La Esperanza", "La Luna", "La Maravilla", "La Melada", "Las Abras", "Las Chacras", "Las Puertas", "Lujan", "Monte Cristo", "Monte Potrero", "Montesino", "Paja Colorada", "Paso De La Patria", "Piedra Buena", "Puerta Alegre", "Puesto Del Medio", "Rosario", "San Arturo", "San Federico", "San Felix", "San Pedro", "Santo Domingo", "Sesteadero", "Tinajeros", "Traslado", "Urizar", "Uturuno", "Villa Desierto De Luz", "Villa El Bache", "Villa El Retiro", "Villa La Soledad", "Villa La Tuna", "Villa Maria", "Villa Mercedes", "Villa Monte Cristo", "Villa San Antonio", "Villa Sta Rosa De Nva Trinidad"],
    "4189": ["Agua Azul", "Campo Amarillo", "Campo Grande", "Copo Viejo", "El Cajon", "Guanacuyoj", "La Aloja", "La Blanca", "La Juliana", "La Tala", "Las Delicias", "Las Lajas", "Las Lomas", "Libertad", "Los Cerros", "Los Molles", "Los Moyas", "Pampa Pozo", "Pozo Betbeder", "Rapelli", "Santa Maria De Las Chacras", "Simbol Pozo", "Simbolar", "Taco Punco", "Tres Varones", "Villa Mercedes", "Yuchancito"],
    "4190": ["Aguas Calientes", "Bajada", "Barbayasco", "Baños Termales", "Cerro Negro", "Cosme", "Duraznito", "El Portezuelo", "La Banda", "La Matilde", "Las Piedritas", "Los Pocitos", "Ojo De Agua", "Ovando", "Palomar", "Potrerillo", "Rosario De La Frontera", "Rosario Funca", "San Esteban", "San Vicente", "Santa Teresa", "Viaducto El Muñal", "Villa Aurelia"],
    "4191": ["El Naranjo", "San Pedro De Los Corrales", "Vaqueria"],
    "4193": ["Almirante Brown", "Antilla", "Bajada Blanca", "Balboa", "Bella Vista", "Cabeza De Anta", "Cañada De La Junta", "Cañadon De Las Juntas", "Cerro Colorado", "Cerro Negro", "Chañar Aguada", "Colgadas", "Condor", "Copo Quile", "El Bordo", "El Ceibal", "El Condor", "El Ojo", "El Potrero", "La Cienaga", "La Cruz", "La Firmeza", "La Pajita", "Las Catitas", "Las Mercedes", "Las Saladas", "Las Tunillas", "Los Baños", "Los Rosales", "Madariaga", "Morenillo", "Pozo Blanco", "Puente De Plata", "Recreo", "Rio Urueña", "San Agustin", "San Juan", "San Lorenzo", "San Luis", "San Pedro", "San Roque", "Santa Catalina", "Santa Maria", "Suri Micuna", "Tala Yaco", "Villa Corta", "Vizcacheral"],
    "4195": ["7 De Abril", "Cortaderas", "El Remate", "La Florida", "Las Colas", "Las Mojarritas", "Los Canteros", "Monte Potrero", "Monte Quemado", "Potrero", "Pozo Grande", "Pozo Largo", "Quebracho Coto", "Quemadito", "Suriyacu", "Tala Bajada"],
    "4197": ["7 De Abril", "Agua Amarga", "Ahi Veremos", "Algarrobal Viejo", "Bagual Muerto", "Belgrano", "Brandan", "Buen Lugar", "Chañar Pozo", "Corral Quemado", "El Balde", "El Baldecito", "El Diablo", "El Florido", "El Gramillar", "El Mojon", "El Potrero", "El Quemado", "El Real", "El Rosario", "El Saladillo", "El Sauce", "Ensenada", "Hahuancuyos", "Isla Mota", "Junalito", "Kilometro 645", "Kilometro 651", "La Aguada", "La Codicia", "La Florida", "La Fragua", "La Melada", "La Mesada", "Las Quebradas", "Loma Grande", "Lomas Blancas", "Maravilla", "Masumpa", "Media Luna", "Mojon", "Molleoj", "Nueva Esperanza", "Peludo Warcuna", "Piedra Buena", "Puesto Del Medio", "Puesto Del Simbol", "Puesto Nuevo", "Quebrada Esquina", "San Cristobal", "San Gregorio", "San Isidro", "San Nicolas", "Sansioj", "Santa Cruz", "Santa Felisa", "Santa Rosa", "Señora Pujio", "Siete Arboles", "Simbol Huasi", "Taco Bajada", "Tres Bajos", "Tres Quebrachos"],
    "4198": ["Arenal", "Bajada De Gavi", "Bajada Grande", "Camara", "Diamante", "El Corral Viejo", "El Ojito", "El Puestito", "El Quemado", "El Tandil", "Federacion", "Horcones", "La Hoyada", "La Palata", "La Plata", "Las Mojarras", "Las Ventanas", "Los Churquis", "Los Zanjones", "Ovejeria", "Paso Verde", "Pozo Verde", "Pozos Largos", "San Felipe", "San Lorenzo Horcones", "Santa Rosa", "Tamas Cortadas"],
    "4200": ["Barrio Villa Cohesa", "Contreras Establecimiento", "El Puestito", "El Vinalar", "Mercedes", "Puesto Del Medio", "Santiago Del Estero", "Tala Pozo", "Upianita", "Villa Constantina", "Villa Grimanesa"],
    "4201": ["Abrita Chica", "Abrita Grande", "Anchanga", "Ancocha", "Aragones", "Arbol Solo", "Brea Puñuna", "Buena Vista", "Cancinos", "Candelaria", "Caneinos", "Cardozos", "Catorce Quebrachos", "Cañada Del Medio", "Chanchillos", "Chauchillas", "Chilcas La Loma", "Chilquita I", "Chuiqui", "Coropampa", "Dique Los Quiroga", "El Carmen", "El Dean", "El Fraile", "El Peral", "Hoyo Con Agua", "Hoyon", "Huachana", "Isla De Aragones", "Kenti Taco", "La Darsena", "La Esquina", "La Florida", "La Grama", "La Perlita", "Leiva", "Lescano", "Lomitas", "Los Nuñez", "Los Quiroga", "Manogasta", "Mirandas", "Monte Cristo", "Morales", "Naranjito", "Negra Muerta", "Ovejeros", "Pocitos", "Pozo Cercado", "Pozo Grande", "Puente Del Salado", "Puesto De Diaz", "Puesto Del Medio", "Ramaditas", "Rodeo De Soria", "Rodeo De Valdez", "San Antonio", "San Antonio De Los Caceres", "San Carlos", "San Dionisio", "San Isidro", "San Martin", "Santa Maria", "Sauzal", "Simbol Pozo", "Sol De Mayo", "Sumamao", "Tipiro", "Toro Human", "Villa Jimenez"],
    "4203": ["Alta Gracia", "Alto Bello", "Arroyo Tala", "Belgrano", "Cabra", "Cañada", "Cerrillos", "Chañar Pozo", "Conzo", "Cortadera", "Cuichicaña", "El Rincon", "El Tala", "Escuela 1050", "Escuela 20", "Escuela 665", "Escuela 708", "Famatina", "Farol", "Favorina", "Guampacha", "Guardia Del Norte", "Ichagon", "La Calera", "La Ensenada", "La Punta", "Laguna", "Las Chacras", "Las Flores", "Lujan", "Maquijata", "Maravilla", "Mate Pampa", "Palma Flor", "Pampa Muyoj", "Parana", "Piedritas", "Pozo Cercado", "Puerta Chiquita", "Puerta Del Cielo", "Puesto Nuevo", "Quebrachos", "Remes", "Rodeo", "San Jose De Flores", "San Justo", "San Lorenzo", "Santa Catalina", "Santa Rosa", "Santos Lugares", "Sayaco", "Sinchi Caña", "Sol De Mayo", "Tronco Juras", "Tunas Punco", "Villa Elvira", "Villa La Punta", "Vizcacheral", "Yeso Alto"],
    "4205": ["25 De Mayo De Barnegas", "Arbol Solo", "Bella Vista", "Beltran Loreto", "Campo De Amor", "Chaves", "El Nerio", "El Señuelo", "Envidia", "Kilometro 55", "La Blanca", "La Cortadera", "La Laura", "La Melada", "La Polvareda", "La Providencia", "La Viuda", "Laprida", "Las Dos Flores", "Los Cerrillos", "Los Ralos", "Pampa Pozo", "Porongal", "San Agustin", "San Benito", "San Ignacio", "San Luis", "San Manuel", "San Pastor", "San Ramon", "San Roque", "Santa Ana", "Santa Rosa De Coronel", "Shishi Pozo", "Tres Bajadas"],
    "4206": ["Abrita", "Arraga", "Buey Rodeo", "Campo Alegre", "Campo Grande", "Campo Nuevo", "Chañar Pujio", "Costa Rica", "Cruz Pozo", "El Marne", "El Mojon", "Establecimiento 14 De Setiembr", "Ezcurra", "Ingeniero Ezcurra", "Kilometro 117", "Kilometro 135", "Kilometro 153", "La Abrita", "La Esperanza", "La Higuera", "La Porteña", "La Sarita", "La Vuelta", "Las Flores", "Los Quiroga", "Maco", "Maco Yanda", "Maguito", "Maquita", "Maquitis", "Maquito", "Monte Rico", "Nanda", "Naquito", "Nueva Francia", "Pueblo Nuevo", "Puestito De San Antonio", "Quebracho Herrado", "San Agustin", "San Andres", "San Benito", "San Ignacio", "San Isidro", "San Pedro", "San Sebastian", "San Vicente", "Santa Maria", "Santa Rosa", "Santa Rosa Arraga", "Santo Domingo", "Sauce Solo", "Silipica", "Simbol", "Trozo Pozo", "Upianita", "Villa De La Barranca", "Villa Zanjon", "Vuelta De La Barranca", "Yanda"],
    "4208": ["Albardon Chuña", "Ayuncha", "Bajadita", "Burra Huañuna", "Cañada Rica", "Chuña Albardon", "Codo", "Collera Hurcuna", "Diente Del Arado", "Dormida", "El Mulato", "El Pinto", "El Remanso", "Jumi Pozo", "Kilometro 112", "Kilometro 118", "Kilometro 120", "Kilometro 88", "La Dormida", "La Noria", "La Ramadita", "La Revancha", "Lomitas", "Loreto", "Los Angeles", "Morampa", "Paaj Muyo", "Pozo Ciego", "Puesto De Juanes", "Ramadita", "Rio Nambi", "San Gregorio", "San Isidro", "San Jeronimo", "San Jose", "San Juan", "San Miguel", "San Pablo", "Sandia Huajchu", "Santa Barbara", "Santa Barbara Ferreira", "Santa Isabel", "Santa Maria", "Sauce Solo", "Sol De Mayo", "Tacañitas", "Taco Pozo", "Tala Atun", "Taquetuyoj", "Tontola", "Toro Charquina", "Totora Pampa", "Totoras", "Tusca Pozo", "Tuscayoj", "Yacuchiri", "Yalan", "Yolohuasi", "Yulu Huasi"],
    "4212": ["Guanaco Sombriana", "Isla Verde", "Monte Redondo", "San Vicente", "Tusca Pozo San Vicente"],
    "4220": ["Aguada", "Alta Gracia", "Anjuli", "Bahoma", "Buena Vista", "Cañada De La Costa", "Cañada Honda", "Chañar Pozo De Abajo", "Colonia Tinco", "El Manantial", "El Rincon", "Escuela 1080", "Escuela 109", "Escuela 57", "Espinal", "Estancia Vieja", "Galeano", "Huascho Patilla", "Isla De Los Castillos", "La Aguada", "La Fortuna", "Las Orellanas", "Las Palmeras", "Las Tigreras", "Loro Huasi", "Los Castillos", "Los Fierros", "Los Ovejeros", "Los Quebrachos", "Los Robles", "Manantiales", "Mansupa", "Posta Sanitaria Pocitos", "San Pablo", "Tacamampa", "Tala", "Termas De Rio Hondo", "Tunales", "Villa Balnearia"],
    "4221": ["La Donosa", "Las Cejas", "Los Decimas", "Perez De Zurita", "Yuto Yaca", "Yutu Yaco"],
    "4223": ["Amapola", "Bajo Verde", "Cañada Tala Pozo", "El Alambrado", "El Puesto", "El Retiro", "Loma Del Medio", "Palma Redonda", "Puesto Del Retiro", "Tala Pozo", "Taquello", "Vinara"],
    "4225": ["Abra De La Cruz", "Abras Del Martirizado", "Alpa Puca", "Amicha", "Antilo", "Barrialito", "Bauman", "Bebidas", "Bejan", "Chañar Pocito", "Chañar Pozo", "Doña Luisa", "El Barrial", "El Churqui", "El Quebrachal", "La Soledad", "Mistol Muyoj", "Palma Pozo", "Patillo", "Pozo Huascho", "Puesto De Vieyra", "Punta Pozo", "Quebrachos", "Quera", "San Carlos", "San Cosme", "Sol De Mayo", "Villa Rio Hondo"],
    "4230": ["Bajo Hondo", "Barrio Jardin", "Bella Vista", "Beltran Loreto", "Brea Chimpana", "Buenos Aires", "Campo De Amor", "Cerrillos De San Isidro", "Chañar Laguna", "Corralitos", "El Escondido", "El Milagro", "El Recreo", "El Rodeo", "El Rosario", "El Vallecito", "Envidia", "Escuela 879", "Frias", "Guatana", "Inti Huasi", "Jumeal O Jumial", "Kilometro 1073", "Kilometro 3", "La Esperanza", "La Esquina", "La Laguna", "La Laura", "Las Dos Flores", "Las Flores", "Las Palomitas", "Las Tejas", "Las Trincheras", "Los Ralos", "Lujan", "Monte Redondo", "Monteagudo", "Palo Lindo", "Palo Parado", "Pampa Pozo", "Porongal", "Pozancones", "Pozo De La Puerta", "Puerta De Las Piedras", "Remansito", "San Carlos", "San Ignacio", "San Luis", "San Patricio", "Santa Rosa", "Serrano Muerto", "Suncho Pozo", "Suncho Pujio", "Taco Quinka", "Tapso", "Tres Bajadas", "Troncos Quemados", "Villa Adela", "Villa Coinor"],
    "4231": ["25 De Mayo", "25 De Mayo Sud", "Albigasta", "Ancastillo", "Anjuli", "Candelaria", "Cerro Rico", "El Barrialito", "El Centenario", "El Salvador", "Garzon", "La Renovacion", "Las Iguanas", "Las Palmitas", "Las Tejas", "Los Cordobeses", "Palo Parado", "Puesto De Los Morales"],
    "4233": ["Abras Del Medio", "Alto Alegre", "Ancajan", "Canario", "Choya", "Divisadero", "El Bajo", "El Rajo", "El Tacial", "El Veinticinco", "Esperanza", "Kilometro 10", "Kilometro 18", "La Guardia", "La Represa", "Lomitas", "Mojoncito", "Oncajan", "Pocito De La Loma", "Pozo Del Campo", "Pueda Ser", "Puesto", "Rodeito", "San Antonio De Las Flores", "San Delfin", "San Juan", "San Juancito", "San Miguel", "San Pedro", "San Romano", "Santa Lucia", "Villa Rivadavia"],
    "4234": ["Achalco", "Ayapaso", "Chañar Laguna", "El Quillin", "El Simbol", "Ichipuca", "Kilometro 1093", "Kilometro 1098", "Kilometro 1121", "La Calera", "La Quebrada", "Las Flores", "Las Lomitas", "Lavalle", "Los Morteros", "Mangrullo", "Pozo Grande", "Rumi Esquina", "San Antonio", "San Martin", "Tapso", "Tonzu"],
    "4235": ["Albigasta", "Barranquitas", "Bebida", "Bella Vista", "El Alto", "El Quebrachito", "El Rodeito", "El Rosario", "El Vallecito", "Estanzuela", "Guayamba", "Iloga", "Inacillo", "Infanzon", "La Calera Del Sauce", "La Estancia", "La Estanzuela", "La Huerta", "Las Cañas", "Las Justas", "Las Lomitas", "Las Pampas", "Las Tapias", "Las Trancas", "Las Trillas", "Lindero", "Los Alamos", "Los Corrales", "Los Nogales", "Los Ortices", "Los Pedrazas", "Mina Dal", "Nogalito", "Orellano", "Oyola", "Pueblito", "Puesto Los Gomez", "Rio De Avila", "Rio De La Plata", "San Jeronimo", "San Vicente", "Sauce Huacho", "Sucuma", "Suruipiana", "Talega", "Tintigasta", "Vilisman"],
    "4237": ["Balde Pozo", "Chillimo", "Cortaderas", "El Abra", "Florida", "La Abra", "Las Peñas", "Mendoza", "Puesto De La Viuda", "San Jose", "Tres Cerros", "Zorro Huarcuna"],
    "4238": ["9 De Julio", "Abra De Quimil", "Agujereado", "Ahi Veremos", "Aibalito", "Campo Verde", "Codillo", "El Cadillo", "El Carmen", "El Porvenir", "El Puestito", "El Simbolar", "Iliages", "Jumial", "La Chilca", "Las Juntas", "Las Maravillas", "Las Talitas", "Loma De Yeso", "Los Cobres", "Los Correas", "Medio Mundo", "Moron", "Palmitas", "Pampa Pozo", "Pozancon", "Pozo Cabado", "Providencia", "Puesto De Diaz", "Puesto Del Medio", "San Antonio", "San Jose", "San Juan", "San Lorenzo", "San Pedro De Guasayan", "San Ramon", "Tableado", "Tala Pozo", "Tibilar", "Villa Guasayan", "Villares"],
    "4242": ["25 De Mayo", "9 De Julio", "Beltran", "Chalchacito", "Chañaritos", "Chilca", "Coco", "Durazno", "El Paraiso", "El Puestito", "El Quebrachito", "El Sesteadero", "El Tostado", "Encrucijada", "Iguana", "La Cañada", "La Chilca", "La Iguana", "La Zanja", "Lachico", "Las Brisas", "Las Talitas", "Los Molles", "Molles", "Montuoso", "Moron", "Paez", "Pampa Pozo", "Pozo Hondo", "Puesto 9 De Julio", "Puesto Los Avilas", "Puesto Los Perez", "Quebrachito", "Ramaditas", "Ramos", "Rumi Yura", "Sala Vieja", "San German", "San Juancito", "San Miguel", "Santa Barbara", "Santa Rosa", "Sauce Gaucho", "Sesteadero", "Simbol", "Taco Ralo", "Talitas", "Toro Muerto", "Tostado", "Viltran", "Yapachin", "Yumillura", "Zapallar"],
    "4300": ["Ahi Veremos", "Barrio Este", "Colonia Maria Luisa", "Cuyoj", "El Alambrado", "El Barrial", "El Bosque", "El Carmen", "El Cruce Kilometro 659", "El Paraiso", "El Rosario", "Jumialito", "Kilometro 1033", "Kilometro 659", "Kilometro 661", "Kilometro 665", "La Banda", "La Capilla", "La Granja", "La Isla", "Las Hermanas", "Las Salinas", "Las Zanjas", "Los Naranjos", "Nueva Antaje", "Nueva Trinidad", "Nuevo Libano", "Paraje La Bajada", "Rincon", "Rubia Moreno", "San Carlos", "San Juan", "Santos Lugares", "Tramo 20", "Tramo 26", "Valdivia", "Villa Union"],
    "4301": ["Aguas Coloradas", "Areas", "Babilonia", "Bajo Grande", "Bandera Bajada", "Belgrano", "Buen Lugar", "Callejon Bajada", "Campo Grande", "Canteros", "Cardon Esquina", "Casa Verde", "Caspi Corral", "Cañada Escobar", "Cejas", "Chañar Bajada", "Chañar Esquina", "Chile", "Churqui", "Churqui Esquina", "Cuquenos", "Dique Chico", "Dique Figueroa", "El Barrial", "El Bañadero", "El Cerrito", "El Chañar", "El Milagro", "El Olivar", "El Pirucho", "El Porvenir", "El Quemado", "Esteco", "Esteros", "Fortuna", "Guarcan", "Hoyo Cerco", "Huachana", "Huñajcito", "Jumi Viejo", "La Florida", "La Guardia", "La Higuera", "La Loma", "La Lomada", "La Manga", "La Paciencia", "La Paloma", "La Paz", "La Rivera", "Las Palmitas", "Los Arias", "Los Pereyra", "Majancito", "Manga Bajada", "Monte Redondo", "Montevideo", "Moradito", "Naranjito", "Norqueoj", "Nueva Granada", "Nuevo Simbolar", "Palizas", "Palma Pozo", "Palmitas De Jerez", "Porongos", "Potrero Bajada", "Pozo Del Castaño", "Pozo Del Simbol", "Pozo Grande", "Pozo Limpio", "Pozo Verde", "Quebrachal", "Quebracho Yacu", "Ranchitos", "Reparo", "Retiro", "Rincon", "Rio Muerto", "Saladillo", "San Gregorio", "San Jorge", "San Jose", "San Jose Del Boqueron", "San Luis", "San Pablo", "San Ramon", "San Roque", "San Vicente", "Santa Cruz", "Santa Rita", "Santo Domingo", "Santo Domingo Copo", "Santos Lugares", "Sauce Esquina", "Sepultura", "Soria Bajada", "Tablada Del Boqueron", "Tacañitas", "Taco Pozo", "Tajamar", "Tarpuna", "Totorillas", "Tramo 16", "Tusca Bajada", "Villa Hipolita", "Villa Huañuna", "Villa Nueva", "Villa Palmar", "Villa Robles", "Vinal Viejo", "Zanja"],
    "4302": ["Acosta", "Alto Pozo", "Antaje", "Ardiles", "Ardiles De La Costa", "Banegas", "Chaupi Pozo", "Chañar Pujio", "Colonias", "Corvalanes", "El Aibe", "El Cebollin", "El Cercado", "El Ojo De Agua", "El Puente", "Guaycuru", "Kiska Hurmana", "La Cañada", "La Colonia", "La Cuarteada", "La Falda", "La Germania", "La Vuelta", "Las Colonias", "Loma Negra", "Los Alderetes", "Los Diaz", "Los Doce Quebrachos", "Los Gallardos", "Los Guerreros", "Los Herreros", "Los Puestos", "Los Puntos", "Los Romanos", "Media Flor", "Palermo", "Quishca", "Quita Punco", "San Andres", "San Lorenzo", "San Martin", "San Ramon", "San Roque", "Santa Cruz", "Santa Rita", "Santa Rosa", "Sarmiento", "Sinquen Punco", "Suri Pozo", "Taperas", "Turena", "Vilmer"],
    "4304": ["Algarrobales", "Chañar Pozo", "Gramilla", "Isla De Los Sotelos", "La Fortuna", "Las Orellanas", "Las Tigreras", "Los Quebrachos", "Los Robles", "Saladillo", "Sotelillos", "Sotelos", "Tunales"],
    "4306": ["Boca Del Tigre", "Cachico", "Cashico", "Casilla Del Medio", "Charco Viejo", "El Añil", "El Charco", "El Guayacan", "Las Abras", "Poleo Pozo", "Pozuelos", "Toro Pozo", "Tres Cruces"],
    "4308": ["Bandera Bajada", "Beltran", "Blanca", "Buey Muerto", "Casilla Del Medio", "El Crece", "El Saladillo", "Higuera Chaqui", "Janta", "La Barrosa", "La Florida", "La Invernada", "Las Colinas", "Mirca", "Morcillo", "Porongos", "Pumitayoj", "San Guillermo", "San Ignacio", "San Pascual", "San Salvador", "Santa Ines", "Taco Pujio", "Totorilla Nuevo", "Tramo Veintiseis", "Tusca Pozo", "Yanta"],
    "4312": ["Mili", "Morello"],
    "4313": ["Anchoriga", "Aspa Sinchi", "Atoj Pozo", "Barranca Colorada", "Barrancas", "Barrial Alto", "Boqueron", "Brea Pozo", "Brea Pozo Viejo", "Charquina", "Chilpa Mayo", "Chimpa Macho", "Colonia Pinto", "El Dorado", "El Puente", "Gallegos", "Garceano", "Isla Verde", "Kilometro 437", "Kilometro 473", "La Blanca", "La Cañada", "Laguna Blanca", "Linton", "Majadas", "Majadas Sud", "Medellin", "Pampa Atun", "Penal Provincial", "Perchil Bajo", "Puestito", "Puesto Del Rosario", "Remedios De Escalada", "Robles", "San Jose", "Tacoyoj", "Tala Pozo", "Tio Chacra", "Tres Jazmines", "Tulum", "Tulun", "Villa Elena", "Villa Nueva", "Villa Vieja"],
    "4315": ["Bajadita", "Cañada San Ramon", "Codo", "Codo Viejo", "Collera Huircuna", "Estacion Atamisqui", "La Noria", "Los Angeles", "Paaj Muyo", "Piruitas", "San Luis", "Santa Isabel", "Sauces", "Sol De Mayo", "Taco Pozo", "Tio Pozo", "Yacuchiri"],
    "4317": ["Burro Pozo", "Carbon Pozo", "Chilca Albardon", "Chilquita", "Chilquitas", "Chuiqui", "Collera Huiri", "Coropampa", "El Carmen", "El Dean", "El Peru", "Escalera", "Esperanza", "Higuerillas", "Hornillos", "Hoyon", "Huachana", "Isla De Aragones", "Juanillo", "Kenti Taco", "Kilometro 436", "La Darsena", "La Esquina", "La Perlita", "Leiva", "Lezcanos", "Lomitas", "Los Mollares", "Los Quiroga", "Los Sauces", "Manogasta", "Mirandas", "Pampallajta", "Pineda", "Pozo Cercado", "Pozo Grande", "Pueblito", "Puente Del Salado", "Puesto De Diaz", "Punta Pozo", "Ramaditas", "Remansito", "Rodeo De Soria", "Rodeo De Valdez", "Salinas", "San Antonio", "San Antonio De Los Caceres", "San Carlos", "San Gregorio", "San Isidro", "San Martin", "Santa Maria", "Saucen", "Saucioj", "Sauzal", "Soconcho", "Tipiro", "Ventura Pampa", "Villa Atamisqui"],
    "4318": ["Huajia"],
    "4319": ["Barrancas", "Cañas Paso", "Chilca Juliana", "Chileno", "Guerra", "La Paloma", "Lechuzas", "Los Cerrillos", "Mal Paso", "Mistol Pozo", "Peralta", "Polvareda", "Puente Del Saladillo", "Sabagasta", "Saladillo", "Santa Lucia", "Taco Totarayol", "Tagan", "Tio Alto", "Tolosa", "Toropan", "Totora", "Vaca Human", "Varas Cuchuna", "Veron", "Villa Salavina"],
    "4321": ["Anca", "Anga", "Bordo Pampa", "Cardajal", "Cerrillos", "Chira", "El Cincuenta", "El Pueblito", "Hutcu Chacra", "Kilometro 364", "Kilometro 390", "La Golondrina", "La Gringa", "La Paliza", "La Pampa", "La Protegida", "La Puerta Del Monte", "Las Lomas", "Loma Blanca", "Los Caños", "Los Telares", "Malota", "Manchin", "Paso Del Saladillo", "Portalis", "Pozo Del Monte", "Puesto Del Medio", "Quimili Paso", "Ramadita", "Rami Yacu", "Remansos", "Rumi Jaco", "San Fernando", "Santa Brigida", "Santa Maria", "Taco Isla", "Troncal", "Yacu Hurmana"],
    "4322": ["Alto Pozo", "Arbolitos", "Aspa Sinchi", "Buena Vista", "Cachi", "Campo Verde", "Candelaria", "Cavadito", "Cavado", "Chaguar Puncu", "Colonias", "Corvalanes", "El Aibal", "El Cebollin", "El Cuello", "El Ojo De Agua", "El Puente", "El Rosario", "El Vizcacheral", "Fernandez", "Industria Nueva", "Ingeniero Forres", "Jimenez", "Jume Esquina", "Kiska Hurmana", "La Bota", "La Cañada", "La Colonia", "La Cruz", "La Cuarteada", "La Esperanza", "La Falda", "La Germania", "La Loma", "La Petronila", "La Primitiva", "La Ramada", "Loma Negra", "Lomitas", "Los Alderete", "Los Diaz", "Los Doce Quebrachos", "Los Gallardos", "Los Guerreros", "Los Herreros", "Los Puestos", "Los Puntos", "Maco", "Maderas", "Maria Delicia", "Nueva Industria", "Palermo", "Quishca", "Quita Punco", "Remansito", "Rio De Gallo", "Rivadavia", "Sainquen Punco", "San Cayetano", "San Javier", "San Lorenzo", "San Martin", "San Ramon", "San Roque", "San Vicente", "Santa Cruz", "Santa Rita", "Santa Rosa", "Sepulturas", "Suri Pozo", "Taperas", "Trancas", "Tres Chañares", "Tusca Pozo", "Vila Isla", "Yaso"],
    "4324": ["Blanca", "Carbon Pozo", "Cazadores", "Cheej", "Collujlioj", "Collun Lioj", "Concepcion", "Coraspino", "Diaspa", "El Bajo", "El Empachado", "El Juncal", "Garza", "Guaipi", "Hornillos", "La Blanca", "La Cruz", "La Falda", "La Overa", "Lapa", "Molle", "Nueve Mistoles", "Paso Mosoj", "Percas", "Pozo", "Pozo Moro", "Pozo Mosoj", "Quimilloj", "Rosiyulloj", "San Enrique", "San Jose", "San Jose Este", "San Marcos", "San Pedro", "Taboada Estacion", "Taco Huaco", "Taco Suyo", "Toro Pozo", "Yacano", "Yalan"],
    "4326": ["Ave Maria", "Caloj", "Chuña Palma", "Codo Pozo", "Conchayos", "Consulñoj", "Cruz Pozo", "Guardia", "Guiñao", "Lugones", "Novillo", "Paaj Rodeo", "Paso Grande", "Pozo Marcado", "Punta Corral", "Punta Pozo", "Ruta Nacional 34", "Ruta Provincial 11", "Ruta Provincial 130", "Ruta Provincial 17", "Ruta Provincial 40", "Ruta Provincial 5", "Ruta Provincial 8", "San Antonio", "San Isidro", "San Jose Oeste", "San Luis", "San Pedro", "San Roque", "Santo Domingo", "Sauce Bajada", "Zapi Pozo"],
    "4328": ["Brealoj", "Chañar Pozo", "Colonia Isla", "El Trece", "Guañagasta", "Herrera", "Lujan", "Mailin", "Mallin Viejo", "Moconza", "Represa", "Rincon De La Esperanza", "Salviaioj Gaitan", "San Antonio De Copo", "San Pedro", "San Ramon", "Taco Atun", "Tala"],
    "4332": ["Blanca Pozo", "Bracho", "Colonia Dora", "Libanesa", "Puente Negro", "Sunchituyoj", "Tacon Esquina"],
    "4334": ["Icaño", "La Costa", "Lago Muyoj", "Mal Paso", "Oro Pampa", "Pozo Cabado", "Real Sayana", "Tiestituyos", "Toro Pampa", "Tronco Blanco", "Yacasnioj"],
    "4336": ["Abra Grande", "Cerrillo", "Coro Abra", "El Diamante", "Huyamampa", "La Aurora", "Los Herreras", "Los Marcos", "Media Flor", "Palos Quemados", "Pampa Mayo", "Puesto Los Marcos", "San Felix", "San Nicolas", "San Pedro", "Simbol Cañada"],
    "4338": ["Bajo Grande", "Bayo Muerto", "Clodomira", "Condor Huasi", "El Favorito", "Favorita", "Jumi Pozo", "Kilometro 629", "Laguna Larga", "Las Chacras", "Negra Muerta", "Palmares", "Palmitas", "Rumios", "San Felipe", "San Francisco Lavalle", "San Isidro", "San Javier", "San Pablo", "Santa Rosa De Vitervo", "Santo Domingo"],
    "4339": ["Kilometro 645", "Kilometro 651", "San Nicolas", "San Ramon", "Santa Rosa", "Señora Pujio", "Simbolar"],
    "4350": ["Alejito", "Ampa", "Azogasta", "Carretero", "Codo Bajada", "Corral Grande", "Cruz Chula", "Cruz Loma", "Dolores", "Dos Hermanos", "El Quemado", "El Sauce", "Guaype", "Iuchan", "Jumi Pozo", "Kilometro 443", "Kilometro 546", "La Balanza", "La Reconquista", "La Reduccion", "Laspa", "Laureles", "Lincho", "Lojlo", "Lote 15", "Nueva Granada", "Padua", "Palermo", "Pampa Pozo", "Pozo Grande", "Puente Rio Salado", "Punco", "Repecho Diaz", "Repecho Montenegro", "Rodeo Bajada", "San Antonio", "San Carlos", "San Francisco", "San Pedro", "San Ramon", "San Simon", "Santa Maria", "Sin Descanso", "Suncho Corral", "Suri", "Tres Hermanas"],
    "4351": ["Campo Verde", "El Carmen", "El Palomar", "El Pertigo", "Floresta", "Huacanitas", "Kiska Loro", "La Potocha", "Las Randas", "Las Tinajas", "Lote S", "Mistol Pampa", "Pampa Muyoj", "Punta De Rieles", "San Luis", "Santa Rosa", "Segundo Pozo", "Simbolar", "Stayle", "Surihuaya", "Tabeanita", "Tabiana", "Tres Pozos", "Villa Brana", "Villa Fanny", "Weisburd", "Yuchan"],
    "4353": ["25 De Mayo", "Aibal", "Alza Nueva", "Amama", "Armonia", "Bella Vista", "Campo Limpio", "Cartavio", "Cañada Limpia", "Celestina", "Colonia Media", "Colonia San Juan", "Dolores", "Dolores Central", "Dos Hermanas", "El Aibalito", "El Bragado", "El Cruce", "El Crucero", "El Descanso", "El Negrito", "El Rosario", "Estancia La Invernada", "Jumial Grande", "Jumialito", "Juncal Grande", "La Invernada", "Los Puentes", "Lujan", "Maravilla", "Maria", "Mercedes", "Minerva", "Nogales", "Nueva Alza", "Nueva Colonia", "Paciencia", "Palomar", "Pampa Pozo", "Pirhuas", "Puesto De Mena", "Quimilioj", "Quisña Loro", "Remansito", "Rosario", "Rumi", "San Antonio", "San Carlos", "San Felipe", "San Francisco", "San Isidro", "San Jose Dto Figueroa", "San Luis", "San Martin", "San Nicolas", "San Pablo", "San Pedro", "San Ramon", "San Roque", "Santa Lucia", "Santa Maria", "Santa Rita", "Santo Domingo", "Trinidad", "Tusca Pozo", "Uturunco", "Vaca Huañuna", "Villa Figueroa", "Yacu Hichacuna"],
    "4354": ["Arbolitos", "Buena Vista", "Cachi", "Campo Verde", "Candelaria", "Cavadito", "Cavado", "Colonia El Simbolar", "Cruz Grande", "El Aibal", "El Cuello", "El Vizcacheral", "Huritu Huasi", "Jume Esquina", "Kilometro 613", "La Bota", "La Brea", "La Cañada", "La Concepcion", "La Cruz", "La Esperanza", "La Loma", "La Paz", "La Petronila", "La Primitiva", "La Ramada", "La Tapa", "Lomitas", "Maco", "Maderas", "Remansito", "Rio De Gallo", "San Cayetano", "San Salvador", "San Vicente", "Santa Maria Dto Figueroa", "Santa Rosa", "Sepulturas", "Trancas", "Tres Chañares", "Villa Isla", "Villa Tolojna", "Yacu Hurmana"],
    "4356": ["Bajo Hondo", "Casa Alta", "Colonia Paz", "Colonia Siegel", "El Aibal", "El Canal", "El Chinchillar", "El Saladillo", "Kilometro 494", "Lagunilla", "Ledesma", "Llajta Mauca", "Lote 29", "Matara", "Melero", "Puente Bajada", "Rincon Esperanza", "Roldan", "San Miguel Del Matara", "Soledad", "Taruy", "Tiun Punco", "Villa Esquina", "Villa Matara"],
    "4400": ["Barrio La Loma", "Barrio San Cayetano", "Belgrano", "Buena Vista", "Campo Caseros", "Chachapoyas", "Chamical", "Cobas", "El Aybal", "El Prado", "Estola", "Higuerillas", "Kilometro 1129", "La Cruz", "La Isla", "La Lagunilla", "La Montaña", "La Pedrera", "La Quesera", "La Troja", "Limache", "Los Noques", "Rio Ancho", "Salta"],
    "4401": ["Antonio Alice", "Atocha", "Caldera", "Calderilla", "Castellanos", "Curuzu", "El Gallinato", "General Alvarado", "Humaita", "Kilometro 1125", "La Isla", "La Union", "Las Costas", "Lesser", "Los Alamos", "Los Mercados", "Los Peñones", "Los Sauces", "Mayo Torito", "Monte", "Paredes", "Peñalva", "Potrero De Castilla", "San Alejo", "San Lorenzo", "Santa Rufina", "Vaqueros", "Velardes", "Villa San Lorenzo", "Yacones"],
    "4403": ["Cebados", "Cerrillos", "Colon", "El Colegio", "El Huaico", "Finca Camino A Colon", "Finca Camino Vallisios", "Finca Colon", "Finca El Colegio", "Isla De La Candelaria", "Kilometro 1156", "La Falda", "La Fama", "Las Blancas", "Las Palmas", "Los Alamos", "Olmos", "Paraje Zanjon", "Piedemonte", "Rio Ancho", "Rodeos", "San Clemente", "San Miguel", "Santa Elena", "Villa Los Tarcos", "Zanjon"],
    "4405": ["Ballenal", "Camara", "Carabajal", "El Carmen", "El Corralito", "El Dorado", "El Manzano", "El Mollar", "El Porvenir", "El Potrero", "El Pucara", "El Puyil", "El Rosal", "El Timbo", "La Estela", "Las Arenas", "Las Mesadas", "Las Rosas", "Media Luna", "Merced De Arriba", "Pascha", "Pie De La Cuesta", "Rosario De Lerma"],
    "4407": ["Alejo De Alberro", "Campo Quijano", "El Encon", "Eltunal", "Kilometro 1172", "La Silleta", "Las Arcas", "Potrero De Linares", "Potrero De Uriburu", "Virrey Toledo"],
    "4409": ["Alfarcito", "Cachiñal", "Cerro Bayo", "Chorrillitos", "Chorrillos", "Damian M Torino", "Diego De Almagro", "El Alfredito", "El Alisal", "El Golgota", "El Toro", "Encrucijada", "Encrucijada De Tastil", "Gobernador Manuel Sola", "Gobernador Saravia", "Huaicondo", "Incahuasi", "Incamayo", "Ingeniero Maury", "Las Capillas", "Las Cebadas", "Las Cuevas", "Meseta", "Mina Carolina", "Puerta De Tastil", "Quebrada Del Toro", "Quebrada Muñano", "San Bernardo De Las Zorras", "Santa Rosa De Tastil", "Tacuara", "Toro", "Tres Cruces", "Villa Sola"],
    "4411": ["Abra Del Gallo", "Acazoque", "Cortaderas", "Estacion Cachiñal", "Grandes Pastos", "Juncal", "Los Patos", "Mina Julio", "Muñano Kilometro 1308", "Paraje Cerro Negro", "Paraje Cobres", "Paraje Cortaderas", "Paraje Esquina De Guardia", "Paraje Las Cuevas", "Paraje Mina Concordia", "Paraje Morro Colorado", "Paraje Nacimientos", "Paraje Pastos Grandes", "Paraje Pircas", "Paraje Pizcuno", "Paraje Uncuru", "Potrerillos", "Potrero De Poyogasta", "San Antonio De Los Cobres", "Sey", "Sta Rosa De Los Pastos Grandes"],
    "4413": ["Caipe", "Catua", "Cauchari", "Chachas", "Chuculaqui", "Incachuli", "Juncalito", "Kilometro 1369", "Kilometro 1373", "Kilometro 1424", "Laguna Seca", "Los Colorados", "Mina La Casualidad", "Mina Tincalaya", "Olacapato Chico", "Olacapato Grande", "Paraje Olacapato", "Quebrada Del Agua", "Salar De Pocitos", "Socompa", "Taca Taca Estacion Fcgb", "Tolar Chico", "Tolar Grande", "Unquillal Embarcadero Fcgb", "Vega De Arizaro"],
    "4415": ["Agua Negra", "Ampata", "Angostura", "Atudillo", "Barro Negro", "Buena Vista", "Cangrejillos", "Cerro Mal Canto", "Chorro Blanco", "Cuesta Chica", "El Candado", "El Maray", "El Molino", "El Nogalar", "El Potrero", "El Rodeo", "El Sunchal", "El Trigal", "Finca Belgrano", "Huayra Huasy", "La Esperanza", "La Herradura", "La Poma", "La Yesera", "Las Animas", "Las Cortaderas", "Las Zanjas", "Loma De Burro", "Los Laureles", "Mal Cante", "Mal Paso", "Mina San Esteban", "Mina San Guillermo", "Mina San Walterio", "Minas Victoria", "Molino De Gongora", "Ojo De Agua", "Palermo Oeste", "Payogasta", "Pie De La Cuesta", "Piul", "Pompeya", "Potrero", "Pueblo Nuevo", "Pueblo Viejo", "Punta De Agua", "Quebrada De Escoipe", "Rumiarco", "Saladillo", "San Martin La Cuesta", "Tonco", "Toro Yaco", "Trigal", "Valle Encantado", "Villitas", "Yacera"],
    "4417": ["Barrio Parabolica", "Cachi", "Cachi Adentro", "Cuesta Del Obispo", "Escalchi", "Fuerte Alto", "Las Arcas", "Las Pailas", "Las Trancas", "Pueblo Viejo", "Puerta De La Paya", "Puil", "Rio Blanco", "Rio Toro", "Rumihuasi"],
    "4419": ["Amaicha", "Angostura", "Banda Grande", "Brealito", "Burro Yaco", "Cerro Bravo", "Cerro De La Zorra Vieja", "Cerro Del Agua De La Falda", "Chicoana", "Colmenar", "Colome", "Colte", "Corrida De Cori", "Cuchiyaco", "Diamante", "El Brealito", "El Carmen", "El Churcal", "Esquina", "Gualfin", "Humanas", "La Paya", "La Puerta", "Luracatao", "Molinos", "Monte Grande", "Peñas Blancas", "Rumihuasi", "Salar Del Hombre Muerto", "San Jose De Colte", "San Jose De Escalchi", "San Martin", "Seclantas", "Seclantas Adentro", "Tacuil", "Tomuco", "Volcan Azufre"],
    "4421": ["Ablome", "Almona", "Ampascachi", "Bella Vista", "Cacho Molino", "Calvimonte", "Colonia El Fuerte", "Coronel Moldes", "Dique Cabra Corral", "Doctor Facundo Zuviria", "El Carancho", "El Carmen", "El Carril", "El Leoncito", "El Potrero De Diaz", "El Simbolar", "Escoipe", "Estacion Zuviria", "Gualiana", "Kilometro 1176 300", "La Argentina", "La Armonia", "La Bodega", "La Bodeguita", "La Costa", "La Merced", "La Toma", "Las Cañas", "Las Garzas", "Las Mercedes", "Las Pircas", "Las Tienditas", "Osma", "Paso Del Rio", "Peñas Azules", "Piedra Del Molino", "Piedras Moradas", "Puente De Diaz", "Quisca Loro", "Retiro", "Saladillo De Osma", "San Agustin", "San Antonio Chicoana", "San Antonio La Viña", "San Geronimo", "San Jose", "San Martin", "San Nicolas", "San Vicente", "Santa Maria", "Sauce Alegre", "Sevillar", "Siñunto", "Sumalao", "Tres Acequias"],
    "4423": ["Bella Vista", "Campo Alegre", "Chicoana", "Chivilme", "Doctor Facundo Zuviria", "El Moyar", "El Quemado", "El Simbolar", "El Tipal", "La Calavera", "La Esperanza", "La Guardia", "La Margarita", "La Maroma", "Las Moras", "Los Los", "Molino", "Palmira", "Pedregal", "Peñaflor", "Potrero De Diaz", "Pulares", "San Fernando De Escoipe", "San Joaquin", "San Jose De La Viña", "Santa Ana", "Santa Gertrudis", "Santa Rosa", "Tilian", "Villa Fanny", "Viñaco"],
    "4425": ["20 De Febrero", "Acosta", "Amblayo", "Bodeguita", "Campos De Alemania", "Carahuasi", "Castañares", "Cerro Alemania", "Cevilar", "Coropampa", "Durazno", "El Acheral", "El Creston", "El Fraile", "El Obelisco", "El Sapo", "Finca El Carmen", "Guachipas", "La Costa", "La Florida", "La Pampa", "La Poblacion", "La Represa", "La Viña", "Las Curtiembres", "Las Juntas De Alemania", "Las Lechuzas", "Los Castillos", "Los Churquis", "Los Sauces", "Mina Don Otto", "Morales", "Pampa Grande", "Potrerillos", "Redondo", "Rio Alemania", "San Roque", "Santa Barbara", "Santa Elena", "Sauce", "Sauce Redondo", "Talapampa", "Tipa Sola", "Tres Cruces", "Vaqueria Los Sauces"],
    "4427": ["Angastaco", "Animana", "Barrial", "Buena Vista", "Cafayate", "Corralito", "El Recreo", "Finca La Rosa", "Isonza", "Jacimana", "La Arcadia", "La Armonia", "La Banda", "La Cabaña", "La Merced", "La Punilla", "La Viña", "Las Conchas", "Las Viñas", "Lorohuasi", "Los Alamos", "Los Sauces", "Monte Viejo", "Palo Pintado", "Payogastilla", "Pucara", "Rumiuarco", "San Antonio", "San Carlos", "San Felipe", "San Isidro", "San Lucas", "San Rafael", "Santa Rosa", "Simbolar", "Yacochuya", "Yanchuya"],
    "4430": ["Aguas Calientes", "Algarrobal", "Arjuntas", "Chacra Experimental", "El Ceibal", "El Colgado", "El Espinillo", "El Moranillo", "El Sunchal", "El Zapallar", "Entre Rios", "Est El Bordo", "Fuerte Quemado", "General Guemes", "Kilometro 1094", "La Asuncion", "La Defensa", "La Maravilla", "Las Vertientes Santa Rita De", "Madre Vieja", "Ojo De Agua", "Paramamaya", "Pozo El Algarrobo", "Puerto De Diaz", "Puesto Viejo", "Quisto", "Saladillo", "San Isidro", "San Pedro De Aranda", "Santa Ana", "Santa Cruz", "Santa Rita", "Sargento Cristobal", "Sausalito", "Simbol Yaco", "Torzalito", "Tres Yuchanes", "Vaqueria", "Villa Mayor Zabaleta", "Yasquiasme", "Zapallito"],
    "4431": ["Aguas Calientes"],
    "4432": ["Altos Hornos Guemes", "Betania", "Campo Santo", "Cantera Del Sauce", "Cobos", "Colonia Santa Rosa De Lima", "Dique Embalse Campo Alegre", "El Borde De San Miguel", "El Bordo", "El Prado", "El Sauce", "Gallinato", "Ingenio San Isidro", "Kilometro 1102", "La Ofelia", "La Oliva", "La Ramada", "La Viña", "Mojotoro", "Rio Lavallen", "Rodeo Grande", "San Martin", "Santa Lucia", "Santa Rosa"],
    "4434": ["Acharas", "Anta", "Cabeza De Anta", "Cabeza De Buey", "Carreras", "Chilcas", "Coba", "Cruz Quemada", "Ebro", "El Algarrobo", "El Estanque", "El Libano", "El Naranjo", "El Oso", "El Rey", "El Salto", "El Yeso", "El Zanjon", "Estancia Vieja", "Finca La China", "Gonzalez", "Juramento", "La Cuestita Anta", "La Cuestita Metan", "La Posta", "La Puntilla", "La Trampa", "Las Acheras", "Las Cañas", "Las Cuestitas", "Las Flacas", "Las Hecheras", "Las Mesitas", "Las Viboras", "Lechiguana", "Los Corrales", "Los Nogales", "Lumbreras", "Miraflores", "Palomitas", "Paso De La Cruz", "Piquete De Anta", "Quesera", "Rio Piedras", "Saladillo", "San Sebastian", "Sauce Bajada", "Virgilio Tedin"],
    "4440": ["Balderrama", "Campo Alegre", "Campo Azul", "Conchas", "Durazno", "El Guanaco", "El Sauzal", "El Vallecito", "Esteco Embarcadero Fcgb", "Hosteria Juramento", "La Aguadita", "La Costosa", "Las Juntas", "Los Bañados", "Metan", "Nogalito", "Paso De Balderrama", "Paso Del Durazno", "Pasteadero", "Peru", "Punta Del Agua", "Sacha Pera", "San Javier", "Santa Elena", "Schneidewind", "Tala Muyo", "Vera Cruz", "Yatasto"],
    "4441": ["Metan Viejo"],
    "4444": ["Arrocero Italiano", "Bajo Grande Desvio Fcgb", "El Galpon", "El Parque", "Finca Armonia", "Finca Rocca", "Foguista J F Juarez", "La Armonia", "La Poblacion", "Las Delicias", "Miraflores M", "Ovejeria", "Poblacion De Ortega"],
    "4446": ["Algarrobal", "Algarrobal Viejo", "Alto Del Mistol", "Bajo Grande", "Ceibalito", "Chañar Muyo", "Chorroarin", "Coronel Olleros", "Corral Quemado", "Divisadero", "El Arenal", "El Carrizal", "El Jaravi", "El Pacara", "El Tunal", "La Carretera", "La Manga", "Lagunita", "Lagunita Nueva Poblacion", "Los Chifles", "Los Rosales", "Molle Pozo", "Paso De Las Carretas", "Paso La Cruz", "Poblacion", "Potrerillo", "Potrero", "Puli", "Rosales", "San Jose De Orqueras", "San Juan", "Sauzal", "Tala Muyo", "Talas", "Tunalito"],
    "4448": ["Coronel Vidt", "El Algarrobal", "Finca Mision Zenta", "Joaquin V Gonzalez", "Kilometro 1088", "La Esperanza", "La Lomita", "Laguna Blanca", "Las Blancas", "Las Flechas", "Limoncito", "Los Mollinedos", "Minas Ypf", "Miraflores", "Piquete De Anta", "Poblacion", "Poso De Algarrobo", "Pozo Cantado", "Pozo Del Greal", "Puerta Blanca", "Saladillo De Juarez", "San Fernando", "San Ignacio", "San Jorge", "Santa Ana", "Santo Domingo", "Sapo Quemado", "Sauce Solo", "Simbolito", "Vieja Pozo", "Weisburg"],
    "4449": ["Agua Sucia", "Alto Alegre", "Apolinario Saravia", "Arita", "Barrealito", "Campo Alegre", "Colonia Hurlingham", "Coronel Mollinedo", "El Bordo", "El Carmen", "El Manantial", "El Pericote", "Espinillo", "Esquina", "General Pizarro", "Kilometro 1104", "Laguna Verde", "Las Bateas", "Las Flores", "Las Lajitas", "Las Palmas", "Las Tortugas", "Las Vateas", "Luis Burela", "Media Luna", "Monasterios", "Palermo", "Palo A Pique", "Piquete Cabado", "Pozo Grande", "Pozo Verde", "Rio Del Valle", "Rosario Del Dorado", "Salta Forestal Kilometro 50", "San Luis", "San Martin", "San Ramon", "Santa Rosa", "Santo Domingo", "Santo Domingo Santa Victoria", "Totoral", "Tunalito"],
    "4452": ["Ahi Veremos", "Botija", "Chañar Aguada", "Cruz Bajada", "Dos Arboles", "El Porvenir", "El Quebrachal", "El Vencido", "Floresta", "Fuerte El Pito", "Gaona", "Guayacan", "Kilometro 1152", "Las Puertas", "Llucha", "Los Colorados", "Macapillo", "Manga Vieja", "Mercedes", "Mistolito", "Nuestra Señora De Talavera", "Picos De Amor", "Picos De Arroz", "Platero", "Pringles", "Quebrachal", "Roca", "Roma", "San Gabriel", "San Isidro", "Santa Rosa De Anta", "Simbolar", "Sunchalito", "Tacioj", "Taco Esquina", "Taco Pampa", "Talavera", "Tolloche", "Toro Pampa", "Vencida", "Villa Matoque", "Vinal Macho", "Vinal Pozo", "Vinalito"],
    "4500": ["Alto Del Saladillo", "Barrio La Providencia", "El Acheral", "El Arenal", "El Chaguaral", "El Saladillo", "Ensenada", "Esquina De Quisto", "La Sanga", "Moralito", "Rodeito", "Saladillo Ledesma", "San Jose Del Bordo", "San Lucas", "San Pedro De Jujuy"],
    "4501": ["Abra Del Trigo", "Aguas Blancas", "Arroyo Colorado", "Arroyo Del Medio", "Bella Vista", "Cachi Punco", "El Fuerte", "El Mistol", "El Olvido", "El Palmar", "El Piquete", "El Sunchal", "El Tipal", "Gobernador Ovejero", "Isla Chica", "Isla Grande", "La Ollada", "La Quinta", "La Ronda", "La Vertiente", "Laguna San Miguel", "Laguna Totorillas", "Lapachal Ledesma", "Lapachal Santa Barbara", "Loma Pelada", "Los Matos", "Milan", "Palma Sola", "Pie De La Cuesta", "Puesto Nuevo", "Real De Los Toros", "San Juan De Dios", "San Rafael", "Santa Clara", "Santa Rita", "Sauzal", "Siete Aguas"],
    "4503": ["Arrayanal", "Ingenio La Esperanza", "La Esperanza", "Lavayen", "Los Bayos", "Lote El Puesto", "Lote La Cienaga", "Lote La Posta", "Lote Miraflores", "Lote Palmera", "Lote Parapeti", "San Antonio"],
    "4504": ["23 De Agosto", "Chalican", "El Quemado", "El Rio Negro", "Finca Leach", "Jaramillo", "Leachs", "Lote Zora", "Rastrojos", "Rio Negro"],
    "4506": ["Alegria", "Arenal Barroso", "Bajada Alta", "El Cardonal", "Fraile Pintado", "Guayacan", "La Bajada", "La Reduccion", "Lote Maiz Negro", "Oculto", "Ojo De Agua", "Siberia"],
    "4512": ["Agua Negra", "Animas", "Aparejo", "Bateas", "Bella Vista", "Campo Bajo", "Campo Colorado", "Candelaria", "Cevilar", "Cienaga", "Colonia 8 De Septiembre", "Cortaderas", "Don Jorge", "Duraznal", "El Aibal", "El Bananal", "El Caulario", "El Manantial", "El Naranjo", "El Sauce", "Esquina", "Falda Del Quebrachal", "Falda Mojon", "Falda Montosa", "Florencia", "Guachan", "Higueritas", "Ingenio Ledesma", "La Calera", "La Puerta", "Las Higueritas", "Las Quintas", "Ledesma", "Libertador Gral San Martin", "Loma Del Medio", "Los Catres", "Lote Prediliana", "Lote San Antonio", "Mal Paso", "Marta", "Mojon Azucena", "Molular", "Naranjito", "Normenta", "Palo A Pique", "Pampa Larga", "Paulete", "Paulina", "Piedra Blanca", "Potrero Alegre", "Pozo Cavado", "Pozo Verde", "Prediliana", "Pueblo Ledesma", "Pueblo Nuevo", "Puerta Vieja", "Ramada", "Rio Seco", "San Francisco", "Santillo", "Sauzalito", "Sepultura", "Socabon", "Soledad", "Tarijita", "Toquillera", "Trementinal", "Tucumancito"],
    "4513": ["Alto Calilegua", "Amancayoc", "Amarguras", "Cacho", "Chorro", "Fundiciones", "Gobernador Tello", "Loma Larga", "Nogal", "Nogales", "Nogalito", "Pampichuela", "Picacho", "Pilcomayo", "Pueblo", "Puerto Tolava", "Queñoal", "San Antonio", "San Lucas", "Santa Barbara", "Santa Clara", "Talar", "Valle Grande"],
    "4514": ["Calilegua", "Lecheria", "Posta Gdaparque Nac Calilegua", "San Lorenzo"],
    "4516": ["Caimancito", "Chañar Solo", "Chañaral", "Finca Agua Salada", "Finca Agua Tapada", "Finca La Lucrecia", "Finca La Realidad", "Finca Santa Cornelia", "Los Baños Termales", "Obraje San Jose"],
    "4518": ["Aguas Calientes", "Vinalito", "Yuto"],
    "4522": ["Alto Del Saladillo", "La Mendieta", "Lote Don David", "Lote Don Emilio", "Lote Piedritas", "Lote San Juancito", "Lote Sauzal", "Palo Blanco", "Palo Santo", "Rio Grande", "Rosario De Rio Grande", "Saladillo Ledesma", "Saladillo San Pedro"],
    "4530": ["Abra Grande", "Aguas Blancas", "Colonia A", "Colonia Agricola San Agustin", "Colonia D", "Colonia Santa Maria", "El Carmen", "El Molle", "El Quemado", "Finca Mision Zenta", "Fortin Belgrano", "Juntas De San Antonio", "La Toma", "Las Cortaderas", "Limoncito", "Lomas De Olmedo", "Lote Josefina", "Lote Lucrecia", "Lote Marcela", "Lote Sarita", "Maria Jose", "Minas Ypf", "Mision Franciscana", "Oran", "Parani", "Piedra Del Potrillo", "Pozo Azul", "Pozo De La Esquina", "Pozo De La Piedra", "Pozo Pringles", "Puesto De Motijo", "Queñua", "Rio Colorado", "Rio De Las Piedras", "Rio Pescado", "San Andres", "San Antonio", "San Bernardo", "San Ignacio", "San Ignacio De Loyola", "San Ramon De La Nueva Oran", "Solazuti", "Soledad", "Tres Pozos", "Vado Hondo"],
    "4531": ["Aguas Blancas", "Colonia Santa Rosa", "Isla De Cañas", "Los Toldos", "Santa Cruz"],
    "4533": ["Angel Peredo", "Angelica", "El Tabacal", "Hipolito Yrigoyen", "Ingenio San Martin", "Kilometro 1298", "Lote Estela", "Maria Luisa", "Tabacal Ingenio"],
    "4534": ["Algarrobal", "Arbol Solo", "El Mistol", "El Quimilar Carboncito", "El Zapallo", "Kilometro 1280", "Kilometro 1281", "Kilometro 1291", "Las Varas", "Pichanal", "Pizarro", "Puesto Del Medio", "Santa Rosa", "Yacara"],
    "4535": ["Aguas Muertas", "Algarrobal", "Alto Verde", "Arenales", "Belgrano Fortin 2", "Bella Vista", "Campo Argentino", "Ciervo Cansado", "El Breal", "El Destierro", "El Mirador", "El Soldadito", "El Tunalito", "El Yacon", "Fortin Frias", "La Cancha", "La Esperanza", "La Esquinita", "La Montaña", "La Tablada", "La Union", "Las Bolsas", "Las Cañitas", "Las Conchas", "Las Llaves", "Martin Garcia", "Mollinedo", "Palmarcito", "Paraiso", "Paso El Milagro San Aniceto", "Porongal", "Pozo Cercado", "Pozo Del Pato", "Pozo Del Sauce", "Pozo Del Zorro", "Pozo Verde", "Puesto De La Viuda", "Rivadavia", "San Isidro", "San Joaquin", "San Miguel", "Santa Rosa", "Santo Domingo", "Santos Lugares", "Victorica", "Villa Petrona"],
    "4537": ["Chaguaral", "Esteban De Urizar", "Jeronimo Matorras", "La Estrella", "Martinez Del Tinco", "Martinez Del Tineo", "Yuchan"],
    "4538": ["El Desmonte", "Finca La Toma", "Las Maravillas", "Saucelito"],
    "4542": ["El Palmar De San Francisco", "El Talar", "Ingenio La Esperanza", "Pozo Del Cuinco", "Santa Marina", "Urundel"],
    "4550": ["Buen Lugar", "Colonia Otomana", "Corzuela", "El Cuchillo", "El Retiro", "Embarcacion", "Kilometro 1306 Fcgb", "La Fortuna", "La Quena", "Los Baldes", "Manuel Elordi", "Nuevo Porvenir", "Otomana", "Puesto Grande", "Santa Victoria"],
    "4552": ["Antonio Quijarro", "Campichuelo", "Coronel Cornejo", "Corralito", "General Ballivian", "Pastor Sevillosa", "Pocoy", "Puerto Baules", "Rio Seco", "Senda Hachada Estacion Fcgb", "Tranquitas"],
    "4554": ["Campo Largo", "Campo Libre", "Capitan Juan Page", "Chirete", "Cnel Juan Sola Est Morillo", "Dos Yuchanes", "Dragones", "El Cienago", "El Espinillo", "El Pertigo", "El Talar", "El Tartagal", "Emboscada", "Hickmann", "La Curva", "La Entrada", "La Mora", "Las Horquetas", "Los Blancos", "Los Ranchillos", "Luna Muerta", "Madrejon", "Media Luna", "Mision Chaqueña", "Misiones", "Mistol Mareado", "Mistolar", "Monte Carmelo", "Palo Santo", "Pedro Lozano", "Pluma Del Pato", "Pozo Bravo", "Pozo Del Chañar", "Pozo Del Cuico", "Pozo Hondo", "Puesto Del Pañuelo", "Resistencia", "San Patricio", "Santa Clara", "Suri Pintado", "Tabaco Cimarron", "Tres Pozos", "Vuelta De Las Tobas"],
    "4560": ["Angostura", "Arenal", "Barrio San Antonio", "Capiazutti", "Carapari", "Colonia Zanja Del Tigre", "El Chorro", "Frontera 4", "Frontera 5", "Frontera Tres", "Guamachi", "La Porcelana", "La Soledad", "Lote 27", "Manuela Pedraza", "Mision Franciscana", "Paraje Campo Largo", "Pluma Del Pato", "Pozo Bermejo", "S Jollin", "San Laurencio", "San Pedro", "Tartagal", "Tonono", "Tuyunti", "Villa General Guemes", "Villa Saavedra", "Yacay", "Yacimiento Tonono", "Yariguarenda", "Zanja Honda"],
    "4561": ["Agua Verde", "Alto De La Sierra", "Amberes", "Balbuena", "Buena Fe", "Colonia Buenaventura", "El Ñato", "Hito 1", "La China", "La Chinaca", "Las Vertientes", "Mision Evenezer", "Mision La Paz", "Mision Santa Lucia", "Mision Vertiente Chica", "Puesto La Paz", "San Bernardo", "Santa Maria", "Santa Victoria Este"],
    "4562": ["General Enrique Mosconi", "Kilometro 1398", "Las Lomitas", "Vespucio"],
    "4563": ["Caminera San Pedrito", "Campamento Tablilla", "Campamento Vespucio", "El Aguay", "Recaredo"],
    "4564": ["Kilometro 1448", "Piquirenda", "Tobantirenda", "Yacuy"],
    "4566": ["Aguaray", "Campo Duran", "Ituyuro", "Macueta", "Rio Carapan"],
    "4568": ["Acambuco", "Dique Itiruyo", "Est Pocitos", "Salvador Mazza"],
    "4600": ["Algarrobal", "Alto Comedero", "Atalaya", "Barrio 9 De Julio", "Barrio Alberdi", "Barrio Alto La Loma", "Barrio Alto La Viña", "Barrio Bajo La Viña", "Barrio Chijra", "Barrio Cuyaya", "Barrio Lujan", "Barrio Parque 19 De Abril", "Barrio Santa Rita", "Chuquina", "El Algarrobal", "El Amancay", "El Cucho", "Guerrero", "Juan Galan", "La Almona", "La Cuesta", "Las Capillas", "Las Escaleras", "Las Higuerillas", "Los Alisos", "Los Blancos", "Nazareno", "Payo", "Reyes", "San Pablo De Reyes", "San Salvador De Jujuy", "Termas De Reyes", "Tesorero", "Tilquiza", "Villa Ciudad De Nieva", "Villa Gorriti", "Villa Jardin De Reyes"],
    "4601": ["Corral De Piedras", "El Arenal", "Huaico Chico", "Ituaicochico", "Ocloyas", "Rio Blanco"],
    "4603": ["Catamontaña", "Chucupal", "El Carmen", "El Ollero", "El Sunchal", "La Cienaga", "La Ollada", "Las Pircas", "Los Cedros", "Perico San Juan"],
    "4605": ["Alisos De Abajo", "Alisos De Arriba", "Ceibal", "Cerro Negro", "El Ollero", "La Cabaña", "La Toma", "Los Alisos", "Paño", "Rio Blanco", "San Antonio"],
    "4606": ["Colonia Los Lapachos", "El Toba", "La Ovejeria", "Las Cañadas", "Las Pichanas", "Los Lapachos", "Los Manantiales", "Maquinista Veron", "Pampa Blanca", "Pampa Vieja", "Puesto Viejo", "Toba"],
    "4608": ["Alto Verde", "Bordo La Isla", "Cadilla", "Campo La Tuna", "Chamical", "Coronel Arias", "El Cabral", "El Cadillal", "El Mollar", "El Pongo", "Entre Rios", "Estacion Perico", "Hornillos", "Iriarte", "Kilometro 1129", "La Union", "Lagunilla El Carmen", "Lagunilla Ledesma", "Las Pampitas", "Monterrico", "Perico", "Pozo De Las Avispas", "San Gabriel", "San Juancito", "San Rafael", "San Vicente", "Santa Rita", "Santo Domingo", "Venecias Argentinas", "Villa Argentina"],
    "4612": ["Carahunco", "Centro Forestal", "Cerros Zapla", "El Algarrobal", "El Brete", "El Cucho", "El Remate", "General Manuel Savio", "Juan Manuel De Rosas", "La Cuesta", "Las Capillas", "Las Escaleras", "Los Blancos", "Mina 9 De Octubre", "Palpala", "Puerta De Salas", "Zapla"],
    "4613": ["Suncho Pozo"],
    "4616": ["Barcena", "Bomba", "Chañi", "Chilcayoc", "Kilometro 1183", "Lagunas De Yala", "Leon", "Lozano", "Molinos", "Potrero", "Santuyoc", "Tesorero", "Tiraxi", "Tiraxi Chico", "Volcan", "Yala"],
    "4618": ["Abra De Pives", "Achacamayoc", "Agua Bendita", "Agua Palomar", "Alto De Casa", "Alto De Lozano", "Alto De Mojon", "Alto Del Angosto", "Alto Huancar", "Alto Minero", "Alto Potrerillo", "Alto Quemado", "Alto Quirquincho", "Boleteria", "Campo Oculto", "Canchahuasi", "Capachacra", "Carcel", "Casa Negra", "Casa Vieja", "Chañarcito", "Chañi Chico", "Chilcar", "Chorrillo", "Coiruro", "Colorados", "Condor", "Cortaderas", "Costillar", "Cruz Nido", "El Colorado", "El Molino", "El Moreno", "El Morro", "Encrucijada", "Esquina De Huancar", "Esquina Grande", "Estancia Grande", "Higueritas", "Huachichocana", "Huancar", "Inca Huasi", "La Aguadita", "La Cienaga", "La Puerta", "Lagunas", "Lindero", "Lipan", "Loma Larga", "Minas De Borato", "Molli Punco", "Moreno Chico", "Morrito", "Piedra Chota", "Piedras Amontonadas", "Piedras Blancas", "Porvenir", "Posta De Hornillos", "Pozo Bravo", "Pozo Colorado", "Pueblo Pla", "Puerta De Colorados", "Puerta De Lipan", "Puerta Patacal", "Puna De Jujuy", "Punta Canal", "Punta Corral", "Puntas De Colorados", "Purmamarca", "Quisquine", "Receptoria", "Riverito", "Sala", "San Bernardo", "San Javier", "San Jose Del Chañi", "Santa Rosa Tumbaya", "Santa Rosa Valle Grande", "Susuyaco", "Tala Grusa", "Totorito", "Tres Morros", "Triunvirato", "Tumbaya", "Tumbaya Grande", "Tunalito"],
    "4622": ["Bella Vista", "Cachihuaico", "El Callejon", "La Sanga", "Las Chicapenas", "Maimara", "Posta De Hornillos", "Punta Del Campo", "San Pedrito", "Tacta", "Yerba Buena Ledesma", "Yerba Buena Tilcara"],
    "4624": ["Abra Mayo", "Alfarcito", "Cañas", "El Durazno", "El Perchel", "Huichaira", "Juella", "La Banda", "Molulo", "Pucara", "Puesto", "Quebrada Huasamayo", "Tilcara", "Yala De Monte Carmelo"],
    "4626": ["Angosto Del Perchel", "Capla", "Chorrillos", "Chucalezna", "Huacalera", "Ocumazo", "San Jose", "Senador Perez", "Uquia", "Villa Del Perchel"],
    "4630": ["Aparzo", "Baliazo", "Balliazo", "Calete", "Chorrillos", "Cianzo", "Condor", "Coraya", "Galeta", "Hornaditas", "Humahuaca", "Kilometro 1289", "Ovara", "Quimazo", "San Andres", "San Roque"],
    "4631": ["Antiguo", "Azul Pampa", "Caspala", "Chilcar", "Chorcan", "Coctaca", "Cortaderas", "Doglonzo", "Palca De Aparzo", "Potrerillo", "Ramada", "Rodero", "Ronque", "Santa Ana", "Soledad", "Tablon", "Toro Muerto", "Trancas", "Valle Colorado", "Varas", "Vizacachal"],
    "4632": ["Antumpa", "Casayock", "Casilla", "Casillas", "Chaupi Rodero", "Hipolito Yrigoyen Est Iturbe", "La Cueva", "Miyuyoc", "Peñas Blancas", "Pisungo", "Pueblo Viejo"],
    "4633": ["Abra De Araguyoc", "Astillero", "Cancillar", "Casa Grande", "Chacar", "Chañar", "Chiyayoc", "Colanzuli", "Colorado", "El Tapial", "Finca Santiago", "Iruya", "La Huerta", "La Mesada Chica", "La Mesada Grande", "Las Cañas", "Las Higueras", "Matancillas", "Pinal", "Pueblo Viejo", "Rodeo Colorado", "San Antonio", "San Antonio De Iruya", "San Isidro De Iruya", "San Juan", "San Pedro De Iruya", "Tipayoc", "Titicoite", "Tres Morros", "Uchogol", "Uchuyoc", "Valle Delgado", "Villa Alem", "Volcan Higuera", "Volcan Higueras"],
    "4634": ["Abralaite", "Casa Grande", "El Aguilar", "Esquinas Blancas", "Kilometro 1321", "La Veta", "Quera", "Rio Grande", "Tejadas", "Tres Cruces", "Veta Mina Aguilar", "Vicuñayoc", "Yacoraite"],
    "4640": ["Abra Pampa", "Agua Chica", "Agua De Castilla", "Catari", "Cerro Chico", "Chaupi Rodero", "Chorojra", "Chulin O Inca Nueva", "Cochagate", "Estacion Zootecnica", "Guemes", "La Banda", "La Falda", "Lagunillas", "Lumara", "Mira Flores", "Miraflores De La Candelaria", "Potrero", "Potrero De La Puna", "Puerta Potrero", "Quebraleña", "Ramallo", "Rontuyoc", "Rumi Cruz", "San Jose De Miraflores", "Santuario", "Sayate", "Sorcuyo", "Tabladitas", "Turu Tari"],
    "4641": ["Abdon Castro Tolay", "Agua Caliente De La Puna", "Barrancas", "Casabindo", "Cauchari", "Cerro Agua Caliente", "Cochinoca", "Doncellas", "El Porvenir", "El Potrero De La Puna", "Huancar", "Kilometro 1369", "Muñayoc", "Olaroz Chico", "Olaroz Grande", "Pastos Chicos", "Queta", "Quichagua", "Rachaite", "Rinconadillas", "San Francisco De Alfarcito", "San Juan De Quillagues", "Santa Ana De La Puna", "Sijes", "Susques", "Tambillos", "Tanques", "Teuco", "Turilari", "Turu Tari", "Tusaquillas"],
    "4643": ["Antiguyos", "Arbolito Nuevo", "Carahuasi", "Casa Colorada", "Cerro Redondo", "Cienaga Grande", "Cienego Grande", "Cincel", "Coranzuli", "Coyaguaima", "Cusi Cusi", "El Toro", "Farillon", "Granadas", "Guayatayoc", "La Veta", "Loma Blanca", "Mina Ajedrez", "Mina Pan De Azucar", "Mina Pirquitas", "Miniaio", "Olacapato", "Orosmayo", "Paicone", "Pairique Chico", "Pairique Grande", "Pozuelo", "Quera", "Rinconada", "Salitre", "San Jose De La Rinconada", "San Juan", "Soysolayte", "Tio Mayo", "Tocol", "Villa Coranzuli"],
    "4644": ["Bacoya", "Cangrejillos", "Cangrejos", "Caracara", "Chocoite", "El Condor", "Escaya", "Kilometro 1397", "Llameria", "Llulluchayoc", "Mayilte", "Mayinte", "Mina Belgica", "Mina Pulpera", "Mina San Francisco", "Mina Sol De Mayo", "Mocoraite", "Molino", "Mollar", "Puesto Del Marquez", "Pumahuasi", "Punta De Agua", "Punta Del Agua", "Quenti Taco", "Redonda", "Rio Colorado", "Toroyoc", "Tuite", "Vallecito", "Vizcarra", "Yavi Chico"],
    "4648": ["Barrio La Union", "Toba"],
    "4650": ["Abra De Peñas", "Barrios", "Corralito", "El Monumento", "La Cienaga", "La Intermedia", "La Quiaca", "Mulli Punco", "Sansana", "Tafna"],
    "4651": ["Acoyte", "Agua De Castilla", "Angosto Pescado", "Baritu", "Cajas", "Capilla Fuerte", "Carayoc", "Casti", "Condado", "Cuesta Azul", "El Aguilar", "Hornillos", "Huerta", "Inticancho", "La Falda", "Lipeo", "Lizoite", "Mecoyita", "Meson", "Nazareno", "Pal Tolco", "Papa Chacra", "Pascalla", "Piscuno", "Poscaya", "Pucara", "Puesto", "Punca Viscana", "Punco Viscana", "Rodeo", "Rodeo Pampa", "San Felipe", "San Francisco", "San Jose", "San Juan De Oro", "San Leon", "San Marcos", "Santa Cruz", "Santa Victoria Oeste", "Soledad", "Soledani", "Suripujio", "Trigo Huayco", "Trusuca", "Tuctuca", "Viscachani", "Yavi"],
    "4653": ["Casira", "Cerrillos", "Cerrito", "Cieneguillas", "Guayatayoc", "Hornillos", "Huallatayoc", "Ornillo", "Pasajes", "Pasto Pampa", "Potrero", "Puesto Chico", "Puesto Grande", "Rodeo Chico", "Tio Mayo", "Toquero", "Yoscaba"],
    "4655": ["Cabreria", "Calahoyo", "Canchuela", "Corral Blanco", "El Angosto", "La Cruz", "Merco", "Minas Azules", "Mires", "Morro", "Oratorio", "Oros San Juan", "Peña Colorada", "Piscuno", "San Francisco", "San Juan", "San Juan De Oros", "San Leon", "Santa Catalina", "Timon Cruz"],
    "4700": ["Banda Varela", "Chacabuco", "El Tala", "La Aguada", "La Brea", "La Calera", "La Chacarita", "La Chacarita De Los Padres", "Las Tejas De Valle Viejo", "Las Varitas", "Lazareto", "Loma Cortada", "Payabuayca", "Peñon", "Rio Del Tala", "San Fdo Del Valle De Catamarca", "Sauce", "Villa Cubas", "Villa Parque Chacabuco"],
    "4701": ["Acostilla", "Amana", "Ancasti", "Anquincila", "Cabrera", "Calacio", "Calera", "Candelaria", "Casa Armada", "Casa Vieja", "Cañada De Ipizca", "Cañada De Paez", "Concepcion", "Corral De Piedra", "Corral Viejo", "El Arbolito", "El Barreal", "El Cercado", "El Cevilarcito", "El Chañaral", "El Chorro", "El Mojon", "El Mollar", "El Potrero De Los Cordoba", "El Pozo", "El Sauce", "El Sauce Ipizca", "El Taco", "El Totoral", "El Vallecito", "El Zapallar", "Estancia Vieja", "Guanaco", "Higuera Del Alumbre", "Ipizca", "La Aguadita", "La Barrosa", "La Bebida", "La Estancia", "La Estancita", "La Falda", "La Higuerita", "La Mesada", "Las Barrancas", "Las Barrancas Casa Armada", "Las Chacras", "Las Tapias", "Las Tunas", "Loma Sola", "Los Bulacio", "Los Cisternas", "Los Huaycos", "Los Morteros", "Los Piquillines", "Los Rastrojos", "Ojo De Agua", "Peñaflor", "Potrero", "Quebracho", "Rio Los Molinos", "San Antonio", "San Jose", "Santa Gertrudis", "Sauce Huacho", "Soledad", "Tacana", "Taco De Abajo", "Totoral"],
    "4705": ["Aguadita", "Antapoca", "Antofagasta De La Sierra", "Balsa", "Cumbre Del Laudo", "Gentile", "Huaycama", "Mina Inca Huasi", "Mota Botello", "Pozo Del Mistol", "Rosario Del Sumalao", "Salar Del Hombre Muerto", "Santa Cruz", "Sumalao", "Tacahuasi", "Toro Muerto", "Vega Curutu", "Vega Tamberia"],
    "4707": ["Chañarcito", "El Bañado", "El Desmonte", "El Hueco", "Estanque", "La Falda De San Antonio", "La Tercena", "Las Esquinas", "Pampa", "Polcos", "Rosario Del Sumalao", "San Antonio De P Blanca", "San Antonio Fray M Esquiu", "San Isidro", "Santa Rosa", "Sebila", "Tala", "Tiorco", "Tres Puentes", "Villa Dolores", "Villa Macedo", "Zanja"],
    "4709": ["San Jose De Piedra Blanca"],
    "4711": ["Ambato", "Casa Viejas", "Chuchucaruana", "Collagasta", "Colpes", "Condor Huasi", "El Arbol Solo", "El Bolson", "El Chorro", "El Nogal", "El Parque", "El Pie De La Cuesta", "El Polear", "El Potrerillo", "El Pucara", "El Rodeo Grande", "El Tabique", "Huaycama", "Humaya", "Isla Larga", "La Aguada", "La Carrera", "La Puerta", "Las Chacritas", "Las Pampitas", "Los Castillos", "Los Guindos", "Los Morteritos", "Los Narvaez", "Los Navarros", "Los Talas", "Los Varela", "Pomancillo", "Sierra Brava", "Singuil"],
    "4713": ["Ocho Vados", "Villa Las Pirquitas"],
    "4715": ["Agua Verde", "Bella Vista", "Biscotal", "Chamorro", "Chavarria", "Corralita", "El Atoyal", "El Biscote", "El Molinito", "El Realito", "El Rodeo", "El Tala", "Faldeo", "Galpon", "La Aguita", "La Cañada", "La Piedra", "La Salvia", "Lampaso", "Las Aguitas", "Las Barras", "Las Burras", "Las Cuchillas", "Las Juntas", "Las Lajas", "Las Piedras Blancas", "Los Loros", "Los Molles", "Molle Quemado", "Villa Quintin Ahumada"],
    "4716": ["Amadores", "Cerviño", "El Cevil", "El Garabato", "El Retiro", "La Bajada", "La Banda", "Monte Potrero", "Palo Labrado", "Portezuelo", "Rafael Castillo", "Salcedo", "Yocan"],
    "4718": ["Barro Negro", "Bastidor", "Chiflon", "El Bastidor", "El Totoral", "La Esquina", "La Falda", "La Merced", "Los Galpones", "Posta", "Santa Ana", "Santa Barbara", "Superi", "Talaguada"],
    "4719": ["Balcosna", "Balcosna De Afuera", "El Chamico", "El Ciflon", "El Contador", "El Rosario", "La Higuera", "La Ovejeria", "Las Lajas", "San Antonio De Paclin", "Tierra Verde", "Villa Collantes"],
    "4722": ["El Duraznillo", "Huacra", "La Viña", "La Viña De Abajo", "Las Huertas", "Las Tranquitas", "Los Ovejeros", "Los Pintados", "Sauce Mayo", "Sumampa"],
    "4723": ["Alijilan", "Almigaucho", "Alta Gracia", "Amancala", "Ampolla", "Bañado De Ovanta", "Cachi", "Caridad", "Dos Pocitos", "Dos Troncos", "El Carmen", "El Desmonte", "El Potrero", "El Rodeito", "El Saucecito", "La Aguada", "La Bajada", "La Calera", "La Victoria", "Las Cayas", "Las Tunas", "Los Altos", "Los Bastidores", "Los Estantes", "Los Molles", "Los Ortices", "Los Pocitos", "Los Troncos", "Los Zanjones", "Manantiales", "Mistol Ancho", "Monte Redondo", "Naipa", "Ovanta", "Pampa Chacra", "Pozo Del Algarrobo", "Pozo Del Campo", "Puerta Grande", "Puesto Del Medio", "Quebrachal", "Quebrachos Blancos", "Quimilpa", "Salauca", "San Luis", "San Pedro", "Santos Lugares", "Yaquicho"],
    "4724": ["Agua Colorada", "Colonia Nueva Coneta", "Coneta", "El Bañado", "La Estrella", "La Paraguaya", "Los Angeles", "Los Bazan", "Los Pinos", "Los Puestos", "Miraflores", "San Lorenzo", "Sisiguasi"],
    "4726": ["Capayan", "Colonia Del Valle", "Concepcion", "El Carrizal", "El Milagro", "Huillapima", "La Cañada", "Lampasillo", "Las Palmas", "Los Chañaritos", "San Pablo", "San Pedro Capayan"],
    "4728": ["Chumbicha", "Kilometro 128", "Las Latillas", "San Geronimo", "Sebila", "Trampasacha"],
    "4740": ["Agua Salada", "Agua Verde", "Algarrobal", "Andalgala", "Arima", "Aserradero El Pilcio", "Chilca", "Distrito Espinillo", "El Colegio", "El Lindero", "El Molle", "Huasan", "Huaschaschi", "Julumao", "La Aguada", "La Banda", "Las Minas", "Malli 1", "Malli 2", "Minas Capillitas", "Pilciao", "Rodeo Grande"],
    "4741": ["Agua De Las Palomas", "Amanao", "Carapunco", "Casa De Piedra", "Chaquiago", "Choya", "El Carrizal", "El Zapallar", "Huaco", "La Laguna", "Villa Coronel Arroyo"],
    "4743": ["Aconquija", "Alto De La Junta", "Buena Vista", "El Alamito", "El Arbolito", "El Espinillo", "El Potrero", "El Suncho", "La Alumbrera", "Las Estancias", "Las Pampitas"],
    "4750": ["Agua Colorada", "Agua Del Campo", "Ampujaco", "Angostura", "Belen", "Cachuan", "Casa Grande", "Chiquerito", "Chucolay", "Cortadera", "Cueva Blanca", "Duraznillo", "El Medio", "El Molino", "El Portezuelo", "Huaco", "La Banda", "La Barranca Larga", "La Costa", "La Puntilla", "La Represa", "La Totora", "Las Latillas", "Londres Este", "Luna Aguada", "Nacimiento", "Nacimientos De Abajo", "Ojo De Agua", "Ojo De La Cortadera", "Palo Blanco", "Pampa Cienaga", "Potrerito", "Pozuelos", "Puerto Blanco", "Puerto Chipi", "Puerto De La Pampa", "Puerto Potrero", "Rincon Grande", "Rumimonion", "San Antonio", "San Buenaventura", "Sebila", "Shincal", "Talamayo", "Viscote", "Zarcito", "Zarza"],
    "4751": ["Agua De Dionisio", "Aguas Calientes", "Alto El Bolson", "Asampay", "Barranca Larga", "Cachijan", "Carrizal", "Carrizal De Abajo", "Carrizal De La Costa", "Chañaryaco", "Condor Huasi De Belen", "Corral Quemado", "Cotagua", "Culampaja", "El Cajon", "El Campillo", "El Carrizal", "El Durazno", "El Eje", "El Tio", "El Tolar", "Farallon Negro", "Hualfin", "Huasayaco", "Huasi Cienaga", "Jacipunco", "La Aguada", "La Capellania", "La Cañada", "La Cienaga", "La Cuesta", "La Estancia", "La Puerta De San Jose", "La Quebrada", "La Toma", "La Viña", "Laguna Blanca", "Laguna Colorada", "Las Barrancas", "Las Cuevas", "Las Juntas", "Las Manzas", "Loconte", "Los Nacimientos", "Los Pozuelos", "Minas Agua Tapada", "Nacimientos De Arriba", "Nacimientos De San Antonio", "Nacimientos Del Bolson", "Papa Chacra", "Pozo De Piedra", "Puerta De Corral Quemado", "Rodeo Gervan", "San Fernando", "Vicuña Pampa", "Villa Vil"],
    "4753": ["Corralito", "Durazno", "El Tambillo", "La Ramada", "Las Bayas", "Londres", "Londres Oeste", "Los Colorados", "Piedra Larga"],
    "5000": ["Cordoba"],
    "5101": ["Bajo Chico Bajo Grande", "Bajo De Fernandez", "Bajo Grande", "Camino A Punta Del Agua", "Capilla De Cosme", "Capilla De Los Remedios", "Cañada De Cuevas", "Colonia Cosme Sud", "Colonia Tirolesa", "El Gateado", "El Quebrachal", "El Quebracho", "Escuela De Artilleria", "General Las Heras", "La Cañada", "La Cocha", "La Puerta", "Lagunilla", "Las Cañas", "Las Chacras Ruta 111 Km 14", "Las Heras", "Las Playas Lozada", "Los Cedros", "Los Cerrillos", "Los Olivares", "Lozada", "Malagueño", "Mi Valle", "Nueva Andalucia", "Paso Del Sauce", "Ruta 111 Kilometro 14", "Tercer Cuerpo Del Ejercito", "Villa Corazon De Maria", "Villa Esquiu", "Villa Parque Santa Ana", "Yocsina"],
    "5105": ["La Redencion", "La Reduccion", "Villa Allende"],
    "5107": ["Agua De Oro", "Animi", "Canteras El Manzano", "Canteras El Sauce", "El Algodonal", "El Manzano", "El Pueblito", "El Talar", "Kilometro 25", "La Quebrada", "Las Vertientes De La Granja", "Los Cigarrales", "Mendiolaza", "San Cristobal", "Valle Del Sol", "Villa Cerro Azul", "Villa Las Mercedes"],
    "5109": ["Cabana", "El Quebrachito", "Las Cusenadas", "Las Encadenadas", "Unquillo", "Villa Diaz", "Villa Leonor", "Villa Tortosa"],
    "5111": ["Barrio Loza", "Candonga", "La Estancita", "Pajas Blancas", "Rio Ceballos", "Villa Los Altos", "Villa San Miguel", "Ñu Pora"],
    "5113": ["Salsipuedes"],
    "5115": ["La Granja", "Valle Verde"],
    "5117": ["Ascochinga", "La Pampa", "La Paz", "Puesto Del Medio", "San Jorge", "San Miguel"],
    "5119": ["Alto De Fierro", "Alto Del Durazno", "Bouwer", "Cnia Hogar Velez Sarsfield", "Duarte Quiros", "La Lagunilla", "La Porfia", "Monte Grande Rafael Garcia", "Monte Ralo", "Rafael Garcia", "San Antonio Norte"],
    "5121": ["Alto Alegre", "Buena Vista", "Despeñaderos", "San Antonio"],
    "5123": ["Barrio Dean Funes", "El Ochenta", "Haras Santa Martha", "Kilometro 25 La Carbonada", "Kilometro 679", "Kilometro 680 Ruta 9", "Kilometro 692", "Toledo", "Villa Mirea", "Villa Posse"],
    "5125": ["Blas De Rosales", "Capilla De Dolores", "Colonia Sagrada Familia", "Constitucion", "Higuerillas", "Kilometro 658", "Kilometro 691", "Kilometro 711", "La Celina", "Los Chañaritos", "Los Pantanillos", "Los Vazquez", "Malvinas Argentinas", "Media Luna", "Mi Granja", "Monte Cristo", "Oratorio De Peralta", "Piquillin", "Pozo De La Loma", "Pozo De Las Yeguas", "Ruta 19 Kilometro 317", "Santiago Temple", "Tejeda"],
    "5127": ["Charcas Norte", "Las Cabras", "Los Guindos", "Los Mansillas", "Pedro E Vivas", "Rio Primero", "Tala Sud"],
    "5129": ["Capilla La Esperanza", "Comechingones", "El Crispin", "Espinillo", "Isla Del Cerro", "Isla Larga", "La Buena Parada", "La Estrella", "Las Acacias", "Las Piguas", "Monte Del Rosario", "Punta Del Agua", "Timon Cruz"],
    "5131": ["Cañada San Antonio", "Colonia Holandesa", "Dolores Nuñez Del Prado", "El Alcalde", "El Espinillo", "Esperanza", "Espinillo Nuñez Del Prado", "Esquina", "Estacion Colonia Tirolesa", "Estancia El Carmen", "Estancia Las Cañas", "Higuerias", "La Tuna Tinoco", "Las Higuerillas", "Nuñez Del Prado", "Pueblo Pianelli", "Puesto De Afuera", "Puesto De La Oveja", "Quebrachos", "Rangel", "Santa Elena", "Tala Norte", "Tinoco"],
    "5133": ["Colonia El Fortin", "El Espinal", "La Cienaga", "Los Alvarez", "Los Chañares", "Pozo De La Esquina", "Santa Rosa De Rio Primero", "Villa Santa Rosa"],
    "5135": ["Buey Muerto", "Castellanos", "Cañada Ancha Santa Rosa", "Colonia Las Cuatro Esquinas", "Corral De Gomez", "Diego De Rojas", "El Carrizal", "La Quinta", "Las Averias", "Las Gramillas", "Monte De Toro Pujio", "Pozo La Piedra", "Tordilla Norte"],
    "5137": ["Balneario Guglieri", "Colonia Cañadon", "Colonia La Argentina", "Colonia Yareta", "Costa Del Castaño", "El Bagual", "El Tostado", "Kilometro 294", "Kilometro 316", "La Mostaza", "La Para", "La Puerta", "Las Hileras", "Las Saladas", "Lomas Del Trozo", "Los Aviles", "Los Castaños", "Los Cerros", "Los Miguelitos", "Plaza De Mercedes", "Pozo De Los Troncos", "San Ramon", "Soledad", "Villa Fontana", "Villa Mar Chiquita"],
    "5139": ["Campo Coyunda", "Colonia Toro Pujio", "Corral De Gomez", "Kilometro 271", "La Primavera", "Marull", "Playa Grande", "Primavera", "Puente Rio Plujunta", "San Rafael", "Toro Pujio"],
    "5141": ["Balnearia", "Jeronimo Cortes", "Plujunta"],
    "5143": ["Barrio Muller", "Miramar", "Vacas Blancas"],
    "5144": ["Recreo Victoria"],
    "5145": ["Alto De Castillo", "Augusto Vandersande", "El Carmen Guiñazu", "El Chingolo", "Est Juarez Celman", "Estacion General Paz", "Juarez Celman", "Kilometro 730", "Los Pocitos", "Paso Castellanos", "Pozo Del Tigre"],
    "5149": ["Campamento Minnetti", "Campo Bourdichon", "Cassaffousth Estacion Fcgb", "Dique San Roque", "Dumesnil", "El Tomillo", "El Zaino", "Kilometro 608", "Saldan", "San Roque", "Tristan Narvaja"],
    "5151": ["Calera Central", "Canteras La Calera", "Casa Bamba", "El Diquecito", "El Pastor", "El Payador", "General Ortiz De Ocampo", "La Calera"],
    "5152": ["Estancia Vieja", "Villa Carlos Paz", "Villa Del Lago", "Villa Parque Siquiman", "Villa Santa Cruz Del Lago"],
    "5153": ["Comechingones", "Copina", "Cuesta Blanca", "Las Ensenadas", "Los Huesos", "Mayu Sumaj", "Mesillas", "Pampa De Achala", "Puesto Guzman", "San Antonio De Arredondo", "Tala Huasi", "Villa Costa Azul", "Villa Cuesta Blanca", "Villa Gracia", "Villa Independencia", "Villa Rio Icho Cruz", "Ycho Cruz Sierras"],
    "5155": ["Agua De Tala", "Angostura", "Batan", "Buen Retiro", "Cabalango", "Casa Nueva", "Colonia Banco Pcia Bs As", "Cuchilla Nevada", "Dos Rios", "El Durazno", "El Peruel", "El Pilcado", "El Potrero", "El Vergel", "Estancia Dos Rios", "Guasta", "La Cañada", "Los Gigantes", "Mallin", "Tanti", "Tanti Lomas", "Tanti Nuevo", "Villa Flor Serrana"],
    "5156": ["Villa Suiza Argentina"],
    "5158": ["Bialet Masse", "Las Casitas", "Los Puentes", "Parque Siquiman"],
    "5162": ["Casa Grande", "Rincon Casa Grande"],
    "5164": ["Domingo Funes", "San Buenaventura", "Santa Maria De Punilla", "Villa Bustos", "Villa Caeiro"],
    "5165": ["Hospital Flia Domingo Funes"],
    "5166": ["Cosquin", "El Perchel", "Kilometro 592", "Molinari", "Pampa De Olaen", "San Jose", "Santa Rosa", "Villa Ahora"],
    "5168": ["Dique Las Vaquerias", "Irigoyen", "Kilometro 579", "La Cantera", "La Usina", "Los Helechos", "Piedra Grande", "Valle Hermoso"],
    "5172": ["El Callejon", "El Cuadrado", "El Puente", "El Vallecito", "Gruta De San Antonio", "La Falda", "La Quebrada", "Las Playas", "Piedras Grandes", "Rio Grande"],
    "5174": ["Alto De San Pedro", "Huerta Grande", "Piedra Movediza", "Piedras Blancas", "Santa Rosa Huerta Grande"],
    "5175": ["Casa Serrana Huerta Grande"],
    "5176": ["Villa Giardino"],
    "5178": ["Cascadas", "Cruz Chica", "El Pingo", "La Cumbre"],
    "5182": ["Alto Castro", "Dolores San Esteban", "El Baldecito", "El Vado", "Las Pampillas", "Los Cocos", "Los Mogotes", "San Esteban", "San Ignacio", "Sauce Arriba"],
    "5184": ["Cajon Del Rio", "Capilla Del Monte", "Cañadon De Los Mogotes", "Corimayo", "El Aguila Blanca", "El Zapato", "La Piedra Movediza", "Las Gemelas", "Las Vaquerias", "Los Terrones", "Ongamira", "Punilla", "Quebrada De Nona", "Suncho Huico", "Uritorco"],
    "5186": ["Alta Gracia", "Canteras Alta Gracia", "Falda De Cañete", "La Isla", "La Isolina", "La Paisanita", "Las Higueritas", "Potrero De Tutzer", "Villa Carlos Pellegrini", "Villa Del Prado", "Villa Los Aromos", "Villa Santa Maria"],
    "5187": ["Bosque Alegre", "Estancia La Punta Del Agua", "Falda Del Carmen", "Golpe De Agua", "La Granadilla", "Los Paraisos", "San Clemente", "San Nicolas"],
    "5189": ["Anisacate", "Bajo Chico", "Bajo Del Carmen", "Colonia San Ignacio", "Dique Chico", "Dos Arroyos", "Fabrica Militar", "Falda De Los Reartes", "Jose De La Quintana", "La Betania", "La Rancherita", "La Serranita", "Los Algarrobos", "Los Molinos", "Obregon", "Potrero De Funes", "Potrero De Garay", "Puesto Mulita", "Rio Los Molinos", "Santa Rita", "Sierras Morenas", "Solar Los Molinos", "Tercera", "Valle Anisacate", "Villa Ciudad De America", "Villa Ciudad Pque Los Reartes", "Villa El Descanso", "Villa La Bolsa", "Villa San Isidro", "Villa Satyta"],
    "5191": ["Calmayo", "Cerro Blanco", "Potrero De Lujan", "San Agustin", "Soconcho"],
    "5192": ["Dique Los Molinos"],
    "5194": ["Athos Pampa", "La Cumbrecita", "Los Reartes", "Villa Alpina", "Villa Berna", "Villa General Belgrano"],
    "5196": ["Arroyo Seco", "Atumi Pampa", "Carahuasi", "Cañada Del Durazno", "Colonia Alemana", "Colonia La Calle", "El Portezuelo", "El Sauce", "La Choza", "Santa Rosa De Calamuchita", "Sarlaco"],
    "5197": ["El Carmen", "El Parador De La Montaña", "Rincon De Luna", "Rio Del Durazno", "Santa Monica", "Villa Yacanto", "Vista Alegre"],
    "5199": ["Amboy", "Cañada De Las Chacras", "Las Higueritas", "Las Sierritas", "Mar Azul", "Rio Grande Amboy", "San Ignacio", "San Roque", "Villa Amancay", "Villa El Corcovado", "Villa El Torreon", "Villa Lago Azul", "Villa San Javier"],
    "5200": ["Canteras Kilometro 428", "Cañada Del Simbol", "Cerro De La Cruz", "Corito", "Dean Funes", "El Portillo", "Ingeniero Bertini", "Kilometro 430", "Kilometro 832", "La Isabela", "La Mesada", "Las Pencas", "Los Puestitos", "Puesto De Cerro", "Puesto De Los Rodriguez", "Sajon", "San Vicente", "Santa Rita", "Sauce Chiquito", "Sauce Punco", "Toro Muerto", "Yerba Buena"],
    "5201": ["Calasuya", "Chuña Huasi", "Copacabana", "El Carrizal Chuñahuasi", "El Pertigo", "El Rodeito", "El Tala", "Ischilin", "La Batalla", "La Cañada Santa Cruz", "La Colonia", "La Higuerita", "La Posta Chuñaguas", "La Zanja", "Las Aguaditas", "Las Cañas", "Las Crucecitas", "Las Palmas", "Las Palomitas", "Lobera", "Los Brinzes", "Los Cejas", "Los Coquitos", "Los Piquillines", "Los Ruices", "San Bernardo", "San Pedro De Toyos", "Santa Cruz", "Todos Los Santos", "Totrilla", "Villa Colimba"],
    "5203": ["Alto De Flores", "El Ojo De Agua", "El Paso", "Espinillo", "Iti Huasi", "Las Juntas", "Majadilla", "Villa Tulumba"],
    "5205": ["Alto Verde", "Camarones", "El Cerrito", "El Desmonte", "El Rosario", "La Laguna", "San Pedro Norte", "Sevilla"],
    "5209": ["Aguada Del Monte", "Aguadita", "Bordo De Los Espinosa", "Cachi Yaco", "Campo Alegre", "Caspichuma", "Caspicuchana", "Graciela", "Invernada", "Jarillas", "Jume", "La Esperanza", "La Quinta", "La Totorilla", "Las Jarillas", "Loma Blanca", "Lomitas", "Los Bordos", "Los Cerrillos", "Majadilla", "Manantiales", "Movado", "Navarro", "Pozo Del Tigre", "Pozo Nuevo", "Puesto Nuevo", "Rodeito", "San Francisco Del Chañar", "San Luis", "San Pablo", "Santa Ana", "Santa Maria De Sobremonte", "Santo Domingo", "Socorro"],
    "5211": ["La Aguada", "Macha"],
    "5212": ["Agua Pintada", "Avellaneda", "Barranca Yaco", "Cantera Los Vieras", "Cruz Mojada", "El Coro", "El Divisadero", "El Estanque", "El Ialita", "El Talita", "El Tambero", "Estancia Gorosito", "Juan Garcia", "Kilometro 784", "Kilometro 807", "Kilometro 827", "La Aguada", "La Chacra", "La Estacada", "La Majada", "La Selva", "La Tuna", "Las Delicias", "Las Lomitas", "Las Manzanas", "Las Piedras Anchas", "Las Sierras", "Los Chañares", "Los Pedernales", "Los Pozos", "Molinos", "Rio De Las Manzanas", "San Carlos", "San Miguel", "Sarmiento", "Villa Gutierrez"],
    "5214": ["El Bañado", "El Molino", "El Veinticinco", "Isla De San Antonio", "Kilometro 859", "Kilometro 865", "Kilometro 881", "La Barranca", "La Botija", "La Florida", "La Ruda", "Las Chacras", "Las Toscas", "Los Cadillos", "Los Morteros", "Los Socabones", "Orcosuni", "Puesto De Arriba", "Quilino", "Villa Quilino"],
    "5216": ["Acollarado", "Agua Hedionda", "Arbol Blanco", "El Tuscal", "Kilometro 907", "Kilometro 931", "Las Cañas", "Lucio V Mansilla", "San Jose", "San Jose De Las Salinas", "Totoralejos", "Tuscal"],
    "5218": ["Cañada De Mayo", "Chuña", "El Chanchito", "El Jume", "El Mojoncito", "El Paraiso", "El Puesto Los Cabrera", "El Quebracho", "El Ranchito", "Huascha", "Jaime Peter", "Kilometro 450", "La Aura", "La Calera", "La Cañada Angosta", "Las Canteras", "Las Tuscas", "Los Tartagos", "Puesto De Batalla"],
    "5220": ["Abburra", "Belen", "Columbo", "El Molino", "El Reymundo", "Estacion Caroya", "Jesus Maria", "Kilometro 745", "La Cotita", "La Virginia", "Las Astillas", "Los Callejones", "Los Chañares", "Los Dos Rios", "Los Duraznos", "Nintes", "Ojo De Agua", "San Isidro", "San Pablo", "Santo Tomas", "Sinsacate", "Villa Maria"],
    "5221": ["Agua De Las Piedras", "Aguasacha", "Algarrobo", "Bajo De Olmos", "Cabindo", "Campo Alegre", "Campo La Piedra", "Candelaria Sud", "Cañada De Jume", "Cañada De Mateo", "Cañada De Rio Pinto", "Cañadas Hondas", "Cerro Negro", "Colonia Vicente Aguero", "Corral De Barranca", "Cruz Del Quemado", "Doctor Nicasio Salas Oroño", "El Algarrobo", "Espinillo", "La Porteña", "Las Palmitas", "Los Cometierra", "Los Miquiles", "Los Quebrachitos", "Miquilos", "Mula Muerta", "Pozo Conca", "Pozo Correa", "Quiscasacate", "Rio Chico", "Rio De Los Sauces", "Rio De Los Talas", "Rio Pinto", "San Lorenzo", "San Pellegrino", "Santa Catalina", "Santa Sabina", "Santa Teresa", "Villa Albertina", "Villa Cerro Negro"],
    "5223": ["Caroya", "Colonia Caroya", "Tronco Pozo"],
    "5225": ["Atahona", "Campo Ramallo", "Isla Verde", "Las Bandurrias Norte", "Los Algarrobitos", "Los Pozos", "Miguelito", "Obispo Trejo", "Pozo Del Moro", "Puesto De Pucheta", "Ramallo"],
    "5227": ["Cañada Honda", "La Posta", "Las Palmitas", "Maquinista Gallini", "Puesto De Fierro", "San Roque", "San Salvador"],
    "5229": ["Cabeza De Buey", "Campo Alvarez", "Cañada De Luque", "Chalacea", "Desvio Chalacea", "El Bosque", "Estancia Bottaro", "Estancia El Taco", "Estancia Las Mercedes", "Estancia Las Rosas", "Kilometro 364", "La Dora", "Los Mistoles", "Santa Lucia", "Tintizaco", "Totoral"],
    "5231": ["Bajo Hondo", "Camoati", "Campo Grande", "Capilla De Siton", "El Durazno", "El Guanaco", "El Rincon", "El Vence", "Encrucijada", "La Cañada", "La Esperanza", "La Maza", "La Palma", "La Penca", "La Providencia", "La Victoria", "Las Aromas", "Las Arrias", "Las Masitas", "Las Palmas", "Providencia", "San Roque Las Arrias", "Sebastian Elcano"],
    "5233": ["El Pozo", "El Vismal", "El Zapallar", "La Rinconada", "Los Tajamares", "Pedania Candelaria Sud", "Puesto De Castro", "Puesto De Luna", "Tajamares", "Villa Rosario Del Saladillo"],
    "5235": ["Est Candelaria Norte"],
    "5236": ["Campo De Las Piedras", "Casas Viejas", "El Creston De Piedra", "El Pedacito", "El Talita Villa Gral Mitre", "Haras San Antonio", "Las Bandurrias", "Puesto Del Rosario", "San Antonio De Bella Vista", "Santa Maria", "Villa Del Totoral", "Villa General Mitre"],
    "5238": ["Canteras Los Morales", "Kilometro 394", "Las Peñas"],
    "5242": ["Chacras Viejas", "Puesto San Jose", "San Jose", "Simbolar"],
    "5243": ["Agua Del Tala"],
    "5244": ["Beuce", "Caminiaga", "Cañada Del Tala", "Cerro Colorado", "Chacras Del Sauce", "Chipitin", "Durazno", "El Bañado", "El Guindo", "El Pantano", "El Perchel", "El Sebil", "Estancia El Nacional", "Guallascate", "La Costa", "La Higuerita", "La Plaza", "La Toma", "Laguna Brava", "Laguna De Gomez", "Las Horquetas", "Las Lomitas", "Las Quintas", "Loma De Piedra", "Los Alamos", "Los Pozos", "Miraflores", "Pisco Huasi", "Pozo Solo", "Puesto Viejo", "San Gabriel", "San Jose De La Dormida"],
    "5246": ["Barreto", "Carnero Yaco", "Casas Vejas", "Chañar Viejo", "Chile Corral Al Aguada", "Chilli Corral", "Churqui Cañada", "Corral Viejo", "El Pantanillo", "El Rodeo", "La Piedra Blanca", "Ladera Yacus", "Las Cañas", "Las Gramillas", "Las Trancas", "Lo Machado", "Los Cajones", "Los Cerrillos", "Los Cocos", "Los Quebrachos", "Los Troncos", "Paso Del Silverio", "Pozo De Juancho", "Rayo Cortado", "Rio Pedro", "Rojas", "Santa Elena", "Vanguardia"],
    "5248": ["Agua De Oro", "Balbuena", "Bañado Del Fuerte", "Caña Cruz", "El Bañado", "El Coro", "El Gabino", "El Jordan", "El Laurel", "El Prado", "El Silverio", "Eufrasio Loza", "La Barranca", "La Pintada", "Las Cardas", "Pocito Del Campo", "San Ignacio", "Santa Catalina", "Santanilla", "Villa De Maria", "Yanacato"],
    "5249": ["Buena Vista", "Cañada De Coria", "Corral Del Rey", "El Algarrobal", "El Barrial", "El Durazno", "El Gallego", "El Mangrullo", "El Progreso", "El Puesto", "El Quebracho", "El Rodeo", "El Simbol", "El Tule", "Estancia Patiño", "Gutemberg", "La Banda", "La Chicharra", "La Costa", "La Cruz", "La Estancia", "La Quintana", "La Rinconada Candelaria", "La Soledad", "Las Chacras", "Las Cortaderas", "Las Flores", "Las Mercedes", "Los Hoyos", "Los Justes", "Los Pocitos", "Los Pozos", "Pozo De Las Ollas", "Pozo De Los Arboles", "Pozo De Molina", "Pozo Del Simbol", "Puerta De Los Rios", "Puesto De Los Alamos", "Punta Del Monte", "Racedo", "Rio Dulce", "Rio San Miguel", "Rio Viejo", "San Bartolo", "San Juancito", "San Martin", "San Pedro", "San Ramon", "Santa Isabel", "Taco Pozo", "Villa Candelaria Norte"],
    "5250": ["Agua Blanca", "Antuco", "Arbolitos", "Bajo Las Piedras", "Balbuena", "Buena Vista", "Cajon", "Caleras", "Campo Rico", "Cantamampa", "Caranchi Yaco", "Carrera Vieja", "Cañada De La Cruz", "Chacras", "Chañar Yaco", "Chañares Altos", "Corral De Carcos", "Corral Del Rey", "Cortaderas", "Cuchi Corral", "El Aguila", "El Arbol De Piedra", "El Arbolito", "El Cajon", "El Cuarenta Y Nueve", "El Divisadero", "El Fuerte", "El Jume", "El Pilar", "El Porvenir", "El Puesto", "El Sauce", "El Segundo", "El Unco", "Esperanza", "Espinillo", "Fivialtos", "Horcos Tucucuna", "Inti Huasi", "Jacimampa", "Jume", "La Cañada", "La Clemira", "La Cruz", "La Primavera", "La Resbalosa", "La Rinconada", "La Soledad", "La Totorilla", "La Trampa", "La Tusca", "La Verde", "Laguna Del Suncho", "Las Aguilas", "Las Cañas", "Las Chacras", "Las Colonias", "Las Horquetas", "Las Talas", "Lescano", "Llama Pampa", "Loma Colorada", "Los Algarrobos", "Los Arbolitos", "Los Chañares", "Los Molles", "Los Pozos", "Los Remansos", "Los Sunchos", "Manfloa", "Miramonte", "Mistol Loma", "Molle Pozo", "Ojo De Agua", "Parada Kilometro 101", "Paso Reducido", "Pozo Cabado", "Pozo Del Chañar", "Pozo Del Macho", "Pozo Escondido", "Pozo Redondo", "Primavera", "Progreso De Jume", "Rey Viejo", "Rio Saladillo", "Salinas", "San Andres", "San Ignacio", "San Jorge", "San Lorenzo", "San Pedro", "Santa Ana", "Santa Elena", "Soledad", "Taco Misqui", "Tala Yacu", "Tigre Muerto", "Villa Ojo De Agua", "Wiñano", "Ylumampa"],
    "5251": ["Agua Caliente", "Agua Turbia", "Aguadita", "Ahi Veremos", "Algarrobo", "Alpapuca", "Ambargasta", "Amiman", "Ancoche", "Bajo Las Piedras", "Barrialito", "Cajon", "Campo Alegre", "Chacras", "Chañaritos", "Chilca", "Chuchi", "Corralito", "El Abra", "El Bajo", "El Cachi", "El Cerro", "El Naranjo", "El Retiro", "El Rodeo", "Gibialto", "Gramillal", "Guardia De La Esquina", "Hilumampa", "Horcos Tucucuna", "Huascan", "Jacimampa", "La Abra", "La Aguadita", "La Argentina", "La Calera", "La Capilla", "La Chilca", "La Cuesta", "La Esperanza", "La Florida", "La Isla", "La Pintada", "La Puerta", "Las Cienagas", "Las Colonias", "Las Flores", "Las Lomas", "Las Lomitas", "Las Parvas", "Las Rosas", "Lomitas", "Lomitas Blancas", "Mistoles", "Molles", "Naranjitos", "Oncan", "Palermo", "Pampa Grande", "Portezuelo", "Pozo Grande", "Puesto", "Quebrachal", "Quebrachito", "Remanso", "Retiro", "Rincon", "Rosada", "Rumi Huasi", "San Luis", "Santa Ana", "Santa Maria", "Santa Rosa", "Santo Domingo", "Santo Domingo Chico", "Simbolar", "Suri Pozo", "Villa Quebrachos", "Wiñano", "Yumampa"],
    "5253": ["Albardon", "Arbol Solo", "Belgrano", "Buena Vista", "Casa De Dios", "Cañitas", "Costa Vieja", "El Bajo", "El Mistol", "El Molle", "El Veinticinco Sumampa", "Jume", "Kenti Tacko", "La Bella Criolla", "La Colina", "La Porfia", "La Yerba", "Las Flores", "Los Paredones", "Los Quebrachos", "Medanos", "Pajaro Blanco", "Palomar", "Pozo Del Chañar", "Pozo Verde", "Punita Norte", "Punita Sud", "Rio Viejo", "San Carlos", "San Francisco", "San Javier", "San Lorenzo", "San Martin", "San Mateo", "San Nicolas", "Siempre Verde", "Sumampa", "Sumampa Viejo", "Taco Palta", "Tronco Quemado"],
    "5255": ["9 De Julio", "Amoladeras", "Baez", "Buena Esperanza", "Campo Del Cisne", "Campo Rico", "Chañares Altos", "Chilca", "Colonia Mercedes", "Coronel Fernandez", "Corral De Carcos", "Corral Del Rey", "Cuchi Corral", "El Aguila", "El Algarrobo", "El Arbol De Piedra", "El Arbolito", "El Bordito", "El Carmen", "El Diamante", "El Fuerte", "El Paraiso", "El Pilar", "El Porvenir", "El Unco", "El Viñalito", "Kilometro 301", "La Grana", "La Granada", "La Oscuridad", "La Palma", "La Pampa", "La Selva", "La Soledad", "La Trampa", "La Tusca", "Laguna Del Suncho", "Lagunitas", "Las Cañas", "Las Cruces", "Las Islas", "Las Lomitas", "Limache", "Los Arbolitos", "Los Cruces", "Los Molles", "Los Remansos", "Manchin", "Milagro", "Miramonte", "Mistol Loma", "Monte Verde", "Ojo De Agua", "Pozo Del Algarrobo", "Pozo Del Garabato", "Primavera", "Progreso De Jume", "Puesto De Arriba", "Puesto Del Medio", "Punta Del Agua", "Quenti Taco", "Rey Viejo", "San Andres", "San Isidro", "San Jorge", "San Pedro", "San Ramon", "San Ramon Quebrachos", "Santa Elena", "Sol De Julio", "Taco Pozo", "Tenti Taco"],
    "5257": ["Cardajal", "Chañar Pozo", "El Pueblito", "Ingeniero Carlos Christiernson", "La Golondrina", "La Gringa", "La Griteria", "La Pampa", "La Protegida", "La Puerta Del Monte", "Los Caños", "Manchin", "Navarro", "Oratorio", "Palo A Pique", "Paso De Oscares", "Polvaredas", "Portalis", "Pozo Del Monte", "Puerta Del Monte", "Puesto Del Medio", "Rama Paso", "Ramadita", "Rami Yacu", "Ramirez De Velazco", "Remansos", "Retiro", "Rumi Jaco", "San Nicolas", "Santa Brigida", "Santa Maria", "Santa Rosa"],
    "5258": ["Cerrito", "Kilometro 49", "Negra Muerta", "Piedra Blanca", "San Francisco", "San Ignacio P Blanca", "San Javier", "San Juan", "San Pedro Kilometro 49"],
    "5260": ["Acheral", "Agua Escondida", "Balde", "Buen Retiro", "Buey Muerto", "Campo Bello", "Campo Blanco", "Catita", "Cerro Colorado", "Cienaga", "Divisadero", "El Barreal", "El Bello", "El Cercado", "El Chañar", "El Lindero", "El Recreo", "El Salto", "Empalme San Carlos", "Jumeal", "Kilometro 955", "Kilometro 969", "Kilometro 997", "La Brea", "La Buena Estrella", "La Campana", "La Hoyada", "La Loma", "Lagunita", "Laja", "Las Cortaderitas", "Las Puertas", "Las Zanjas", "Liebre", "Los Caudillos", "Los Chañares", "Mollegasta", "Navigan", "Ollita", "Olmos", "Palo Seco", "Pampa Pozo", "Paraje Los Chañaritos", "Plumero", "Pozancones", "Pto Espinal", "Puesto De Fadel O De Lobo", "Punta Del Pozo", "Recreo", "San Rafael", "San Roque", "Sancho", "Santa Lucia", "Santo Domingo", "Tajamares", "Tinajera", "Villa Ofelia", "Villa Sotomayor", "Yapes"],
    "5261": ["Agua Del Simbol", "Alto Bello", "Alto Del Rosario", "Bañado De Divisadero", "Caballa", "Casa De La Cumbre", "Cortaderas", "El Abra", "El Arenal", "El Aybal", "El Barrial", "El Bañado", "El Cacho", "El Cerrito", "El Chañaral", "El Cienago", "El Gacho", "El Milagro", "El Mistolito", "El Moreno", "El Polear", "El Portezuelo", "El Potrero", "El Puestito", "El Puesto", "El Quebrachal", "El Saladillo", "El Saltito", "El Suncho", "El Valle", "Esquiu", "Garay", "Kilometro 38", "La Aguada", "La Antigua", "La Cañada", "La Colonia", "La Dorada", "La Florida", "La Higuerita", "La Huerta", "La Montosa", "La Peña", "La Quinta", "La Tigra", "La Valentina", "La Zanja", "Las Cortaderas", "Las Cuchillas", "Las Flores", "Las Lomitas", "Las Palomas", "Los Cadillos", "Los Mogotes", "Los Molles", "Los Pocitos", "Maria Elena", "Motegasta", "Navaguin", "Olta", "Palo Cruz", "Portillo Chico", "Puesto Sabatte", "Ramblones", "Rio De Bazanes", "Rio De Don Diego", "Rio De La Dorada", "San Lorenzo", "San Miguel", "San Nicolas", "Tacopampa"],
    "5263": ["Adolfo E Carranza", "Balde La Punta", "Balde Nuevo", "Buena Vista", "El Medano", "El Quimilo", "El Rosario", "Esperanza De Los Cerrillos", "Kilometro 99", "La Guardia", "La Horqueta", "La Libertad", "Las Peñas", "Parada Kilometro 62", "San Martin", "Telaritos"],
    "5264": ["Angelina", "Cañada", "Cerrillada", "Chañaritos", "El Retiro", "El Rosario", "El Tala", "Jesus Maria", "Kilometro 1008", "Kilometro 1017", "La Granja", "La Isla", "La Maravilla", "Maria Dora", "San Antonio", "San Antonio De La Paz", "San Antonio Viejo", "San Manuel", "Tula"],
    "5265": ["Agua Los Matos", "Baviano", "Brea", "Cañada Larga", "Chacritas", "Corralito", "Estancia", "Icaño", "La Barrosa", "La Falda", "La Parada", "Las Cuchillas Del Aybal", "Las Toscas", "Majada", "Puesto De Vera", "Rio Chico", "San Francisco", "Sauce De Los Cejas", "Sicha", "Talar", "Yerba Buena"],
    "5266": ["Chichagasta", "Ensenada", "Parana", "Pozos Cavados", "Quiros"],
    "5270": ["Bajo Lindo", "El Barreal", "El Quicho", "Iglesia Vieja", "La Batea", "Las Abras", "Las Aleras", "Los Eslabones", "Los Valdes", "Quilmes", "Serrezuela"],
    "5271": ["La Pintada", "Piedrita Blanca", "Puesto De Vera"],
    "5272": ["9 De Julio", "Comandante Leal", "El Chacho", "El Medanito", "El Moyano", "Kilometro 619", "Las Latas", "Miraflores", "Pozo Del Barrial"],
    "5274": ["Altillo Del Medio", "Balde Salado", "Cuatro Esquinas", "Dique Los Sauces", "El Consuelo", "El Fraile", "Hunquillal", "La Isla", "Los Barriacitos", "Los Barrialitos", "Milagro", "Pozo Del Medio", "San Cristobal"],
    "5275": ["Agua Colorada", "Catuna", "Colonia Ortiz De Ocampo", "Dique De Anzulon", "El Cienago", "El Verde", "Esquina Grande", "Francisco Ortiz De Ocampo", "Kilometro 682", "La Aguadita", "Las Palomas", "Los Aguirres", "Los Alanices", "Los Mistoles", "Olpas", "Torrecitas", "Villa Santa Rita"],
    "5276": ["Baldes De Pacheco", "Castro Barros", "Chañar", "El Bordo", "El Chusco", "Kilometro 645", "La Florida", "Las Vertientes", "Nepes", "Paraje Monte Grande", "Santa Rita La Zanja", "Simbolar", "Verde Olivo"],
    "5280": ["Cañada Honda", "Cruz Del Eje", "Kilometro 505", "La Carbonera", "La Toma", "Negro Huasi", "Nueva Esperanza", "Olivares San Nicolas", "Palo Cortado", "Rio De La Poblacion"],
    "5281": ["Alto De Los Quebrachos", "Barrial", "Canteras Quilpo", "El Brete", "El Simbolar", "Esquina Del Alambre", "Guanaco Muerto", "La Abra", "La Concepcion", "La Florida", "La Lilia", "La Puerta", "La Virginia", "Las Piedritas", "Las Tapias", "Los Algarrobitos", "Los Chañaritos", "Los Hormigueros", "Los Mistoles", "Media Naranja", "Palo Labrado", "Palo Parado", "Pozo Del Simbol", "Puesto Del Gallo", "San Antonio", "San Isidro", "San Jose", "San Nicolas", "Simbolar", "Tabaquillo", "Villa Los Leones"],
    "5282": ["Calabalumba", "Chacha Del Rey", "Charbonier", "El Carrizal", "El Frances", "El Rincon", "El Salto", "Escobas", "La Costa", "La Fronda", "La Gramilla", "Los Guevara", "Los Paredones", "Los Sauces", "Quebrada De Luna", "San Marcos Sierras", "San Salvador", "Santa Isabel"],
    "5284": ["Aguas De Ramon", "Barrialitos", "Bella Vista", "Cachiyullo", "Chacras", "Chacras Del Potrero", "Desaguadero", "El Caracol", "El Puesto", "Estacion Soto", "Kilometro 541", "La Laguna", "La Puerta Villa De Soto", "Las Cañadas", "Las Chacras", "Las Lomas", "Las Tinajeras", "Los Pantalles", "Mandala", "Palo Quemado", "Paloma Pozo", "Paso De Montoya", "Paso Viejo", "Pichanas", "Piedras Amontonadas", "Piedras Anchas", "Puesto El Abra", "Ramblon", "Rio Seco", "Santa Ana", "Sendas Grandes", "Tala Del Rio Seco", "Tasacuna", "Totora Guasi", "Tuclame", "Villa De Soto"],
    "5285": ["Agua De Crespin", "Bañado De Soto", "Canteras Iguazu", "Carrizal", "Casas Viejas", "El Barrial", "El Guaico", "El Rio", "Guasapampa", "La Aguada", "La Higuera", "La Mesilla", "La Playa", "Las Playas", "Las Totoritas", "Mesa De Mariano", "Piedra Blanca", "Pozo Seco", "Represa De Morales", "Rumihuasi", "Tres Arboles"],
    "5287": ["Candelaria", "Characato", "Cruz De Caña", "Majada De Santiago", "Oro Grueso", "Rara Fortuna"],
    "5289": ["Cienaga Del Coro", "El Sauce", "Ramirez", "Rumiaco", "Tosno"],
    "5291": ["Cañada De Las Gatiadas", "Chañariaco", "El Rodeo", "El Sunchal", "El Vallesito", "Estancia De Guadalupe", "La Bismutina", "La Estancia", "Los Barriales", "Mina La Bismutina", "Mogote Verde", "Ninalquin", "Pajonal", "Paso Grande", "Piedras Anchas", "San Carlos Minas", "Sapansoto", "Sierra De Abregu", "Sierra De Las Paredes", "Sunchal", "Talaini", "Totoritas", "Tres Esquinas", "Tres Lomas"],
    "5293": ["Cerro Bola", "El Durazno", "La Argentina", "Las Cortaderas", "Ojo De Agua", "Ojo De Agua De Totox"],
    "5295": ["Alto Del Tala", "Buena Vista", "Cuchillo Yaco", "El Potrero", "La Esquina", "Las Cortaderas", "Las Rosas", "Piedritas Rosadas", "Pitoa", "Salsacate", "Toro Muerto", "Tres Chañares", "Villa Taninga", "Viso"],
    "5297": ["Arcoyo", "Arroyo", "Buena Vista", "Cañada Del Puerto", "Cerro Negro", "Cienaga De Britos", "Dos Rios", "La Calera", "La Quebrada", "La Sierrita", "Las Chacras", "Mina Araujo", "Potrero De Marques", "Puerta De La Quebrada", "Rio Hondo", "Sagrada Familia", "San Geronimo", "Sauce De Los Quevedos", "Tala Cañada"],
    "5299": ["Ambul", "Carrizal", "Casa Blanca", "Cañada De Pocho", "Cañada De Salas", "Chamico", "Desvio El Volcan", "El Carrizal", "La Aguadita", "La Mudana", "La Tablada", "Las Palmas", "Loma Redonda", "Los Talares", "Mussi", "Pusisuna", "Taruca Pampa", "Villa De Pocho"],
    "5300": ["Amilgancho", "Ampata", "Bajo Hondo", "Bazan", "Carrizal Estacion Fcgb", "Cebollar", "Chumbicha", "Dique Los Sauces", "El Cantadero", "El Duraznillo", "El Plumerillo", "Estacion 69", "Flamenco", "Jesus Maria", "Kilometro 861", "Kilometro 875", "La Buena Suerte", "La Esperanza", "La Flor", "La Lancha", "La Lata", "La Ramadita", "La Rioja", "Las Cañas", "Las Higuerillas", "Las Padercitas", "Medano", "Pozo De Avila", "Pozo Escondido", "Puerta De La Quebrada", "Puerto Alegre", "Punta Del Negro", "San Agustin", "San Guillermo", "San Javier", "San Juan", "San Martin", "Santa Rosa", "Santo Domingo", "Trampa Del Tigre"],
    "5301": ["Agua Blanca", "Aguada", "Aminga", "Anchico", "Anillaco", "Campo Tres Pozos", "Chuquis", "El Barrial", "El Bayito", "El Escondido", "El Estanquito", "El Huaco", "El Quebracho", "El Valle", "Huaco", "Ismiango", "La Antigua", "La Buena Estrella", "La Rosilla", "Las Bombas", "Las Catas", "Las Peñas", "Las Sierras Bravas", "Los Cerrillos", "Los Molinos", "Mesillas Blancas", "Pinchas", "Pozo Blanco", "Pozo De La Yegua", "Puerto Del Valle", "San Antonio", "San Bernardo", "San Ignacio", "San Jose", "San Lorenzo", "San Miguel", "San Nicolas", "San Pedro", "San Rafael", "Santa Ana", "Santa Cruz", "Santa Teresa", "Santa Vera Cruz", "Sierra Brava", "Villa Bustos", "Villa Sanagasta"],
    "5303": ["Anjullon"],
    "5304": ["El Tala", "Talamuyuna"],
    "5306": ["Carrizal"],
    "5310": ["Aimogasta", "Bañados Del Pantano", "Las Tuscas", "Los Baldes", "San Antonio", "Señor De La Peña"],
    "5311": ["Arauco", "Machigasta", "Udpinango"],
    "5313": ["Estacion Mazan", "Kilometro 891", "Kilometro 921", "Termas De Santa Teresita", "Tinocan", "Villa Mazan"],
    "5315": ["Calera La Norma", "El Pajonal", "Estacion Poman", "Joyanguito", "Las Casitas", "Las Cienagas", "Los Baldes", "Malcasco", "Mischango", "Poman", "Tuscumayo"],
    "5317": ["Apoyaco", "Establecimiento Minero Cerro B", "Los Cajones", "Mutquin", "Retiro", "Retiro De Colana", "Rincon", "Rosario De Colana"],
    "5319": ["Colpes", "Los Puestos", "Mollecito", "San Jose", "Sijan"],
    "5321": ["El Potrero", "Joyango", "Kilometro 975", "La Aguada Grande", "La Yegua Muerta", "Las Breas", "San Miguel", "Saujil"],
    "5325": ["Alpasinche", "El Retiro", "La Pirgua", "Lorohuasi"],
    "5327": ["Capihuas", "Cerro Negro", "Chaupihuasi", "Cordobita", "El Pueblito", "Los Olivares", "Salicas", "San Blas"],
    "5329": ["Amuschina", "Andolucas", "Cuipan", "La Plaza", "Las Talas", "Los Robles", "Schaqui", "Suriyaco", "Tuyubil"],
    "5331": ["Andalucia", "Cerro Negro", "Cordobita", "El Pueblito", "Kilometro 1006", "Kilometro 999", "La Puntilla", "Las Chacras", "Los Balverdis", "Los Gonzales", "Los Quinteros", "Los Rincones", "Peñas Blancas", "Rio Colorado", "Salado", "Santa Cruz", "Villa Seleme"],
    "5333": ["Banda De Lucero", "Carrizal", "Cienaguita", "Copacabana", "El Alto", "La Candelaria", "La Capellania", "La Isla", "Viña Del Cerro"],
    "5340": ["Agua Grande", "Aguada", "Anchoca", "Apocango", "Balungasta", "Cantera Rota", "Casa De Alto", "Casa Grande", "Castañar", "Cerdas", "Chanero", "Chavero", "Cortadera", "Estancito", "Guanchicito", "Guanchin", "Guincho", "Junta", "La Chilca", "Las Higueritas", "Las Losas", "Las Peladas", "Loma Grande", "Loro Huasi", "Los Chanampa", "Los Guaytimas", "Los Palacios", "Los Robledos", "Los Valdez", "Los Valveros", "Matambre", "Medano", "Negro Muerto", "Ojo De Agua", "Palacios", "Pan De Azucar", "Pantanos", "Pastos Amarillos", "Pillahuasi", "Planchada", "Pocitos", "Quebrada Honda", "Quemadita", "Quemado", "Quiquero", "Qusto", "Rio Abajo", "Rio De Los Indios", "Rodeo", "San Buenaventura", "Suncho", "Tala Zapata", "Talita", "Tamberia", "Tambu", "Tinogasta", "Totora", "Troya", "Vallecito", "Vega", "Vinquis", "Yacochuyo"],
    "5341": ["Anillaco", "Antinaco", "Corral De Piedra", "Costa De Reyes", "El Cachiyuyo", "El Puesto", "La Cañada Larga", "La Cienaga", "La Cienaga De Los Zondones", "La Falda", "La Florida", "La Majada", "La Mesada", "La Palca", "La Puntilla De San Jose", "La Ramadita", "Las Pampas", "Las Papas", "Los Potrerillos", "Medanitos", "Mesada De Los Zarate", "Mesada Grande", "Palo Blanco", "Pampa Blanca", "Paso San Francisco", "Plaza De San Pedro", "Rio Grande", "San Jose", "Santo Tomas", "Saujil De Tinogasta", "Taton"],
    "5343": ["Lavalle", "Santa Rosa", "Villa San Roque"],
    "5345": ["Baños Termales", "El Barrialito", "El Peñon", "El Retiro", "Fiambala", "La Aguadita", "Las Retamas", "Los Morteros", "Punta De Agua"],
    "5350": ["El Molle", "La Cienaga", "La Perlita", "Los Frances", "San Bernardo", "San Jose", "Villa Union"],
    "5351": ["Banda Florida", "El Fuerte", "La Maravilla", "Los Palacios", "Paso San Isidro", "Santa Clara"],
    "5353": ["El Zapallar", "Guandacol", "Los Nacimientos"],
    "5355": ["El Altillo", "El Condado", "Las Aguaditas", "Las Padercitas", "Padercitas", "Parecitas", "Pastos Largos", "Punta De Agua", "Rivadavia", "Villa Castelli"],
    "5357": ["El Horno", "Vinchina"],
    "5359": ["Alto Jaguel", "Bajo Jaguel", "Boca De La Quebrada", "Buena Vista", "Casa Pintada", "Distrito Pueblo", "Jague", "La Armonia", "La Banda", "La Pampa", "Peñas Blancas", "Potrero Grande", "Valle Hermoso", "Villa San Jose De Vinchina"],
    "5360": ["Chilecito", "El Vallecito", "Samay Huasi", "San Nicolas", "Santa Florentina"],
    "5361": ["Aicuña", "Alto Carrizal", "Anchumbil", "Angulos", "Antinaco", "Barrio De Galli", "Campanas", "Carrizal", "Carrizalillo", "Chañarmuyo", "El Chocoy", "El Chuschin", "El Pedregal", "El Potrerillo", "Estancia De Maiz", "La Cuadra", "La Higuera", "La Pampa", "Las Tucumanesas", "Los Corrales", "Los Sarmientos", "Los Tambillos", "Malligasta", "Piedra De Talampaya", "Piedra Pintada", "Pituil", "Plaza Vieja", "Puerto Alegre", "Salinas Del Leoncito", "San Miguel", "Santa Cruz", "Santa Elena", "Santo Domingo", "Santo Domingo Famatina", "Tilimuqui", "Tres Cerros"],
    "5363": ["Anguinan"],
    "5365": ["El Jumeal", "Famatina", "La Banda", "Las Gredas", "Plaza Nueva"],
    "5367": ["Cachiyuyal", "Guachin", "La Puntilla", "Miranda", "Sañogasta"],
    "5369": ["Pagancillo"],
    "5372": ["Nonogasta"],
    "5374": ["Catinzaco", "Catinzaco Embarcadero Fcgb", "Vichigasta"],
    "5380": ["Chamical", "Chulo", "Colonia Alfredo", "El Garabato", "El Quemado", "El Retamo", "Esquina Del Norte", "Gobernador Gordillo", "La Invernada", "La Serena", "Los Bordos", "Palo Labrado", "Polco", "Pozo De La Orilla", "Quebracho Herrado", "Santa Lucia"],
    "5381": ["Bella Vista", "Cortaderas", "El Mollar", "Iliar", "La Cienaga", "Loma Blanca", "Quebrachal", "Santa Barbara", "Talva"],
    "5383": ["Agua Colorada", "Bajo Grande", "Balde Salado", "Cisco", "El Alto", "El Quebrachal", "El Quebracho", "Esquina Del Sud", "La Chimenea", "La Huerta", "La Trampa", "Loma Larga", "Monte Grande", "Olta", "San Ramon", "Tala Verde", "Tres Cruces"],
    "5384": ["Punta De Los Llanos"],
    "5385": ["Aguadita", "Alcazar", "Atiles", "Carrizalillo", "Casagate", "Casangate", "Chila", "Chimenea", "El Barranco", "El Carrizal Tama", "El Portezuelo", "El Potrerillo", "El Potrero", "El Puesto", "El Retamal", "Falda De Citan", "Huaja", "La Aguadita", "La Lomita", "La Merced", "La Represa", "Las Higueras", "Loma Larga", "Los Algarrobos", "Malanzan", "Mollaco", "Nacate", "Pacatala", "Puluchan", "Quebrada De Los Condores", "Retamal", "Rio De Las Cañas", "Rios De Las Mesadas", "Rios De Los Colcoles", "Salana", "San Pedro", "San Ramon", "San Roque", "Sierra De Los Quinteros", "Solca", "Tama", "Tasquin", "Tuani", "Tuizon"],
    "5386": ["Amana", "Bajo De Gallo", "Balde San Isidro", "Cueva Del Chacho", "El Chiflon", "Guayapa", "La Torre", "Los Baldecitos", "Los Colorados", "Los Mogotes Colorados", "Paganzo", "Patquia", "Puesto Talita", "Represa De La Punta", "Salinas De Bustos", "Termas"],
    "5400": ["Desamparados", "Diaz Velez", "El Medanito", "Presbitero Fco Perez Hernadez", "Rivadavia", "San Juan", "Talacasto", "Trinidad", "Villa Carolina", "Villa Huasihul", "Villa Marini"],
    "5401": ["Barrio El Tontal", "Cerro Aguaditas", "Cerro Aguila", "Cerro Blanco", "Cerro Casa De Piedra", "Cerro Divisadero", "Cerro Infiernillo", "Cerro Jaguel", "Cerro La Cienaga", "Cerro La Flecha", "Cerro La Jarilla", "Cerro La Rinconada", "Cerro Las Barrancas", "Cerro Las Placetas", "Cerro Negro", "Cerro Pachaco", "Cerro Pircas", "Cerro Santa Rosa", "Cerro Sasito", "Cerro Tambolar", "Cerro Tres Mogotes", "Colon", "Dique Soldano", "Estancia Maradona", "Hilario", "Huaicos", "La Isla", "Los Paramillos", "Portezuelo De Los Sombreros", "Pto Cordova", "Pto Del Agua De Pinto", "Pto El Molle", "Pto Las Cuevas", "Pto Los Papagallos", "Puchuzun", "Ruta 20 Kilometro 114", "Sorocayense", "Tamberias", "Villa Basilio Nievas", "Villa Corral", "Villa Media Agua", "Villa Nueva", "Zonda"],
    "5403": ["Barrialitos", "Bella Vista", "Cabecera Del Barrial", "Calingasta", "Castaño Nuevo", "Mina San Jorge"],
    "5405": ["Agua Y Energia", "Barreal", "Barreales", "Campo Del Leoncito", "Castaño Viejo", "Cerro Amarillo", "Cerro Bayo", "Cerro Blanco", "Cerro Bonete", "Cerro Bramadero", "Cerro Chiquero", "Cerro Cortadera", "Cerro De Las Vacas", "Cerro De Los Pozos", "Cerro Del Tome", "Cerro Grande", "Cerro Guanaquero", "Cerro Hornito", "Cerro La Fortuna", "Cerro Las Mulas", "Cerro Los Patos", "Cerro Mercedario", "Cerro Mudadero", "Cerro Panteon", "Cerro Pichereguas", "Cerro Puntudo", "El Leoncito", "Estancia Casa Rio Blanco", "Estancia El Totoral", "Estancia La Puntilla", "Estancia Leoncito", "Gendarmeria Nacional", "La Alumbrera", "La Capilla", "Las Hornillas", "Manantiales", "Pachaco", "Peñasquito", "Po De Barahona", "Po De La Guardia", "Po De Las Llaretas", "Po De Las Ojotas", "Po De Los Piuquenes", "Po De Los Teatinos", "Po Del Portillo", "Portezuelo De Longomiche", "Potrerillos", "Pto Santa Rosa De Abajo", "Tira Larga", "Tontal", "Yacimiento De Cobre El Pachon"],
    "5407": ["Dique Toma", "La Bebida", "Marquesado", "Rio Saso", "Villa Obrera"],
    "5409": ["Adan Quiroga", "Aurora", "Barrio Agua Y Energia", "Barrio Colon", "Barrio Graffigna", "Bodega Graffigna", "Camp D P V La Cienaga", "Castaño", "Cerro La Ventanita", "Cerro Tambolar", "Cerro Villa Loncito", "Cienaguita", "Coyon", "Cumiyango", "El Balde", "El Chilote", "El Fuerte", "El Volcan", "Est La Cienaga De Gualila", "Imsa", "Ingeniero Matias G Sanchez", "Isla Del Sauce", "Las Aguaditas", "Los Diaguitas", "Mina Gualilan", "Mogna", "Niquivil", "Niquivil Viejo", "Portezuelo Del Colorado", "Refugio D P V", "Refugio Los Gauchos", "San Roque", "Santa Barbara", "Tucunuco", "Ullum"],
    "5411": ["La Legua", "Luz Del Mundo", "Pajas Blancas", "Santa Lucia", "Villa 20 De Junio", "Villa Bermejito", "Villa Estevez", "Villa General Las Heras", "Villa Gobernador Chavez", "Villa J C Sarmiento", "Villa Luz Del Mundo", "Villa Muñoz", "Villa N Larrain", "Villa Patricias Sanjuaninas", "Villa Pueyrredon", "Villa Rizzo", "Villa Rufino Gomez", "Villa Sargento Cabral"],
    "5413": ["Apeadero Las Chimbas", "Chimbas", "El Mogote", "Los Viñedos", "Villa Juan Xxiii", "Villa Morrones", "Villa P A De Sarmiento", "Villa Santa Paula"],
    "5415": ["Angaco Norte", "Calle Aguileras", "Calle Nacional", "Domingo De Oro", "El Alamito", "El Bosque", "La Cañada", "Las Tapias", "Paquita", "Pichagual", "Plumerillo", "Punta Del Monte", "Ranchos De Famacoa", "Villa Del Salvador", "Villa General Acha", "Villa San Isidro"],
    "5417": ["9 De Julio", "Aeropuerto San Juan", "Angaco Sud", "Colonia Fiorito", "Finca Zapata", "La Majadita", "Las Chacritas", "Los Quillay", "Tierra Adentro"],
    "5419": ["Baños De La Laja", "Baños Del Salado", "Campo Afuera", "Cerro Bola", "Cerro Villicun", "Dos Puentes", "El Salado", "Est Albardon", "La Cañada", "La Laja", "Las Lomitas", "Las Piedritas", "Los Puestos", "Matagusanos", "Obispo Zapata", "Terma La Laja", "Tierra Adentro", "Villa General San Martin"],
    "5421": ["Colonia Centenario", "Colonia Rodas", "Contegrand", "Encon", "La Callecita", "La Tranca", "Medano De Oro"],
    "5423": ["Capitan Lazo", "Villa Santa Anita"],
    "5424": ["Villa Lerga"],
    "5425": ["Albarracin", "Barrio Obrero Rawson", "Colonia El Molino", "Colonia Florida", "Colonia Juan Solari", "Colonia Rodriguez Zavalla", "Colonia Yorner", "Colonia Zabala", "El Molino", "Germania", "La Florida", "La Orilla", "Lloveras", "Primer Cuartel", "Santa Clara", "Segundo Cuartel", "Villa Fleury", "Villa Franca", "Villa General Acha", "Villa Krause", "Villa Laprida", "Villa Rachel", "Zavalla"],
    "5427": ["Apeadero Quiroga", "Barrio Santa Barbara", "Centro Aviacion Civil San Juan", "Colonia Cantoni", "Colonia Castro Padin", "Colonia Moya", "Colonia Roca", "Juan Celani", "La Cosechera", "Quinto Cuartel", "Sanchez De Loria", "Villa Aberastain", "Villa Barboza", "Villa Nacusi"],
    "5429": ["El Abanico", "Pocito", "Rinconada"],
    "5431": ["Apeadero Guanacache", "Baños Del Cerro", "Bodega San Antonio", "Carbometal", "Cañada Honda", "Cerro De Los Burros", "Cerro Del Medio", "Cerro Hediondo", "Cerro Los Pozos", "Cerro Riquiliponche", "Cienaguita", "Dique Las Crucecitas", "Divisadero", "El Infierno", "Estancia Acequion", "Estancia El Durazno", "Estancia La Posta", "Guanacache", "Kilometro 10650", "La Chilca", "Lomas Del Aguaditas", "Los Berros", "Los Nogales", "Los Sombreros", "Pedernal", "Potranca", "Puesto Angostura", "Puesto De Arriba", "Puesto La Chilca De Abajo", "Puesto Olguin", "Puesto Retiro", "Puesto Santa Rosa", "Santa Clara", "Villa General Sarmiento"],
    "5433": ["Estacion La Rinconada"],
    "5435": ["Algarrobo Grande", "Azucarera De Cuyo", "Campo De Batalla", "Carpinteria", "Cochagual", "Colonia Fiorito", "Colonia Fiscal Sarmiento", "Colonia San Antonio", "El Chañar", "La Cieneguita", "Laguna Del Rosario", "Las Lagunas", "Los Chañares", "Lote Alvarado", "Media Agua", "Puesto Isla Chañar", "Puesto Los Chañares", "Puesto Quemado", "Punta De Laguna", "Punta Del Medano", "Quiroga", "Ramblon", "Retamito", "San Carlos", "Tres Esquinas"],
    "5436": ["Colonia Zapata", "Las Chimbas", "Pedro Echague"],
    "5438": ["Alto De Sierra", "Callecita", "Coll", "Colonia Gutierrez", "Colonia Richet", "Los Viñedos", "Puente Nacional", "Puente Rio San Juan", "Puente Rufino", "Usina"],
    "5439": ["Belgrano", "Calle Larga", "Callecita", "Dos Acequias", "Kilometro 905", "La Germania", "La Puntilla", "Los Angacos", "Los Compartos", "Puntilla Blanca", "Puntilla Negra", "San Isidro", "San Martin", "Villa Alem", "Villa Dominguito", "Villa Lugano"],
    "5442": ["Ambas Puntillas", "Calibar", "Caucete", "Cerro Tigre", "El Pozo Del 20", "Finca De Izasa", "Guayaguas", "Kilometro 810", "Kilometro 895", "La Puntilla", "Las Liebres", "Los Mellizos", "Lotes De Alvarez", "Lotes De Coria", "Lotes De Uriburu", "Lotes Escuela 138", "Lotes Rivera", "Pozo Salado", "Puerto Alegre", "Puerto Tapones De Maya", "Rincon", "Uriburu", "Villa Colon"],
    "5443": ["Algarrobo Verde", "Amarfil", "Chañar Seco", "Cruz De San Pedro", "Cuatro Esquinas", "Cuyo", "Diaz Velez", "Difunta Correa", "Divisoria", "El Rincon", "Jose Marti", "Kilometro 910", "Kilometro 936", "La Chimbera", "La Rinconada", "Las Casuarinas", "Las Higueritas", "Los Corredores", "Los Medanos", "Nueva España", "Pozo De Los Algarrobos", "Punta Del Medano", "Puntilla", "Puntilla Blanca", "San Antonio", "Santa Maria Del Rosario", "Tupeli", "Vallecito", "Villa Borjas", "Villa Independencia", "Villa Santa Rosa"],
    "5444": ["Ampacama", "Bermejo", "Guayamas", "Kilometro 893", "Laguna Seca", "Nikisanga", "Nueva Castilla", "Pie De Palo"],
    "5446": ["Balde De Leyes", "Balde Del Lucero", "El Chupino", "Las Chacras", "Las Salinas", "Los Papagayos", "Marayes", "San Carlos"],
    "5447": ["Agua Cercada", "Agua Escondida", "Astica", "Balde Plumerito", "Balde San Carlos", "Baldes Del Tarabay", "Barranca Colorada", "Barrealito", "Casa De Javier", "Cañada De Laguna", "Cañada Del Pozo", "Cerro Asilan", "Cerro La Colorada", "Cerro Tres Puntas", "Chanchos", "Chica Negra", "Chucuma", "Cienaga", "Condor Muerto", "Corral De Pirca", "Cuchillazo", "Cuesta Viejo", "Culebra", "Dos Mojones", "El Barrialito", "El Gigantillo", "El Lechuzo", "El Plumerito", "El Rincon", "El Salto", "Est De Herrera Vegas", "Est Marayes", "Estancia Bajo De Las Tumanas", "Estancia El Chañar Nuevo", "Estancia El Jumeal", "Estancia El Molino", "Estancia El Polear", "Estancia Elizondo", "Estancia La Escalera", "Estancia La Florida", "Estancia La Lata", "Estancia Quiroga", "Estancia Rio Verde", "Estancia San Roque", "Filo Del Mocho", "Finca Del Japones", "Ichigualasto", "Ischigualasto", "Jarilla Chica", "Juntas Del Guandacol", "La Carpa", "La Cercada", "La Cienaguita", "La Cruz", "La Esquina", "La Huerta", "La Mesada", "La Orqueta", "La Penca", "La Ripiera", "La Rosita", "La Sal", "Laprida", "Las Delicias", "Las Hermanas", "Las Juntas", "Las Ramaditas", "Las Tumanas", "Las Yeguas", "Loma Ancha", "Loma De Cocho", "Loma Leones", "Los Baldes", "Los Baldes De Astica", "Los Lagares", "Los Porongos", "Los Sanchez", "Mesada Aguada", "Mica", "Milagro", "Morterito", "Naquera", "Pampa De Los Caballos", "Pampa Grande", "Paso De Ferreira", "Paso De Lamas", "Piedra Blanca", "Piedra Colorada", "Piedra Rajada", "Pila De Macho", "Portezuelo Las Chilcas", "Portezuelo Las Francas", "Pozo De Aguadita", "Pto Chanquia", "Pto Chavez", "Pto Gordillo", "Pto Huasi", "Pto Lima", "Pto Romero", "Pto San Isidro", "Pto Vega", "Puerta De La Chilca", "Punta Blanca", "Punta Norte", "Refugio", "Richard", "Rincon Chico", "Rincon Grande", "Sanjuanino", "Santo Domingo", "Sarmiento", "Sierra De Elizondo", "Tamberias", "Tumanas", "Yerba Buena"],
    "5449": ["Aguango", "Balde Del Norte", "Balde Del Rosario", "Baldecito", "Baldecito Del Morado", "Baldes De La Chilca", "Baldes Del Sud", "Cabeza Del Toro", "Chañar", "El Puerto", "La Cieneguita", "La Colonia", "La Majadita", "La Ramada", "Las Higueritas", "Loma Negra", "Lomas Blancas", "Los Baldecitos", "Los Barriales", "Los Chaves", "Los Molles", "Los Rincones", "Majadita", "Medano Colorado", "Papagayos", "Rincones", "San Agustin Del Valle Fertil", "San Antonio", "San Juan Bautista Usno", "Sierra De Chavez", "Sierra De Rivero", "Usno", "Villa Carlota", "Yoca"],
    "5460": ["Agua De La Zorra", "Agua De Los Caballos", "Algarrobo Del Cura", "Aschichusca", "Barranca De Los Loros", "Barrancas Blancas", "Bella Vista", "Campo Las Liebres", "Campo Los Pozos", "Casa Vieja", "Cerro Aspero", "Cerro Caballo Anca", "Cerro Colorado", "Cerro De Los Caballos", "Cerro El Durazno", "Cerro Iman", "Cerro La Cañada Amarilla", "Cerro Lajitas", "Cerro Negro", "Cerro Negro Del Corral", "Cerro Potrero", "Chañar Pintado", "Chepical", "Colanqui", "Cruz De Piedra", "Dique Cauquenes", "El Chacrero", "El Chamizudo", "El Corralito", "El Jaboncito", "El Medano", "El Quemado", "El Salitre", "El Tapon", "El Treinta", "Est Niquivil", "Finca El Molino", "Guachipampa", "Hosteria El Balde", "Indio Muerto", "Jachal", "La Chilca", "La Cienaga De Cumillango", "La Esquina", "La Estaca", "La Legua", "La Overa", "La Toma", "La Valentina", "Las Cienagas Verdes", "Las Espinas", "Las Puestas", "Loma Negra", "Los Hornos", "Los Puestos", "Los Ranchos", "Los Terremotos", "Mina De Guachi", "Mina El Algarrobo", "Mina El Pescado", "Mina Escondida", "Mina General Belgrano", "Mina La Abundancia", "Mina La Delfina", "Mina La Esperanza", "Mina La Salamanta", "Mina Los Caballos", "Mina Montosa", "Mina San Antonio", "Otra Banda", "Pasleam", "Paso De Otarola", "Piedra Parada", "Po De Usno", "Porton Grande", "Pto Ag Del Burro", "Pto Aguadita", "Pto Aguadita De Abajo", "Pto Anjulio", "Pto Cumillango", "Pto Durazno", "Pto El Arbol Ligudo", "Pto El Sarco", "Pto El Toro", "Pto Figueroa", "Pto La Chilca", "Pto La Cortadera", "Pto La Espina", "Pto La Represa", "Pto La Tuna", "Pto La Virgencita", "Pto Los Alamos", "Pto Los Pozos", "Pto Majadita", "Pto Pajarito", "Pto Pantanito", "Pto Perico", "Pto Pescado", "Pto Pimpa", "Pto Portezuelo Hondo", "Pto Potrerillo", "Pto Punilla", "Pto Recreo", "Pto Sabato", "Pto Segovia", "Pto Trapiche", "Pto Vallecito", "Pto Varejon", "Rincon", "Rincon Colorado", "Rincon Del Gato", "Rio Palo", "Sierra Billicum", "Tap Gallardo", "Termas Agua Hedionda", "Termas De Agua Negra", "Trancas", "Travesia De Mogna", "Tuminico", "Villa", "Volcan"],
    "5461": ["Aguada De La Peña", "Aguaditas", "Aguaditas Del Rio Jachal", "Aguas Del Pajaro", "Alcaucha", "Boca De La Quebrada", "El Buen Retiro", "El Fical", "Entre Rios", "Gran China", "Guaja", "Huerta De Guachi", "La Falda", "Los Quimbaletes", "Ojos De Agua", "Pampa Del Chañar", "Pampa Vieja", "Panacan", "Pimpa", "San Isidro", "Tamberias", "Villa Mercedes"],
    "5463": ["Alto Huaco", "Huaco", "La Cienaga", "Paso Del Lamar", "Punta De Agua"],
    "5465": ["Baños Pismanta", "Cerro Negro", "Colola", "Guañizul", "La Cañada", "La Maral", "La Moral", "Rodeo", "Totoralito"],
    "5467": ["Acerillos", "Agua De La Zanja", "Angualasto", "Arrequintin", "Baños Centenario", "Baños De Los Despoblados", "Baños De San Crispin", "Bella Vista", "Buena Esperanza", "Cacho Ancho", "Cajon De Los Tambillos", "Campanario Nuevo", "Carrizalito", "Cañada", "Cerro Alto Del Descubrimiento", "Cerro Amarillo", "Cerro Boleadora", "Cerro Bravo", "Cerro Caballo Bayo", "Cerro Colorado", "Cerro Cortadera", "Cerro De Conconta", "Cerro De Dolores", "Cerro De La Cuesta Del Viento", "Cerro De La Sepultura", "Cerro De Los Bañitos", "Cerro De Los Burros", "Cerro Del Agua De Las Vacas", "Cerro Del Alumbre", "Cerro Del Cachiyuyal", "Cerro Del Coquimbito", "Cerro Del Guanaco", "Cerro Del Salado", "Cerro El Bronce", "Cerro El Cepo", "Cerro El Frances", "Cerro Espantajo", "Cerro Hediondo", "Cerro Iman", "Cerro Joaquin", "Cerro La Bolsa", "Cerro La Ortiga", "Cerro Lagunita", "Cerro Las Mulitas", "Cerro Las Raices", "Cerro Las Yeguas", "Cerro Lavaderos", "Cerro Los Mogotes", "Cerro Los Pozos", "Cerro Negro De Chita", "Cerro Nico", "Cerro Ocucaros", "Cerro Pata De Indio", "Cerro Pintado", "Cerro Potrerito De Agua Blanco", "Cerro Senda Azul", "Cerro Silvio", "Cerro Silvo", "Champones", "Chaparro", "Chigua De Abajo", "Chisnasco", "Cienaguillos", "Colanguil", "Concota", "Divisadero De La Mujer Helada", "El Carrizal", "El Chinguillo", "El Retiro", "El Salado", "Fierro", "Fierro Nuevo", "Fierro Viejo", "Finca El Toro", "Hachango", "Huañizuil", "Hueso Quebrado", "Iglesia", "Jaguelito", "Jarillito", "Junta De Santa Rosa", "Juntas De La Jarilla", "Juntas De La Sal", "Juntas Del Frio", "La Angostura", "La Chigua", "La Estrechura", "Las Casitas", "Las Cuevas", "Las Flores", "Las Higueras", "Las Peñitas", "Lomas Blancas", "Los Cogotes", "Los Loros", "Los Penitentes", "Los Sapitos", "Maclacasto", "Maipirinqui", "Maliman", "Maliman Arriba", "Maliman De Abajo", "Manantiales", "Mina De Las Carachas", "Mondaca", "Ojos De Agua", "Paso Del Agua Negra", "Peñasco Colorado", "Peñasquito", "Piedras Blancas", "Pircas Blancas", "Pircas Negras", "Pismania", "Po Cajon De La Brea", "Po Del Chollay", "Po Del Inca", "Po Las Tortolas", "Portezuelo De La Punilla", "Portezuelo Las Caracachas", "Portezuelo San Guillermo", "Portezuelo Santa Rosa", "Potreros Los Amadores", "Pto Gen", "Puerta Del Infiernillo", "Quilinquil", "Refugio", "Rincon De La Brea", "Rincon De La Ollita", "Rincon De Los Chinchilleros", "Ruinas Indigenas", "Tamberias", "Terma Pismanta", "Termas Centenario", "Tocota", "Tres Quebraditas", "Tudcum", "Tutianca", "Valle Del Cura", "Venillo"],
    "5470": ["Abra Verde", "Agua De Piedra", "Alto Bayo", "Bayo Muerto", "Cañada Honda", "Chepes", "Chepes Viejos", "El Alto", "El Barreal", "El Cincuenta", "El Divisadero", "La Aguada", "La Carrizana", "La Consulta", "La Pintada", "La Primavera", "Las Tuscas", "Los Olmos", "Los Oros", "Punta Del Cerro", "Represa Del Monte", "San Antonio", "San Vicente", "Santa Cruz"],
    "5471": ["Agua Blanca", "Casas Viejas", "Cañada Verde", "Corral De Isaac", "El Balde", "El Barrial", "El Rodeo", "El Tala", "Ilisco", "Illisca", "La Calera", "La Callana", "La Escondida", "La Esquina", "La Jarilla", "La Laguna", "La Reforma", "La Represa", "La Tordilla", "La Yesera", "Las Barrancas", "Las Salinas", "Las Toscas", "Los Corias", "Mascasin", "Portezuelo De Los Arce", "Puesto De Carrizo", "Puesto De Los Sanchez", "Puesto Dichoso", "Quebrada Del Vallecito", "Real Del Cadillo", "San Antonio", "San Isidro", "San Jose", "San Rafael", "Santa Cruz", "Totoral", "Valle Hermoso", "Villa Casana", "Villa Chepes", "Ñoqueves"],
    "5473": ["Aguayo", "Algarrobo Grande", "Bajo Corral De Isaac", "Bajo Hondo", "Balde Del Quebracho", "Cuatro Esquinas", "El Abra", "El Valdecito", "La America", "La Chilca", "La Envidia", "La Esquina", "La Libertad", "Nueva Esperanza", "Pozo De La Piedra", "Pozo De Piedra", "San Antonio", "San Nicolas", "San Solano", "Santo Domingo", "Siempre Verde", "Ulapes", "Villa Nidia"],
    "5474": ["Barranquitas", "Cortaderas Embarcadero Fcgb", "Desiderio Tello", "El Catorce", "La Igualdad"],
    "5475": ["Agua De La Piedra", "Ambil", "Chelcos", "El Carrizal", "El Cerco", "El Potrerillo", "El Potrerillo R V Peñaloza", "El Quemado", "La Dora", "Piedra Larga", "San Jose"],
    "5500": ["Cerro Aconcagua", "Cerro De Los Potrerillos", "Mendoza", "Paramillo De Las Vacas", "Plaza De Mulas"],
    "5501": ["Cerrillos Al Sud", "Godoy Cruz"],
    "5503": ["Paso De Los Andes", "San Francisco Del Monte"],
    "5505": ["Carbometal", "Carrodilla La Puntilla", "Chacras De Coria", "Los Filtros"],
    "5507": ["Baños Lunlunta", "Calle Terrada", "Colonia Cano", "Dique Rio Mendoza", "Distrito Compuerta", "Lotes De Gaviola", "Lujan De Cuyo", "Mayor Drummond", "Puesto La Jarilla", "Vertientes Del Pedemonte", "Villa Gaviola"],
    "5509": ["Agrelo", "Anchoris", "Carrizal De Abajo", "Carrizal De Arriba", "Cerrillos", "Cerrillos Al Norte", "Colonia Barraquero", "Colonia Funes", "El Carrizal", "El Carrizal De Abajo", "El Infiernillo", "Jaguel De Las Chilcas", "Las Colonias", "Minas De Petroleo", "Perdriel", "Ugarteche", "Vistalba"],
    "5511": ["General Gutierrez"],
    "5513": ["Coquimbito", "Luzuriaga", "Sarmiento"],
    "5515": ["Maipu"],
    "5517": ["Cespedes", "Chachingo", "Cruz De Piedra", "General Ortega", "La Jaula", "Las Barrancas", "Lunlunta", "Marquez Escuela117", "Maza", "Russell", "Tres Banderas", "Villa Seca"],
    "5519": ["Alto De Las Arañas", "Cañadita Alegre", "Dorrego", "San Jose", "Villas Unidas 25 De Mayo"],
    "5521": ["Los Corredores", "Villa Nueva"],
    "5523": ["Buena Nueva", "Capilla Del Rosario", "Jesus Nazareno", "Villa Suava"],
    "5525": ["Buena Vista", "Canal Pescara", "Colonia Segovia", "Kilometro 11", "La Primavera", "Paradero La Superiora", "Rodeo De La Cruz"],
    "5527": ["Colonia Santa Teresa", "Lagunita", "Los Corralitos", "Vergel"],
    "5529": ["Colonia Bombal", "Colonia Jara", "Pedregal", "Rodeo Del Medio"],
    "5531": ["Barrio Ferri", "Cartellone", "El Altillo", "El Paraiso", "Finca El Arroz", "Finca Los Alamos", "Fray Luis Beltran", "Los Alamos", "Santa Blanca"],
    "5533": ["9 De Julio", "Algarrobo", "Alto Del Olvido", "Bermejo", "Capilla Del Covadito", "Capilla San Jose", "Colonia Estrella", "Colonia Italiana", "Colonia San Francisco", "El 15", "El Balsadero", "El Calvadito", "El Chilcal", "El Chircal", "El Pascal", "El Retiro", "El Sauce", "El Tapon", "El Vergel", "General Acha", "Gobernador Luis Molina", "Guadal De Los Perez", "Jocoli Viejo", "La Esperanza", "La Fortuna", "La Holanda", "La Palmera", "La Pega", "Las Delicias", "Las Gateadas", "Las Violetas", "Limon", "Los Yaullines", "Paramillo", "Paso Del Cisne", "Puerto Hortensa", "Puesto Algarrobo Grande", "Puesto El Pichon", "Ramblon De Los Chilenos", "Santa Marta", "Tulumaya", "Villa Tulumaya"],
    "5535": ["Asuncion", "Bajada Araujo", "Colonia Andre", "Colonia Del Carmen", "Costa De Araujo", "El Alpero", "El Colon", "El Rosario", "Ingeniero Gustavo Andre", "Kilometro 1013", "Kilometro 1032", "Kilometro 43", "La Bajada", "La Celia", "Laguna De Guanacache", "Laguna Del Rosario", "Moluches", "Nueva California", "Pampa Del Salado", "Progreso", "Resurreccion", "San Jose"],
    "5537": ["Algarrobito", "Alto Amarillo", "Alto Tres Compadres", "Arroyito", "Cruz Blanca", "Don Martin", "El Cavadito", "El Guanaco", "El Retamo", "Forzudo", "La Excavacion", "Las Cruces", "Los Algodones", "Los Baldes", "Los Blancos", "Los Ralos", "Los Sauces", "Puesto La Hortensia", "San Miguel", "San Pedro"],
    "5539": ["Arenales", "Barreal De La Pampa Seca", "Barreal Pajaro Muerto", "Buitrera", "Ca Del Diablo", "Casilla", "Cerrillos Negros", "Cerro Agua Salada", "Cerro Aguadita", "Cerro Alojamiento", "Cerro Angostura", "Cerro Aspero", "Cerro Barauca", "Cerro Bay", "Cerro Blanco", "Cerro Bravo", "Cerro Catedral", "Cerro Chiquero", "Cerro Cielo", "Cerro Cienaga", "Cerro Clementino", "Cerro Color", "Cerro Cortaderas", "Cerro Cuerno", "Cerro Cupula", "Cerro De Las Leñas", "Cerro De Los Burros", "Cerro De Los Dedos", "Cerro Del Medio", "Cerro Del Rincon Bayo", "Cerro Durazno", "Cerro El Guanaco", "Cerro Fundicion", "Cerro Grande", "Cerro Horqueta", "Cerro Invernada", "Cerro Juan Pobre", "Cerro L Corrales", "Cerro La Mano", "Cerro Lagañoso", "Cerro Los Dientitos", "Cerro Manantial", "Cerro Masillas", "Cerro Melocoton", "Cerro Mexico", "Cerro Montura", "Cerro Pampa Seca", "Cerro Pan De Azucar", "Cerro Panta", "Cerro Ponderado", "Cerro Pozo", "Cerro Punta De Agua", "Cerro Puntilla Negra", "Cerro Puntudo", "Cerro Puquios", "Cerro Riquitipanche", "Cerro San Lorenzo", "Cerro Santa Maria", "Cerro Sapo", "Cerro Tigre", "Cerro Tolosa", "Cerro Tunduquera", "Cerro Yareta", "Cerros Colorados", "Cto Del Tigre", "El Challao", "El Infierno", "El Puestito", "Empalme Resguardo", "Espejo", "Espejo Resguardado", "Estancia Casa De Piedra", "Estancia Cueva Del Toro", "Estancia El Carrizal", "Estancia Jocoli", "Estancia San Martin", "Estancia Villavicencio", "Estancia Yalguaraz", "Garganta Del Leon", "La Angostura", "La Boveda", "La Casa Del Tigre", "La Fundicion", "La Horqueta", "La Jaula", "Las Canteras", "Las Heras", "Loma Colorada", "Loma De Los Burros", "Loma Sola", "Lomas Bayas", "Los Chacayes", "Los Tamarindos", "Monte Bayo", "Monumento Al Ejercito De Los A", "P San Ignacio", "Pampa Yalguaraz", "Panquehua", "Po De Contrabandista", "Po De La Cumbre", "Po De La Quebrada Honda", "Po Del Rubio", "Po Valle Hermoso", "Portillo De Indio", "Portillo De La Lagrima Viva", "Portillo De Las Vacas", "Portillo De Lomas Coloradas", "Portillo Del Medio", "Portillo Del Norte", "Portillo Del Tigre", "Portillo La Pampa", "Portillo Quemado", "Puesto Agua De Zanjon", "Puesto Carrizalito", "Puesto Chambon", "Puesto El Peral", "Puesto El Totoral", "Puesto Escondido", "Puesto Guamparito", "Puesto La Gruta", "Puesto La Mojada", "Puesto Las Higueras", "Puesto Los Alojamientos", "Puesto Los Pajaritos", "Puesto Riquitipanche", "Puesto Santa Clara De Arriba", "Rodeo Grande", "San Ignacio", "Sanchez De Bustamante", "Santa Elena", "Sierra Ansilta", "Sierra Del Tontal", "Tropero Sosa", "Tte Benjamin Matienzo", "Vega De Los Burros", "Vegas De Los Corrales De Araya", "Villavicencio", "Vra De Las Vacas"],
    "5541": ["Algarrobal Abajo", "Algarrobal Arriba", "El Algarrobal", "El Borbollon", "El Pastal", "El Plumerillo", "Paso Hondo"],
    "5543": ["3 De Mayo", "Alto Grande", "Capdeville", "Colonia 3 De Mayo", "Colonia Alemana", "El Cañito", "El Resguardo", "Hornito Del Gringo", "Hornos De Moyano", "Jocoli", "Matheu Norte", "Moyano"],
    "5544": ["Gobernador Benegas"],
    "5545": ["Agua De Diaz", "Cerro Bonete", "Colon Sandalho", "Estancia Uspallata", "La Cortadera", "Las Cortaderas", "Minas Salagasta", "Portillo Agua De Toro", "San Alberto", "Sierra De Las Higueras", "Termas Villavicencio", "Uspallata", "Valle De Uspallata"],
    "5547": ["Villa Hipodromo"],
    "5549": ["Agua De Los Manantiales", "Alto De Los Manantiales", "Alto Del Plomo", "Alvarez Condarco", "Blanco Encalada", "Cacheuta", "Campamento Cacheuta Ypf", "Carlos Subercaseux", "Casa De Piedra", "Cerro Pelado", "Concha Subercaseaux", "El Altillo", "El Salto", "Glaciares Del Rio Blanco", "Guido", "Kilometro 1085", "Kilometro 55", "La Divisoria", "La Hullera", "Las Carditas", "Las Chacritas", "Las Compuertas", "Las Vegas", "Los Papagayos", "Petroleo", "Potrerillos", "San Ignacio", "Vega Ferraina"],
    "5551": ["Estacion Uspallata", "Polvaredas"],
    "5553": ["Empalme Frontera", "La Pirata", "Los Penitentes", "Punta De Vacas", "Rio Blanco", "Zanjon Amarillo"],
    "5555": ["Puente Del Inca"],
    "5557": ["Caracoles", "Cristo Redentor", "Las Cuevas"],
    "5560": ["Arroyo Claro", "Capiz", "Casa De Las Peñas", "Colonia De Las Mulas", "Colonia Del Diablo", "Colonia Faro", "Colonia La Escondida", "Colonia La Torrecilla", "Colonia Los Oscuros", "Colonia Los Tapones", "Colonia Tabanera", "Dique Del Valle De Uco", "Doctor Antonio Soomas", "El Manzano Historico", "El Portillo", "El Topon", "El Toscal", "Estancia Aveiro", "Estancia Bella Vista", "Estancia Correa", "Estancia El Carrizalito", "Estancia Guinazu", "Estancia La Rosa", "Estancia Las Higueras", "Estancia Los Chacayes", "Estancia Mallea", "Estancia Silva", "La Estacada", "Las Pintadas", "Las Rosas", "Las Torrecitas", "Loma Chata", "Los Cometierras", "Los Sauces Lavalle", "Paso Los Palos", "Portillo De Pinquenes", "Portillo Del Diablo", "Potrero San Pablo", "Puesto El Manzano", "Puesto La Tosca", "Puesto Manzanito", "Puesto Mironda", "Puesto Santa Maria", "Ruiz Huidobro", "Totoral", "Tunuyan", "Zapata"],
    "5561": ["Ancon", "Arboleda", "Cordon Del Plata", "El Algarrobo", "El Peral", "El Zampal", "Gualtallary", "La Arboleda", "La Carrera", "Puesto Alfarfa", "Puesto La Jerilla", "San Jose De Tupungato", "Santa Clara", "Tupungato", "Villa Bastias"],
    "5563": ["Agua Amarga", "Arroyo Los Sauces", "El Salado", "Estancia La Pampa", "La Toma", "Los Arboles", "Los Sauces", "Maria Luisa", "San Pablo", "Villa Seca De Tunuyan"],
    "5565": ["Campo De Los Andes", "Colonia Las Rosas", "La Primavera", "Melocoton", "Vista Flores"],
    "5567": ["La Cañada", "La Consulta"],
    "5569": ["Aguada", "Araganita", "Bajada De La Salada", "Bajada De Los Gauchos", "Bajada De Los Papagayos", "Bajada De Yaucha", "Bajada Del Agua Escondida", "Bajada Del Fuerte", "Bajada Del Sauce", "Baños De Capiz", "Baños La Salada", "Bordo Amarillo De La Cruz Pied", "Bordo El Algarrobo", "Bordo Lechuzo", "Bordos Del Plumerillo", "Camp Vizcacheras Ypf", "Casas Viejas", "Cepillo Viejo", "Cerrito Moro", "Cerro Agua Negra", "Cerro Alto De Las Peñas", "Cerro Alvarado Centro", "Cerro Arroyo Hondo", "Cerro Baleado", "Cerro Barbaran O Tres Picos", "Cerro Chato", "Cerro Colorado", "Cerro Colorado De Las Lagunill", "Cerro De La Banderola", "Cerro De Los Leones", "Cerro Del Pozo", "Cerro Del Zorro", "Cerro Divisadero De La Cienegu", "Cerro Fiero", "Cerro Gaspar", "Cerro Guadaloso", "Cerro La Invernada", "Cerro Las Piedras", "Cerro Los Bajos", "Cerro Los Barros", "Cerro Negros De Las Mesillas", "Cerro Piedra Colorada", "Cerro Plomo", "Cerro Potrerillos", "Chilecito", "Cienaga Del Alto", "Colonia Alazanes", "Colonia Aspera", "Colonia Chalet", "Colonia Chato", "Colonia Colina", "Colonia Curniñan", "Colonia De Los Guanaqueros", "Colonia Del Leon", "Colonia Divisadero Del Cardal", "Colonia Divisadero Negro", "Colonia Durazno", "Colonia El Campanario", "Colonia Guadal", "Colonia Guanaco", "Colonia Lola", "Colonia Los Huevos", "Colonia Mirador", "Colonia Muralla", "Colonia Nacional De Los Indios", "Colonia Negro", "Colonia Osamenta", "Colonia Papal", "Colonia Pedernales", "Colonia Pencal", "Colonia Pico Colorado", "Colonia San Agustin", "Colonia Torrecillas", "Colonia Torrecito", "Colonia Tres Altitos", "Control Ypf", "Cruz De Piedra Pto Gendarmeria", "Divisadero Colorado", "Divisadero Negro", "El Capacho", "El Cepillo", "El Guadal De Campos", "El Lechucito", "El Parral", "El Puma", "El Rincon", "Estancia Aguanda", "Estancia Arroyo Hondo", "Estancia Casas Viejas", "Estancia La Puma", "Estancia Viluco", "Estancia Yaucha", "Eugenio Bustos", "Huaiqueria De La Horqueta", "Huaiqueria De Los Burros", "Isla Del Cuchillo", "J Campos", "J Veron", "Jaucha", "L Prado", "La Argentina", "La Florida", "La Jaula", "La Picaza", "Las Minas", "Las Peñas", "Las Violetas", "Loma Alta", "Loma Del Cerro Aspero", "Loma Del Medio", "Loma Negra", "Loma Negra Grande", "Loma Pelada", "Lomita Larga", "Lomita Morada", "Los Alamos", "Los Paramillos", "Los Toscales", "Meseta Colorada", "Mina Volcan Overo", "Morro Del Cuero", "Pampa De Las Yaretas", "Pampa De Los Bayos", "Papagayo", "Pareditas", "Paso De Las Carretas", "Picos Bayos", "Piedras Blancas", "Pircas De Osorio", "Po Alvarado Norte", "Po Alvarado Sur", "Po Amarillo", "Po De Los Escalones", "Po Maipu", "Portillo Canales", "Portillo Cruz De Piedra", "Portillo De Colina", "Portillo De La G Del Camino", "Portillo De La Yesera", "Portillo De Las Cabezas", "Portillo Del Papal", "Portillo Del Viento", "Portillo Occidental Del Bayo", "Portillo Pedernales", "Puesto A Martinez", "Puesto Agua De La Zorra", "Puesto Canales", "Puesto De La Salada", "Puesto El Carrizalito", "Puesto El Jagual", "Puesto F Tello", "Puesto Horqueta", "Puesto J Alvarez", "Puesto J Castro", "Puesto Las Aguadas", "Puesto Las Cortaderas", "Puesto Los Ramblones", "Puesto Luffi", "Puesto Luna", "Puesto Mallin", "Puesto Manga De Arriba", "Puesto Nieves Negras", "Puesto Ojo De Agua", "Puesto P Miranda", "Puesto P Montriel", "Puesto Punta Del Agua", "Puesto Quiroga", "Puesto Rincon De La Pampa", "Puesto S Perez", "Puesto Seco", "Puesto Sosa", "Puesto Ultima Aguada", "Puesto Viuda De Estrella", "R Barri", "Real Bayo", "Real De Moyano", "Real Del Colorado", "Real Del Leon", "Real Del Pelambre", "Real Escondido", "Real Loma Blanca", "Real Piedra Horadada", "Real Primer Rio", "Real Rincon De Las Ovejas", "Refugio La Faja", "Refugio Vialidad", "Rincon Huaiquerias", "Rivas", "S Estrella", "San Carlos", "Tierras Blancas", "Tres Esquinas", "Vega De Praso", "Vegas De Las Ovejas", "Viuda De Satelo", "Volcan Maipu"],
    "5570": ["Alto Del Salvador", "Buen Orden", "La Colonia", "San Martin", "Villa Centenario", "Villa Del Carmen"],
    "5571": ["Chivilcoy", "Colonia Lambare", "Colonias De Montecaseros", "El Alto Salvador", "Espino", "Los Olmos", "Montecaseros", "Villa Molino Orfila"],
    "5572": ["Alto Grande", "El Jume"],
    "5573": ["Colonia Delfino", "El Moyano", "Junin"],
    "5575": ["Andrade", "Los Arboles"],
    "5577": ["El Alto", "Estancia La Argentina", "La Verde", "Rivadavia", "Villa Rivadavia", "Villa San Isidro"],
    "5579": ["El Mirador", "El Retiro", "La Central", "La Florida", "La Libertad", "La Sirena", "Los Campamentos", "Los Otoyanes", "Minelli", "Mundo Nuevo", "Pachango", "Phillips", "Reduccion", "Santa Maria De Oro"],
    "5582": ["Alberto Flores", "Algarrobo Grande", "Alto Verde", "Azcurra", "Balde De La Jarilla", "Balde De Los Gauchos", "Balde E Aquera", "Balde Jofre", "Balde La Pichana Vieja", "Balde Las Carpas", "Balde Las Catitas", "Balde San Agustin", "Carril Norte", "Colonia Monte Caseros", "El Plumero", "El Puntiagudo", "Florindo Flores", "Ingeniero Giagnoni", "Isabel Flores", "La Pastoral", "La Pichana", "La Verde", "Las Torrecitas", "Lola Mora", "Los Ahumados", "Los Eucaliptos", "Los Tordillos", "Masa", "Puesto La Costa", "Puesto La Florida", "Puesto Las Juntitas", "Puesto Las Pichanas", "Puesto Las Viboras", "Puesto Los Causes", "Puesto Los Gauchos", "Puesto Rancho De La Pampa", "Puesto San Jose", "Puesto San Miguel", "Puesto Santa Maria", "Puesto Vega", "Ramblon", "Retamo", "Ricardo Videla", "Roberts", "Ruta 7 Kilometro 1014", "Tapera Negra"],
    "5584": ["Barrio Villa Adela", "Chimbas Palmira", "Colonia Reina", "Gurruchaga", "Palmira", "Reina"],
    "5585": ["El Cipres", "Jorge Newbery", "La Isla", "La Isla Chica", "La Isla Grande", "Los Barriales", "Medrano", "Rodriguez Peña", "Tres Acequias"],
    "5587": ["Isla Chica", "Isla Grande", "San Roque", "Valle Hermoso"],
    "5589": ["Chapanay", "El Central", "El Divisadero", "El Ñango", "La Chimba", "Reyes", "Teresa B De Tittarelli", "Tres Porteñas"],
    "5590": ["Adrian Maturano", "Alejandro Perez", "Alfredo Lucero", "Alto De Los Perros", "Alto De Los Sapos", "Alvarez", "Ana De Donaire", "Anacleta Viuda De Perez", "Andres Perez", "Antonio Sosa", "B Elena", "Bajada Del Perro", "Becerra", "Blas Panelo", "Boyeros", "C Gonzales Videla", "Cadetes De Chile", "Campo El Toro", "Chacras De Lima", "Chamuscao", "Chañaral Redondo", "Cirilo Mahona", "Clarentino Roldan", "Colonia El Regadio", "Corral De Cuero", "Corral Del Molle", "Cruz Del Yugo", "Cruz Ledesma", "Dalmiro Zapata", "Daniel Lucero", "Daniel Morgan", "Delgadillo", "Dionisio Ordoñez", "Dionisio Ortubia", "Domingo Gimenez", "Domingo Lara", "Domingo Oga", "Domingo Real", "Donato Ojeda", "Doroteo Ordoñez", "Dulce", "E Rosales", "El Caranchito", "El Cavado Chico", "El Cercado", "El Chalet", "El Consuelo", "El Gonzano", "El Guerrino", "El Jilguero", "El Lechucito", "El Perino", "El Regadio", "El Vaquero", "El Zampal", "El Zapatino", "Eloy Funes", "Emilio Nieta", "Epifanio Fernandez", "Ernesto Alcaraz", "Estancia La Salcedina", "Estancia La Vizcachera", "Estancia Las Vizcacheras", "Estanislao Ordoñez", "Eusebia Viuda De Gomez", "Evaristo Acevedo", "Evaristo Salas", "Fabriciano Rojas", "Felipe Garro", "Fermin Perez", "Florencio Garro", "Florencio Molina", "Florencio Ordoñez", "Francisco Molina", "Francisco Rojas", "Fructuoso Diaz", "German Maturano", "Gertrudis De Ojeda", "Gilberto Perez", "Gregorio Zapata", "Guillermo Donaire", "H Garzala", "Hermenegildo Diaz", "Honorio Zapata", "Huaicos De Rufino", "Huecos De Los Tordillos", "Ignacio Villegas", "Irineo Zapata", "Isla Retamito", "J Ortubia", "Jose Diaz", "Jose Fernandez", "Jose Lucero", "Jose R Molina", "Jose Suarez", "Juan B Dufau", "Juan H Ortiz", "Juan Millan", "Juan Zapata", "Julio Comeglio", "Junta De Los Rios", "Kilometro 935 Desvio Fcgsm", "La Cautiva", "La Cañada", "La Chapina", "La Cola", "La Cortadera", "La Esquina", "La Estancia", "La Fortuna", "La Isla", "La Leona", "La Paz", "La Primavera", "Ladislao", "Ladislao Campos", "Las Cruces", "Las Rosas", "Las Viscacheras", "Las Vistas", "Las Vizcachas", "Lino Perez", "Lisandro Escudero", "Los Algarrobos", "Los Altamiques", "Los Burgos", "Los Colorados", "Los Horconcitos", "Los Ramblones", "Los Roseti", "Los Tamarindos", "Los Verdes", "Los Villegas", "Lucas Donaire", "Luis Marquez", "M Escudero", "M Quiroga", "Maquinista Levet", "Maravilla", "Maria Garcia", "Maria Viuda De Donaire", "Mario Olguin", "Matias Garro", "Mauricio Calderon", "Medardo Miranda", "Mosmota", "Natalia Donaire", "Necto Sosa", "Nestor Aguilera", "Nicolas Ordoñez", "Onotre Puebla", "Pascual Sosa", "Paso De Las Canoas", "Paulino Matura", "Pedro Castelu", "Pedro Pablo Perez", "Pirquita Embarcadero Fcgsm", "Puente Viejo", "Puerta De La Isla", "Puesto De Garro", "Puesto De Las Carretas", "Puesto De Las Tropas", "Puesto De Olguin", "Puesto De Orozco", "Puesto De Petra", "Puesto De Sosa", "Puesto Del Chañacal", "Puesto El Retamito", "Puesto Nueras", "Puesto Zampal", "Puntos De Agua", "R Bebedera", "Ramblon De La Pampa", "Ramblon Grande", "Ramon Donaire", "Ramon Gimenez", "Regino Ojeda", "Retamo", "Retamo Partido", "Rosario Gatica", "Rufino Gomez", "S Cortis", "San Antonio", "San Pedro", "Santiago Romero", "Saturnino Romero", "Serviliano Ojeda", "Sixto Ledesma", "Teodoro Garro", "Teodoro Villaruel", "Teofila Acevedo", "Teofilo Ruben", "Teofilo Zapata", "Tila", "Tilio Alcaraz", "Tomas Mercado", "Travesia", "Trino Rosaleso", "Vicente Muñoz", "Vicente Peletay", "Villa Antigua", "Villa Vieja", "Viuda De Orozco", "Zanon Canal"],
    "5591": ["Alpatacal", "Circunvalacion", "El Gigantillo", "La Favorita", "La Jacintita", "La Porteña", "Las Totoritas", "Sopanta", "Villa La Paz"],
    "5592": ["El Carbalino", "El Colorado", "La Bandera", "La Dormida"],
    "5594": ["Alto Con Zampa", "Arancibia", "Aranzabal", "B De Araya", "B De Quebrado", "Bajo Del Yuyo", "Balde Las Lagunitas", "Balde Nuevo", "Banderita", "Belle Ville", "Borde De La Linea", "Casa De Adobe", "Catitas Viejas", "Chilote", "Clodomiro Reta", "Colonia San Jorge", "Comandante Salas", "Cristobal Lopez", "Cruz Gimenez", "D Lopez", "Divisadero", "El Algarrobo", "El Bonito", "El Cabao Viejo", "El Carmen", "El Chacallal", "El Corbalno", "El Divisadero", "El Escondido", "El Gorgino", "El Guanaco", "El Lemino", "El Luquino", "El Marcado", "El Marucho", "El Maurino", "El Molino", "El Plumero", "El Porvenir", "El Retamoso", "El Retiro", "El Tamarindo", "El Valle", "El Villeguino", "El Vilteguino", "El Zampal", "El Zorzal", "Emiliano Lucero", "Ernesto Lopez", "Escudero", "Estancia El Bonito", "Estancia Gil", "Estancia La Chuña", "Felipe Perez", "Gobernador Civit", "Huaicos De Rufino", "Jarilloso", "Jofre", "Jose Campos", "Jose Sosa", "Kilometro 947", "L Del Aguero", "L Perez", "La Angelina", "La Argentina", "La Cienaguita", "La Clarita", "La Colonia Sud", "La Florida", "La Jacinto", "La Lagunita", "La Porteña", "La Sombrilla", "Las Arabias", "Las Catitas", "Las Gatitas", "Las Rajaduras", "Las Vayas", "Lezcano", "Lira", "Loma Del Chañar", "Lomas Blancas", "Lomas Coloradas", "Los Medanos Negros", "Los Moros", "Los Verdes", "Los Yoles", "Maturana", "Meliton Campos", "Miguez", "Moron Chico", "Moron Viejo", "N Zapata", "Navarro", "P Rosales", "Peña", "Pichi Ciego Estacion Fcgsm", "Ponce", "Puesto El Trueno", "Puesto Garcia", "Puesto Lorca", "Puesto San Vicente", "Punta Del Canal", "R Bustos", "Rodriguez", "San Pedro", "Santa Ana", "Santa Maria", "Santo Domingo", "T Orozco", "Talquenca", "Urisa"],
    "5595": ["Cupiles", "El Algarrobo", "El Colorado", "Estancia Las Chilcas", "La Chilca", "La Chuna", "Los Embarques", "Ñacuñan", "Ñancuñan"],
    "5596": ["12 De Octubre", "Balde De Piedra", "La Costa", "Recoaro", "Santa Rosa", "Villa Catala"],
    "5598": ["Bañado Verde", "Desaguadero", "Pampita Embarcadero Fcgsm", "Tapon"],
    "5600": ["Agua De La Mula", "Agua Nueva", "Algarrobo De Sortue", "Cajon De Mayo", "Central Hidroelectrica 1", "Central Hidroelectrica 2", "Colonia La Llave", "Colonia Soitue", "Com Nac De Energia Atomica", "Comision Nac De Emergencia", "Cuesta De Los Terneros", "El Cerrito", "El Picona", "El Plateado", "Embalse Valle Grande", "Estancia El Campamento", "Estancia La Sarita", "Estancia La Trintrica", "Estancia Los Huaicos", "Estancia Los Leones", "Estancia Sofia Raquel", "Estancia Tierras Blancas", "La Carusina", "La Jaula", "La Lata", "La Llave Nueva", "La Mina Del Peceño", "La Picarona", "La Picasa", "La Pichana", "La Tosca", "Los Claveles", "Los Patos", "Los Pejecitos", "Los Repuntes", "Los Terneros", "Los Tolditos", "Minas El Sosneado", "Pta Del Agua Vieja", "Pueblo Diamante", "Pueblo Soto", "Puesta El Cavado", "Puesto Agua De La Liebre", "Puesto Agua Del Medano", "Puesto El Jilguero", "Puesto Las Puntanas", "San Rafael"],
    "5601": ["Capitan Montoya", "El Usillal", "Iguazu", "Las Paredes", "Resolana"],
    "5603": ["Cañada Seca", "Colonia Colomer", "Colonia Elena", "Colonia Rusa", "Cuadro Benegas", "El Porvenir", "El Tropezon", "Goudge", "Ingeniero Balloffet", "La Llave", "La Llave Vieja", "Los Pejes", "Pedro Vargas", "Pueblo Echevarrieta", "Rama Caida", "Rincon Del Atuel", "Rodolfo Iselin", "Salto De Las Rosas"],
    "5605": ["Calle Larga Vieja", "Colonia Atuel Norte", "El Nihuil", "Las Malvinas", "Minas Del Nevado", "Nihuil", "Salinas El Diamante", "Santa Teresa"],
    "5607": ["Colonia Bombal Y Tabanera", "Colonia Española", "Cuadro Bombal", "Cuadro Nacional", "El Algarrobal", "Tabanera"],
    "5609": ["Aristides Villanueva", "El Campamento", "Gaspar Campos", "Goico", "Guadales", "Monte Coman"],
    "5611": ["Agua Rica", "Aguada Puesto La Totora", "Balde El Sosneado", "Bardas Blancas", "Baños De Azufre", "Boliche Los Barreales", "Calmuco", "Campamento Carapacho", "Cañada Amarilla", "Cerro Alquitran", "Chacharalen", "Coihueco", "Coihueco Norte", "El Alambrado", "El Cienago", "El Durazno", "El Manzano", "El Mollar", "El Sosneado", "Ex Fortin Malargue", "Jaguel", "Jaguel Amarillo", "Jaguel De Rosas", "Jaguel Del Catalan", "La Valenciana", "Llano Blanco", "Los Arroyos", "Los Britos", "Los Molles", "Los Parlamentos", "Los Ramblones", "Luanco", "Malal Del Medio", "Matoncilla", "Nire Co", "Ojo De Agua", "Puesto Gentile", "Puesto Marfil", "Puesto Rincon Escalona", "Ranquil Norte", "Rincon De Correa"],
    "5612": ["Valle De Las Leñas"],
    "5613": ["Agua Botada", "Agua De Cabrera", "Agua Del Chancho", "Aguada Penepe", "Aguada Perez", "Bajo Del Peludo", "Barreal Colorado", "Barreal De La Mesilla", "Barreal Jose Luis", "Barriales Los Ranchos", "Beltran", "Boliche", "Buta Billon", "Cabeza De Vaca", "Cajon Grande", "Campamento Ranquilco", "Campo El Alamo", "Cancha De Esqui", "Cañada Ancha", "Cañada Colorada", "Chachao", "Charco Vacas", "Coronel Beltran", "El Alamo", "El Cajon", "El Chacay", "El Choique", "El Payen", "El Puestito", "El Vatro", "El Zampal", "Guayqueria Colorada", "Hotel Portezuelo Del Viento", "Hotel Termas Del Azufre", "Hotel Termas El Sosneado", "Jaguel Del Gaucho", "Jaguel Del Gobierno", "Junta De La Vaina", "La Bandera", "La Barda Cortada", "La Batra", "La Cortadera", "La Estrechura", "La Junta", "La Negrita", "La Salinilla", "La Yesera", "Laguna Negra", "Laguna Salada", "Las Chacras", "Las Juntas", "Las Loicas", "Las Taguas", "Las Vegas", "Las Yeguas", "Loma Extendida", "Loma Jaguel Del Gaucho", "Lomas Altas", "Lomas Chicas", "Lonco Vacas", "Los Barriales", "Los Carrizales", "Los Colados", "Los Pozos", "Malargue", "Mallin Quemado", "Matancilla", "Mechanquil", "Mechenguil", "Mina Argentina", "Mina Ethel", "Mina Huemul", "Mina Santa Cruz", "Minacar", "Molino", "P Planchon", "Pampa Amarilla", "Pata Mora", "Patimalal", "Payun", "Po Del Huanaco", "Po Mallan", "Po Pehuenche", "Portezuelo Choique", "Puerto Rincon Escalona", "Puesto Agua Amarga", "Puesto Agua De La Merina", "Puesto Atamisqui", "Puesto Gendarmeria Nacional Po", "Puesto La Cachaca", "Puesto La Invernada", "Puesto La Negrita", "Puesto La Niebla", "Puesto La Porteña", "Puesto La Suiza", "Puesto La Ventana", "Puesto Malo", "Puesto Rincon Del Sauce", "Quircaco", "Ranchitos", "Ranquilco Pozos Petroliferos", "Refugio Militar Gral Alvarado", "Rincon Chico", "Rincon De La Ramada Chato", "Rincon Escondido", "Rio Barrancas", "Rio Chico", "Rio Grande", "Tapera De Los Viejos", "Toscal Del Toro", "V N De Cochiquita"],
    "5615": ["25 De Mayo", "Colonia Pascual Iaccarini", "Los Reyunos", "Piedra De Afilar"],
    "5620": ["El Juncalito", "El Nevado", "General Alvear", "Kilometro 56", "Kilometro 882", "La Pomona", "Villa Comparto"],
    "5621": ["Agua De Torre", "Agua Del Toro", "Agua Escondida", "Carmensa", "Cañadon De Bonilla", "Cerro Del Chacay", "Cerro Nevado", "Cerro Yalguaras", "Cochico", "El Azufre", "El Ceibo", "El Desvio", "El Ventarron", "Estancia Chacaico", "La California", "Los Compartos", "Los Corrales", "Los Tordillos", "Posta De Hierro", "Poste De Fierro", "Puesto La Caldenada", "Puesto Loreto", "Puesto Lunina", "Punta Del Agua", "San Pedro Del Atuel", "Tambito"],
    "5622": ["Colonia Jauregui", "Colonia Lopez", "Finca Lopez", "La Guevarina", "La Quebrada", "Villa Atuel"],
    "5623": ["Atuel Sud", "Colonia Atuel", "Jaime Prats", "La Vasconia", "Negro Quemado"],
    "5624": ["Kilometro 47", "Palermo Chico", "Real Del Padre"],
    "5632": ["Colonia Alvear", "Colonia Alvear Oeste", "Colonia Bouquet", "Compuertas Negras", "El Retiro", "La Marzolina", "Las Compuertas Negras", "Pueblo Luna", "Soitue"],
    "5633": ["Ochenta Y Cuatro"],
    "5634": ["Bowen", "Ciudad Oeste", "El Banderon", "El Buen Pastor", "El Refugio", "Estancia El Balderon", "Estancia La Cortadera", "Estancia La Varita", "Kilometro 84", "Kilometro 884", "La Adelina", "La Caldenada", "La Corona", "La Escandinava", "La Lunina", "La Montilla", "La Seña", "La Varita", "Los Amarillos", "Los Angeles", "Los Campamentos", "Santa Elena", "Vuelta Del Zanjon"],
    "5636": ["Canalejas", "El Aguila", "El Arbolito", "Favelli", "La Mora", "Los Huarpes", "Medanos Colorados", "Mojon Ocho", "Nueva Constitucion", "Paso De Los Gauchos", "Pto Los Amarillos", "Puesto De La Corona", "Puesto Del Buen Pastor", "Puesto La Seña", "Puesto Vuelta Del Zanjon", "Toscal"],
    "5637": ["30 De Octubre", "Corral De Lorca", "Costa Del Diamante", "El Plumerito", "La Cañada", "La Lechuga", "Ovejeria", "Pampa Del Tigre", "Plumerito", "Usiyal"],
    "5645": ["El Cenizo"],
    "5700": ["Alto Blanco", "Alto Grande", "Cortaderas", "El Quebracho", "La Cortadera", "La Espesura", "La Nelida", "Pescadores", "Pozo Escondido", "Represa Del Monte", "San Luis", "Santa Teresa", "Santo Domingo", "Tres Marias"],
    "5701": ["11 De Mayo", "9 De Julio", "Algarrobitos", "Antihuasi", "Arenilla", "Balde De La Isla", "Buena Ventura", "Buena Vista", "Carolina", "Casa De Piedra", "Cañada Honda", "Cañada Honda De Guzman", "Cerro Blanco", "Cerro De Piedra", "Cerros Largos", "Chipical", "Cruz De Caña", "Cruz De Piedra", "Cuchi Corral", "Daniel Donovan", "El Amparo", "El Arenal", "El Chorrillo", "El Durazno", "El Manantial Escondido", "El Tala", "El Talita", "El Trapiche", "El Valle", "El Volcan", "Embalse La Florida", "Estancia Grande", "Gruta De Intihuasi", "Hinojito", "Intihuasi", "Isla", "Juana Koslay", "La Alianza", "La Bajada", "La Calaguala", "La Cienaga", "La Florida", "La Higuerita", "La Pampa", "Laguna Brava", "Las Barranquitas", "Las Chacras De San Martin", "Las Vertientes", "Los Arroyos", "Los Carricitos", "Los Montes", "Los Pasitos", "Los Puquios", "Los Tapiales", "Manantial Blanco", "Maray", "Marmol Verde", "Mina Carolina", "Mina Santo Domingo", "Monte Chiquito", "Ojo De Agua", "Pampa De Los Gobernadores", "Pampa Del Tamborero", "Pampita", "Pantanillos", "Paso De Cuero", "Paso Del Rey", "Paso Juan Gomez", "Potrero De Los Funes", "Quebrada De La Burra", "Rio Grande", "San Jose De Los Chañares", "San Miguel", "San Roque", "Santa Clara", "Saucesito", "Sol De Abril San Martin", "Solobasta", "Talarcito", "Totoral", "Tukiros", "Valle De La Pancanta", "Vallecito", "Virarco"],
    "5703": ["6 De Septiembre", "Ahi Veremos", "Alta Gracia", "Alto", "Arbol Solo", "Balde De Amira", "Balde Del Rosario", "Barranca Colorada", "Cañada Angosta", "Divisadero", "El Bagual", "El Balde", "El Barrial", "El Chañar", "El Espinillo", "El Paraiso", "El Potrero De Leyes", "El Salto", "Espinillo", "Hipolito Yrigoyen", "La Chilca", "La Corina", "La Duda", "La Escondida", "La Esperanza", "La Eulogia", "La Garza", "La Julia", "La Majada", "La Quebrada", "La Salud", "La Sandia", "La Serrana", "La Union", "Las Caritas", "Las Lomas", "Leandro N Alem", "Longari", "Los Algarrobos", "Los Chañares", "Los Molles", "Los Ramblones", "Manantiales", "Nogoli", "Paliguanta", "Paraiso", "Pozo Del Carril", "Pozo Del Espinillo", "Pozo Del Tala", "Pozo Santiago", "Pozo Simon", "Represa Del Chañar", "Retamo", "Retiro", "Rumiguasi", "San Jose", "San Raimundo", "San Roque", "Taza Blanca", "Toro Negro", "Villa De La Quebrada", "Villa General Roca", "Vizcacheras"],
    "5705": ["Agua Hedionda", "Balde Hondo", "Banda Sud", "Bañado Lindo", "Bella Vista", "Campanario", "La Bava", "La Porfia", "La Represita", "Las Salinas", "Maravilla", "Pampa Invernada", "Posta Del Portezuelo", "Pozo Cavado", "Pozo De Los Rayos", "Puerto Rico", "Puesto Pampa Invernada", "Puesto Quebrada Cal", "Ramadita", "Ramblones", "Rio Juan Gomez", "Rodeo Cadenas", "San Francisco Del Monte De Oro", "Socoscora", "Tintitaco"],
    "5707": ["Aguaditas", "Algarrobal", "Balde De Arriba", "Balde De Azcurra", "Balde De Puertas", "Baldecito La Pampa", "Barriales", "Barzola", "Bañado", "Bella Vista Botijas", "Botijas", "Cantantal", "Carmelo", "Cerro Bayo", "Cerro Negro", "Chimbas", "Chimborazo", "El Mollarcito", "El Payero", "El Rincon", "El Verano", "El Zampal", "La Patria", "La Salvadora", "Las Lagunitas", "Las Mesias", "Las Pampitas", "Lindo", "Los Almacigos", "Los Mendocinos", "Monte Carmelo", "Pampa Grande", "Paso De Piedra", "Pastal", "Peñon Colorado", "Pozo Del Molle", "Reconquista", "San Rufino", "San Salvador", "Santa Victoria", "Santo Domingo", "Serafina", "Sol De Abril", "Temeraria", "Vista Alegre"],
    "5709": ["Bañadito Viejo", "Cañada Quemada", "Cebollar", "Consulta", "Corral De Piedra", "El Manantial", "El Molino", "La Esquina", "La Legua", "Los Pejes", "Lujan", "Manantial", "Santa Rufina", "Santa Teresita"],
    "5710": ["La Punta"],
    "5711": ["Angelita", "Bajada", "Balde Retamo", "Balde Viejo", "Bañadito", "Bañado De Cautana", "Baños Zapallar", "Becerra", "El Bañado", "El Calden", "El Chañar", "El Injerto", "El Potrerillo", "El Puesto", "El Quebracho", "El Retamo", "El Rio", "El Zapallar", "Entre Rios", "Estancia La Blanca", "Estancia La Union", "La Aguada", "La Brea", "La Florida", "La Linea", "La Represita", "La Union", "La Vertiente", "Las Claritas", "Las Playas", "Las Puertas", "Los Chenas", "Los Molles", "Naranjo", "Paso Del Medio", "Pie De La Cuesta", "Puesto De Tabares", "Puesto Talar", "Puntos De La Linea", "Quebrada Del Tigre", "Quines", "Represa Del Monte", "San Miguel", "Santa Ana Quines", "Santa Clara", "Talita"],
    "5713": ["Balde Ahumada", "Balde De Guardia", "Balde De La Linea", "Balde De Torres", "Balde El Carril", "Baldecito", "Candelaria", "El Cadillo", "El Hormiguero", "El Mollar", "El Puestito", "El Sembrado", "La Bajada", "La Colonia", "La Medula", "La Moderna", "La Plata", "La Ramada", "La Resistencia", "La Sirena", "La Tusca", "Las Bajadas", "Las Chimbas", "Las Playas Argentinas", "Los Arces", "Medano Bello", "Patio Limpio", "Puesto Roberto", "Quebrachito", "Salinas", "San Celestino", "San Martin", "San Pedro", "Tres Cañadas"],
    "5715": ["Arbol Verde", "Balde De Escudero", "Balde De Garcia", "Balde De Guiñazu", "Balde De Ledesma", "Balde De Monte", "Balde De Nuevo", "Balde De Quines", "Balde Del Escudero", "Cañada", "El Alto", "El Barrial", "El Pocito", "El Tembleque", "Florida", "Islitas", "Las Cabras", "Las Islitas", "Las Palomas", "Las Rosadas", "Los Algarrobitos", "Los Cerrillos", "Pocitos", "Pozo Del Medio", "San Jorge", "Santa Lucia", "Santa Lucinda"],
    "5717": ["El Calden", "El Pimpollo", "Kilometro 732"],
    "5719": ["Agua Amarga", "Aguadita", "Alazanas", "Algarrobos Grandes", "Altillo", "Alto Negro", "Bajo De La Cruz", "Bebida", "Bella Estancia", "Cañada De Vilan", "Chacras Del Cantaro", "Charlone", "Charlones", "Chipiscu", "El Calden", "El Carmen", "El Charabon", "El Dichoso", "El Jarillal", "El Molle", "El Pedernal", "El Ramblon", "El Valle", "Estancia El Medano", "Estancia Rivadavia", "Estancia San Roque", "Gigante", "Gualtaran", "Hualtaran", "La Aguada", "La Alameda", "La Calera", "La Chañarienta", "La Empajada", "La Estrella", "La Florida", "La Josefa", "La Juanita", "La Merced", "La Primavera", "La Yesera", "Las Barrancas", "Las Galeras", "Las Lagunas", "Lomas Blancas", "Los Aguados", "Los Araditos", "Los Cerritos", "Los Chancaros", "Los Talas", "Los Telarios", "Monte Verde", "Moyarcito", "Portezuelo", "Puerto Alegre", "Puesto Balzora", "Punta De La Sierra", "Recreo", "Represa Del Carmen", "Romance", "San Agustin", "San Antonio", "San Geronimo", "San Isidro", "San Jose", "San Pedro", "San Roque", "Santa Ana", "Santa Maria", "Santa Rosa", "Santa Rosa Del Chipiscu", "Santa Rosa Del Gigante", "Tres Lomas", "Tres Puertas"],
    "5721": ["Agua Seballe", "Aguas De Piedras", "Alto Del Valle", "Alto Pelado", "Beazley", "Caña Larga", "Cerro Varela", "Cerro Viejo", "Chalanta", "Chichaquita", "Chischaca", "Colonia Santa Virginia", "El Cazador", "El Molle", "El Socorro", "El Totoral", "Estacion Zanjitas", "Fortin Salto", "Gorgonta", "Huejeda", "La Agua Nueva", "La Amarga", "La Bonita", "La Cañada", "La Costa", "La Dulce", "La Emilia", "La Irene", "La Jerga", "La Peregrina", "La Represa", "La Seña", "La Tosca", "La Totora", "La Verde", "Las Colonias", "Las Gamas", "Las Lagunitas", "Las Piedritas", "Las Tres Cañadas", "Las Vizcacheras", "Los Cerrillos", "Los Chañaritos", "Los Claveles", "Los Coros", "Mosmota", "Paje", "Paso Ancho", "Paso De La Tierra", "Paso De Las Salinas", "Paso De Las Toscas", "Paso De Las Vacas", "Paso De Los Bayos", "Pozo Cercado", "Puente La Orqueta", "Puerta De La Isla", "Puesto De Los Jumes", "Punta Del Cerro", "Puntos De Agua", "Salitral", "Salto Chico", "San Antonio", "San Geronimo", "San Jorge", "San Martin", "San Vicente", "Santa Isabel", "Santo Domingo", "Tamascanes", "Transval", "Travesia", "Tres Cañadas", "Vacas Muertas", "Varela"],
    "5722": ["Acasape", "Alto Del Leon", "Alto Grande", "Balda", "Campo De San Pedro", "El Riecito", "Eleodoro Lobos", "Juan W Gez", "La Delia", "La Maria", "La Yerba Buena", "Las Cañitas", "Las Higueras", "Lince", "Santa Dionisia"],
    "5724": ["Alto Pencoso", "Balde", "Bebedero", "Bella Vista", "Chosmes", "Desaguadero", "El Charco", "El Lechuzo", "El Mataco", "El Milagro", "El Negro", "Guasquita", "Jarilla", "La Brea", "La Cabra", "La Reforma", "La Selva", "La Union", "Laguna Seca", "Los Jagueles", "Los Tamariños", "Mantilla", "Mataco", "Negro Muerto", "Palomar", "Paso Los Algarrobos", "Reforma Chica", "Salinas Del Bebedero", "San Antonio", "Santa Rita"],
    "5730": ["20 De Febrero", "Agua Del Portezuelo", "Chacra La Primavera", "Ciudad Jardin De San Luis", "Coronel Alzogaray", "El Chañar", "El Dique", "El Fortin", "Estancia El Chamico", "Estancia El Divisadero", "Estancia El Quebrachal", "Estancia El Saucecito", "Estancia La Guardia", "Estancia La Reserva", "Estancia La Zulemita", "Estancia Las Bebidas", "Estancia Los Hermanos", "Estancia Los Nogales", "Estancia San Alberto", "Estancia San Francisco", "La Negra", "La Primavera", "Las Isletas", "Las Palmas", "Lavaisse", "Liborio Luna", "Marlito", "Medano Chico", "Medano Grande", "Pedernera", "Puesto Bella Vista", "Puesto El Tala", "San Ramon", "Santa Clara", "Tres Esquinas", "Villa Mercedes", "Villa Santiago", "Vista Hermosa"],
    "5731": ["Alfaland", "Cerro Blanco", "Cerro Negro", "El Morro", "El Pasajero", "El Plateado", "El Sarco", "Estancia La Guillermina", "Estancia La Morena", "Estancia San Antonio", "Juan Jorba", "Juante", "La Angelina", "La Bertita", "La Gama", "La Iberia", "La Javiera", "La Negrita", "La Portada", "Las Carolinas", "Las Praderas", "Lomas Blancas", "Los Cisnes", "San Jose Del Morro", "San Juan De Tastu", "Tasto", "Viscacheras"],
    "5733": ["Cramer", "Villa Reynolds"],
    "5734": ["La Ribera"],
    "5735": ["Colonia Bella Vista", "Isondu", "Juan Llerena", "La Venecia"],
    "5736": ["Comandante Granville", "Fraga", "La Adela", "La Cautiva", "Medanos", "Paines", "Paso De Las Carretas", "San Ignacio"],
    "5738": ["Avanzada", "Caldenadas", "Colonia Luna", "El Carmen", "El Mangrullo", "El Nasao", "General Pedernera", "Justo Daract", "Kilometro 656", "La Carmen", "La Elida", "La Garrapata", "La Magdalena", "La Mascota", "La Tula", "Las Encadenadas", "Las Meladas", "Las Totoritas", "Los Cesares", "Los Esquineros", "Los Medanos", "Los Pozos", "Paunero", "Rio Quinto", "Santa Catalina"],
    "5741": ["13 De Enero", "Alto Verde", "Aviador Origone", "Bajos Hondos", "Capelen", "El Calden", "La Elisa", "La Flecha", "La Josefina", "La Palmira", "La Realidad", "La Silesia", "Laguna Capelen", "Laguna Sayape", "Nossar", "Portada Del Sauce", "San Jose Del Durazno"],
    "5743": ["La Isabel", "Nueva Escocia", "San Camilo"],
    "5750": ["Alto De La Leña", "Arboleda", "Canteras Santa Isabel", "Casas Viejas", "Cañada Del Pasto", "Cañada San Antonio", "Cerro De La Pila", "Cerro Verde", "Cuatro Esquinas", "Dique La Florida", "El Blanco", "El Portezuelo", "El Pozo", "El Rosario", "El Salado", "El Vallecito", "Establecimiento Las Flores", "Estancia El Salado", "La Aguada", "La Alameda", "La Atalaya", "La Cañada", "La Fragua", "La Justa", "La Providencia", "La Rinconada", "La Toma", "Las Delicias", "Las Flores", "Las Peñas", "Las Rosas", "Loma Del Medio", "Ojo De Agua", "Piedras Blancas", "Quebrada Honda", "Riecito", "San Antonio", "Santa Isabel", "Sololosta", "Tamboreo", "Yacoro"],
    "5751": ["Agua Salada", "El Chañar", "El Talita", "La Arboleda", "La Petra", "La Totora", "Los Medanitos", "Los Membrillos", "Manantial Grande", "Saladillo", "San Gregorio", "Santa Clara"],
    "5753": ["Agua Linda", "Ancamilla", "Arroyo La Cal", "Bajo De Conlara", "Bajo La Laguna", "Casa De Condor", "Casa De Piedra", "Cañada Blanca", "Cañada Del Puestito", "Cañada La Tienda", "Cañada Quemada", "Cerrito", "Cerro Colorado", "Chacritas", "Chutunsa", "Consuelo", "Corral Del Tala", "Corrales", "Cruz Brillante", "Divisadero", "Dormida", "El Baldecito", "El Burrito", "El Cardal", "El Cerrito", "El Condor", "El Coro", "El Pajarete", "El Pantanillo", "El Pantano", "El Paraguay", "El Progreso", "El Puerto", "El Salado", "El Salto", "El Talita", "El Valle", "Hinojos", "Hornito", "La Agueda", "La Carmencita", "La Dora", "La Esperanza", "La Esquina", "La Esquina Del Rio", "La Estancia", "La Huerta", "La Ramada", "La Totora", "La Ulbara", "Laguna Larga", "Las Chacras", "Las Chacritas", "Las Flores", "Las Lajas", "Las Lomas", "Las Mangas", "Las Toscas", "Los Alamos", "Los Algarrobos", "Los Comederos", "Los Corrales", "Los Hinojos", "Los Lechuzones", "Los Molles", "Los Sauces", "Los Talas", "Manantial Lindo", "Ojo De Agua", "Pampa Del Bajo", "Pantanillo", "Paso Grande", "Piedra Bola", "Piedra Larga", "Piedra Rosada", "Piedra Sola", "Planta De Sandia", "Potrerillo", "Pozo Seco", "Puestito", "Quebrada De Los Barrosos", "San Fernando", "San Isidro", "San Jose", "San Lorenzo", "San Miguel", "San Pedro", "San Rafael", "San Ramon", "Sauce", "Venta De Los Rios", "Villa De Praga"],
    "5755": ["Alto Del Molle", "Alto Del Valle", "Cañaditas", "Cerrito Negro", "Cueva De Tigre", "El Bajo", "El Hornito", "El Paraiso", "El Peje", "El Puesto", "El Rincon", "Fortuna De San Juan", "La Huertita", "La Mina", "La Puerta", "Las Barranquitas", "Las Chacras De San Martin", "Las Higueras", "Los Poleos", "Manantial", "Media Luna", "Pampa", "Piedras Anchas", "Puerta De Palo", "Quebrada De La Mora", "Quebrada De San Vicente", "Salado", "San Martin"],
    "5757": ["San Lorenzo"],
    "5759": ["Calera Argentina", "Caleras Cañada Grande", "Conlara", "El Puesto", "Guanaco", "Huchisson", "La Esquina", "La Guardia", "La Suiza", "Las Canteras", "Los Corralitos", "Los Mollecitos", "Manantial De Renca", "Mollecito", "Naschel", "Piedras Chatas", "Retazo Del Monte", "San Felipe"],
    "5763": ["General Urquiza"],
    "5770": ["Chacras Viejas", "Concaran", "El Arroyo", "El Bañado", "El Calden", "El Cavado", "El Cerro", "El Poleo", "El Sauce", "El Socorro", "Fenoglio", "La Elvira", "La Gramilla", "Las Nieves", "Los Comedores", "Los Puestos", "Los Quebrachos", "Mina Los Condores", "San Vicente", "Santa Martina", "Santa Simona", "Villa Dolores"],
    "5771": ["Alanices", "Arboles Blancos", "Arroyo De Vilches", "Barranquitas", "Cabeza De Novillo", "Cain De Los Tigres", "Cañada De Atras", "Cañada De Los Tigres", "Cortaderas", "El Rodeo", "El Salado De Amaya", "El Salvador", "Guanaco Pampa", "Huertas", "La Aurora", "La Chilla", "La Sala", "Laguna De Patos", "Las Aguadas", "Los Lobos", "Pampa Grande", "Puerta Colorada", "Rincon Del Carmen", "Salado De Amaya", "San Isidro", "Tala Verde", "Totoral", "Totorilla", "Unquillo"],
    "5773": ["Cañada", "Cañada De Las Lagunas", "Cañitas", "Chañar De La Legua", "Crucecitas", "Cuatro Esquinas", "Duraznito", "El Olmo", "El Poleo", "El Porvenir", "El Torcido", "El Totoral", "El Vallecito", "Ensenada", "Guzman", "La Armonia", "La Cocha", "La Cristina", "La Crucesita", "La Elvira", "La Estanzuela", "La Florida", "La Mesilla", "La Riojita", "Laguna De La Cañada", "Laguna De Los Patos", "Las Cañas", "Las Lagunas", "Las Raices", "Los Condores", "Los Duraznitos", "Los Manantiales", "Los Noques", "Otra Banda", "Paso De Los Algarrobos", "Pozo Frio", "Puente Hierro", "Punta De La Loma", "Punta Del Alto", "Riojita", "San Pablo", "Santa Maria", "Selci", "Tilisarao", "Vieja Estancia"],
    "5775": ["Bajo Grande", "El Algarrobal", "La Escondida", "Los Sauces", "Manantial De Flores", "Piscoyaco", "Renca", "San Ramon Sud", "Valle San Agustin", "Valle San Jose"],
    "5777": ["Adolfo Rodriguez Saa", "Barrio Blanco", "Cañada De La Negra", "Cañada Grande", "Cañada Verde", "Cerrito Blanco", "Chilcas", "Corral De Torres", "Duraznito", "El Pueblito", "Invernada", "Las Chilcas", "Las Tigras", "Los Arguellos", "Los Chañares", "Los Peros", "Los Roldanes", "Los Tigres", "Moyar", "Ojo Del Rio", "Paso De La Cruz", "Picos Yacu", "Pizarras Bajo Velez", "Pozo De Las Raices", "Santa Rosa De Conlara"],
    "5779": ["La Chilca"],
    "5800": ["Pueblo Alberdi", "Rio Cuarto"],
    "5801": ["Alpa Corral", "Campo De La Torre", "Colonia El Carmen Paraje", "Colonia La Piedra", "Colonia Paso Carril", "Costa Del Tambo", "Cuatro Vientos", "El Bañado", "El Duraznito", "El Potosi", "El Tambo", "La Aguada", "La Cumbre", "La Esquina", "La Invernada", "La Mesada", "La Veronica", "Las Abahacas", "Las Albahacas", "Las Calecitas", "Las Cañitas", "Las Guindas", "Las Moras", "Las Tapias", "Monte La Invernada", "Permanentes", "Piedra Blanca", "Rio Seco", "Rodeo Viejo", "San Bartolome", "Villa El Chacay", "Villa Santa Rita"],
    "5803": ["La Cañada Grande", "Paso Del Durazno", "Reduccion"],
    "5805": ["Carnerillo", "Chucul", "Colonia Santa Paula", "Las Higueras"],
    "5807": ["Bengolea", "Charras", "Lagunillas", "Olaeta", "Pastos Altos"],
    "5809": ["Colonia Dolores", "General Cabrera", "Puente Los Molles"],
    "5811": ["Coronel Baigorria", "Espinillo"],
    "5813": ["Alcira Gigena", "Alpapuca", "Bajada Nueva", "Capilla De Tegua", "Dos Lagunas", "El Barreal", "El Chiquillan", "El Espinillal", "La Calera", "La Ramoncita", "La Sierrita", "Laguna Clara", "Tegua"],
    "5815": ["Elena", "Los Medanos"],
    "5817": ["Berrotaran", "Cañada Del Sauce", "La Dormida", "Las Peñas", "Paso Cabral", "Puerta Colorada"],
    "5819": ["Arroyo Santana", "Arroyo Toledo", "Cañada De Alvarez", "El Manantial", "La Calera", "Las Caleras", "Las Gamas", "Las Peñas Sud", "Paso Sandialito", "Sierra Blanca", "Villa La Coba"],
    "5821": ["Campo San Antonio", "Cerro Colorado", "Cerro San Lorenzo", "El Cano", "Guindas", "Los Cerros Negros", "Los Cocos", "Permanentes", "Rio De Los Sauces", "Rodeo De Los Caballos", "Rodeo Las Yeguas"],
    "5823": ["Las Peñas Norte", "Los Condores", "Modesto Acuña"],
    "5825": ["Arroyo Santa Catalina", "Arsenal Jose Maria Rojas", "Holmberg", "La Lagunilla", "Las Ensenadas", "Santa Catalina"],
    "5829": ["Chañaritos", "Laguna Seca", "Sampacho", "Soria"],
    "5831": ["9 De Julio", "Agua Fria", "Aguada", "Boca Del Rio", "Chancarita", "El Sauce", "El Talita", "Estacion Achiras", "Estanzuela", "La Aguada", "La Cañada", "La Colorada", "La Hermosura", "La Punilla", "La Rosada", "Los Alamos", "Monte De Los Gauchos", "No Es Mia", "Posta De Fierro", "Primer Agua", "Real", "San Alberto", "San Alejandro", "San Nicolas Punilla", "San Pedro", "Santa Clara", "Santa Felisa", "Santa Isabel", "Toigus"],
    "5833": ["Achiras", "La Barranquita"],
    "5835": ["Bella Vista", "Dominguez", "El Tala", "La Argentina", "La Aurora", "Los Chañares", "Los Cuadros", "Piquillines", "Porvenir", "San Antonio", "Uspara", "Villa Del Carmen", "Volcan Estanzuela"],
    "5837": ["Chajan", "Glorialdo Fernandez", "San Lucas Norte", "Suco"],
    "5839": ["Estacion Punta De Agua", "Las Vertientes", "Los Jagueles", "Malena", "Punta Del Agua", "Zapoloco"],
    "5841": ["Colonia Orcovi", "La Carolina", "La Mercantil", "Las Cinco Cuadras", "San Basilio", "Yatay"],
    "5843": ["Adelia Maria"],
    "5845": ["Bulnes"],
    "5847": ["Colonia Dean Funes", "Colonia La Celestina", "Coronel Moldes", "Fragueyro"],
    "5848": ["La Brianza", "La Gilda", "Las Acequias", "San Ambrosio", "San Bernardo"],
    "5850": ["Barrio Del Libertador", "Colonia Luque", "Fabrica Militar Rio Tercero", "Los Potreros", "Rio Tercero"],
    "5851": ["Colonia Santa Catalina", "Las Bajadas", "Los Tres Pozos", "Monsalvo"],
    "5853": ["Corralito"],
    "5854": ["Almafuerte", "El Quebracho", "El Salto Norte", "La Cascada"],
    "5856": ["Embalse"],
    "5857": ["Cnia Vacaciones De Empleado", "Segunda Usina", "Unidad Turistica Embalse", "Villa Aguada De Los Reyes", "Villa Sierras Del Lago"],
    "5859": ["Arroyo San Antonio", "Cañada Del Tala", "Cerros Asperos", "La Cruz", "Lutti", "Tala Cruz", "Tigre Muerto", "Usina Nuclear Embalse", "Villa Del Tala", "Villa Quillinzo"],
    "5862": ["Villa Del Dique"],
    "5864": ["El Torreon", "Valle Dorado", "Villa Del Parque", "Villa Naturaleza", "Villa Rumipal"],
    "5865": ["Colonia Videla"],
    "5870": ["Barrio La Feria", "Chaquinchuna", "Corral De Caballos", "El Baldecito", "La Cañada", "La Concepcion", "La Ventana", "Las Cañadas", "Las Palomas", "Los Pozos", "Nicho", "San Antonio", "San Roque", "Tabanillo", "Villa Dolores"],
    "5871": ["Acostilla", "Altautina", "Balde De La Mora", "Balde De La Orilla", "Balde Lindo", "Bañado De Paja", "Cartaberol", "Chancani", "Chua", "Concepcion", "Condor Huasi", "El Bordo", "El Medanito", "El Paso De La Pampa", "El Rincon", "La Aguada De Las Animas", "La Alegria", "La Compasion", "La Cortadera", "La Finca", "La Jarilla", "La Linea", "La Loma", "La Patria", "La Trampa", "Lafinur", "Las Barrancas", "Las Encrucijadas", "Las Jarillas", "Las Oscuras", "Las Toscas", "Lomitas", "Los Cajones", "Los Callejones", "Los Cerrillos", "Los Dos Pozos", "Los Medanitos", "Piedra Pintada", "Pozo De La Pampa", "Quebracho Solo", "San Jose", "San Miguel San Vicente", "San Nicolas", "San Pedro", "San Pedro De San Alberto", "San Rafael", "San Vicente", "Santa Ana", "Santo Domingo", "Sauce Arriba", "Villa Luisa", "Villa Sarmiento"],
    "5873": ["Arboles Blancos", "Capilla De Romero", "Cañada Grande", "Conlara", "El Manantial", "Isla", "La Angostura", "La Celia", "Los Chañares", "Los Chañaritos", "Los Manguitos", "Manguitas", "Paso De Las Sierras", "Pozo Del Chañar", "Pozo Del Molle", "Punta Del Agua", "Salto", "Tilquicho", "Zapata"],
    "5875": ["Achiras", "Alto De Las Mulas", "Banda De Varela", "Chuchiras", "Colonia Montes Negros", "Come Tierra", "Cruz De Caña", "Diez Rios", "El Cerro", "El Pueblito", "Guanaco Boleado", "Huasta", "La Poblacion", "La Ramada", "La Siena", "La Travesia", "Las Chacras", "Lomitas", "Luyaba", "Quebracho Ladeado", "Rio De Jaime", "Rio Hondo", "Rodeo De Piedra", "Sagrada Familia", "San Isidro", "San Javier"],
    "5877": ["Yacanto"],
    "5879": ["Corralito San Javier", "La Fuente", "La Paz", "Las Tres Piedras", "Loma Bola"],
    "5881": ["Cañada La Negra", "Cerro De Oro", "El Rincon", "Estancia Tres Arboles", "La Ramada", "Merlo", "Piedra Blanca", "Rincon Del Este"],
    "5883": ["Alto Lindo", "Balcarce", "Balde", "Carpinteria", "Chañaritos", "Cortaderas", "El Recuerdo", "Estancia", "La Cumbre", "Los Espinillos", "Los Molles", "Papagayos", "San Miguel", "Villa Elena", "Villa Larca"],
    "5885": ["Algarrobal", "Alto Resbaloso", "Boca Del Rio", "Dique La Viña", "El Algadobal", "El Alto", "El Pantanillo", "El Perchel", "El Tajamar", "Hornillos", "La Costa", "Las Calles", "Las Cebollas", "Las Conanitas", "Las Rabonas", "Las Tapias", "Los Hornillos", "Los Molles", "Quebrada De Los Pozos", "Villa Angelica", "Villa Clodomira", "Villa De Las Rosas", "Villa Rafael Benegas"],
    "5887": ["Bajo El Molino", "El Alto", "El Sauzal", "Hucle", "La Aguadita", "La Majada", "La Quinta", "Los Algarrobos", "Los Molles", "Nono", "Ojo De Agua", "Paso Las Tropas", "Piedra Blanca", "Rio Arriba"],
    "5889": ["Arroyo De Los Patos", "Arroyo La Higuera", "Cañada Larga", "El Bajo", "El Corte", "La Gruta", "La Toma", "Las Palmitas", "Mina Clavero", "Monte Redondo", "Nido Del Aguila", "Niña Paula", "Quebrada Del Horno", "San Sebastian", "Santa Maria"],
    "5891": ["Casa De Piedra", "Cañada Grande", "Cienaga De Allende", "El Mirador", "Juan Bautista Alberdi", "La Guardia", "Mogigasta", "Puente Del Cura", "Rio Hondo", "Villa Cura Brochero"],
    "5893": ["Alto Grande", "Isla Verde", "La Cocha", "Pachango", "Panaholma", "San Lorenzo", "Santa Rita", "Tasma"],
    "5900": ["Fabrica Militar", "La Herradura", "Las Cuatro Esquinas", "Las Pichanas", "Monte De Los Lazos", "Ramon J Carcano", "Villa Aurora", "Villa Emilia", "Villa Maria"],
    "5901": ["Arroyo Del Pino", "Ausonia", "Cayuqueo", "Kilometro 267", "La Laguna", "Los Zorros", "Sanabria"],
    "5903": ["Villa Del Parque", "Villa Nueva"],
    "5905": ["Ana Zumaran"],
    "5907": ["Alto Alegre", "Pellico Silvio"],
    "5909": ["Arroyo Algodon", "India Muerta", "Las Mojarras", "Santa Rosa", "Trinchera"],
    "5911": ["La Playosa"],
    "5913": ["Corral Del Bajo", "La Palmerina", "La Zara", "La Zarita", "Pozo Del Molle", "Santa Rosa"],
    "5915": ["Campo Ambroggio", "Carrilobo"],
    "5917": ["Arroyo Cabral", "Colonia Yucat Sud", "Luca"],
    "5919": ["Dalmacio Velez Sarsfield"],
    "5921": ["Las Perdices"],
    "5923": ["General Deheza"],
    "5925": ["Carlomagno", "Ferreyra", "La Palestina", "La Reina", "Los Reyunos", "Maria", "Pasco", "Sarmica"],
    "5927": ["Ticino"],
    "5929": ["Hernando"],
    "5931": ["Las Isletillas", "Monte Del Frayle", "Pampayasta Norte", "Pampayasta Sud", "Punta Del Agua"],
    "5933": ["Colonia Hamburgo", "Colonia La Primavera", "Colonia Santa Margarita", "El Porteño", "General Fotheringham", "Tancacha"],
    "5935": ["Villa Ascasubi"],
    "5936": ["Capilla San Antonio De Yucat", "Colonia Santa Rita", "San Antonio De Yucat", "Tio Pujio"],
    "5940": ["Corral De Guardia", "Las Varillas"],
    "5941": ["Colonia Angelita", "Las Varas"],
    "5943": ["Campo Bandillo", "Saturnino M Laspiur"],
    "5945": ["Colonia General Deheza", "Corral De Mulas", "La Pobladora", "Sacanta"],
    "5947": ["El Arañado", "El Jumial", "Pozo Del Avestruz", "Villa San Esteban"],
    "5949": ["Alicia", "La Tigra"],
    "5951": ["El Florentino", "El Fortin", "La Rosarina", "Overa Negra"],
    "5960": ["Rio Segundo", "San Rafael"],
    "5961": ["Bajo De Gomez", "Bajo Galindez", "Cañada De Machado", "Costa Sacate", "Palo Negro", "Rincon", "San Jose"],
    "5963": ["Capilla Del Carmen", "Cañada De Machado Sud", "Costa Alegre", "El Carrilito", "El Carrizal", "La Isleta", "Monte Redondo", "San Jeronimo", "Villa Del Rosario"],
    "5965": ["Calchin Oeste", "Colazo", "Las Junturas", "Matorrales"],
    "5967": ["Galpon Chico", "Luque", "Plaza Minetti"],
    "5969": ["Calchin", "Estacion Calchin"],
    "5972": ["Lagunilla", "Paso De Velez", "Pilar", "Tres Pozos"],
    "5974": ["Laguna Larga"],
    "5980": ["Oliva"],
    "5984": ["James Craik"],
    "5986": ["Oncativo"],
    "5987": ["Campo Rossiano", "Colonia Almada", "Colonia Garzon", "Estancia Los Matorrales", "Impira", "Plaza Rodriguez"],
    "5988": ["Independencia", "Laguna Larga Sud", "Manfredi"],
    "6000": ["Barrio Carosio", "Barrio General San Martin", "Barrio Villa Ortega", "Cuartel V", "Junin", "Pueblo Nuevo", "Villa Belgrano", "Villa Mayor", "Villa Ortega", "Villa Penotti", "Villa Talleres", "Villa Triangulo", "Villa York"],
    "6001": ["Agustin Roca", "Agustina", "Fortin Tiburcio", "Laguna De Gomez", "Rafael Obligado"],
    "6003": ["Ascencion", "Colonia La Beba", "Escuela Agricola Salesiana", "Estacion Ascension", "Ferre", "La Angelita", "La Beba", "La Trinidad"],
    "6005": ["Estacion General Arenales", "General Arenales", "Ham", "La Huayqueria"],
    "6007": ["Arribeños", "Colonia Los Hornos", "Delgado", "Desvio Kilometro 95", "La Pinta"],
    "6009": ["San Marcelo", "Teodelina"],
    "6013": ["Baigorrita", "Campo Maipu", "Irala", "Laplacette", "Morse"],
    "6015": ["Campo Coliqueo", "Campo La Tribu", "General Viamonte", "La Tribu", "Los Huesos", "Los Toldos"],
    "6017": ["Chancay", "Colonia San Francisco", "El Retiro", "Kilometro 282", "La Delfina", "San Emilio", "San Roque"],
    "6018": ["Colonia Los Bosques", "Colonia Los Huesos", "Los Bosques", "Quirno Costa", "Zavalia"],
    "6022": ["La Oriental", "Las Parvas", "Saforcada"],
    "6030": ["Edmundo Perkins", "Sauzales", "Vedia"],
    "6031": ["De Bruyn", "Desvio El Chingolo", "El Dorado", "Fortin Acha", "Kilometro 95"],
    "6032": ["Blandengues", "Cuartel Iv", "Leandro N Alem"],
    "6034": ["Colonia Alberdi", "Juan Bautista Alberdi"],
    "6036": ["Diego De Alvear", "La Picasa"],
    "6042": ["Dos Hermanos", "Iriarte"],
    "6050": ["Cuartel Vii", "Dussaud", "General Pinto", "Haras El Catorce", "La Suiza"],
    "6051": ["Ingeniero Balbin", "Pichincha"],
    "6053": ["El Peregrino", "Germania", "Gunther", "Mayor Jose Orellano", "Trigales"],
    "6058": ["Pazos Kanki", "Villa Francia"],
    "6062": ["Coronel Granada", "Los Callejones"],
    "6063": ["Porvenir"],
    "6064": ["Eduardo Costa", "Florentino Ameghino", "Halcey", "Solale", "Volta"],
    "6065": ["Blaquier"],
    "6070": ["Balsa", "Estacion Lincoln", "Kilometro 321", "Lincoln", "Vigelencia"],
    "6071": ["Bermudez", "Santa Maria", "Triunvirato"],
    "6073": ["El Triunfo", "Fortin Vigilancia"],
    "6075": ["Arenaza", "Estancia Mitikili", "Estancia San Antonio", "Haras Trujui", "Kilometro 352", "Kilometro 356", "Los Altos", "Roberts"],
    "6077": ["Encina", "La Zarateña", "Necol Estacion Fcgm", "Nueva Suiza", "Pasteur"],
    "6078": ["Bayauca"],
    "6100": ["La Ines", "Rufino", "Villa Rosello"],
    "6101": ["La Cesira", "Villa Saboya"],
    "6103": ["Amenabar", "El Refugio", "La Adelaida", "La Constancia", "Lazzarino", "Tarragona"],
    "6105": ["Cañada Seca", "Santa Regina"],
    "6106": ["Aaron Castellanos", "Coronel Roseti", "El Alberdon", "Kilometro 396", "La Asturiana", "La Calma", "Las Dos Angelitas", "Miramar", "San Carlos", "Santa Paula", "Santa Teresa"],
    "6120": ["Curapaligue", "Fray Cayetano Rodriguez", "Guardia Vieja", "Laboulaye", "Ruiz Diaz De Guzman", "Salguero"],
    "6121": ["Colonia Valle Grande", "El Rastreador", "Huanchilla", "Huanchilla Sud", "Kilometro 55", "Pacheco De Melo", "Pavin"],
    "6123": ["Colonia Santa Ana", "La Ramada", "Melo", "San Joaquin", "Santa Clara", "Tacurel"],
    "6125": ["Serrano"],
    "6127": ["El Arbol", "El Noy", "Jovita", "Los Gauchos De Guemes", "Santa Magdalena"],
    "6128": ["Leguizamon", "Miguel Salas", "Rosales", "Villa Rossi", "Vivero"],
    "6132": ["Colonia La Magdalena De Oro", "Gavilan", "General Levalle"],
    "6134": ["Colonia La Providencia", "Julio Argentino Roca", "Rio Bamba", "Santa Cristina"],
    "6140": ["Colonia La Argentina", "General Pueyrredon", "Pretot Freyre", "Vicuña Mackenna"],
    "6141": ["Colonia La Carmensita", "Tosquita"],
    "6142": ["General Soler", "Kilometro 545", "La Cautiva"],
    "6144": ["Laguna Oscura", "Washington"],
    "6200": ["Realico"],
    "6201": ["Chanilao"],
    "6203": ["El Olivo", "El Tigre", "Embajador Martini", "La Elina", "Lote 2 La Elina"],
    "6205": ["El Guanaco", "El Tajamar", "Ingeniero Luiggi", "Lote 5 Caleufu Esc 120"],
    "6207": ["Alta Italia", "Ojeda"],
    "6212": ["Adolfo Van Praet", "El Tordillo", "Falucho", "La Juanita", "Maisonnave", "Pueblo Alassa", "Quetrequen", "San Hilario", "San Juan Simson", "Santa Gracia", "Tres Hermanos Quetrequen"],
    "6213": ["Lote 11 Escuela 107", "Lote 15", "Parera"],
    "6214": ["Casimiro Gomez", "Chamaico", "Colonia La Margarita", "Colonia San Basilio", "Jardon", "La Margarita", "La Pomona", "La Primavera Chamaico", "Las Delicias", "Rancul", "San Basilio", "San Marcelo"],
    "6216": ["Bagual", "Bajada Nueva", "Billiken", "Boca De La Quebrada", "Cochequingan", "Colonia El Campamento", "Colonia La Florida", "Colonia Urdaniz", "El Campamento", "El Cinco", "El Martillo", "El Pigue", "El Porvenir", "El Toro Muerto", "Fortuna", "La Alcorteña", "La Aurora", "La Caldera", "La Cherindu", "La Colonia", "La Donostia", "La Elena", "La Elenita", "La Emma", "La Ernestina", "La Escondida", "La Estrella", "La Florida", "La Gaviota", "La Gitana", "La Holanda", "La Josefa", "La Juanita", "La Linda", "La Maravilla", "La Margarita", "La Margarita Carlota", "La Maroma", "La Mascota", "La Media Legua", "La Melina", "La Reserva", "La Tigra", "La Uruguaya", "Las Cortaderas", "Las Gitanas", "Las Lagunas", "Las Martinetas", "Los Barriales", "Los Dos Rios", "Los Dueros", "Los Duraznos", "Los Lobos", "Milagro", "Monte Cochequingan", "Nueva Galia", "Paso De Los Gauchos", "Polledo", "Ranquelco", "Rosales", "San Jorge", "Santa Lucia", "Santa Teresa", "Santo Domingo", "Toingua", "Union"],
    "6220": ["Bernardo Larroude", "Colonia Trenquenda", "Colonia Trequen", "El Antojo", "El Recreo", "Santa Felicitas"],
    "6221": ["Ceballos", "Chacra La Casilda", "Colonia Las Mercedes", "Estancia La Lucha", "Estancia La Pampeana", "Estancia La Voluntad", "Intendente Alvear", "La Paulina", "La Victoria", "Las Delicias"],
    "6223": ["Coronel Charlone"],
    "6225": ["Buchardo", "Burmeister"],
    "6227": ["Onagoity"],
    "6228": ["Aguas Buenas", "Colonia Denevi", "Coronel Hilario Lagos", "El Porvenir", "Gallinao", "La Casilda", "La Energia", "La Invernada", "La Lucha", "La Magdalena", "La Pampeana", "La Pradera", "La Voluntad", "Malvinas Argentinas", "Mariano Miro", "Ramon Segundo", "San Jose", "San Urbano", "Sarah", "Tres Lagunas"],
    "6230": ["Francisco Casal", "General Villegas", "Los Laureles", "Moores"],
    "6231": ["Cuenca", "Pradere Juan A", "Tres Algarrobos"],
    "6233": ["Condarco", "Hereford", "Sansinena"],
    "6235": ["Villa Sauze"],
    "6237": ["America", "Cerrito", "Rivadavia"],
    "6239": ["Gonzalez Moreno", "Meridiano Vo", "San Mauricio", "Santa Aurelia"],
    "6241": ["El Dia", "Emilio Bunge", "Gondra", "Piedritas", "Santa Eleodora"],
    "6242": ["Drabble", "Elordi", "Los Caldenes"],
    "6244": ["Banderalo"],
    "6269": ["La Colina"],
    "6270": ["Colonia Boero", "Colonia Dorotea", "Huinca Renanco", "Melideo", "Nazca", "Watt"],
    "6271": ["Antonio Catalano", "Campo San Juan", "Costa Del Rio Quinto", "De La Serna", "Del Campillo", "Italo", "La Luz", "La Perlita", "Mattaldi", "Nicolas Bruzzone", "Pincen", "Ranqueles", "Tomas Echenique"],
    "6273": ["El Pampero", "Lecueder", "Modestino Pizarro", "Villa Sarmiento", "Villa Valeria"],
    "6275": ["Cañada Verde", "La Nacional", "Larsen", "Los Alfalfares", "Villa Huidobro", "Villa Moderna"],
    "6277": ["Buena Esperanza", "Cochenelos", "El Oasis", "El Quingual", "El Verano", "Frisia", "La Dulce", "La Esmeralda", "La Ethel", "La Invernada", "La Maria Luisa", "La Rosina", "La Segunda", "Las Aromas", "Las Mestizas", "Los Oscuros", "Machao", "Nilinast", "Placilla", "San Juan"],
    "6279": ["Batavia", "Centenario", "Colonia Calzada", "Coronel Segovia", "El Aguila", "El Espinillo", "El Piche", "El Recuerdo", "El Yacatan", "Estancia 30 De Octubre", "Estancia Don Arturo", "Fortin El Patria", "Gloria A Dios", "Ingeniero Malmen", "La Amalia", "La Aroma", "La Bavaria", "La Bolivia", "La Cora", "La Esperanza", "La Felisa", "La Germania", "La Hortensia", "La Isla", "La Juana", "La Laura", "La Luisa", "La Maria Esther", "La Nutria", "La Penca", "La Reina", "La Reserva", "La Rosalia", "Las Carretas", "Laura Elisa", "Los Chañares", "Los Huaycos", "Los Valles", "Martin De Loyola", "Media Luna", "Nacion Ranquel", "Nahuel Mapa", "Navia", "Nueva Esperanza", "Penice", "San Antonio", "San Isidro", "San Jose", "Santa Cecilia", "Santa Maria", "Santa Teresa", "Toro Bayo", "Uchaima", "Valle Hermoso", "Viva La Patria", "Ñurilay"],
    "6300": ["Barrancas Coloradas", "Colonia Lagos", "El Mirador De Juarez", "El Oasis", "La Fortuna", "La Juanita", "La Malvina", "La Primavera Santa Rosa", "Las Malvinas", "Los Nogales", "Medano Blanco", "Santa Rosa"],
    "6301": ["Ataliva Roca", "Boliche La Araña", "Cereales", "Colonia Aguirre", "Colonia Echeta", "Colonia Maria Luisa", "Colonia San Victorio", "Colonia Sobadell", "La Araña", "La Dolores", "La Primavera Miguel Riglos", "Los Quinientos", "Miguel Riglos", "Tomas M De Anchorena"],
    "6303": ["Cachirulo", "Calchahue", "Chacu", "Chapalco", "Colonia Ferraro", "Colonia Ramon Quintas", "Colonia Roca", "El Volante", "La Baya", "La Baya Muerta", "La Celina", "La Celmira", "La Vanguardia", "Lindo Ver", "Los Algarrobos", "Nerre Co", "Oficial E Segura", "Pichi Huilco", "Ramon Quintas", "Ta Huilco", "Toay"],
    "6305": ["Atreuco", "Bella Vista", "Colonia Guiburg N 2", "Doblas", "El Deslinde", "El Destino Rolon", "El Palomar", "Hipolito Yrigoyen", "La Catalinita", "La Esperanza Hidalgo", "La Manuelita", "La Nueva Provincia", "La Pampita Hidalgo", "La Sarita", "Las Felicitas", "Los Dos Hermanos", "Ojo De Agua", "Rolon", "Salinas Grandes Hidalgo", "San Felipe", "San Pedro Rolon", "Santa Stella"],
    "6307": ["Colonia La Oracion", "El Centenario", "Hidalgo", "La Antonia", "La Esmeralda Macachin", "La Esperanza Macachin", "La Josefina", "La Oracion", "Macachin", "Santo Tomas", "Tres Hermanos Macachin", "Valle Argentino"],
    "6309": ["Alpachiri", "Campo Urdaniz", "Colonia Anasagasti", "Colonia La Chispa", "Colonia Las Vizcacheras", "Colonia Santa Ana", "Gral Manuel Campos", "La Maria Rosa", "Monte Ralo", "Salinas Mari Manuel", "Santa Ana"],
    "6311": ["Campo De Los Toros", "Campo La Florida", "Colonia La Esperanza", "Colonia Los Toros", "Colonia Luna", "Colonia Santa Teresa", "Guatrache", "La Nueva", "La Piedad", "Las Quintas", "Los Toros", "Remeco"],
    "6312": ["Ricardo Lavalle"],
    "6313": ["Bajo De Las Palomas", "Colonia Espiga De Oro", "Colonia La Paz", "Colonia San Felipe", "Colonia Santa Elena", "El Destino", "El Furlong", "El Guanaco", "La Delfina", "Lote 12", "Lote 13 Escuela 173", "Lote 21 Colonia Santa Elena", "Lote 23 Escuela 221", "San Jose", "Winifreda"],
    "6315": ["Colonia Baron", "Colonia La Carlota", "Colonia San Jose", "Ines Y Carlota", "Los Pirineos", "Lote 25 Escuela 178", "Lote 6 Escuela 171", "Lote 9 Escuela 140", "Mauricio Mayer", "Villa Mirasol", "Villa San Jose", "Zona Rural De Mirasol"],
    "6317": ["La Florencia", "Lote 5 Luan Toro", "Loventuel", "Luan Toro"],
    "6319": ["Carro Quemado", "Chacras De Victorica", "El Durazno", "El Eucalipto Carro Quemado", "Guadaloza", "La Morocha", "Labal", "Lote 8 Escuela 179", "Poitague", "San Francisco", "Victorica"],
    "6321": ["Caichue", "Colonia El Porvenir", "Costa Del Salado", "Dos Amigos", "El Destino", "El Mate", "El Odre", "El Refugio", "El Retiro", "El Silencio", "Jaguel Del Esquinero", "Jaguel Del Monte", "Juzgado Viejo", "La Catalina", "La Cienaga", "La Constancia", "La Elenita", "La Elia", "La Elina", "La Esmeralda", "La Estrella", "La Eulogia", "La Fe", "La Guadalosa", "La Isabel", "La Laurentina", "La Luz", "La Marcela", "La Pencosa", "La Razon", "La Tinajera", "La Union", "La Verde", "La Zota", "Leona Redonda", "Loma Redonda", "Lomas De Gatica", "Lomas Ombu", "Los Manantiales", "Los Tres Pozos", "Manantiales", "Mayaco", "Nahuel Napa", "Nanquel Huitre", "Pichi Merico", "San Emilio", "San Jose", "Telen"],
    "6323": ["Algarrobo Del Aguila", "Arbol De La Esperanza", "Arbol Solo", "Butalo", "Chicalco", "Colonia La Pastoril", "Curru Mahuida", "El Centinela", "Emilio Mitre", "Establecimiento El Centinela", "La Esperanza", "La Humada", "La Imarra", "La Pastoril", "La Primavera", "La Puñalada", "La Razon Santa Isabel", "La Soledad", "La Veintitres", "Los Tajamares", "Los Turcos", "Medanos Negros", "Paso De Los Algarrobos", "Paso De Los Puntanos", "Paso La Razon", "San Francisco De La Ramada", "Santa Isabel", "Vista Alegre"],
    "6325": ["Colonia Devoto", "Colonia La Amarga", "Colonia Ministro Lobos", "El Chillen", "La Avanzada", "La Esther", "Los Alamos", "Naico", "Parque Luro", "San Humberto", "Santiago Orellano"],
    "6326": ["Anguil", "Colonia San Juan", "Colonia Torello", "La Carola", "La Constancia Anguil", "La Elvira", "La Esperanza Anguil", "La Florida", "La Reserva Anguil", "La Verde Anguil", "San Carlos", "San Jose Anguil"],
    "6330": ["Arturo Almaraz", "Campo Ludueña", "Catrilo", "Cayupan", "Ivanowsky", "La Blanca", "La Leña", "La Puna", "La Rebeca", "La Unida", "San Eduardo", "San Justo", "San Pedro"],
    "6331": ["Colonia Beaufort", "Colonia Giusti", "Curilco", "El Belgica", "El Parque", "La Elsa", "La Verde", "Las Tres Hermanas", "Miguel Cane", "Pavon", "Relmo", "Rucahue", "San Alberto", "San Benito", "San Miguel", "Zona Rural"],
    "6333": ["Alfredo Peña", "Colonia La Abundancia", "Colonia La Sara", "Colonia Santa Cecilia", "Huelen", "La Cautiva", "La Celina", "La Delicia", "La Enriqueta", "La Olla", "Mari Mari", "Quemu Quemu", "Santa Elvira", "Sol De Mayo"],
    "6335": ["Graciarena", "Quenuma"],
    "6337": ["Ingeniero Thompson", "Maria P Moreno"],
    "6338": ["Leubuco"],
    "6339": ["Cailomuta", "Estacion Caiomuta", "Salliquelo"],
    "6341": ["Chapi Talo", "Colonia Murature", "Colonia Naviera", "El Malacate", "El Parque", "Francisco Murature", "La Matilde", "La Pala", "La Reserva Ivanowsky", "San Joaquin"],
    "6343": ["Los Gauchos", "Thames", "Villa Maza"],
    "6345": ["La Bilbaina"],
    "6346": ["Pellegrini"],
    "6348": ["Bocayuva", "De Bary", "La Gloria"],
    "6352": ["Colonia La India", "Colonia San Miguel", "El Brillante", "El Descanso Lonquimay", "El Guaicuru", "El Rubi", "El Salitral", "El Triunfo", "La Atalaya", "La Celia", "La Esmeralda", "La Paz", "La Perla", "La Perlita", "La Segunda", "La Violeta", "Lonquimay", "Pueblo Quintana", "Quintana", "San Manuel"],
    "6354": ["Colonia La Gaviota", "La Carmen", "La Catalina", "La Cumbre", "La Gaviota", "La Luisa", "La Marianita", "La Suerte", "La Trinidad", "La Victoria", "Las Gaviotas", "San Andres", "San Jose", "San Juan", "Uriburu"],
    "6360": ["Barrio El Molino", "Carlos Berg", "General Pico", "La Chapelle", "La Gueñita", "La Puma", "Mocovi", "San Ignacio", "San Joaquin", "San Jose", "Santa Elena", "Santa Ines"],
    "6361": ["Agustoni", "Caimi", "El Eucalipto", "El Sauce", "La Gavenita", "La Maria", "La Teresita", "Trebolares"],
    "6365": ["Azteazu", "Colonia Santa Elvira", "Dorila", "La Barrancosa", "La Esperanza Vertiz", "La Maria Vertiz", "San Ildefonso", "Santa Catalina", "Speluzzi", "Trili", "Vertiz", "Zona Rural De Vertiz", "Zona Rural Dorila"],
    "6367": ["Argentina Belvedere", "Colonia Migliori", "Metileo", "Ministro Orlando", "San Joaquin Metileo", "Zona Rural Metileo"],
    "6369": ["Campo Salusso", "Lote 8 Escuela 141", "Trenel", "Zona Rural"],
    "6380": ["Boeuf", "Chacra 16", "Colonia San Lorenzo", "Eduardo Castex", "El Guanaco", "Lote 17 Escuela 95", "Lote 2 Escuela 185", "Lote 20 La Carlota", "Lote 8 Escuela 184", "Nicolas Vera", "Zona Urbana Norte"],
    "6381": ["Campo Caretto", "Campo Pico", "Colonia El Destino", "Colonias Drysdale", "Colonias Murray", "Conhelo", "El Destino", "El Peludo", "Kilometro 619", "Las Chacras", "Loo Co", "Lote 25 Conhelo", "Lote 25 Escuela 146", "Rucanelo", "Tte Gral Emilio Mitre"],
    "6383": ["Campo Moises Seccion 1A", "Lote 24 Seccion 1A", "Monte Nievas", "San Ramon", "Seccion Primera Conhello"],
    "6385": ["Arata", "Colonia El Tigre", "Colonia Las Piedritas", "Ingeniero Foster", "La Maruja", "Pichi Huinca"],
    "6387": ["Caleufu", "Caraman", "Las Piedritas", "Lote 15 Escuela 18", "Lote 4"],
    "6389": ["Alegria", "Anchorena", "Arizona", "El Rodeo", "La Travesia", "La Vaca", "La Verde", "San Carlos"],
    "6400": ["Barrio Indio Trompa", "La Zanja", "Laguna Redonda", "Las Guasquitas", "Lertora", "Mari Lauquen", "Martin Fierro", "Trenque Lauquen"],
    "6401": ["Sundblad", "Valentin Gomez"],
    "6403": ["Badano", "Colonia El Balde", "Fortin Olavarria", "Francisco De Vitoria", "La Cautiva", "Mira Pampa", "Roosevelt", "Villa Sena"],
    "6405": ["30 De Agosto", "Albariño", "Corazzi", "Duhau"],
    "6407": ["Girodias", "La Porteña", "Tronge"],
    "6409": ["Jose Maria Blanco", "Pehuelches", "Tres Lomas"],
    "6411": ["Bravo Del Dos", "Garre", "Papin", "Victorino De La Plaza"],
    "6417": ["Casbas", "Casey", "Fortin Paunero", "San Fermin", "Saturno"],
    "6422": ["Primera Junta"],
    "6424": ["Beruti", "San Ramon"],
    "6430": ["Adolfo Alsina", "Carhue", "Fatralo", "Juan V Cilley", "Pocito", "Rolito Estacion Fcgb", "Villa Castelar Est Erize", "Villa Sauri"],
    "6431": ["Estacion Lago Epecuen", "Lago Epecuen"],
    "6433": ["Arturo Vatteone"],
    "6434": ["Palantelen"],
    "6435": ["Guamini", "Laguna Del Monte", "Vuelta De Zapata"],
    "6437": ["Alamos", "Alfa", "Arroyo El Chingolo", "Arroyo Venado", "Colonia San Ramon", "El Nilo", "El Trebañon", "La Gregoria", "La Herminia", "Las Cuatro Hermanas", "Las Mercedes", "Las Tres Flores", "Santa Rita Pdo Guamini"],
    "6438": ["Masurel"],
    "6439": ["Bonifacio", "La Manuela", "Laguna Alsina", "Luro"],
    "6441": ["Colonia Baron Hirsch", "Rivera"],
    "6443": ["Arano", "Epumer", "Malabia", "Tres Lagunas", "Yutuyaco"],
    "6450": ["Abel", "Barrio Obrero", "Pehuajo", "Pueblo San Esteban", "Rovira", "Santa Cecilia Sud"],
    "6451": ["Ancon", "Curaru", "Girondo", "Gnecco", "Inocencio Sosa", "Larramendy", "Los Indios", "Magdala", "Marucha", "Nueva Plata", "Pedro Gamen", "San Carlos"],
    "6453": ["Carlos Salas", "La Pradera", "Las Toscas"],
    "6455": ["Carlos Tejedor", "Drysdale", "Husares"],
    "6457": ["Ingeniero Beaugey", "Kilometro 386", "Timote"],
    "6459": ["Colonia Sere", "Santa Ines"],
    "6461": ["Capitan Castro", "La Cotorra"],
    "6463": ["Alagon", "El Santiago", "Santa Cecilia Centro"],
    "6465": ["Coraceros", "Henderson"],
    "6467": ["El Trio", "Enrique Lavalle", "Kilometro 393", "Maria Lucila"],
    "6469": ["Asturias", "Mones Cazon"],
    "6471": ["Atahualpa", "La Carreta", "La Margarita", "Mouras", "Salazar", "Santa Ines", "Villa Aldeanita", "Villa Branda"],
    "6472": ["Francisco Madero", "Santa Cecilia Norte"],
    "6474": ["Campo Aristimuño", "El Recado", "Juan Jose Paso"],
    "6475": ["Esteban De Luca", "Francisco Magnano", "La Higuera", "Los Chañares"],
    "6476": ["Chiclana", "Guanaco", "Las Juanitas", "San Bernardo"],
    "6500": ["9 De Julio", "Barrio Julio De Vedia", "Fauzon", "San Juan", "Villa Diamantina"],
    "6501": ["12 De Octubre", "Estacion Provincial", "Laguna Del Cura", "Mulcahy", "Norumbega", "Tropezon"],
    "6503": ["Desvio Kilometro 234", "Patricios"],
    "6505": ["Dudignac"],
    "6507": ["Corbett", "Gerente Cilley", "Las Negras", "Morea", "Santos Unzue"],
    "6509": ["Del Valle", "Desvio Garbarini", "Escuela Agricola Salesiana"],
    "6511": ["Hale", "Huetel", "Villa Sanz"],
    "6513": ["Colonia Las Yescas", "Galo Llorente", "La Aurora", "La Niña", "La Yesca"],
    "6515": ["Carlos Maria Naon", "El Tejar"],
    "6516": ["Amalia", "Bacacay", "Cambaceres", "Dennehy", "French"],
    "6530": ["Carlos Casares", "San Juan De Nelson", "Santo Tomas"],
    "6531": ["Algarrobo", "Colonia La Esperanza", "Colonia Mauricio", "El Jabali", "Gobernador Arias", "Mauricio Hirsch", "Moctezuma", "Smith"],
    "6533": ["Alfredo Demarchi", "Kilometro 322", "La Adela", "Las Rosas", "Pueblo Martinez De Hoz", "Quiroga", "Ramon J Neild", "Reginaldo J Neild"],
    "6535": ["Bellocq", "Cadret", "Centenario", "Colonia Santa Maria", "La Sofia", "Santa Maria Belloq"],
    "6537": ["El Camoati", "El Carpincho", "Estancia San Claudio", "Hortensia", "Ordoqui"],
    "6538": ["La Dorita", "Santo Tomas Chico"],
    "6550": ["Bolivar", "El Porvenir", "La Perla", "Paraje Miramar", "Santa Isabel"],
    "6551": ["Juan F Ibarra", "Mariano Unzue", "Pirovano", "San Andres"],
    "6553": ["La Torrecita", "Nueva España", "Urdampilleta", "Villa Lynch Pueyrredon"],
    "6555": ["Alfalad", "Andant", "Coronel Marcelino Freyre", "Daireaux", "La Armonia", "La Larga", "Los Coloniales", "Mauras", "Villa Carola"],
    "6557": ["Arboleda", "Herrera Vegas", "Iturregui", "Mapis", "Paula", "Vallimanca"],
    "6559": ["Recalde"],
    "6561": ["Blanca Grande", "Espigas", "La Protegida", "San Bernardo"],
    "6600": ["Kilometro 125", "Mercedes", "San Jacinto", "Seminario Pio Xii"],
    "6601": ["Altamira", "Comahue Oeste", "Espora", "La Valerosa", "La Verde", "San Eladio", "Tomas Jofre"],
    "6603": ["Ingeniero Williams", "Juan Jose Almeyra", "Kilometro 117"],
    "6605": ["Campo Peña Lopez", "Gonzalez Risos", "Kilometro 116", "Kilometro 83", "Kilometro 90", "Navarro", "Rincon Norte"],
    "6607": ["Anasagasti", "Esteban Diaz", "Las Marianas"],
    "6608": ["Agote", "Gowland", "Manuel Jose Garcia", "Olivera"],
    "6612": ["Capdepont", "Haras La Elvira", "La Sara", "Roman Baez", "Suipacha"],
    "6614": ["Franklin", "General Rivas", "Goldney"],
    "6616": ["Castilla", "La California Argentina"],
    "6620": ["Chivilcoy", "Puente Batalla"],
    "6621": ["Anderson", "Chacra La Magdalena", "Gobernador Ugarte", "Henry Bell", "Presidente Quintana"],
    "6623": ["Indacochea", "La Rica", "San Sebastian"],
    "6625": ["Cañada La Rica", "Villa Moquehua"],
    "6627": ["Achupallas", "Grisolia", "Haras El Carmen", "La Victoria Desvio", "Moll", "Ramon Biaus"],
    "6628": ["Colonia Zambungo", "Coronel Mom", "Coronel Segui", "Emilio Ayarza", "La Carlota", "La Dormilona", "Palemon Huergo", "Villa Maria", "Villa Ortiz"],
    "6632": ["Benitez", "Gorostiaga"],
    "6634": ["Alberti", "Andres Vaccarezza", "Emita", "Larrea", "Pla"],
    "6640": ["Asamblea", "Bragado", "La Maria"],
    "6641": ["Comodoro Py"],
    "6643": ["Araujo", "Baudrix", "Colonia Palantelen", "San Jose"],
    "6645": ["La Limpia", "Maximo Fernandez"],
    "6646": ["Colonia San Eduardo", "General O Brien", "Warnes"],
    "6648": ["Mecha", "Mechita"],
    "6651": ["Ingeniero De Madrid"],
    "6652": ["Olascoaga"],
    "6660": ["25 De Mayo", "La Tribu", "Laguna Las Mulitas", "Ortiz De Rosas", "Santiago Garbarini"],
    "6661": ["Blas Durañona", "Lucas Monteverde", "Mamaguita", "Pueblitos", "San Enrique"],
    "6663": ["Juan Vela", "Norberto De La Riestra"],
    "6665": ["Ernestina", "La Gloria", "Pedernales", "San Jose"],
    "6667": ["Agustin Mosconi", "Colonia Inchausti", "Islas", "La Rabia", "Martin Berraondo", "Valdez"],
    "6700": ["Caminera Lujan", "Cañada De Arias", "Cuartel Cuatro", "La Loma", "Lezica Y Torrezuri", "Lujan", "Pueblo Nuevo", "Santa Elena"],
    "6701": ["Carlos Keen"],
    "6703": ["Alastuey", "Etchegoyen", "Parada Robles", "Ruta 8 Kilometro 77", "Torres", "Villa Preceptor Manuel Cruz"],
    "6705": ["Villa Ruiz"],
    "6706": ["Est Jauregui Va Flandria", "Jauregui Jose Maria", "Villa Francia"],
    "6708": ["Colonia Nac De Alienados", "Doctor Domingo Cabred", "Mariscal Sucre", "Open Door", "Sucre"],
    "6712": ["Cortines", "Villa Espil"],
    "6720": ["Kilometro 125", "La Florida", "Ruiz Solis", "San Andres De Giles", "Villa San Alberto"],
    "6721": ["Azcuenaga", "Tatay", "Tuyuti"],
    "6723": ["Cucullu", "Heavy", "Kilometro 108"],
    "6725": ["Carmen De Areco", "Estrella Naciente", "La Central", "Parada Tatay", "San Ernesto"],
    "6727": ["Gouin", "Tres Sargentos"],
    "6734": ["Rawson", "San Patricio"],
    "6740": ["Chacabuco", "Gregorio Villafañe", "Villafañe"],
    "6743": ["Coliqueo", "Ingeniero Silveyra"],
    "6746": ["Cucha Cucha"],
    "6748": ["Membrillar", "O Higgins"],
    "7000": ["Cantera Aguirre", "Cantera Albion", "Cantera La Aurora", "Cantera La Federacion", "Cantera La Movediza", "Cantera Monte Cristo", "Cantera San Luis", "Cerro De Los Leones", "Desvio Aguirre", "El Gallo", "Empalme Cerro Chato", "La Numancia", "Los Leones", "Tandil", "Villa Daza", "Villa Dufau", "Villa Galicia", "Villa Italia", "Villa Laza"],
    "7001": ["La Pastora"],
    "7003": ["Aceilan", "Gardey", "Maria Ignacia", "Vela"],
    "7005": ["Barker", "Claraz", "Kilometro 404", "La Azucena", "La Negra", "Villa Cacique"],
    "7007": ["Caminera Napaleofu", "Dos Naciones", "El Cheique", "El Hervidero", "Fulton", "La Azotea", "La Esperanza", "La Palma", "Las Suizas", "Licenciado Matienzo", "Napaleofu", "San Manuel", "San Pascual"],
    "7009": ["Iraola", "La Aurora"],
    "7011": ["Aneque Grande", "Arroyo Chico", "Haras La Lula", "Juan N Fernandez", "San Cala"],
    "7013": ["De La Canal", "Egaña"],
    "7020": ["Benito Juarez", "Caminera Juarez", "Chapar", "Estancia Chapar", "Haras El Cisne", "La Calera", "Molino Galileo", "Monte Crespo", "Pachan", "Parque Muñoz", "Villa Juarez"],
    "7021": ["Alzaga", "Lopez", "Tedin Uriburu"],
    "7100": ["Dolores", "El 60", "Esquina De Crotto", "Kilometro 212", "La Estrella", "Las Viboras", "Loma De Salomon", "Paraje La Vasca", "Parravichini", "Tres Leguas"],
    "7101": ["General Conesa", "Sevigne", "Tordillo", "Villa Roch"],
    "7103": ["Faro San Antonio", "General Lavalle"],
    "7105": ["San Clemente Del Tuyu"],
    "7106": ["Las Toninas"],
    "7107": ["Santa Teresita"],
    "7108": ["Costa Del Este", "Mar Del Tuyu"],
    "7109": ["Barrio Pedro Rocco", "Costa Esmeralda", "Driades Links", "La Victoria", "Mar De Ajo", "Playa Las Margaritas", "Punta Medanos", "San Jose De Los Quinteros", "Villa Clelia"],
    "7110": ["Cuartel Iv", "La Reforma"],
    "7111": ["San Bernardo Del Tuyu"],
    "7112": ["Aguas Verdes", "Costa Azul", "La Isabel", "La Posta", "La Proteccion"],
    "7113": ["La Lucila Del Mar", "Nueva Atlantis"],
    "7114": ["Canal 15 Cerro De La Gloria", "Castelli", "Centro Guerrero", "India Muerta", "La Corina", "La Corinco", "La Costa", "Parque Taillade", "San Jose De Gali"],
    "7116": ["Camaron Chico", "Don Vicente", "El Destino", "El Vence", "Guerrero", "La Alcira", "La Despierta", "La Florida", "La Larga Nueva", "La Piedra", "Las Achiras", "Las Chilcas", "Las Tortugas", "Lezama", "Pila", "San Antonio", "San Daniel", "San Enrique"],
    "7118": ["General Guido", "San Justo", "Vecino"],
    "7119": ["Cari Larquea", "La Amorilla", "La Colorada", "La Mascota", "Monsalvo", "Santo Domingo", "Segurola"],
    "7130": ["Caminera Samborombon", "Chascomus", "El Eucaliptus", "El Rincon", "Estancia San Rafael", "La Alameda", "La Amalia", "La Amistad", "La Azotea Grande", "La Horqueta", "La Reforma", "Las Bruscas", "Las Mulas", "Legaristi", "San Rafael", "Vista Alegre", "Vitel"],
    "7135": ["Atilio Pessagno", "Comandante Giribone", "Cuartel 8", "Don Cipriano", "El Carbon", "Espartillar", "Libres Del Sud", "Pedro Nicolas Escribano", "Vergara"],
    "7136": ["Adela", "Colonia Escuela Argentina", "Cuartel 6", "Gandara", "Haras San Ignacio", "Monasterio"],
    "7150": ["Ayacucho", "El Boqueron", "Las Pajas", "San Laureano"],
    "7151": ["Langueyu", "Las Sultanas", "Magallanes", "San Ignacio", "Solanet", "Udaquiola"],
    "7153": ["Cangallo", "Fair", "La Constancia", "La Posta"],
    "7160": ["La Union", "Maipu"],
    "7161": ["Labarden"],
    "7163": ["Claverie", "El Chaja", "Espadaña", "General Madariaga", "Gobos", "Goroso", "Goñi", "Hinojales", "Invernadas", "Isondu", "La Esperanza Gral Madariaga", "La Tablada", "Pasos", "Salada Chica", "Salada Grande", "Santa Teresa", "Speroni", "Tio Domingo"],
    "7165": ["Faro Querandi", "Mar Azul", "Mar De Las Pampas", "Villa Gesell"],
    "7167": ["Carilo", "Montecarlo", "Ostende", "Parque Carilo", "Pinamar", "Valeria Del Mar"],
    "7169": ["Juancho", "Macedo", "Medaland"],
    "7172": ["Colonia Ferrari", "General Piran", "Hogar Mariano Ortiz Basualdo", "Las Armas"],
    "7174": ["Arroyo Grande", "Coronel Vidal", "El Vigilante", "Escuela Agricola Rural", "Haras 1 De Mayo", "La Tobiana", "Las Chilcas", "Mar Chiquita"],
    "7200": ["El Gualicho", "Las Flores"],
    "7201": ["Colman", "El Chalar", "Miranda", "Plaza Montero"],
    "7203": ["Chapaleufu", "El Carmen De Langueyu", "Galera De Torres", "Loma Negra", "Loma Partida", "Rauch", "San Jose", "Villa Burgos", "Villa Loma", "Villa San Pedro"],
    "7205": ["La Esperanza Rosas Las Flores", "Rosas"],
    "7207": ["El Trigo", "Estrugamou", "La Porteña"],
    "7208": ["Coronel Boerr", "Vilela"],
    "7212": ["Doctor Domingo Harosteguy", "Pardo", "Santa Rosa De Minellono"],
    "7214": ["Cachari", "La Verde", "Laguna Medina", "Miramonte"],
    "7220": ["Funke", "Goyeneche", "Guardia Del Monte", "Kilometro 88", "Los Eucaliptos", "San Miguel Del Monte"],
    "7221": ["Francisco Berra", "Gobernador Udaondo", "Kilometro 128", "Kilometro 88", "Palmitas"],
    "7223": ["Bonnement", "Chas", "El Siasgo", "General Belgrano", "Haras Chacabuco", "Ibañez", "La Chumbeada", "La Esperanza", "La Verde", "Newton"],
    "7225": ["Casalins", "El Alba", "Estancia Vieja", "La Luz", "La Mascota", "La Victoria", "Peñaflor", "Puente El Ochenta", "Real Audiencia", "Rincon De Vivot", "Villanueva"],
    "7226": ["Gorchs", "Kilometro 146", "Los Cerrillos", "Zenon Videla Dorna"],
    "7228": ["Abbott"],
    "7240": ["Kilometro 112", "Laguna De Lobos", "Lobos"],
    "7241": ["La Porteña", "Las Chacras", "Salvador Maria"],
    "7243": ["Antonio Carboni", "Arevalo", "Elvira", "La Adelaida", "La Blanqueada", "Santa Alicia", "Santa Felicia", "Sol De Mayo"],
    "7245": ["Campo Sabate", "Haras El Salaso", "Juan Atucha", "La Paz", "La Reforma", "La Rinconada", "Roque Perez", "Santiago Larre"],
    "7247": ["Barrientos", "Campo Funke", "Carlos Beguerie", "Juan Tronconi", "La Paz Chica"],
    "7249": ["El Araza", "Empalme Lobos", "Zapiola"],
    "7260": ["Barrio Villa Saladillo", "El Mangrullo", "Emiliano Reynoso", "Esther", "Gobernador Ortiz De Rosas", "Jose Sojo", "La Barrancosa", "La Campana", "La Margarita", "La Razon", "Saladillo"],
    "7261": ["Saladillo Norte", "San Benito"],
    "7263": ["El Chumbeau", "El Parche", "El Tabare", "Emma", "General Alvear", "Haras R De La Parva", "Jose M Micheo", "La Pampa", "Los Chucaros", "Los Cuatro Caminos", "Los Gatos"],
    "7265": ["Cazon", "Del Carril"],
    "7267": ["Alvarez De Toledo", "Juan Blaquier", "Polvaredas", "Toldos Viejos"],
    "7300": ["Azul", "Caminera Azul", "Cuartel Ii", "Estacion Lazzarino", "La Colorada", "La Mantequeria", "Las Cortaderas", "Lazzarino", "Vicente Pereda"],
    "7301": ["Ariel", "Arroyo Los Huesos", "Base Naval Azopardo", "Francisco J Meeks", "Pablo Acosta", "Uballes", "Vaña"],
    "7303": ["Altona", "Campo Rojas", "El Sauce", "Sabbi", "Santa Rosa", "Tapalque", "Yerbas"],
    "7305": ["Antonio De Los Heros", "Campodonico", "Covello", "El Mirador", "San Andres De Tapalque", "San Gervacio", "Velloso"],
    "7307": ["Crotto", "Requena"],
    "7311": ["Chillar", "La Protegida", "Martin Fierro", "San Ramon De Anchorena"],
    "7313": ["16 De Julio", "Bernardo Vera Y Pintado", "Coronel Rodolfo Bunge", "El Luchador", "Kilometro 433", "La Nutria", "Ricardo Gaviña"],
    "7316": ["Fortin Irene", "La Chumbeada", "Las Nieves", "Nieves", "Parish", "Shaw"],
    "7318": ["Colonia Hinojo", "Colonia Nieves", "Colonia Rusa", "Hinojo", "Villa Monica"],
    "7400": ["Barrio La Luisa", "Calera Avellaneda", "Kilometro 333", "La Navarra", "Las Piedritas", "Olavarria", "Pueblo Nuevo", "San Jacinto"],
    "7401": ["Canteras De Gregorini", "Durañona", "Empalme Querandies", "San Juan", "Santa Luisa", "Sierra Chica", "Teniente Coronel Miñana"],
    "7403": ["Alvaro Barros", "Cerro Aguila", "Cerro Negro", "Cerro Sotuyo", "Colonia San Miguel", "La Estrella", "La Narcisa", "La Palmira", "La Providencia", "La Tomasa", "Loma Negra", "Sierras Bayas", "Villa La Serrania"],
    "7404": ["Fortin Lavalle", "Muñoz", "Pourtale", "Rocha", "San Jorge"],
    "7406": ["Aldecon", "Chala Quilca", "Fortin Necochea", "General La Madrid", "Las Bandurrias", "Las Martinetas", "Lastra", "Quilco", "San Quilco", "Santa Clementina"],
    "7407": ["Libano"],
    "7408": ["La Colina"],
    "7412": ["Las Hermanas", "Los Pinos", "Paraguil", "Voluntad"],
    "7414": ["Laprida", "Santa Elena", "Villa Pueblo Nuevo"],
    "7500": ["El Carretero", "El Triangulo", "Estacion Barrow", "Hueso Clavado", "La Horqueta", "La Pastora", "La Tigra", "Las Vaquerias", "Tres Arroyos"],
    "7501": ["Indio Rico"],
    "7503": ["Cristiano Muerto", "El Cristiano", "General Valdez", "La Feliciana", "Los Molles", "Orense", "Santa Catalina"],
    "7505": ["Balneario Claromeco", "Est San Francisco Belloq", "Lin Calel", "San Francisco De Bellocq", "Villa Carucha"],
    "7507": ["El Bombero", "Irene", "Micaela Cascallares"],
    "7509": ["Oriente"],
    "7511": ["Balneario Oceano", "Balneario Orense", "Copetonas", "Paso Del Medano", "Reta"],
    "7513": ["Adolfo Gonzales Chaves", "El Lucero"],
    "7515": ["Claudio C Molina", "De La Garma", "Pedro Lasalle"],
    "7517": ["Juan E Barra", "La Sortija", "Mariano Roldan", "Pierini"],
    "7519": ["San Mayol", "Vasquez"],
    "7521": ["Defferrari", "La Ballena", "La Gaviota", "Loma Del Indio", "Ochandio", "San Cayetano", "San Severo"],
    "7530": ["Coronel Pringles", "El Chelforo", "El Gavilan", "Krabbe", "Las Mostazas", "Paraje Fra Pal", "Pillahuinco", "Raulet", "Tejo Galeta", "Zoilo Peralta"],
    "7531": ["Despeñaderos", "El Divisorio", "El Pensamiento", "Lartigau"],
    "7533": ["Quiñihual Estacion"],
    "7535": ["Pontaut"],
    "7536": ["Estacion Coronel Pringles", "La Reserva", "Stegmann"],
    "7540": ["Bathurst Estacion", "Coronel Suarez", "Paraje Santa Ana", "Piñeyro", "Sauce Corto", "Villa Arcadia"],
    "7541": ["D Orbigny", "Pueblo San Jose", "Pueblo Santa Maria", "Santa Trinidad"],
    "7543": ["La Primavera"],
    "7545": ["Huanguelen", "La Copeta", "La Nevada", "Louge", "Ombu", "Otoño", "Zentena"],
    "7547": ["Cascada", "Pasman"],
    "7548": ["Cura Malal"],
    "7600": ["Barrio Emir Ramon Juarez", "Barrio Gastronomico", "Barrio Pueblo Nuevo", "Barrio Tierra De Oro", "Barrio Tiro Federal", "El Soldado", "Laguna Del Soldado", "Mar Del Plata", "Villa Vignolo"],
    "7601": ["Barrio Batan", "El Boqueron", "La Peregrina", "Laguna De Los Padres", "Los Ortiz", "San Jose De Otamendi", "Sierra De Los Padres"],
    "7603": ["Comandante Nicanor Otamendi", "Dionisia", "La Colmena", "La Elma", "La Lucia", "La Madrecita", "La Reforma", "Las Lomas", "Los Patos", "San Cornelio", "San Felipe"],
    "7605": ["Barrio Estacion Chapadmalal", "Haras Chapadmalal", "La Ballenera", "Las Piedritas", "Mechongue", "Yraizos"],
    "7607": ["Balneario Atlantida", "Balneario Camet Norte", "Balneario Frente Mar", "Balneario La Baliza", "Balneario Playa Dorada", "Barrio Oeste", "Barrio Parque Bristol", "Centinela Del Mar", "El Centinela", "El Marquesado", "El Pito", "General Alvarado", "Mar Del Sud", "Miramar", "Pla Y Ragnoni", "San Eduardo Del Mar", "Santa Irene", "Villa Copacabana"],
    "7609": ["Balneario La Caleta", "Balneario Mar Chiquita", "Balneario Mar De Cobo", "Balneario Santa Elena", "Colonia De Vac Chapadmalal", "La Caleta", "Mar De Cobo", "Playa Chapadmalal", "Santa Clara Del Mar", "Santa Elena", "Siempre Verde", "Unidad Turistica Chapadmalal"],
    "7612": ["Camet", "Cobo", "El Refugio", "Vivorata"],
    "7613": ["Calfucura", "Campamento", "Nahuel Ruca", "San Julian", "San Valentin"],
    "7620": ["Balcarce", "Bosch", "El Cruce", "El Junco", "El Verano", "El Volante", "Haras Ojo Del Agua", "La Brava", "La Para", "Laguna Brava", "Los Cardos", "San Alberto"],
    "7621": ["La Sara", "Ramos Otero", "Rincon De Baudrix", "San Simon"],
    "7623": ["Campo La Plata", "Campo Leite", "Campo Pelaez", "El Moro", "Las Nutrias", "Los Pinos", "San Agustin"],
    "7630": ["Hospital Necochea", "La Primitiva", "Medano Blanco", "Necochea", "Valenzuela Anton", "Villa Diaz Velez"],
    "7631": ["Costa Bonita Balneario", "Haras El Moro", "Haras Nacional", "La Playa", "Malecon Gardella", "Quequen", "San Miguel Del Moro", "Villa Puerto Quequen"],
    "7633": ["Maori", "Pieres", "Tamangueyu"],
    "7635": ["El Lenguaraz", "Kilometro 440", "Loberia", "Los Cerros", "San Jose"],
    "7637": ["La Dulce", "Nicanor Olivera"],
    "7639": ["Cooper", "Lumb"],
    "7641": ["Balneario Los Angeles", "El Pito", "Energia", "Puerto Necochea", "Ramon Santamarina"],
    "8000": ["Adela Corti", "Bahia Blanca", "Choique", "Colonia Bella Vista", "Puerto Galvan", "Villa Buenos Aires", "Villa Cerrito", "Villa Delfina", "Villa Domingo Pronsato", "Villa Floresta", "Villa Italia", "Villa Libre", "Villa Loreto", "Villa Mitre", "Villa Nocito", "Villa Obrera", "Villa Olga Grumbein", "Villa Sanchez Elia"],
    "8101": ["Calderon", "Grunbein", "Kilometro 11", "Kilometro 9 Sud", "Villa General Arias", "Villa Harding Green", "Villa Herminia"],
    "8103": ["Garro", "Ingeniero White", "Spurr", "Villa Rosas", "Villa Serra", "Zona Cangrejales"],
    "8105": ["Aguara", "Colonia La Merced", "Gral Daniel Cerri", "Kilometro 666", "Sauce Chico"],
    "8107": ["Base Aeronaval Cmte Espora", "Espora"],
    "8109": ["Almirante Solier", "Balneario Parada", "Desvio Sandrini", "Kilometro 652", "La Martina", "Pehuen Co", "Punta Alta", "Villa Del Mar", "Villa Laura", "Villa Maio"],
    "8111": ["Arroyo Pareja", "Isla Catarelli", "Puerto Belgrano", "Puerto Rosales"],
    "8113": ["Baterias"],
    "8115": ["Bajo Hondo", "La Virginia", "Las Oscuras", "Paso Mayor"],
    "8117": ["Alferez San Martin", "Chasico", "El Cortapie", "Empalme Piedra Echada", "Lopez Lecube", "Nueva Roma", "Pelicura", "Piedra Ancha", "Venancio"],
    "8118": ["Cabildo", "Cochrane", "Coronel Falcon", "Corti", "Estomba"],
    "8122": ["La Viticola"],
    "8124": ["Berraondo", "General Rondeau", "La Pochola", "San German"],
    "8126": ["Aldea San Andres", "La Colorada Chica", "Villa Iris"],
    "8127": ["Estela", "Rivadeo"],
    "8129": ["17 De Agosto", "Adela Saenz", "Felipe Sola", "Glorialdo"],
    "8132": ["Balneario Chapalco", "Balneario San Antonio", "Colonia Los Alfalfares", "Colonia San Enrique", "Medanos"],
    "8133": ["La Rosa"],
    "8134": ["6 De Octubre", "Argerich", "Cabeza De Buey", "Colonia Ocampo", "La Gleva", "La Mascota", "Laguna Chasico", "Las Escobas", "Las Piedras", "Medanos Negros", "Nicolas Levalle", "Paso Cramer", "Rio Salado", "Salinas Chicas"],
    "8136": ["Algarrobo", "Colonia Cuarenta Y Tres", "Colonia La Catalina", "Juan Couste", "La Blanca", "La Celina", "La Eva", "La Sombra", "Montes De Oca", "San Emilio", "San Jose"],
    "8138": ["Anzoategui", "Balo Los Morros", "Caleu Caleu", "Colonia Julia Y Echarren", "Coronel Eugenio Del Busto", "El Aguila", "Gaviotas", "Juan De Garay", "La Adela", "La Maria Ines", "La Tosca", "Los Morros", "Lote 14", "Lote 17", "Lote 18", "Lote 19 Colonia N Leven", "Lote 22", "Lote 23", "Lote 24", "Lote 6", "Lote 7", "Lote 8", "Pichi Mahuida", "Rio Colorado", "Salinas", "Salinas Grandes Anzoategui", "San Leon"],
    "8142": ["Colonia Barga", "Colonia El Guanaco", "Colonia La Graciela", "Colonia Los Alamos", "Colonia San Francisco", "Colonia Tapatta", "Hilario Ascasubi", "Juan A Pradere", "Ombucta", "Paso Alsina", "Puerto Coloma", "San Adolfo"],
    "8144": ["Colonia Monte La Plata", "Colonia Pueblo Ruso", "El Paraiso", "Kilometro 697", "La Celia", "Teniente Origone"],
    "8146": ["El Rincon", "Isla Verde", "Mayor Buratovich", "Villa Rio Chico"],
    "8148": ["Estancia Las Isletas", "Fortin Mercedes", "Fortin Viejo", "Las Isletas", "Pedro Luro"],
    "8150": ["Campo La Lima", "Coronel Dorrego", "Faro", "La Luna", "La Sirena", "Laguna Sauce Grande", "San Ramon", "Sauce Grande"],
    "8151": ["El Zorro", "Gil", "Kilometro 563", "La Aurora", "Nicolas Descalzi", "Zubiaurre"],
    "8153": ["Balneario Oriente", "Balneario Sauce Grande", "Monte Hermoso"],
    "8154": ["Calvo", "La Soberana", "San Roman"],
    "8156": ["El Perdido Est Jose Guisasola"],
    "8158": ["Aparicio", "Paraje La Aurora"],
    "8160": ["Fortin Chaco", "Fuerte Argentino", "Tornquist", "Villa Ventana"],
    "8162": ["Garcia Del Rio", "Tres Picos"],
    "8164": ["Arquedas", "Colonia San Martin", "Colonia San Pedro", "Dufaur", "San Martin De Tours"],
    "8166": ["Saldungaray"],
    "8168": ["Sierra De La Ventana"],
    "8170": ["Abra De Hinojo", "Alta Vista", "Ducos", "Pigue"],
    "8171": ["Espartillar"],
    "8172": ["Arroyo Corto"],
    "8174": ["Arroyo Aguas Blancas", "La Saudade", "Saavedra"],
    "8175": ["Goyena"],
    "8180": ["Colonia Dr Gdor Udaondo", "Desvio San Alejo", "Puan", "San Andres", "Viboras"],
    "8181": ["Azopardo", "Colonia El Pincen", "Colonia Hipolito Yrigoyen", "Colonia Santa Rosa", "Erize", "La Vascongada"],
    "8183": ["Avestruz", "Cañada Mariano", "Colonia La Vascongada", "Darregueira", "Tres Cuervos"],
    "8185": ["Campo Del Norte Americano", "Campo La Zulema", "Campo Los Aromos", "Campo San Juan", "Canonigo Gorriti", "Colonia La Estrella", "Colonia Lapin", "Colonia Leven", "Colonia Phillipson N 1", "Colonia Santa Mariana", "Delfin Huergo", "Esteban A Gascon", "La Florida", "Monte Fiore", "San Antonio", "San Miguel Arcangel", "Villa Margarita"],
    "8187": ["Bordenave", "La Rosalia"],
    "8200": ["Colonia Lia Y Allende", "El Boqueron", "El Carancho", "El Madrigal", "El Veraneo", "Ex Escuela Hogar Nro 5", "General Acha", "La Aurora", "La Banderita", "La Chita", "La Escondida", "La Lonja", "La Magdalena", "La Moderna", "La Nilda", "La Paloma", "La Pampita", "La Sorpresa", "Las Acacias", "Las Dos Naciones", "Lote 10", "Lote 11", "Lote 12", "Lote 13", "Lote 18", "Lote 19", "Lote 21", "Lote 22", "Lote 3", "Maraco", "Maraco Chico", "Medano Colorado", "Quiñi Malal", "San Simon", "Sierras De Lihuel Calel", "Valle Argentino", "Valle Daza"],
    "8201": ["25 De Mayo", "Barrancas Coloradas", "Belgrano", "Casa De Piedra", "Cerro Azul", "Cerro Bayo", "Cerro Del Aigre", "Cerro La Bota", "Chacharramendi", "Colonia Chica", "Colonia El Sauzal", "Colonia Los Piojos", "Colonia San Ignacio", "El Cinco", "El Diez", "El Diez Y Siete", "El Escabel", "El Huitru", "El Nueve", "El Tartagal", "El Trece", "El Uno", "Euskadi", "Gobernador Ayala", "Guaraco", "Julian A Mansilla", "La Asturiana", "La Chita Puelches", "La Clelia", "La Limpia", "La Lucha La Reforma", "La Reforma", "La Reforma Vieja", "Laguna Quiroga", "Legasa", "Lihue Calel", "Limay Mahuida", "Minerales De La Pampa", "Puelches", "San Roberto", "San Salvador", "Santa Elena"],
    "8203": ["La Chirlandia", "La Sin Nombre", "Los Olivos", "Quehue", "San Antonio", "San Ernesto", "Santo Domingo", "Utracan"],
    "8204": ["Bernasconi", "Colonia 17 De Agosto", "Colonia Las Tres Piedras", "Dos Chañares", "Gervasio Ortiz De Rosas", "La Esperanza", "Lote 12", "Lote 20", "Maria", "Narciso Leven", "San Bernardo", "San Fernando", "San Jose"],
    "8206": ["Colonia España", "Colonia Helvecia", "Colonia Villa Alba", "El Trigo", "El Vasquito", "General San Martin", "La Colorada Chica", "La Colorada Grande", "La Juanita", "La Porteña", "La Primera", "La Puma", "Lote 17 Escuela 121", "Lote 18 Escuela 158", "Lote 23 Escuela 264", "Lote 7 Escuela 270", "Lote 8  Escuela 179", "Minas De Sal", "Traico", "Villa Alba"],
    "8208": ["Campo Cicare", "Campo De Salas", "Campo Nicholson", "Colonia Beatriz", "Colonia San Rosario", "Colonia Vascongada", "Jacinto Arauz", "Traico Grande", "Villa Mencuelle"],
    "8212": ["Abramo", "Cona Lauquen", "Cotita", "Dos Amigos", "Dos De Ipiña", "Dos Violetas", "El Lucero", "El Mirador", "Hucal", "Ipiña", "La Administracion", "La Catita", "La Constancia", "La Elva", "La Estrella Del Sud", "La Isabel", "La Maria", "La Maria Elena", "La Maria Elisa", "La Union", "La Victoria", "Lote 11 Bernasconi", "Lote 22 Ipiña", "Lote 8", "Luna", "Peru", "Piche Cona Lauquen", "Remeco", "San Aquilino", "San Diego", "San Juan", "San Miguel", "Tres Botones", "Tres Naciones", "Tribuluci", "Trubuluco"],
    "8214": ["Colonia Cazaux", "Colonia La Mutua", "Colonia Medano Colorado", "Colonia Santa Clara", "Colonia Santa Maria", "Cuchillo Co", "El Descanso", "El Pimia", "El Porvenir", "El Puma", "Epu Pel", "La Torera", "Pichi Mahuida", "Santa Clara", "Santa Maria", "Unanue"],
    "8300": ["Las Perlas", "Loma De La Lata", "Mari Menuco", "Neuquen", "Portezuelo Grande", "Rincon De Emilio"],
    "8301": ["Aguada De Los Pajaritos", "Contralmirante Cordero", "Cuenca Vidal", "Ferri", "Planicie Banderita"],
    "8303": ["Cinco Saltos"],
    "8305": ["Aguada San Roque", "Auca Mahuida", "Añelo", "Barda Del Medio", "Colonia El Manzano", "Coronel Vidal", "Kilometro 1218", "Lago Pellegrini", "Los Chihuidos", "Los Chinitos", "Punta De Sierra", "San Patricio Del Chañar", "Sargento Vidal", "Tratayen"],
    "8307": ["Aguara", "Catriel", "Colonia Alte Guerrico", "Colonia Gobernador Ayala", "Cos Zaures", "La Bota", "La Copelina", "Los Sauces", "Paso La Balsa", "Peñas Blancas", "Puelen", "Valle De Los Alamos"],
    "8308": ["Villa Manzano"],
    "8309": ["Centenario", "Vista Alegre Norte", "Vista Alegre Sur"],
    "8311": ["Villa El Chocon"],
    "8313": ["Arroyito", "Arroyito Challaco", "Cerro Del Leon", "El Sauce", "Limay Centro", "Los Sauces", "Naupa Huen", "Pantanitos", "Paso Aguerre", "Picun Leufu"],
    "8315": ["Achico", "Bajada Colorada", "Carran Cura", "Carri Lauquen", "Costa Limay", "La Pintada", "La Teresa", "Nogueira", "Piedra Del Aguila", "Piedra Pintada", "San Bernardo", "Santa Isabel", "Santo Tomas", "Sañico", "Villa Rincon Chico", "Zaina Yegua"],
    "8316": ["Balsa Senillosa", "China Muerta", "Plottier", "Senillosa"],
    "8318": ["Challaco", "Paso De Los Indios", "Plaza Huincul"],
    "8319": ["Campamento Sol", "Octavio Pico", "Puesto Hernandez Baterias", "Rincon De Los Sauces", "Sauzal Bonito"],
    "8322": ["Cutral Co", "Pueblo Nuevo"],
    "8324": ["Cipolletti", "Cuatro Esquinas", "General Fernandez Oro", "Iris", "La Alianza", "La Emilia", "La Esmeralda", "La Estancia Vieja", "La Lucinda", "Las Perlas", "San Jorge"],
    "8326": ["Cervantes", "Chichinales", "Mainque"],
    "8328": ["Allen", "Barrio Norte", "Chacras De Allen", "Contralmirante M Guerrico", "El Manzano"],
    "8332": ["Colonia Rusa", "General Roca", "Padre Alejandro Stefenelli", "Quempu Niyeu", "Tricaco"],
    "8333": ["Aguada Guzman", "Alanitos", "Barda Colorada", "Cerro Policia", "Coronel Juan Jose Gomez", "El Cuy", "Michi Honoca", "Paso Cordova", "Planicie De Jaguelito"],
    "8334": ["Ingeniero Huergo"],
    "8336": ["Colonia Regina", "General Enrique Godoy", "Gobernador Duval", "Krause Ingeniero Otto", "La Japonesa", "Tercera Zona", "Valle Azul", "Villa Alberdi", "Villa Regina"],
    "8340": ["Aguada Florencio", "Bajada De Los Molles", "Bajada Del Marucho", "Barda Anguil", "Barda Negra", "Caichihue", "Chacayco", "Covunco", "Covunco Arriba", "El Overo", "El Tropezon", "Goñi Co", "La Fria", "La Isabel", "La Patagonia", "La Patria", "La Picaza", "La Pochola", "La Susana", "La Teresa", "Laguna Blanca", "Laguna Miranda", "Las Barditas", "Las Cortaderas", "Los Catutos", "Los Muchachos", "Mallin De Los Caballos", "Ojo De Agua", "Portada Covunco", "Puente Picun Leufu", "Ramon M Castro", "Santo Domingo", "Taqui Nileu", "Tres Piedras", "Zapala", "Ñireco Sud"],
    "8341": ["Arroyo Quillen", "Catan Lil", "Charahuilla", "El Dormido", "El Gato", "Espinazo Del Zorro", "Fortin 1 De Mayo", "La Arboleda", "La Ofelia", "Laja", "Lapa", "Lapachal", "Las Coloradas", "Los Rodillos", "Malalco", "Media Luna", "Ojo De Agua", "Paso Cata Tun", "Quillen", "Quinineliu", "Rahue", "San Juan Rahue"],
    "8345": ["Alumine", "Carri Lil", "Chanquil Quilla", "Haras Patria", "Kilca Casa", "La Angostura De Icalma", "Lago Pulmari", "Lago Ñorquinco", "Lagotera", "Litran", "Lonco Luan", "Lonco Mula", "Moquehue", "Pampa De Lonco Luan", "Quilca", "Ruca Choroy Arriba", "Sainuco", "Villa Pehuenia"],
    "8347": ["Arroyo Cahunco", "Arroyo Ranquilco", "Cajon Del Toro", "Calihue", "Carreri", "Cerro Colorado", "Cerro De La Grasa", "Chacay", "Cochico", "Codihue", "Corral De Piedra", "Cuchillo Cura", "El Atravesado", "El Escorial", "El Palao", "Haichol", "Huillilon", "La Buitrera", "La Porteña", "La Verdad", "Las Lajas", "Las Lajitas", "Las Toscas", "Las Tres Lagunas", "Liu Cullin", "Llamuco", "Los Galpones", "Mallin Blanco", "Mallin Chileno", "Mallin De La Cueva", "Mallin De Mena", "Mallin Del Rubio", "Mallin Quemado", "Paso Ancho", "Piche Ponon", "Piedras Bayas", "Pino Hachado", "Pino Solo", "Pozo Hualiches", "Primeros Pinos", "Quebrada Honda", "Ramichal", "Salquico", "San Demetrio"],
    "8349": ["Aguas De Las Mulas", "Cajon De Almaza", "Cajon De Los Patos", "Cajon De Manzano", "Caviahue", "Cerro De La Parva", "Chenquecura", "Chochoy Mallin", "Colipili", "Copahue", "El Bosque", "El Huecu", "El Pino Andino", "Haycu", "Hualcupen", "Huarenchenque", "La Argentina", "Loncopue", "Mallin Del Toro", "Mulichinco", "Nalay Cullin", "Ranqueles", "Ranquilco", "Ranquilon", "Richoique", "Santa Isabel", "Tralaitue", "Vilu Mallin", "Ñorquin"],
    "8351": ["Agrio Balsa", "Bajada Del Agrio", "Balneario Del Rio Agrio", "Balsa Del Rio Agrio", "Chorriaca", "Coihueco", "Coli Malal", "Confluencia Del Aguijon", "Costa Del Arroyo Salado", "Covunco Abajo", "Covunco Centro", "El Peralito", "El Salado", "Franhucura", "Huncal", "Mariano Moreno", "Nau Nauco", "Pampa Del Salado", "Pichaihue", "Pichi Neuquen", "Pilmatue", "Quili Malal", "Quintuco", "Rio Agrio", "Taquimilan", "Trahuncura", "Vaca Muerta"],
    "8353": ["Aguada Chacay Co", "Andacollo", "Anquinco", "Arroyo Blanco", "Barrancas", "Batre Lauquen", "Bella Vista", "Buta Co", "Buta Mallin", "Buta Ranquil", "Butalon", "Caepe Malal", "Cajon Grande", "Camaleones", "Cancha Huinganco", "Casa De Piedra", "Cayanta", "Cañada Seca", "Cerro Negro Chapua", "Cerro Negro Tricao", "Chacay Co", "Chacay Melehue", "Chapua", "Chapua Abajo", "Chos Malal", "Coyuco Cochico", "Cura Co", "Curi Leuvu", "El Alamito", "El Chingue", "El Cholar", "El Curileo", "El Durazno", "El Porton", "El Tromen", "Filmatue", "Flores", "Fortin Guañacos", "Guañacos", "Huantraico", "Huaraco", "Huinganco", "Huitrin", "Humigamio", "Invernada Vieja", "Jecanasco", "Juaranco", "La Cienaga", "La Cieneguita", "La Primavera", "La Salada", "Las Abejas", "Las Chacras", "Las Cortaderas", "Las Lagunas", "Las Ovejas", "Las Saladas", "Leuto Caballo", "Lileo", "Los Bolillos", "Los Carrizos", "Los Chacales", "Los Cisnes", "Los Entierros", "Los Menucos", "Los Miches", "Los Molles", "Los Tres Chorros", "Luicoco", "Luin Coco", "Machico", "Manzano Amargo", "Mayan Mahuida", "Milla", "Mina Carrascosa", "Mina Lileo", "Nahueve", "Nereco Norte", "Nireco", "Palau", "Pampa De Tril", "Pampa Ferreira", "Paso Barda", "Quempu Leufu", "Ranquil Vega", "Reñileo", "Rio Barrancas", "San Eduardo", "Taquimillan Abajo", "Tierras Blancas", "Tihue", "Tres Chorros", "Tricao Malal", "Trili", "Varvarco", "Villa Curi Leuvu"],
    "8360": ["Bajo Rico", "Benjamin Zorrilla", "Buena Esperanza", "Choele Choel", "Fortin Uno", "La Elvira", "La Sara", "Los Molinos", "Maria Cristina", "Negro Muerto", "Paso Piedra", "Puesto Faria", "Rinconada", "Sauce Blanco"],
    "8361": ["Isla Grande", "Luis Beltran", "Paso Lezcano"],
    "8363": ["Colonia Josefa", "Estancia Las Julias", "Isla Chica", "La Julia", "Lamarque", "Pomona", "Salitral Negro", "Santa Genoveva"],
    "8364": ["Belisle Coronel", "Chimpay", "Darwin", "Santa Gregoria", "Santa Nicolasa"],
    "8366": ["Chelforo"],
    "8370": ["Caminera", "Chapelco", "El Cerrito", "El Oasis", "El Porvenir", "Filo Hua Hum", "Hua Hum", "La Fortuna", "Lago Lolog", "Las Bandurrias", "Lascar", "Lolog", "Quila Quina", "Quita Quina", "San Martin De Los Andes", "Trompul", "Villa Lago Meliquina", "Villa Raur"],
    "8371": ["Atreuco", "Chiuquillihuin", "Collun Co", "Huechulafquen", "Junin De Los Andes", "La Atalaya", "La Union", "Lubeca", "Mamul Malal", "Nahuel Mape", "Palitue", "Piedra Mala", "Quila Quehue", "Quilquihue", "San Juan Junin De Los Andes", "Tres Picos", "Tromen"],
    "8373": ["Alianza", "Auca Pan", "Caleufu", "Cerro De Los Pinos", "Chacabuco", "Chacoyal", "Chichiguay", "Chimehuin", "Chinchina", "Las Mercedes", "Pampa Del Malleo", "Peña Colorada", "Pilo Lil", "Quentrenquen", "Quinquimitreo", "Tipiliuke"],
    "8375": ["Cañadon De Los Indios", "Cañadon Del Indio", "Cerro Gato", "Collon Cura", "El Salitral", "Huechahue", "La Negra", "La Rinconada", "Mallin De Las Yeguas", "Pampa Collon Cura", "Paso De San Ignacio", "Quemquemtreu", "San Ignacio", "Santa Isabel", "Zingone Y Cia M", "Zulemita"],
    "8379": ["Gente Grande"],
    "8400": ["El Condor Estancia", "Isla Victoria", "Laguna Los Juncos", "Peninsula Huemul", "Perito Moreno Estacion Fcgr", "Playa Bonita", "Puerto Anchorena", "Puerto Tigre Isla Victoria", "San Carlos De Bariloche", "Ñirihuao Estacion Fcgr"],
    "8401": ["Arroyo Chacay", "Cullin Manzano", "El Foyel", "Estancia Newbery", "Estancia Tequel Malal", "La Araucaria", "La Estacada", "La Lipela", "Nahuel Huapi", "Paso Chacabuco", "Paso Coihue", "Rincon Chico", "Rincon Grande", "Rio Villegas", "Santa Maria", "Villa Llanquin", "Villa Mascardi"],
    "8402": ["Dina Huapi"],
    "8403": ["Alicura", "Arroyo Blanco", "Caminera Traful", "Cerro Alto", "Corralito", "El Manzano", "Estancia La Primavera", "Huinca Lu", "Paso Del Limay", "Paso Flores", "Paso Miranda", "Villa Traful"],
    "8407": ["Correntoso", "El Arbolito", "El Machete", "Puerto Manzano", "Villa La Angostura"],
    "8409": ["Puerto Ojo De Agua", "Tunquelen"],
    "8411": ["Cascada Los Cantaros", "Laguna Frias", "Puerto Blest"],
    "8412": ["Carhue", "Casa Quemada", "Cañadon Del Corral", "Chenqueniyeu", "Churquiñeo", "Corral De Los Pinos", "Costas Del Pichi Leufu", "El Pantanoso", "La Quebrada", "Las Bayas", "Menuco Vaca Muerta", "Panquehuao", "Paso De Los Molles", "Pichi Leufu", "Pichi Leufu Abajo", "Pichi Leufu Arriba", "Pilcaniyeu", "Pilquiniyeu Del Limay", "Rayhuao", "San Pedro"],
    "8415": ["Arroyo Las Minas", "Cerro Mesa", "Chacalhua Ruca", "Chacay Huarruca", "Fitalancao", "Fitamiche", "Fitatimen", "Mamuel Choique", "Portezuelo", "Repollos", "Rio Chico", "Ñorquinco", "Ñorquinco Sud"],
    "8416": ["Anecon Grande", "Cañadon Camallo", "Clemente Onelli", "Comallo", "Comallo Abajo", "Coquelen", "Ingeniero Zimmermann Resta", "Neneo Ruca", "Perito Moreno", "Pilquiniyeu", "Quinta Panal", "San Ramon", "Tres Ojos De Aguas"],
    "8417": ["Canllequin", "Carri Yegua", "Cañadon Chileno", "Chasico", "Cura Lauquen", "El Cacique", "El Camaruro", "El Gaucho Pobre", "El Jardinero", "Hua Miche", "Jita Rusia", "Kili Malal", "La Angostura", "La Chilena", "La Criollita", "La Estrella", "La Excurra", "La Mimosa", "La Porteña", "La Rubia", "La Vencedora", "Laguna Blanca", "Lanquiñeo", "Las Mellizas", "Lonco Vaca", "Los Costeros", "Los Pirineos", "Los Quebrachos", "Mencue", "Michihuao", "Mulanillo", "Palenque Niyeu", "Pilahue", "Santa Elena"],
    "8418": ["Anecon Chico", "Atraico", "Carrilauquen", "Chaiful", "Colan Conhue", "Coli Toro", "El Cheiful", "El Moligue", "Empalme Kilometro 648", "Fita Ruin", "Huan Luan", "Ingeniero Jacobacci", "Ojos De Agua Embarcadero Fcgb", "Quentrequile", "Yuquinche"],
    "8422": ["Aguada De Piedra", "Barril Niyeo", "Chichihuao", "El Cain", "Los Juncos", "Los Manantiales", "Mancullique", "Maquinchao", "Niluan", "Rucu Luan", "Tromeniyeu", "Vaca Lauquen"],
    "8424": ["Aguada De Guerra", "Caltrauna", "Cerro Abanico", "Comi Co", "Ganzu Lauquen", "La Rinconada", "Lagunita", "Lenzaniyen", "Loma Blanca", "Los Menucos", "Prahuaniyeu"],
    "8430": ["Cerro Radal", "Costa Del Rio Azul", "El Bolson", "El Manso", "Las Golondrinas", "Los Repollos", "Mallin Ahogado", "Villa Turismo"],
    "8431": ["El Hoyo", "Lago Puelo", "Paraje Entre Rios"],
    "8500": ["El Dique", "General Liborio Bernal", "La Meseta", "Mata Negra", "Viedma"],
    "8501": ["Bahia Creek", "Balneario El Condor", "Colonia General Frias", "Cubanea", "La Granja", "La Loberia", "San Javier", "Segunda Angostura", "Tte Gral Eustaquio Frias"],
    "8503": ["Chocori", "Colonia La Luisa", "Colonia San Juan", "Coronel Francisco Sosa", "El Porvenir", "General Conesa", "Ingenio San Lorenzo", "La Carolina", "La Flecha", "Luis M Zagaglia", "Nueva Carolina", "Puesto Gaviña", "Rincon De Gastre", "San Juan", "San Lorenzo", "San Simon", "Travesia Castro"],
    "8504": ["Cantera Villalonga", "Carmen De Patagones", "China Muerta", "El Bagual", "Faro Segunda Barrancosa", "Las Cortaderas", "Termas Los Gauchos", "Villa 7 De Marzo"],
    "8505": ["Boca De La Travesia", "Emilio Lamarca", "Guardia Mitre", "Primera Angostura", "Sauce Blanco"],
    "8506": ["Bahia San Blas", "Cardenal Cagliero", "Jose B Casas", "Puerto Wassermann", "Salina De Piedra"],
    "8508": ["Ambrosio P Lezica", "Colonia La Celina", "Colonia Miguel Esteverena", "Jarrilla", "Los Pocitos Balneario", "Puerto Tres Bonetes", "Stroeder"],
    "8512": ["Igarzabal", "Los Pozos", "Villa Elena", "Villalonga"],
    "8514": ["Laguna Del Barro", "Laguna Del Monte", "Nuevo Leon", "Pozo Salado", "Saco Viejo"],
    "8520": ["Aguada Del Loro", "Bajo Del Gualicho", "Barrio Laguna", "Cinco Chañares", "Jaguel Campo Monte", "La Bombilla", "La Primavera", "Laguna Cortes", "Laguna De La Prueba", "Las Maquinas", "Mancha Blanca", "Percy H Scott", "Pozo Moro", "San Antonio Oeste"],
    "8521": ["Arroyo De La Ventana", "Arroyo Los Berros", "Arroyo Tembrao", "Arroyo Verde", "Balneario Las Grutas", "Cona Niyeu", "Puerto San Antonio Este", "Sierra De La Ventana", "Sierra Paileman"],
    "8532": ["Arroyo Salado", "Arroyo Verde", "Campana Mahuida", "Empalme Puerto Lobos", "Playas Doradas", "Puerto Lobos", "Sierra Grande"],
    "8534": ["Aguada Cecilio", "Falckner", "La Esperanza", "Ministro Ramos Mexia", "Sierra Colorada", "Teniente Maza Estacion Fcgr", "Treneta", "Yaminue"],
    "8536": ["Chipauquil", "El Salado", "Musters", "Nahuel Niyeu", "Paja Alta", "Punta De Agua", "Valcheta"],
    "9000": ["Comodoro Rivadavia", "El Trebol", "Kilometro 11", "Manantiales Behr", "Pampa Del Castillo", "Pico Salamanca"],
    "9001": ["Cañadon Ferrais", "Rada Tilly"],
    "9003": ["Bahia Solano", "Barrio Astra", "Caleta Cordova", "Empalme A Astra"],
    "9007": ["El Jaguel", "Garayalde", "La Castellana", "La Salamanca", "Malaspina", "Pampa Pelada", "Pampa Salamanca", "Rio Chico", "Ruta 3 Kilometro 1711", "Sierra Colorada", "Sierra Cuadrada", "Sierra Overa Chicas Y Grandes", "Uzcudun"],
    "9009": ["Cañadon Lagarto", "Cañadon Lopez", "Cañadon Pedro Ex Valle Hermoso", "Holdich"],
    "9011": ["Bahia Langara", "Caleta Olivia", "Cerro Mangrullo", "La Esther"],
    "9013": ["Cañadon Seco"],
    "9015": ["Alma Grande", "Jelaina", "La Antonia", "La Guardia", "La Rosa", "Minerales", "Pico Truncado", "Zanjon Del Pescado"],
    "9017": ["Cameron", "Cañadon Pluma", "Cerro La Setenta", "Cerro Renzel", "Cerro Silva", "Colonia Carlos Pellegrini", "Cueva De Las Manos", "El Guadal", "El Pluma", "India Muerta", "La Argentina", "La Maria", "Lago Buenos Aires", "Las Heras", "Las Masitas", "Las Piramides", "Leandro Niceforo Alem", "Los Perales", "Mata Magallanes", "Meseta Guengue", "Pampa Verdum", "Pellegrini", "Piedra Clavada", "Yegua Muerta"],
    "9019": ["Aguada Escondida", "Cerro Moro", "Fitz Roy", "Koluel Kaike", "Monte Verde", "Tehuelches"],
    "9020": ["Arroyo Quilla", "Cañadon Carril", "Cañadon Tacho", "Colonia Germania", "Costa Rio Chico", "Enrique Hermitte", "Kilometro 191", "Laguna Del Mate", "Laguna Palacio", "Las Pulgas", "Manantial Grande", "Paso De Torres", "Sarmiento", "Sierra Corrientes", "Sierra Victoria", "Valle Hermoso"],
    "9021": ["Colhue Huapi"],
    "9023": ["Buen Pasto", "Lago Musters", "Sierra Nevada Buen Pasto"],
    "9030": ["Rio Mayo"],
    "9031": ["Bajo La Cancha", "Facundo", "Los Tamariscos"],
    "9033": ["Aldea Apeleg", "Alto Rio Senguer", "Arroyo Gato", "El Coite", "La Pepita", "Lago Fontana", "Pastos Blancos"],
    "9035": ["Arroyo Chalia", "Doctor Ricardo Rojas"],
    "9037": ["Aldea Beleiro", "Alto Rio Mayo", "El Triana"],
    "9039": ["Hito 45", "Hito 50", "La Cancha", "La Nicolasa", "La Siberia", "Lago Blanco", "Valle Huemules"],
    "9040": ["Cañadon Botello", "Colonia Leandro N Alem", "El Portezuelo", "Ingeniero Pallavicini", "La Asturiana", "Lago Buenos Aires", "Monte Ceballos", "Nacimientos Del Pluma", "Perito Moreno", "Rio Fenix"],
    "9041": ["Los Antiguos"],
    "9050": ["Gobernador Moyano", "Kilometro 8", "Paso Gregores", "Puerto Deseado", "Tellier", "Tres Cerros"],
    "9051": ["Aguada A Pique", "Aguada La Oveja", "Cabo Blanco", "Cabo Tres Puntas", "Cerro Puntudo", "Cerro Redondo", "El Chara", "El Hueco", "El Loro", "El Polvorin", "La Aguada", "La Central", "La Estela", "La Fecundidad", "La Madrugada", "La Margarita", "La Protegida", "La Rosada", "La Victoria", "La Violeta", "Mazaredo", "Sarai", "Tres Puntas"],
    "9053": ["Aguada Grande", "Cerro Alto", "Cerro Negro", "Desamparados", "El Barbucho", "Floradora", "Jaramillo"],
    "9100": ["Cerro Santa Ana", "Dos Pozos", "Trelew"],
    "9101": ["Alto De Las Plumas", "Bajada Del Diablo", "Base Aeronaval Alte Irizar", "Cabeza De Buey", "Dique Florentino Ameghino", "El Mirasol", "Las Plumas", "Puente Hendre"],
    "9103": ["Bajo De Los Huesos", "Casa Blanca", "Charque Chico", "Playa Union", "Rawson", "Sol De Mayo"],
    "9105": ["Angostura", "Angostura Segunda", "Betesta", "Bryn Brown", "Bryn Gwyn", "Cabaña Del Valle", "El Argentino", "Gaiman", "Glasfryn", "Loma Redonda", "Maesteg", "Treorki", "Valle Los Martires", "Villa Ines"],
    "9107": ["28 De Julio", "Boca De La Zanja", "Boca Zanja Sud", "Campamento Villegas", "Dolavon", "Ebenecer", "Laguna Grande", "Las Chapas", "Toma De Los Canales"],
    "9111": ["Bahia Bustamante", "Cabo Raso", "Camarones", "La Castellana", "Ruta 3 Kilometro 1646"],
    "9113": ["Florentino Ameghino"],
    "9120": ["Bahia Cracher", "Catayco", "Cerro Pichalao", "El Desempeño", "Puerto Madryn", "Punta Ninfas", "Punta Quiroga"],
    "9121": ["Aguada De Las Tejas", "Aguada Del Pito", "Bajada Moreno", "Bajo Bartolo", "Bajo Del Gualicho", "Bajo Las Damajuanas", "Blancuntre", "Caleta Valdez", "Carhue Niyeo", "Cañadon Bagual", "Cañadon Blanco", "Cañadon Chileno", "Chacay Este", "Chacay Oeste", "Chasico", "Colelache", "El Alamo", "El Chacay", "El Escorial", "El Pastizal", "El Piquillin", "El Quilimuay", "El Ruano", "El Salitral", "Estancia El Moro", "Gan Gan", "Gastre", "La Corona", "La Rosilla", "Laguna De Vacas", "Laguna Fria", "Lagunita Salada", "Larralde", "Loreto", "Mallin Grande", "Mallin Grande Corcovado", "Medanos", "Painaluf", "Pirre Mahuida", "Puerto Piramides", "Puerto San Roman", "Punta Bajos", "Punta Delgada", "Punta Norte", "Sacanana", "Salinas Chicas", "Salinas Grandes", "San Jose", "Seprucal", "Sierra Chata", "Sierra Chica", "Sierra Rosada", "Talagapa", "Tatuen", "Telsen", "Valle Del Rio Chubut"],
    "9200": ["Arroyo Pescado", "Cerro Mallaco", "Chacra De Austin", "Colonia 16 De Octubre", "Esquel", "La Cancha", "La Lancha", "Laguna Terraplen", "Matucana", "Mayoco", "Nahuel Pan Estacion Fcgr", "Sierra De Tecka", "Sunica", "Villa Futalaufquen"],
    "9201": ["Cachel", "Cajon De Ginebra Chico", "Cajon De Ginebra Grande", "Carrenleufu", "Cerro Lonco Trapial", "Colan Conhue", "Colonia Epulef", "Corcovado", "Costa Del Lepa", "El Calafate", "El Cronometro", "El Cuche", "El Kaquel", "El Mirador", "El Pajarito", "El Portezuelo", "El Poyo", "Estancia La Mimosa", "Estancia Pampa Chica", "Gualjaina", "La Primavera", "Languiñeo", "Las Salinas", "Mallin Blanco", "Pampa De Agnia", "Pampa Tepuel", "Parque Nacional Los Alerces", "Paso Del Sapo", "Piedra Parada", "Pocitos De Quichaura", "Taquetren", "Tecka", "Valle Del Tecka", "Valle Garin"],
    "9203": ["Aldea Escolar", "Arroyo Percy", "Cerro Centinela", "Futaleufu", "Lago Rosario", "Legua 24", "Los Cipreses", "Rio Corinto", "Trevelin", "Valle Frio"],
    "9207": ["Arroyo Guilaia", "Cañada Bagual", "Cerro Condor", "El Canquel", "El Chalet", "El Sombrero", "La Bombilla", "Laguna Rincon Del Moro", "Las Cortaderas", "Las Horquetas", "Los Altares", "Los Manantiales", "Paso De Indios", "Sierra Nevada Paso De Indios", "Toro Hosco"],
    "9210": ["Boquete Bolson", "Buenos Aires Chico", "Costa Chubut", "Cuesta Del Ternero", "El Boquete", "El Maiten", "El Turbio", "Fithen Verin", "Fitirhuin", "Ing Bruno J Thomae"],
    "9211": ["Cushamen", "El Coihue", "El Colhue", "Epuyen"],
    "9213": ["Cañadon Caliente", "Cañadon Grande", "Cerro Fofocahuel", "Colonia Cushamen", "Fofo Cahuel", "Leleque", "Ranquil Huao", "Siempre Viva"],
    "9217": ["Arroyo El Mosquito", "Cholila", "El Cajon", "Lago Carlos Pellegrini", "Lago Lezana", "Lago Rivadavia", "Rio Carrileufu", "Villa Lago Rivadavia"],
    "9220": ["Casa Blanca", "Cañadon La Madera", "Corralitos", "El Molle", "Jose De San Martin", "Laguna Blanca", "Laguna Verde", "Mata Grande"],
    "9221": ["Valle Hondo"],
    "9223": ["Alto Rio Pico", "Cañadon Chacay", "Cerro Negro", "El Cherque", "El Shaman", "El Tropezon", "Gobernador Costa", "Las Mulas", "Lenzanilleo", "Los Corralitos", "Niriguao", "Niriguce Pampa", "Putrachoique", "Tres Picos"],
    "9225": ["Arenoso", "Frontera De Rio Pico", "Hito 43", "Lago Paz", "Lago Verde", "Lago Vintter", "Rio Pico", "Viglione Doctor Atilio Cesar"],
    "9227": ["El Porvenir", "Estancia Nueva Lubecka", "La Laurita", "Paso Moreno", "Piedra Shotel", "Rio Frias"],
    "9300": ["Cañadon De Las Vacas", "Cañadon Del Rancho", "El Guadal", "Puerto Santa Cruz"],
    "9301": ["El Chalten", "Guardaparque Fitz Roy", "La Federica", "La Florida", "Lago Cardiel", "Lago San Martin", "Lago Tar", "Paso Rio La Leona", "Peninsula Maipu", "Piedra Clavada", "Punta Del Lago Viedma", "Tres Lagos"],
    "9303": ["Cañadon Del Toro", "Cerro Redondo", "Chonque", "Comandante Luis Piedrabuena", "El Baile", "El Pan De Azucar", "El Paso", "Garminue", "La Barreta", "La Julia", "La Leona", "La Pigmea", "La Porteña", "Laguna Grande", "Las Mercedes", "Paso De Los Indios", "Paso Del Rio Santa Cruz", "Paso Ibañez", "Rio Chico", "Sierra De La Ventana", "Tauel Aike"],
    "9305": ["Cañada De Las Vacas"],
    "9310": ["Aguada Alegre", "Bahia Laura", "Bajo Fuego", "Cañadon 11 De Setiembre", "Lago Pueyrredon", "Puerto San Julian", "Yacimiento Cerro Vanguardia"],
    "9311": ["Cañadon Leon", "Cañadon Molinari", "Gobernador Gregores", "La Manchuria", "La Peninsula", "Lago Strobel", "Paso Del Aguila", "Tucu Tucu"],
    "9313": ["Cara Mala", "El Salado", "Faro Cabo Guardian", "Faro Campana", "Los Manantiales", "Punta Mercedes"],
    "9315": ["Bajo Caracoles", "H Yrigoyen Lago Posadas", "Hotel Las Horquetas", "Lago Posadas", "Paso Roballo", "Tamel Aike"],
    "9400": ["An Aike", "Bella Vista", "Cabo De Las Virgenes", "Camuzu Aike", "Cancha Carrera", "Cap", "Cañadon Fabre", "Cerro Palique", "Chall Aike", "Condor", "Coronel Guarumba", "Estacion Ing Atilio Cappa", "Ingeniero Atilio Cappa", "Laguna Colorada", "Las Horquetas", "Monte Aymond", "Palermo Aike", "Pali Aike", "Paso Del Medio", "Punta Del Monte", "Punta Loyola", "Rio Gallegos", "San Benito"],
    "9401": ["El Zurdo", "Fortaleza", "Fuentes Del Coyle", "Gobernador Mayer", "La Esperanza"],
    "9405": ["Bahia Tranquila", "Charles Fuhr", "Condor Clif", "El Calafate", "El Cerrito", "Lago Argentino", "Lago Roca", "Paso Charles Fhur", "Punta Bandera", "Quien Sabe", "Rio Bote", "Rio Calafate", "Rio Mitre", "Ventisquero Moreno"],
    "9407": ["28 De Noviembre", "Campamento Dorotea", "Coronel Martin Irigoyen", "El Turbio", "Gaypon", "Glencross", "Julia Dufour", "Mina 3", "Morro Chico", "Pueblo Nuevo", "Puente Blanco", "Rincon De Los Morros", "Rio Turbio", "Rospentek", "Rospentek Aike"],
    "9409": ["Isla Gran Malvina", "Isla Soledad"],
    "9410": ["Bahia Lapataia", "Estancia Harberton", "Hosteria Kaiken", "Isla De Los Estados", "Laguna Escondida", "Ushuaia"],
    "9411": ["Base Aerea Teniente Matienzo", "Base Aerea Vicecomod Marambio", "Base Belgrano", "Base Belgrano 2", "Base Belgrano 3", "Base Cientifica Tte Jubany", "Base Ejercito Esperanza", "Base Ejercito Gral San Martin", "Base Ejercito Primavera", "Base Ejercito Sobral", "Base Orcadas", "Destacamento Melchior", "Estacion Aeronaval", "Estacion Cientifica Alte Brown", "Isla Joinville", "Isla Shetland Del Sur", "Islas Georgias Del Sur", "Islas Orcadas Del Sur", "Islas Sandwich Del Sur"],
    "9420": ["Aserradero Arroyo", "Cabaña Ruby", "Cabo San Pablo", "Campamento Central Ypf", "Campamento Los Chorrillos", "Comisaria Radman", "El Paramo", "Estacion Osn", "Estancia Aurelia", "Estancia Buenos Aires", "Estancia Carmen", "Estancia Cauchico", "Estancia Costancia", "Estancia Cullen", "Estancia Despedida", "Estancia Dos Hemanas", "Estancia El Roble", "Estancia El Rodeo", "Estancia El Salvador", "Estancia Guazu Cue", "Estancia Herminita", "Estancia Ines", "Estancia Jose Menendez", "Estancia La Criolla", "Estancia La Fueguina", "Estancia La Indiana", "Estancia La Porteña", "Estancia Las Hijas", "Estancia Las Violetas", "Estancia Laura", "Estancia Libertad", "Estancia Los Cerros", "Estancia Los Flamencos", "Estancia Maria Behety", "Estancia Maria Cristina", "Estancia Maria Luisa", "Estancia Marina", "Estancia Miramonte", "Estancia Pirinaica", "Estancia Policarpo", "Estancia Rio Claro", "Estancia Rio Ewan", "Estancia Rio Irigoyen", "Estancia Rivadavia", "Estancia Rolito", "Estancia Rosita", "Estancia Ruby", "Estancia San Jose", "Estancia San Julio", "Estancia San Justo", "Estancia San Martin", "Estancia San Pablo", "Estancia Santa Ana", "Estancia Sara", "Estancia Tepi", "Estancia Viamonte", "Lago Khami", "Mision Salesiana Mñor Fagnano", "Punta Maria", "Rio Grande", "San Sebastian", "Santa Ines", "Seccion Aviles Estancia San J", "Tapi Aike", "Tolhuin"],
    "9421": ["Frigorifico Cap"],
}

LINEA_DISPLAY = {
    'espuma':   'Línea Espuma',
    'resortes': 'Línea Resortes',
    'box':      'Colchón en Caja',
}

PLAZA_MAP = {
    '80':  '1 Plaza',
    '90':  '1½ Plaza',
    '100': '1½ Plaza',
    '140': '2 Plazas',
    '150': '2 Plazas',
    '160': 'Queen Size',
    '180': 'King Size',
    '200': 'King Size',
}

def get_plaza(medida):
    if not medida:
        return ''
    ancho = medida.split('x')[0]
    return PLAZA_MAP.get(ancho, medida)

def format_price(price):
    """Formatea precio como $424.000"""
    if not price:
        return '$0'
    return '${:,.0f}'.format(float(price)).replace(',', '.')



def get_coeficientes_cuotas():
    """Lee coeficientes de cuotas desde configuracion. Defaults: 1.11 (3c) y 1.22 (6c)."""
    coef_3 = 1.11
    coef_6 = 1.22
    try:
        db  = get_db()
        cur = db.cursor()
        cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('cuotas_3_coef','cuotas_6_coef')")
        for row in cur.fetchall():
            if row['clave'] == 'cuotas_3_coef':
                coef_3 = float(row['valor'])
            elif row['clave'] == 'cuotas_6_coef':
                coef_6 = float(row['valor'])
        cur.close()
        db.close()
    except Exception:
        pass
    return coef_3, coef_6


def get_coef_12():
    """Coeficiente de recargo para 12 cuotas (MercadoPago). Default 1.6."""
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave='cuotas_12_coef'")
        row = cur.fetchone()
        cur.close(); db.close()
        if row and row['valor']:
            return float(row['valor'])
    except Exception:
        pass
    return 1.6


def mp_12_cuotas_activo():
    """True si el medio 'MercadoPago 12 cuotas' está activo (flag en configuracion)."""
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave='mp_12_enabled'")
        row = cur.fetchone()
        cur.close(); db.close()
        return bool(row and row['valor'] == '1')
    except Exception:
        return False


def calc_cuotas(precio, coef_3, coef_6, coef_12=1.6):
    """Devuelve dict con info de cuotas para mostrar en detalle del producto."""
    total_3  = round(precio * coef_3)
    total_6  = round(precio * coef_6)
    total_12 = round(precio * coef_12)
    return {
        '3':  {'cuota': format_price(total_3 / 3),   'total': format_price(total_3)},
        '6':  {'cuota': format_price(total_6 / 6),   'total': format_price(total_6)},
        '12': {'cuota': format_price(total_12 / 12), 'total': format_price(total_12)},
    }


def sku_colchon_a_conjunto(sku):
    """CEX140 → SEX140, CDO80 → SDO80, etc."""
    if sku and sku[0] == 'C':
        return 'S' + sku[1:]
    return sku

def sku_conjunto_a_colchon(sku):
    """SEX140 → CEX140, SEXP100+1 → CEXP100 (limpia sufijo +N)"""
    if sku and sku[0] == 'S':
        base = sku.split('+')[0]  # quitar sufijo +1, +2, etc.
        return 'C' + base[1:]
    return sku

def get_fotos_producto(sku):
    """
    Busca fotos en /static/img/productos/<SKU>/
    Si no encuentra, intenta sin sufijo _DEP/_FULL.
    """
    fotos = []
    try:
        from flask import current_app
        skus_a_probar = [sku]
        # Si el SKU tiene sufijo _DEP o _FULL, probar también sin él
        for sufijo in ('_DEP', '_FULL'):
            if sku.endswith(sufijo):
                skus_a_probar.append(sku[:-len(sufijo)])
                break

        for sku_intento in skus_a_probar:
            carpeta = os.path.join(current_app.root_path, 'static', 'img', 'productos', sku_intento)
            if os.path.isdir(carpeta):
                for i in range(1, 10):
                    for ext in ['jpg', 'jpeg', 'png', 'webp']:
                        nombre = f'{i}.{ext}'
                        if os.path.exists(os.path.join(carpeta, nombre)):
                            fotos.append(url_for('static', filename=f'img/productos/{sku_intento}/{nombre}'))
                if fotos:
                    break
    except Exception:
        pass

    if not fotos:
        fotos.append(url_for('static', filename='img/placeholder-colchon.svg'))
    return fotos

def get_foto_url(sku):
    """Retorna URL de la foto principal (primera disponible)."""
    return get_fotos_producto(sku)[0]

# ── HOME ───────────────────────────────────────────────────────────────────────


def get_demora_sin_stock():
    """Retorna los días de demora configurados para productos sin stock (0 si está desactivado)."""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave = 'demora_sin_stock'")
        row = cur.fetchone()
        cur.close()
        db.close()
        return int(row['valor']) if row and row['valor'] else 0
    except Exception:
        return 0


def get_hot_event():
    """
    Lee el flag del evento promocional desde la tabla configuracion.
    Valores soportados para 'hot_event_activo':
      - '1'    → forzado activo (override manual)
      - '0'    → forzado inactivo (override manual)
      - 'auto' → activo si datetime.now() en hora ARG está entre
                 'hot_event_fecha_inicio' y 'hot_event_fecha_fin'
    Las fechas se interpretan en zona horaria America/Argentina/Buenos_Aires
    sin importar el timezone del servidor.
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        TZ_AR = ZoneInfo('America/Argentina/Buenos_Aires')
    except Exception:
        TZ_AR = None

    activo = False
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            SELECT clave, valor FROM configuracion
            WHERE clave IN ('hot_event_activo', 'hot_event_fecha_inicio', 'hot_event_fecha_fin')
        """)
        rows = cur.fetchall()
        cur.close()
        db.close()
        config = {r['clave']: (str(r.get('valor') or '')).strip() for r in rows}

        flag = config.get('hot_event_activo', '0').lower()

        if flag == '1':
            activo = True
        elif flag == 'auto':
            inicio_str = config.get('hot_event_fecha_inicio', '')
            fin_str    = config.get('hot_event_fecha_fin', '')
            if inicio_str and fin_str:
                try:
                    inicio = datetime.strptime(inicio_str, '%Y-%m-%d %H:%M:%S')
                    fin    = datetime.strptime(fin_str,    '%Y-%m-%d %H:%M:%S')
                    if TZ_AR is not None:
                        inicio = inicio.replace(tzinfo=TZ_AR)
                        fin    = fin.replace(tzinfo=TZ_AR)
                        ahora  = datetime.now(TZ_AR)
                    else:
                        ahora = datetime.now()
                    activo = inicio <= ahora <= fin
                except ValueError:
                    activo = False
    except Exception:
        activo = False

    fecha_fin_iso = ''
    if activo:
        fin_str = config.get('hot_event_fecha_fin', '')
        if fin_str:
            try:
                fin_dt = datetime.strptime(fin_str, '%Y-%m-%d %H:%M:%S')
                if TZ_AR is not None:
                    fin_dt = fin_dt.replace(tzinfo=TZ_AR)
                fecha_fin_iso = fin_dt.isoformat()
            except (ValueError, NameError):
                fecha_fin_iso = ''

    return {
        'activo': activo,
        'titulo': 'HOT MERCADOMUEBLES',
        'fechas': '11 AL 18 DE MAYO',
        'descuento_max': 15,
        'fecha_fin_iso': fecha_fin_iso,
        'descuento_extra_catalogo': 2 if activo else 0,
        'descuento_extra_oferta': 3 if activo else 0,
    }


def _aplicar_extra_hot(desc_cat, desc_oferta=0):
    """
    Calcula el descuento efectivo aplicando el extra del evento HOT:
    - Toma el máximo entre desc_cat (descuento_catalogo) y desc_oferta (ofertas_home).
    - Si gana oferta (do >= dc y do > 0): suma extra_oferta (+3).
    - Si gana catálogo (dc > do y dc > 0): suma extra_catalogo (+2).
    - Si ambos son 0 o NULL: retorna 0 (sin cambio).

    Cachea los extras por request usando flask.g para no consultar la BD
    múltiples veces durante el mismo render de página.

    Retorna float con el descuento final a aplicar al precio.
    """
    from flask import g
    dc = float(desc_cat or 0)
    do = float(desc_oferta or 0)
    desc_base = max(dc, do)
    if desc_base <= 0:
        return desc_base

    if not hasattr(g, '_hot_extras_cached'):
        try:
            he = get_hot_event()
            if he.get('activo'):
                g._hot_extras_cached = (
                    int(he.get('descuento_extra_catalogo', 0)),
                    int(he.get('descuento_extra_oferta', 0)),
                )
            else:
                g._hot_extras_cached = (0, 0)
        except Exception:
            g._hot_extras_cached = (0, 0)
    extra_cat, extra_oferta = g._hot_extras_cached

    # Gana oferta (incluye empate)
    if do > 0 and do >= dc:
        return desc_base + extra_oferta
    # Gana catálogo
    return desc_base + extra_cat


def _get_stock_real(cursor, sku):
    """Stock real para cualquier SKU — maneja sommiers (busca colchon+base)."""
    sku_col = ('C' + sku.split('+')[0][1:]) if (sku.startswith('S') and len(sku) > 1 and sku[1].isalpha()) else None
    if sku_col:
        cursor.execute(
            "SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1",
            (sku_col,)
        )
        cfg = cursor.fetchone()
        if cfg:
            stock_col = get_stock_disponible_sku(cursor, cfg['colchon_sku'])
            cursor.execute("SELECT stock_actual FROM productos_base WHERE sku = %s", (cfg['base_sku_default'],))
            rb = cursor.fetchone()
            stock_base = int(rb['stock_actual'] or 0) if rb else 0
            return min(stock_col, stock_base // int(cfg['cantidad_bases'] or 1))
    return get_stock_disponible_sku(cursor, sku)




# Lineas/tipos que NO aplican demora — siempre muestran sin stock
LINEAS_SIN_DEMORA = {'compac', 'almohadas', 'box'}
MODELOS_SIN_DEMORA = {'compac'}

def aplica_demora(linea, tipo, modelo=None):
    """Retorna True si este producto puede mostrar demora en vez de sin-stock."""
    if not linea and tipo == 'almohada':
        return False
    if (modelo or '').lower() in MODELOS_SIN_DEMORA:
        return False
    return (linea or '').lower() not in LINEAS_SIN_DEMORA


def calcular_fecha_demora(dias):
    """Retorna la fecha de disponibilidad como string DD/MM/YYYY."""
    from datetime import date, timedelta
    fecha = date.today() + timedelta(days=dias)
    return fecha.strftime('%d/%m/%Y')


def get_stock_disponible_sku(cursor, sku):
    """
    Stock disponible = (stock_actual + stock_full) - vendido en ventas pendientes.
    Replica la lógica del sistema de gestión (app.py).
    """
    cursor.execute(
        "SELECT stock_actual, COALESCE(stock_full,0) as stock_full FROM productos_base WHERE sku = %s",
        (sku,)
    )
    prod = cursor.fetchone()
    if not prod:
        return 0
    stock_fisico = int(prod['stock_actual'] or 0) + int(prod['stock_full'] or 0)

    # Vendido en ventas pendientes (no entregadas)
    cursor.execute("""
        SELECT COALESCE(SUM(
            iv.cantidad * COALESCE(c.cantidad_necesaria, 1)
        ), 0) as vendido
        FROM items_venta iv
        JOIN ventas v ON iv.venta_id = v.id
        LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
        LEFT JOIN componentes c ON pc.id = c.producto_compuesto_id
        LEFT JOIN productos_base pb_comp ON c.producto_base_id = pb_comp.id
        WHERE v.estado_entrega = 'pendiente'
          AND COALESCE(pb_comp.sku, iv.sku) = %s
    """, (sku,))
    vendido = int(cursor.fetchone()['vendido'] or 0)

    return max(0, stock_fisico - vendido)

@tienda_bp.route('/')
def home():
    db = get_db()
    cursor = db.cursor()

    # Filtros desde query params — multi-selección con checkboxes
    linea       = request.args.get('linea', '')
    modelos_sel = request.args.getlist('modelo')   # lista
    plazas_sel  = request.args.getlist('plaza')    # lista
    tipos_sel   = request.args.getlist('tipo')     # lista
    orden    = request.args.get('orden', 'precio_asc')
    busqueda = request.args.get('q', '')
    pagina   = int(request.args.get('pagina', 1))
    por_pagina = 12

    # Modelos ocultos
    MODELOS_OCULTOS = ['Compac Plus Pocket']

    # Query base — colchones
    sql = """
        SELECT 
            p.sku, p.nombre, p.linea, p.modelo, p.medida,
            p.precio_base, p.stock_actual, p.descuento_catalogo
        FROM productos_base p
        WHERE p.tipo = 'colchon'
          AND COALESCE(p.activo, 1) = 1
          AND p.medida IS NOT NULL
          AND p.sku NOT LIKE '%%_FULL%%'
          AND (p.modelo IS NULL OR p.modelo NOT IN ({hidden}))
    """.format(hidden=','.join(['%s'] * len(MODELOS_OCULTOS)))
    params = list(MODELOS_OCULTOS)

    if linea:
        sql += " AND p.linea = %s"
        params.append(linea)

    if modelos_sel:
        placeholders = ','.join(['%s'] * len(modelos_sel))
        sql += f" AND p.modelo IN ({placeholders})"
        params.extend(modelos_sel)

    if plazas_sel:
        medida_anchos = {
            '1-plaza':          ['80'],
            '1-plaza-y-media':  ['90', '100'],
            '2-plazas':         ['140', '150'],
            'queen':            ['160'],
            'king':             ['180', '200'],
        }
        anchos = []
        for p_val in plazas_sel:
            anchos.extend(medida_anchos.get(p_val, []))
        if anchos:
            placeholders = ','.join(['%s'] * len(anchos))
            sql += f" AND SUBSTRING_INDEX(p.medida,'x',1) IN ({placeholders})"
            params.extend(anchos)

    if busqueda:
        sql += " AND (p.nombre LIKE %s OR p.modelo LIKE %s OR p.medida LIKE %s)"
        b = f'%{busqueda}%'
        params.extend([b, b, b])

    # Orden
    orden_map = {
        'precio_asc':  'p.precio_base ASC',
        'precio_desc': 'p.precio_base DESC',
        'nombre_asc':  'p.nombre ASC',
    }
    sql += f" ORDER BY {orden_map.get(orden, 'p.precio_base ASC')}"

    # Escapar % literales para pymysql (los que no son placeholders)
    # pymysql usa % como placeholder, hay que asegurarse que params esté bien

    cursor.execute(sql, tuple(params))
    colchones_raw = cursor.fetchall()

    # Traer bases para calcular precio conjunto
    cursor.execute("SELECT sku, precio_base, stock_actual FROM productos_base WHERE tipo = 'base'")
    bases_raw = {r['sku']: r for r in cursor.fetchall()}
    # Stock disponible de bases (descontando ventas pendientes)
    bases = {}
    for bsku, brow in bases_raw.items():
        bases[bsku] = dict(brow)
        bases[bsku]['stock_disponible'] = get_stock_disponible_sku(cursor, bsku)

    cursor.execute("SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE activo = 1")
    conjuntos_cfg = {r['colchon_sku']: r for r in cursor.fetchall()}

    # Mapa exacto colchon_sku -> sku_comp (match exacto, no LIKE%)
    # Evita ambiguedad SEXP100 vs SEXP100+1
    cursor.execute("""
        SELECT cc.colchon_sku, pc.sku AS sku_comp, pc.nombre AS nombre_comp
        FROM conjunto_configuracion cc
        JOIN productos_compuestos pc
          ON pc.sku = CONCAT('S', SUBSTRING(cc.colchon_sku, 2))
        WHERE cc.activo = 1 AND pc.activo = 1
    """)
    _comp_rows = cursor.fetchall()
    colchon_a_compuesto = {r['colchon_sku']: r['sku_comp'] for r in _comp_rows}
    colchon_a_nombre_comp = {r['colchon_sku']: r['nombre_comp'] for r in _comp_rows}

    # Cargar ofertas_home para aplicar max(desc_cat, desc_oferta) en todo el catálogo
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ofertas_home (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sku VARCHAR(50) NOT NULL,
                descuento_pct DECIMAL(5,2) DEFAULT 8.00,
                orden INT DEFAULT 0,
                activo TINYINT DEFAULT 1
            )
        """)
        cursor.execute("SELECT sku, descuento_pct FROM ofertas_home WHERE activo=1 ORDER BY orden, id")
        filas_oferta = cursor.fetchall()
        skus_oferta_cfg = [(r['sku'], float(r['descuento_pct'])) for r in filas_oferta] if filas_oferta else [(s, 8.0) for s in SKUS_OFERTA]
    except Exception:
        skus_oferta_cfg = [(s, 8.0) for s in SKUS_OFERTA]
    ofertas_map = {sku: pct for sku, pct in skus_oferta_cfg}

    # Construir lista de productos (colchón + conjunto si aplica)
    productos = []
    for col in colchones_raw:
        sku    = col['sku']
        medida = col['medida'] or ''
        precio_colchon = float(col['precio_base'] or 0)
        stock_colchon  = get_stock_disponible_sku(cursor, sku)

        desc_cat = float(col.get('descuento_catalogo') or 0)
        desc_efectivo = _aplicar_extra_hot(desc_cat, ofertas_map.get(sku, 0.0))

        # Solo colchón
        if (not tipos_sel or 'colchon' in tipos_sel) and precio_colchon > 0:
            nombre_col = f"Colchón Cannon {col['modelo']} {medida}cm"
            precio_venta = precio_colchon * (1 - desc_efectivo/100) if desc_efectivo else precio_colchon
            productos.append({
                'sku':       sku,
                'sku_url':   sku,
                'slug':      slugify(nombre_col),
                'nombre':    nombre_col,
                'modelo':    col['modelo'],
                'linea':     col['linea'],
                'medida':    medida,
                'plaza':     get_plaza(medida),
                'precio':    precio_venta,
                'precio_base_real': precio_colchon,
                'precio_fmt': format_price(precio_venta),
                'precio_original_fmt': format_price(precio_colchon) if desc_efectivo else None,
                'descuento_catalogo': desc_efectivo,
                'stock':     stock_colchon,
                'tipo':      'colchon',
                'tipo_label': 'Solo Colchón',
                'foto':      get_foto_url(sku),
                'fotos':     get_fotos_producto(sku),
            })

        # Conjunto — SKU real desde mapa exacto (CEX100->SEXP100, no SEXP100+1)
        sku_conj = colchon_a_compuesto.get(sku, sku_colchon_a_conjunto(sku))
        desc_efectivo_conj = _aplicar_extra_hot(desc_cat, ofertas_map.get(sku_conj, 0.0))
        if (not tipos_sel or 'conjunto' in tipos_sel) and sku in colchon_a_compuesto:
            cfg        = conjuntos_cfg[sku]
            base_sku   = cfg['base_sku_default']
            cant_bases = int(cfg['cantidad_bases'] or 1)
            precio_base_unit = float(bases.get(base_sku, {}).get('precio_base', 0) or 0)
            precio_conjunto  = precio_colchon + precio_base_unit * cant_bases
            stock_base       = int(bases.get(base_sku, {}).get('stock_disponible', 0) or 0)
            stock_conjunto   = min(stock_colchon, stock_base // cant_bases)
            precio_conj_venta = precio_conjunto * (1 - desc_efectivo_conj/100) if desc_efectivo_conj else precio_conjunto

            nombre_conj_real = colchon_a_nombre_comp.get(sku, f"Sommier y Colchón Cannon {col['modelo']} {medida}cm")
            nombre_conj = nombre_conj_real or f"Sommier y Colchón Cannon {col['modelo']} {medida}cm"
            productos.append({
                'sku':       sku_conj,
                'sku_url':   sku_conj,
                'slug':      slugify(nombre_conj),
                'nombre':    nombre_conj,
                'modelo':    col['modelo'],
                'linea':     col['linea'],
                'medida':    medida,
                'plaza':     get_plaza(medida),
                'precio':    precio_conj_venta,
                'precio_base_real': precio_conjunto,
                'precio_fmt': format_price(precio_conj_venta),
                'precio_original_fmt': format_price(precio_conjunto) if desc_efectivo_conj else None,
                'descuento_catalogo': desc_efectivo_conj,
                'stock':     stock_conjunto,
                'tipo':      'conjunto',
                'tipo_label': 'Con Sommier',
                'foto':      get_foto_url(sku_conj),
                'fotos':     get_fotos_producto(sku_conj),
            })

    # Almohadas — filtradas por busqueda si hay texto
    if not linea and not plazas_sel and not modelos_sel and (not tipos_sel or 'almohada' in tipos_sel):
        alm_sql = "SELECT sku, nombre, precio_base, stock_actual, descuento_catalogo FROM productos_base WHERE activo = 1 AND tipo = 'almohada' AND precio_base > 0"
        alm_params = []
        if busqueda:
            alm_sql += " AND (nombre LIKE %s OR sku LIKE %s)"
            alm_params += [f'%{busqueda}%', f'%{busqueda}%']
        alm_sql += " ORDER BY nombre"
        cursor.execute(alm_sql, alm_params)
        for alm in cursor.fetchall():
            desc_alm = _aplicar_extra_hot(float(alm.get('descuento_catalogo') or 0), 0)
            precio_bruto = float(alm['precio_base'] or 0)
            precio_final = precio_bruto * (1 - desc_alm / 100) if desc_alm else precio_bruto
            productos.append({
                'sku':               alm['sku'],
                'sku_url':           alm['sku'],
                'nombre':            alm['nombre'],
                'modelo':            alm['nombre'],
                'linea':             'almohadas',
                'medida':            '70x40',
                'plaza':             '',
                'precio':            precio_final,
                'precio_fmt':        format_price(precio_final),
                'precio_base_real':  precio_bruto,
                'precio_original_fmt': format_price(precio_bruto) if desc_alm else None,
                'descuento_catalogo': desc_alm,
                'stock':             get_stock_disponible_sku(cursor, alm['sku']),
                'tipo':              'almohada',
                'tipo_label':        'Almohada',
                'foto':              get_foto_url(alm['sku']),
                'fotos':             get_fotos_producto(alm['sku']),
            })

    # Busqueda directa en compuestos — para "sommier X" donde "sommier" no aparece
    # en ningún campo de productos_base, usa conexion propia para evitar conflicto de cursor
    if busqueda and (not tipos_sel or 'conjunto' in tipos_sel):
        skus_ya = {p['sku'] for p in productos}
        termino_limpio = busqueda.lower()
        for palabra in ('sommier y colchon', 'sommier y colchon', 'sommier'):
            termino_limpio = termino_limpio.replace(palabra, '').strip()
        buscar_terminos = []
        for t in [busqueda, termino_limpio]:
            if t and t not in buscar_terminos:
                buscar_terminos.append(t)
        try:
            db2  = get_db()
            cur2 = db2.cursor()
            rows_comp = []
            for termino in buscar_terminos:
                cur2.execute(
                    "SELECT sku, nombre FROM productos_compuestos WHERE activo = 1 AND (nombre LIKE %s OR sku LIKE %s)",
                    (f'%{termino}%', f'%{termino}%')
                )
                for r in cur2.fetchall():
                    if r['sku'] not in skus_ya:
                        rows_comp.append(r)
                        skus_ya.add(r['sku'])
            for comp in rows_comp:
                sku_c     = comp['sku']
                sku_col_c = ('C' + sku_c[1:].split('+')[0]) if sku_c.startswith('S') else None
                if not sku_col_c or sku_col_c not in conjuntos_cfg:
                    continue
                cfg_c  = conjuntos_cfg[sku_col_c]
                bsku_c = cfg_c['base_sku_default']
                cant_c = int(cfg_c['cantidad_bases'] or 1)
                cur2.execute(
                    "SELECT precio_base, stock_actual, modelo, medida, linea, descuento_catalogo FROM productos_base WHERE sku=%s",
                    (sku_col_c,)
                )
                pb_col = cur2.fetchone()
                cur2.execute("SELECT precio_base, stock_actual FROM productos_base WHERE sku=%s", (bsku_c,))
                pb_bas = cur2.fetchone()
                if not pb_col:
                    continue
                p_col  = float(pb_col['precio_base'] or 0)
                p_bas  = float(pb_bas['precio_base'] or 0) if pb_bas else 0
                p_conj = p_col + p_bas * cant_c
                s_col  = get_stock_disponible_sku(cursor, sku_col_c)
                s_bas  = get_stock_disponible_sku(cursor, bsku_c) if pb_bas else 0
                stock  = min(s_col, s_bas)
                desc   = _aplicar_extra_hot(float(pb_col.get('descuento_catalogo') or 0), ofertas_map.get(sku_c, 0.0))
                p_ven  = p_conj * (1 - desc/100) if desc else p_conj
                med    = pb_col.get('medida') or ''
                nom    = comp['nombre'] or f"Sommier y Colchón Cannon {pb_col.get('modelo','')} {med}cm"
                productos.append({
                    'sku':                sku_c,
                    'sku_url':            sku_c,
                    'slug':               slugify(nom),
                    'nombre':             nom,
                    'modelo':             pb_col.get('modelo', ''),
                    'linea':              pb_col.get('linea', ''),
                    'medida':             med,
                    'plaza':              get_plaza(med),
                    'precio':             p_ven,
                    'precio_base_real':   p_conj,
                    'precio_fmt':         format_price(p_ven),
                    'precio_original_fmt': format_price(p_conj) if desc else None,
                    'descuento_catalogo': desc,
                    'stock':              stock,
                    'tipo':               'conjunto',
                    'tipo_label':         'Con Sommier',
                    'foto':               get_foto_url(sku_c),
                    'fotos':              get_fotos_producto(sku_c),
                    'demora_aplica':      aplica_demora(pb_col.get('linea'), 'conjunto', pb_col.get('modelo')),
                })
            cur2.close()
            db2.close()
        except Exception as e:
            print(f"[busqueda_compuestos] Error: {e}")

    # Bases — visibles en tienda solo si activo=1 (apagadas por default)
    if not linea and not plazas_sel and not modelos_sel and (not tipos_sel or 'base' in tipos_sel):
        base_sql = "SELECT sku, nombre, precio_base, stock_actual, medida FROM productos_base WHERE activo = 1 AND tipo = 'base' AND precio_base > 0"
        base_params = []
        if busqueda:
            base_sql += " AND (nombre LIKE %s OR sku LIKE %s)"
            base_params += [f'%{busqueda}%', f'%{busqueda}%']
        base_sql += " ORDER BY nombre"
        cursor.execute(base_sql, base_params)
        for base in cursor.fetchall():
            productos.append({
                'sku':                base['sku'],
                'sku_url':            base['sku'],
                'slug':               slugify(base['nombre']),
                'nombre':             base['nombre'],
                'modelo':             base['nombre'],
                'linea':              'bases',
                'medida':             base['medida'] or '',
                'plaza':              get_plaza(base['medida'] or ''),
                'precio':             float(base['precio_base'] or 0),
                'precio_base_real':   float(base['precio_base'] or 0),
                'precio_fmt':         format_price(base['precio_base']),
                'precio_original_fmt': None,
                'descuento_catalogo': 0,
                'stock':              get_stock_disponible_sku(cursor, base['sku']),
                'tipo':               'base',
                'tipo_label':         'Base',
                'foto':               get_foto_url(base['sku']),
                'fotos':              get_fotos_producto(base['sku']),
                'demora_aplica':      False,
            })

    # ── Ofertas desde DB ─────────────────────────────────────────────────────────
    # Agregar campo demora_aplica a cada producto
    for p in productos:
        p['demora_aplica'] = aplica_demora(p.get('linea'), p.get('tipo'), p.get('modelo'))

    hay_filtros = bool(linea or modelos_sel or plazas_sel or tipos_sel or busqueda)

    productos_map = {p['sku']: p for p in productos}

    # skus_oferta_cfg y ofertas_map ya cargados antes del loop de productos

    productos_oferta = []
    for sku_o, desc_pct_oferta in skus_oferta_cfg:
        if sku_o in productos_map and productos_map[sku_o]['stock'] > 0:
            p = dict(productos_map[sku_o])
            # desc_catalogo ya contiene max(desc_cat, oferta) desde el loop
            desc_pct = float(p.get('descuento_catalogo') or desc_pct_oferta)
            factor = 1 - desc_pct / 100
            precio_base_real = p.get('precio_base_real', p['precio'])
            p['precio_original']     = precio_base_real
            p['precio_original_fmt'] = format_price(precio_base_real)
            p['precio_oferta']       = precio_base_real * factor
            p['precio_oferta_fmt']   = format_price(precio_base_real * factor)
            p['descuento_pct']       = int(desc_pct)
            productos_oferta.append(p)

    mas_vendidos = []
    try:
        fecha_semana = datetime.now() - timedelta(days=7)
        cursor.execute("""
            SELECT iv.sku, SUM(iv.cantidad) as total_vendido
            FROM items_venta iv
            JOIN ventas v ON iv.venta_id = v.id
            WHERE v.fecha_venta >= %s
            GROUP BY iv.sku
            ORDER BY total_vendido DESC
            LIMIT 30
        """, (fecha_semana,))
        skus_mv = [r['sku'] for r in cursor.fetchall()]
        skus_oferta_set = set(s for s, _ in skus_oferta_cfg)
        for s in skus_mv:
            if s in productos_map and s not in skus_oferta_set:
                p = productos_map[s]
                if p['tipo'] in ('colchon', 'conjunto') and p['stock'] > 0:
                    mas_vendidos.append(p)
                    if len(mas_vendidos) >= 9:
                        break
        # Completar con otros si faltan
        if len(mas_vendidos) < 9:
            ya = {p['sku'] for p in mas_vendidos} | skus_oferta_set
            for p in productos:
                if p['sku'] not in ya and p['tipo'] in ('colchon', 'conjunto') and p['stock'] > 0:
                    mas_vendidos.append(p)
                    if len(mas_vendidos) >= 9:
                        break
    except Exception as e_mv:
        logger.warning(f"Error más vendidos: {e_mv}")

    # Paginación
    total     = len(productos)
    inicio    = (pagina - 1) * por_pagina
    productos = productos[inicio: inicio + por_pagina]
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    # Opciones para filtros
    cursor.execute("SELECT DISTINCT linea FROM productos_base WHERE activo = 1 AND tipo='colchon' AND linea IS NOT NULL ORDER BY linea")
    lineas_disponibles = [r['linea'] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT modelo FROM productos_base WHERE activo = 1 AND tipo='colchon' AND modelo IS NOT NULL AND modelo NOT IN ('Compac Plus Pocket') ORDER BY modelo")
    modelos_disponibles = [r['modelo'] for r in cursor.fetchall()]

    cursor.close()
    db.close()

    # Query string con todos los filtros activos (para paginación y sort)
    from urllib.parse import urlencode

    def make_qs(excl_key=None, excl_val=None):
        """Arma filter_qs excluyendo opcionalmente un par key=val."""
        parts = []
        if linea and not (excl_key == 'linea'):
            parts.append(('linea', linea))
        for t in tipos_sel:
            if not (excl_key == 'tipo' and excl_val == t):
                parts.append(('tipo', t))
        for pl in plazas_sel:
            if not (excl_key == 'plaza' and excl_val == pl):
                parts.append(('plaza', pl))
        for m in modelos_sel:
            if not (excl_key == 'modelo' and excl_val == m):
                parts.append(('modelo', m))
        if busqueda and not (excl_key == 'q'):
            parts.append(('q', busqueda))
        return urlencode(parts)

    filter_qs = make_qs()  # sin exclusión — para paginación

    # Tags activos con su URL de "quitar este filtro"
    TIPO_LABELS  = {'colchon': 'Solo Colchón', 'conjunto': 'Con Sommier', 'almohada': 'Almohadas', 'base': 'Bases'}
    PLAZA_LABELS = {'1-plaza':'1 Plaza','1-plaza-y-media':'1½ Plaza','2-plazas':'2 Plazas','queen':'Queen Size','king':'King Size'}
    active_tags = []
    for t in tipos_sel:
        qs = make_qs('tipo', t)
        active_tags.append({'label': TIPO_LABELS.get(t, t), 'url': '/tienda/?' + qs})
    if linea:
        qs = make_qs('linea')
        active_tags.append({'label': LINEA_DISPLAY.get(linea, linea), 'url': '/tienda/?' + qs})
    for pl in plazas_sel:
        qs = make_qs('plaza', pl)
        active_tags.append({'label': PLAZA_LABELS.get(pl, pl), 'url': '/tienda/?' + qs})
    for m in modelos_sel:
        qs = make_qs('modelo', m)
        active_tags.append({'label': m, 'url': '/tienda/?' + qs})
    if busqueda:
        qs = make_qs('q')
        active_tags.append({'label': '🔍 "' + busqueda + '"', 'url': '/tienda/?' + qs})

    return render_template('tienda/home.html',
        productos           = productos,
        productos_oferta    = productos_oferta,
        mas_vendidos        = mas_vendidos,
        hay_filtros         = hay_filtros,
        total             = total,
        pagina            = pagina,
        total_paginas     = total_paginas,
        por_pagina        = por_pagina,
        linea             = linea,
        modelos_sel       = modelos_sel,
        plazas_sel        = plazas_sel,
        tipos_sel         = tipos_sel,
        orden             = orden,
        busqueda          = busqueda,
        filter_qs         = filter_qs,
        active_tags       = active_tags,
        lineas_disponibles = lineas_disponibles,
        modelos_disponibles = modelos_disponibles,
        linea_display     = LINEA_DISPLAY,
        carrito_count     = sum(i['cantidad'] for i in session.get('carrito', [])),
        carrito_dict      = {i['sku']: i['cantidad'] for i in session.get('carrito', [])},
        demora_dias       = get_demora_sin_stock(),
    )

# ── DETALLE PRODUCTO ───────────────────────────────────────────────────────────

@tienda_bp.route('/producto/<sku_url>')
def detalle(sku_url):
    # ── Determinar si es slug o SKU ──────────────────────────────────────────
    # SKU: mayúsculas/números/+ (ej: CTR80, SEXP140, CEX100)
    # Slug: minúsculas con guiones (ej: colchon-cannon-tropical-80x190cm)
    es_slug = bool(re.search(r'[a-z]', sku_url))

    if es_slug:
        # Buscar el SKU que corresponde al slug
        db_s = get_db()
        cur_s = db_s.cursor()
        cur_s.execute("""
            SELECT sku, nombre, modelo, medida FROM productos_base
            WHERE activo = 1 AND tipo = 'colchon'
        """)
        filas = cur_s.fetchall()
        cur_s.close()
        db_s.close()

        sku_encontrado = None
        # Buscar por modelo+medida (mismo formato que genera la home)
        for fila in filas:
            modelo = (fila.get('modelo') or fila.get('nombre') or '')
            medida = (fila.get('medida') or '')
            slug_c = slugify(f"Colchón Cannon {modelo} {medida}cm") if medida else ''
            slug_s = slugify(f"Sommier y Colchón Cannon {modelo} {medida}cm") if medida else ''
            if slug_c and slug_c == sku_url:
                sku_encontrado = fila['sku']
                break
            if slug_s and slug_s == sku_url:
                sku_encontrado = 'S' + fila['sku'][1:] if fila['sku'].startswith('C') else fila['sku']
                break

        # Buscar por nombre real de productos_compuestos (ej: "Sommier Exclusive 140x190")
        if not sku_encontrado:
            db_s3 = get_db()
            cur_s3 = db_s3.cursor()
            cur_s3.execute("SELECT sku, nombre FROM productos_compuestos WHERE activo = 1")
            for fila in cur_s3.fetchall():
                if slugify(fila['nombre']) == sku_url:
                    sku_encontrado = fila['sku']
                    break
            cur_s3.close()
            db_s3.close()

        # Si no se encontró como colchón/sommier, buscar como almohada o base
        if not sku_encontrado:
            db_s2 = get_db()
            cur_s2 = db_s2.cursor()
            cur_s2.execute("SELECT sku, nombre FROM productos_base WHERE activo = 1 AND tipo IN ('almohada','base')")
            for fila in cur_s2.fetchall():
                if slugify(fila['nombre']) == sku_url:
                    sku_encontrado = fila['sku']
                    break
            cur_s2.close()
            db_s2.close()

        if not sku_encontrado:
            return redirect(url_for('tienda.home'))
        sku_url = sku_encontrado
    else:
        # Es un SKU directo → redirigir a la URL slug (SEO canonical)
        db_r = get_db()
        cur_r = db_r.cursor()

        # Primero verificar si es almohada o base (tienen SKU directo sin slug)
        cur_r.execute("SELECT sku, nombre, tipo FROM productos_base WHERE activo = 1 AND sku = %s", (sku_url,))
        prod_directo = cur_r.fetchone()
        if prod_directo and prod_directo['tipo'] in ('almohada', 'base'):
            cur_r.close()
            db_r.close()
            # Redirigir al slug del nombre
            return redirect(url_for('tienda.detalle', sku_url=slugify(prod_directo['nombre'])), 301)

        es_conj_r = sku_url and sku_url[0] == 'S'
        sku_col_r = sku_conjunto_a_colchon(sku_url) if es_conj_r else sku_url
        cur_r.execute("SELECT modelo, medida FROM productos_base WHERE activo = 1 AND sku=%s", (sku_col_r,))
        row_r = cur_r.fetchone()
        cur_r.close()
        db_r.close()
        if row_r:
            nombre_r = f"{'Sommier y ' if es_conj_r else ''}Colchón Cannon {row_r['modelo']} {row_r['medida']}cm"
            return redirect(url_for('tienda.detalle', sku_url=slugify(nombre_r)), 301)

    # Conjunto si empieza con S (SEX140, SSUP140), colchon si empieza con C
    es_conjunto = bool(sku_url and sku_url[0] == 'S')
    sku_colchon = sku_conjunto_a_colchon(sku_url) if es_conjunto else sku_url

    db = get_db()
    cursor = db.cursor()

    # Manejar almohadas y bases — tienen página de detalle simple
    cursor.execute("SELECT sku, nombre, tipo, precio_base, stock_actual, descuento_catalogo FROM productos_base WHERE activo = 1 AND tipo IN ('almohada','base') AND sku = %s", (sku_colchon,))
    prod_simple = cursor.fetchone()
    if prod_simple:
        stock_simple = get_stock_disponible_sku(cursor, prod_simple['sku'])
        desc_s = _aplicar_extra_hot(float(prod_simple.get('descuento_catalogo') or 0), 0)
        precio_s = float(prod_simple['precio_base'] or 0)
        precio_venta_s = precio_s * (1 - desc_s/100) if desc_s else precio_s
        cursor.close()
        db.close()
        return render_template('tienda/detalle.html',
            producto = {
                'sku': prod_simple['sku'],
                'sku_url': prod_simple['sku'],
                'sku_colchon': prod_simple['sku'],
                'nombre': prod_simple['nombre'],
                'modelo': prod_simple['nombre'],
                'linea': 'almohadas' if prod_simple['tipo'] == 'almohada' else 'bases',
                'medida': '70x40' if prod_simple['tipo'] == 'almohada' else '',
                'plaza': '',
                'tipo': prod_simple['tipo'],
                'tipo_label': 'Almohada' if prod_simple['tipo'] == 'almohada' else 'Base',
                'precio': precio_venta_s,
                'precio_base_real': precio_s,
                'precio_fmt': format_price(precio_venta_s),
                'precio_original_fmt': format_price(precio_s) if desc_s else None,
                'descuento_catalogo': desc_s,
                'stock': stock_simple,
                'fotos': get_fotos_producto(prod_simple['sku']),
                'slug': slugify(prod_simple['nombre']),
                'tiene_conjunto': False,
                'demora_aplica': False,
                'fecha_demora': None,
            },
            relacionados = [],
            demora_dias = 0,
            desc_bajada = '',
            desc_bullets = [],
            specs = {},
            patas_sommier = None,
            altura_total_sommier = None,
            carrito_count = len(session.get('carrito', [])),
            now = __import__('datetime').datetime.now(),
            ga4_view_item = {
                'item_id': prod_simple['sku'],
                'item_name': prod_simple['nombre'],
                'item_category': prod_simple['tipo'],
                'price': precio_venta_s,
            },
            cuotas = calc_cuotas(precio_venta_s, *get_coeficientes_cuotas(), get_coef_12()),
            mp_12_enabled = mp_12_cuotas_activo(),
        )

    cursor.execute("""
        SELECT sku, nombre, linea, modelo, medida, precio_base, stock_actual, descuento_catalogo
        FROM productos_base WHERE activo = 1 AND sku = %s
    """, (sku_colchon,))
    col = cursor.fetchone()

    if not col:
        cursor.close()
        db.close()
        return redirect(url_for('tienda.home'))

    precio_colchon = float(col['precio_base'] or 0)
    desc_cat       = float(col.get('descuento_catalogo') or 0)
    stock_colchon  = get_stock_disponible_sku(cursor, sku_colchon)

    # Descuento efectivo = max(desc_catalogo, oferta_home para este SKU)
    try:
        cursor.execute("SELECT descuento_pct FROM ofertas_home WHERE sku = %s AND activo = 1 LIMIT 1", (sku_url,))
        row_of = cursor.fetchone()
        desc_oferta = float(row_of['descuento_pct']) if row_of else 0.0
    except Exception:
        desc_oferta = 0.0
    desc_efectivo = _aplicar_extra_hot(desc_cat, desc_oferta)

    producto = {
        'sku':        sku_url,
        'sku_colchon': sku_colchon,
        'nombre':     f"{'Sommier y ' if es_conjunto else ''}Colchón Cannon {col['modelo']} {col['medida']}cm",
        'modelo':     col['modelo'],
        'linea':      col['linea'],
        'medida':     col['medida'],
        'plaza':      get_plaza(col['medida']),
        'tipo':       'conjunto' if es_conjunto else 'colchon',
        'tipo_label': 'Con Sommier' if es_conjunto else 'Solo Colchón',
        'precio':     precio_colchon * (1 - desc_efectivo/100) if desc_efectivo else precio_colchon,
        'precio_base_real': precio_colchon,
        'descuento_catalogo': desc_efectivo,
        'stock':      stock_colchon,
    }

    if es_conjunto:
        cursor.execute("""
            SELECT base_sku_default, cantidad_bases 
            FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1
        """, (sku_colchon,))
        cfg = cursor.fetchone()
        if cfg:
            cursor.execute("SELECT precio_base, stock_actual FROM productos_base WHERE activo = 1 AND sku = %s", (cfg['base_sku_default'],))
            base = cursor.fetchone()
            if base:
                cant = int(cfg['cantidad_bases'] or 1)
                precio_base_sum = float(base['precio_base'] or 0) * cant
                precio_conjunto_raw = precio_colchon + precio_base_sum
                producto['precio_base_real'] = precio_conjunto_raw
                producto['precio'] = precio_conjunto_raw * (1 - desc_efectivo/100) if desc_efectivo else precio_conjunto_raw
                producto['stock'] = min(stock_colchon, get_stock_disponible_sku(cursor, cfg['base_sku_default']))

    producto['precio_fmt'] = format_price(producto['precio'])
    precio_base_real = producto.get('precio_base_real', precio_colchon)
    producto['precio_original_fmt'] = format_price(precio_base_real) if desc_efectivo else None
    producto['fotos'] = get_fotos_producto(sku_url)
    producto['slug']  = slugify(producto['nombre'])
    producto['demora_aplica'] = aplica_demora(col.get('linea'), producto['tipo'], col.get('modelo'))

    # Fecha disponible si aplica demora
    _demora_dias = get_demora_sin_stock()
    if producto['stock'] == 0 and _demora_dias and producto['demora_aplica']:
        from datetime import date, timedelta
        producto['fecha_demora'] = (date.today() + timedelta(days=_demora_dias)).strftime('%d/%m/%Y')
    else:
        producto['fecha_demora'] = None

    # SEO
    linea_txt  = (col.get('linea') or '').title()
    modelo_txt = col.get('modelo') or ''
    medida_txt = col.get('medida') or ''
    plaza_txt  = get_plaza(medida_txt)
    producto['seo_desc'] = (
        f"Comprá el {producto['nombre']} en Mercadomuebles. "
        f"Distribuidores oficiales Cannon en Buenos Aires. "
        f"{plaza_txt} · {linea_txt}. Hasta 12 cuotas. Envío a todo el país."
    )

    # Verificar si existe conjunto para este colchón
    cursor.execute("SELECT COUNT(*) as cnt FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_colchon,))
    producto['tiene_conjunto'] = cursor.fetchone()['cnt'] > 0

    # Productos relacionados (mismo modelo, otra medida)
    cursor.execute("""
        SELECT sku, medida, precio_base, stock_actual FROM productos_base
        WHERE activo = 1 AND tipo = 'colchon' AND modelo = %s AND precio_base > 0
        ORDER BY medida LIMIT 7
    """, (col['modelo'],))
    relacionados = []
    for r in cursor.fetchall():
        precio_rel = float(r['precio_base'] or 0)
        if es_conjunto:
            # Calcular precio conjunto para esta medida
            cursor2 = db.cursor()
            cursor2.execute("""
                SELECT cc.base_sku_default, cc.cantidad_bases, pb.precio_base as precio_base_u
                FROM conjunto_configuracion cc
                JOIN productos_base pb ON pb.sku = cc.base_sku_default
                WHERE cc.colchon_sku = %s AND cc.activo = 1
            """, (r['sku'],))
            cfg_rel = cursor2.fetchone()
            cursor2.close()
            if cfg_rel:
                precio_rel += float(cfg_rel['precio_base_u'] or 0) * int(cfg_rel['cantidad_bases'] or 1)
        sku_rel = sku_colchon_a_conjunto(r['sku']) if es_conjunto else r['sku']
        # Si es conjunto, verificar que el compuesto esté activo
        if es_conjunto:
            cursor2b = db.cursor()
            cursor2b.execute("SELECT activo FROM productos_compuestos WHERE sku = %s", (sku_rel,))
            comp_row = cursor2b.fetchone()
            cursor2b.close()
            if comp_row and not comp_row['activo']:
                continue  # saltar medidas con sommier desactivado
        stock_rel = get_stock_disponible_sku(cursor, r['sku'])
        # Para conjuntos, el stock es el mínimo entre colchón y base / cantidad_bases
        if es_conjunto and cfg_rel:
            stock_base_rel = get_stock_disponible_sku(cursor, cfg_rel['base_sku_default'])
            cant_b = int(cfg_rel['cantidad_bases'] or 1)
            stock_rel = min(stock_rel, stock_base_rel // cant_b)
        linea_rel = r.get('linea', '') or ''
        modelo_rel = r.get('modelo', '') or ''
        relacionados.append({
            'sku':          sku_rel,
            'medida':       r['medida'],
            'precio_fmt':   format_price(precio_rel),
            'activo':       r['sku'] == sku_colchon,
            'sin_stock':    stock_rel == 0,
            'demora_aplica': aplica_demora(linea_rel, 'conjunto' if es_conjunto else r.get('tipo',''), modelo_rel),
        })

    cursor.close()
    db.close()

    modelo_key = (producto.get('modelo') or '').lower()
    desc_data  = DESCRIPCIONES_MODELO.get(modelo_key, {})
    specs_data = SPECS_MODELO.get(modelo_key, {})
    patas      = get_patas_sommier(producto.get('medida')) if producto.get('tipo') == 'conjunto' else None

    # Altura total sommier = colchón + base + patas
    altura_total_sommier = None
    if producto.get('tipo') == 'conjunto' and specs_data.get('altura_col'):
        altura_total_sommier = specs_data['altura_col'] + BASE_ALTURA_CM + PATAS_ALTURA_CM

    return render_template('tienda/detalle.html',
        producto             = producto,
        relacionados         = relacionados,
        demora_dias          = get_demora_sin_stock(),
        desc_bajada          = desc_data.get('bajada', ''),
        desc_bullets         = desc_data.get('bullets', []),
        specs                = specs_data,
        patas_sommier        = patas,
        altura_total_sommier = altura_total_sommier,
        carrito_count        = len(session.get('carrito', [])),
        now                  = __import__('datetime').datetime.now(),
        ga4_view_item        = {
            'item_id':       producto.get('sku', ''),
            'item_name':     producto.get('nombre', ''),
            'item_category': producto.get('linea', ''),
            'price':         float(producto.get('precio', 0)),
        },
        cuotas = calc_cuotas(float(producto.get('precio', 0)), *get_coeficientes_cuotas(), get_coef_12()),
        mp_12_enabled = mp_12_cuotas_activo(),
    )

# ── CARRITO ────────────────────────────────────────────────────────────────────

SKUS_ALMOHADA = {'CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE'}


def _shipping_unificado():
    """Lee el flag global 'shipping_unificado_zipnova' de configuracion.
    Cuando vale '1' todo el carrito (incluidas almohadas y Compac) cotiza Zipnova.
    Default False — si el flag no existe o falla la lectura, comportamiento ME2 actual."""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT valor FROM configuracion WHERE clave = 'shipping_unificado_zipnova'")
        row = cur.fetchone()
        cur.close()
        db.close()
        return bool(row and row['valor'] == '1')
    except Exception:
        return False


def _tipo_envio_sku(sku):
    """
    Devuelve 'almohada', 'me2' o 'zipnova' según el SKU.
    Debe coincidir con la lógica de get_shipping_info.
    Con flag shipping_unificado_zipnova='1', todo devuelve 'zipnova'.
    """
    if _shipping_unificado():
        return 'zipnova'
    if sku in SKUS_ALMOHADA:
        return 'almohada'
    sku_base = sku.split('_')[0]
    if sku == 'PRUEBA' or sku_base.startswith('CCO') or sku_base.startswith('CCP'):
        return 'me2'
    return 'zipnova'


@tienda_bp.route('/carrito/agregar', methods=['POST'])
def agregar_carrito():
    data = request.get_json() or {}
    sku      = data.get('sku')
    nombre   = data.get('nombre')
    precio   = float(data.get('precio', 0))
    cantidad = int(data.get('cantidad', 1))

    if not sku or not precio:
        return jsonify({'error': 'Datos inválidos'}), 400

    carrito = session.get('carrito', [])
    tipo_nuevo = _tipo_envio_sku(sku)
    flag_unificado = _shipping_unificado()

    # ── Validaciones ──────────────────────────────────────────────────────────
    if flag_unificado:
        # Todo cotiza Zipnova: no hay conflictos por tipo. Único límite: 20 unidades del mismo SKU.
        cant_actual_sku = sum(i['cantidad'] for i in carrito if i['sku'] == sku)
        if cant_actual_sku + cantidad > 20:
            return jsonify({'ok': False, 'error': 'sku_max',
                'msg': f'Podés agregar hasta 20 unidades del mismo producto por compra. Ya tenés {cant_actual_sku}.'})
    else:
        tipos_en_carrito = {_tipo_envio_sku(i['sku']) for i in carrito}
        total_almohadas  = sum(i['cantidad'] for i in carrito if _tipo_envio_sku(i['sku']) == 'almohada')

        if tipo_nuevo == 'almohada':
            if 'me2' in tipos_en_carrito:
                return jsonify({'ok': False, 'error': 'me2_conflict',
                    'msg': 'Las almohadas y los colchones deben comprarse por separado.'})
            if total_almohadas + cantidad > 6:
                return jsonify({'ok': False, 'error': 'almohada_max',
                    'msg': f'Podés agregar hasta 6 almohadas por compra. Ya tenés {total_almohadas}.'})
        elif tipo_nuevo == 'me2':
            if 'almohada' in tipos_en_carrito:
                return jsonify({'ok': False, 'error': 'me2_conflict',
                    'msg': 'Los colchones Compac y las almohadas deben comprarse por separado.'})
            if any(_tipo_envio_sku(i['sku']) == 'me2' for i in carrito):
                return jsonify({'ok': False, 'error': 'me2_max',
                    'msg': 'Solo podés comprar un colchón Compac por vez con envío incluido. Para más unidades hacé otra compra.'})

    # ── Validar que el producto esté activo ──────────────────────────────────
    try:
        db_act = get_db()
        cur_act = db_act.cursor()
        # Para sommiers verificar en productos_compuestos
        sku_col_act = ('C' + sku.split('+')[0][1:]) if (sku.startswith('S') and len(sku) > 1 and sku[1].isalpha()) else None
        if sku_col_act:
            cur_act.execute("SELECT activo FROM productos_compuestos WHERE sku = %s", (sku,))
            row_act = cur_act.fetchone()
            if row_act and not row_act['activo']:
                cur_act.close(); db_act.close()
                return jsonify({'ok': False, 'msg': 'Este producto no está disponible.'})
        else:
            cur_act.execute("SELECT COALESCE(activo,1) AS activo FROM productos_base WHERE sku = %s", (sku,))
            row_act = cur_act.fetchone()
            if row_act and not row_act['activo']:
                cur_act.close(); db_act.close()
                return jsonify({'ok': False, 'msg': 'Este producto no está disponible.'})
        cur_act.close(); db_act.close()
    except Exception:
        pass

    # ── Validar stock disponible ─────────────────────────────────────────────
    try:
        db = get_db()
        cur = db.cursor()
        sku_col = ('C' + sku.split('+')[0][1:]) if (sku.startswith('S') and len(sku) > 1 and sku[1].isalpha()) else None
        cur.execute("SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_col,)) if sku_col else None
        cfg = cur.fetchone() if sku_col else None
        if cfg:
            base_sku   = cfg['base_sku_default']
            cant_bases = int(cfg['cantidad_bases'] or 1)
            stock_col  = get_stock_disponible_sku(cur, cfg['colchon_sku'])
            # Para la base usamos stock_actual directo (evita doble descuento por componentes en ventas pendientes)
            cur.execute("SELECT stock_actual FROM productos_base WHERE sku = %s", (base_sku,))
            _rb = cur.fetchone()
            stock_base = int(_rb['stock_actual'] or 0) if _rb else 0
            # Cuántas bases ya están comprometidas en el carrito por OTROS conjuntos que usan la misma base
            bases_en_carrito = 0
            for item in carrito:
                if item['sku'] == sku:
                    continue  # este mismo SKU lo contamos aparte
                sku_col_item = ('C' + item['sku'][1:]) if (item['sku'].startswith('S') and len(item['sku']) > 1 and item['sku'][1].isalpha()) else None
                if not sku_col_item:
                    continue
                cur.execute("SELECT base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_col_item,))
                cfg_item = cur.fetchone()
                if cfg_item and cfg_item['base_sku_default'] == base_sku:
                    bases_en_carrito += item['cantidad'] * int(cfg_item['cantidad_bases'] or 1)
            stock_base_disp = stock_base - bases_en_carrito
            stock_disp = min(stock_col, stock_base_disp // cant_bases)
            print(f"[STOCK_DEBUG] sku={sku} sku_col={sku_col} base={base_sku} cant_bases={cant_bases} stock_col={stock_col} stock_base={stock_base} bases_en_carrito={bases_en_carrito} stock_base_disp={stock_base_disp} stock_disp={stock_disp} ya_en_carrito={next((i['cantidad'] for i in carrito if i['sku']==sku),0)}", flush=True)
        else:
            stock_disp = get_stock_disponible_sku(cur, sku)
        cur.close()
        db.close()
        ya_en_carrito = next((i['cantidad'] for i in carrito if i['sku'] == sku), 0)
        if ya_en_carrito + cantidad > stock_disp:
            # Verificar si el producto admite demora
            if get_demora_sin_stock() > 0:
                db3 = get_db()
                cur3 = db3.cursor()
                cur3.execute("SELECT linea, tipo, modelo FROM productos_base WHERE sku = %s", (sku,))
                prod_row = cur3.fetchone()
                if not prod_row:
                    # Es un sommier — buscar por colchon base
                    sku_col_dem = ('C' + sku.split('+')[0][1:]) if sku.startswith('S') else None
                    if sku_col_dem:
                        cur3.execute("SELECT linea, tipo, modelo FROM productos_base WHERE sku = %s", (sku_col_dem,))
                        prod_row = cur3.fetchone()
                cur3.close(); db3.close()
                linea_prod = prod_row['linea'] if prod_row else ''
                tipo_prod = prod_row['tipo'] if prod_row else 'conjunto'
                modelo_prod = prod_row['modelo'] if prod_row else ''
                if not aplica_demora(linea_prod, tipo_prod, modelo_prod):
                    disponible = max(0, stock_disp - ya_en_carrito)
                    if disponible <= 0:
                        return jsonify({'ok': False, 'msg': 'No hay más stock disponible para este producto.'})
                    else:
                        return jsonify({'ok': False, 'msg': f'Solo quedan {disponible} unidades disponibles.'})
                # else: permitir — cantidad puede superar stock si hay demora
            else:
                disponible = max(0, stock_disp - ya_en_carrito)
                if disponible <= 0:
                    return jsonify({'ok': False, 'msg': 'No hay más stock disponible para este producto.'})
                else:
                    return jsonify({'ok': False, 'msg': f'Solo quedan {disponible} unidades disponibles.'})
    except Exception as _e:
        import traceback; traceback.print_exc()
        pass  # Si falla la consulta, dejamos pasar (no bloquear por error de DB)

    # ── Agregar o sumar ───────────────────────────────────────────────────────
    for item in carrito:
        if item['sku'] == sku:
            item['cantidad'] += cantidad
            session['carrito'] = carrito
            session.modified = True
            return jsonify({'ok': True,
                'total_items': sum(i['cantidad'] for i in carrito),
                'cantidad_sku': item['cantidad'],
                'sku_tipo': tipo_nuevo})

    carrito.append({'sku': sku, 'nombre': nombre, 'precio': precio, 'cantidad': cantidad})
    session['carrito'] = carrito
    session.modified = True
    return jsonify({'ok': True,
        'total_items': sum(i['cantidad'] for i in carrito),
        'cantidad_sku': cantidad,
        'sku_tipo': tipo_nuevo})


@tienda_bp.route('/carrito/actualizar', methods=['POST'])
def actualizar_carrito():
    """Cambia la cantidad de un item (solo almohadas). delta = +1 o -1."""
    data    = request.get_json() or {}
    sku     = data.get('sku')
    delta   = int(data.get('delta', 0))
    carrito = session.get('carrito', [])

    flag_unificado = _shipping_unificado()
    total_almohadas = sum(i['cantidad'] for i in carrito if _tipo_envio_sku(i['sku']) == 'almohada')

    for item in carrito:
        if item['sku'] == sku:
            nueva = item['cantidad'] + delta
            if nueva <= 0:
                carrito = [i for i in carrito if i['sku'] != sku]
            elif flag_unificado and nueva > 20:
                return jsonify({'ok': False, 'msg': 'Máximo 20 unidades del mismo producto por compra.'})
            elif (not flag_unificado) and _tipo_envio_sku(sku) == 'almohada' and total_almohadas + delta > 6:
                return jsonify({'ok': False, 'msg': 'Máximo 6 almohadas por compra.'})
            else:
                # Validar stock antes de sumar
                try:
                    db = get_db()
                    cur = db.cursor()
                    sku_col = ('C' + sku.split('+')[0][1:]) if (sku.startswith('S') and len(sku) > 1 and sku[1].isalpha()) else None
                    cur.execute("SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_col,)) if sku_col else None
                    cfg = cur.fetchone() if sku_col else None
                    if cfg:
                        base_sku   = cfg['base_sku_default']
                        cant_bases = int(cfg['cantidad_bases'] or 1)
                        stock_col  = get_stock_disponible_sku(cur, cfg['colchon_sku'])
                        cur.execute("SELECT stock_actual FROM productos_base WHERE sku = %s", (base_sku,))
                        _rb = cur.fetchone()
                        stock_base = int(_rb['stock_actual'] or 0) if _rb else 0
                        bases_en_carrito = 0
                        for item in carrito:
                            if item['sku'] == sku:
                                continue
                            sku_col_item = ('C' + item['sku'][1:]) if (item['sku'].startswith('S') and len(item['sku']) > 1 and item['sku'][1].isalpha()) else None
                            if not sku_col_item:
                                continue
                            cur.execute("SELECT base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_col_item,))
                            cfg_item = cur.fetchone()
                            if cfg_item and cfg_item['base_sku_default'] == base_sku:
                                bases_en_carrito += item['cantidad'] * int(cfg_item['cantidad_bases'] or 1)
                        stock_base_disp = stock_base - bases_en_carrito
                        stock_disp = min(stock_col, stock_base_disp // cant_bases)
                    else:
                        stock_disp = get_stock_disponible_sku(cur, sku)
                    cur.close()
                    db.close()
                    if nueva > stock_disp:
                        # Permitir si aplica demora
                        _dem = get_demora_sin_stock()
                        _permite = False
                        if _dem > 0:
                            cur3d = db.cursor()
                            cur3d.execute("SELECT linea, tipo, modelo FROM productos_base WHERE sku = %s", (sku,))
                            _pr = cur3d.fetchone()
                            cur3d.close()
                            if _pr and aplica_demora(_pr.get('linea',''), _pr.get('tipo',''), _pr.get('modelo','')):
                                _permite = True
                        if not _permite:
                            return jsonify({'ok': False, 'msg': f'Solo quedan {stock_disp} unidades disponibles.'})
                except Exception:
                    pass
                item['cantidad'] = nueva
            break

    session['carrito'] = carrito
    session.modified = True
    subtotal = sum(i['precio'] * i['cantidad'] for i in carrito)
    nueva_cant = next((i['cantidad'] for i in carrito if i['sku'] == sku), 0)
    precio_unit = next((i['precio'] for i in carrito if i['sku'] == sku), 0)

    # Recalcular hay_demora para que el carrito actualice la leyenda sin recargar
    hay_demora = False
    fecha_disponible = ''
    _demora_dias = get_demora_sin_stock()
    if _demora_dias and carrito:
        try:
            _db_d = get_db()
            _cur_d = _db_d.cursor()
            for _item in carrito:
                _sku = _item['sku']
                _sku_col = ('C' + _sku.split('+')[0][1:]) if (_sku.startswith('S') and len(_sku) > 1 and _sku[1].isalpha()) else None
                _cfg = None
                if _sku_col:
                    _cur_d.execute("SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (_sku_col,))
                    _cfg = _cur_d.fetchone()
                if _cfg:
                    _sc = get_stock_disponible_sku(_cur_d, _cfg['colchon_sku'])
                    _cur_d.execute("SELECT stock_actual FROM productos_base WHERE sku = %s", (_cfg['base_sku_default'],))
                    _rb = _cur_d.fetchone()
                    _sb = int(_rb['stock_actual'] or 0) if _rb else 0
                    _stock = min(_sc, _sb // int(_cfg['cantidad_bases'] or 1))
                else:
                    _stock = _get_stock_real(_cur_d, _sku)
                if _stock < _item['cantidad']:
                    hay_demora = True
                    break
            _cur_d.close()
            _db_d.close()
        except Exception:
            pass
    if hay_demora:
        fecha_disponible = calcular_fecha_demora(_demora_dias)

    return jsonify({
        'ok': True,
        'total_items': sum(i['cantidad'] for i in carrito),
        'subtotal_fmt': format_price(subtotal),
        'cantidad_sku': nueva_cant,
        'total_item_fmt': format_price(precio_unit * nueva_cant) if nueva_cant > 0 else '',
        'hay_demora': hay_demora,
        'fecha_disponible': fecha_disponible,
        'demora_dias': _demora_dias if hay_demora else 0,
    })


@tienda_bp.route('/carrito/vaciar', methods=['POST'])
def vaciar_carrito():
    session['carrito'] = []
    session.pop('cupon', None)
    session.modified = True
    return redirect(url_for('tienda.ver_carrito'))


@tienda_bp.route('/carrito')
def ver_carrito():
    carrito  = session.get('carrito', [])
    subtotal = sum(i['precio'] * i['cantidad'] for i in carrito)
    cupon    = session.get('cupon')
    descuento_monto = 0
    if cupon:
        if cupon['tipo'] == 'pct':
            descuento_monto = round(subtotal * cupon['valor'] / 100)
        else:
            descuento_monto = min(cupon['valor'], subtotal)
    total = subtotal - descuento_monto
    shipping_tipo, _ = get_shipping_info(carrito) if carrito else (None, None)

    # Demora sin stock
    demora_dias = get_demora_sin_stock()
    hay_demora = False
    if demora_dias and carrito:
        db = get_db()
        cur = db.cursor()
        for item in carrito:
            sku_item = item['sku']
            # Para sommiers (SEXP90, SEXP100+1, etc.) calcular stock real
            sku_col_item = ('C' + sku_item.split('+')[0][1:]) if (sku_item.startswith('S') and len(sku_item) > 1 and sku_item[1].isalpha()) else None
            cur.execute("SELECT colchon_sku, base_sku_default, cantidad_bases FROM conjunto_configuracion WHERE colchon_sku = %s AND activo = 1", (sku_col_item,)) if sku_col_item else None
            cfg_item = cur.fetchone() if sku_col_item else None
            if cfg_item:
                stock_col  = get_stock_disponible_sku(cur, cfg_item['colchon_sku'])
                cur.execute("SELECT stock_actual FROM productos_base WHERE sku = %s", (cfg_item['base_sku_default'],))
                rb = cur.fetchone()
                stock_base = int(rb['stock_actual'] or 0) if rb else 0
                stock = min(stock_col, stock_base // int(cfg_item['cantidad_bases'] or 1))
            else:
                stock = _get_stock_real(cur, sku_item)
            if stock < item['cantidad']:
                hay_demora = True
                break
        cur.close()
        db.close()

    fecha_disponible = calcular_fecha_demora(demora_dias) if (demora_dias and hay_demora) else None

    return render_template('tienda/carrito.html',
        carrito          = carrito,
        subtotal         = subtotal,
        subtotal_fmt     = format_price(subtotal),
        total            = total,
        total_fmt        = format_price(total),
        descuento_monto  = descuento_monto,
        descuento_fmt    = format_price(descuento_monto) if descuento_monto else None,
        cupon            = cupon,
        carrito_count    = len(carrito),
        shipping_tipo    = shipping_tipo,
        demora_dias      = demora_dias,
        hay_demora       = hay_demora,
        fecha_disponible = fecha_disponible,
        ga4_items        = [
            {'item_id': i['sku'], 'item_name': i.get('nombre', i['sku']),
             'price': float(i.get('precio', 0)), 'quantity': int(i.get('cantidad', 1))}
            for i in carrito
        ],
        ga4_value        = float(total),
    )


@tienda_bp.route('/carrito/validar-cupon', methods=['POST'])
def validar_cupon():
    data    = request.get_json() or {}
    codigo  = data.get('codigo', '').strip().upper()
    email   = data.get('email', '').strip().lower()
    carrito = session.get('carrito', [])
    subtotal = sum(i['precio'] * i['cantidad'] for i in carrito)

    if not codigo:
        return jsonify({'ok': False, 'error': 'Ingresá un código'})

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM cupones WHERE codigo=%s AND activo=1", (codigo,))
        cup = cursor.fetchone()
        if not cup:
            return jsonify({'ok': False, 'error': 'Cupón inválido o inactivo'})

        from datetime import date
        if cup['fecha_vencimiento'] and cup['fecha_vencimiento'] < date.today():
            return jsonify({'ok': False, 'error': 'Este cupón está vencido'})

        if cup['usos_maximos'] and cup['usos_actuales'] >= cup['usos_maximos']:
            return jsonify({'ok': False, 'error': 'Este cupón ya alcanzó el límite de usos'})

        if cup['minimo_compra'] and subtotal < float(cup['minimo_compra']):
            return jsonify({'ok': False, 'error': f"Compra mínima: {format_price(cup['minimo_compra'])}"})

        if cup['solo_un_uso'] and email:
            cursor.execute("SELECT id FROM cupones_uso WHERE cupon_id=%s AND email=%s LIMIT 1", (cup['id'], email))
            if cursor.fetchone():
                return jsonify({'ok': False, 'error': 'Ya usaste este cupón anteriormente'})

        # Calcular descuento
        if cup['tipo'] == 'pct':
            descuento = round(subtotal * float(cup['valor']) / 100)
            label = f"-{int(cup['valor'])}%"
        else:
            descuento = min(float(cup['valor']), subtotal)
            label = f"-{format_price(cup['valor'])}"

        session['cupon'] = {
            'id':     cup['id'],
            'codigo': cup['codigo'],
            'tipo':   cup['tipo'],
            'valor':  float(cup['valor']),
            'label':  label,
        }
        session.modified = True

        return jsonify({
            'ok':             True,
            'codigo':         cup['codigo'],
            'label':          label,
            'descuento':      descuento,
            'descuento_fmt':  format_price(descuento),
            'total_fmt':      format_price(subtotal - descuento),
        })
    finally:
        cursor.close()
        db.close()


@tienda_bp.route('/carrito/quitar-cupon', methods=['POST'])
def quitar_cupon():
    session.pop('cupon', None)
    session.modified = True
    return jsonify({'ok': True})


@tienda_bp.route('/carrito/eliminar', methods=['POST'])
def eliminar_carrito():
    data = request.get_json() or {}
    sku  = data.get('sku')
    carrito = [i for i in session.get('carrito', []) if i['sku'] != sku]
    session['carrito'] = carrito
    subtotal = sum(i['precio'] * i['cantidad'] for i in carrito)
    return jsonify({
        'ok': True,
        'total_items': len(carrito),
        'subtotal_fmt': format_price(subtotal),
    })

# ── CHECKOUT ───────────────────────────────────────────────────────────────────


# ── ENVÍOS ──────────────────────────────────────────────────────────────────────

almohadas_list = ['CLASICA','SUBLIME','CERVICAL','RENOVATION','PLATINO','DORAL','DUAL','EXCLUSIVE']
SKUS_OFERTA = ['CTR80', 'SEXP140', 'CREP140', 'SPR14020', 'SSUP160', 'SEX200', 'CEX100', 'SEXP100', 'CEX200']

# ── Descripciones y specs por modelo ──────────────────────────────────────────
DESCRIPCIONES_MODELO = {
    'tropical': {
        'bajada': 'La mejor relación calidad-precio para uso diario. Ideal para dormitorios secundarios, estudiantiles o quien busca comodidad sin complicaciones.',
        'bullets': [
            'Espuma de poliuretano flexible de 22 kg/m³',
            'Sistema flip: giralo para duplicar su vida útil',
            'Tela sábana matelaseada suave al tacto',
            'Sensación de apoyo suave — ideal para descanso cotidiano',
            'Soporte recomendado hasta 70 kg',
            'Altura 18 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'princess 20cm': {
        'bajada': 'El equilibrio perfecto entre precio y calidad. Firmeza confiable para el descanso de todos los días, con una densidad superior que garantiza durabilidad.',
        'bullets': [
            'Espuma de poliuretano flexible de 24 kg/m³',
            'Sistema flip: mayor durabilidad rotando el colchón',
            'Tela sábana matelaseada de alta resistencia',
            'Sensación de apoyo firme — respaldo parejo en toda la superficie',
            'Soporte recomendado hasta 80 kg',
            'Altura 20 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'princess 23cm': {
        'bajada': 'Más altura, más confort. La Princess 23 suma centímetros y un acabado Jackard para quienes quieren dar un paso más en calidad sin resignar firmeza.',
        'bullets': [
            'Espuma de poliuretano flexible de 24 kg/m³',
            'Sistema flip para prolongar la vida útil',
            'Tela Jackard matelaseado — textura premium',
            'Sensación de apoyo firme con mayor amortiguación',
            'Soporte recomendado hasta 80 kg',
            'Altura 23 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'exclusive': {
        'bajada': 'Alta densidad para un descanso que dura años. El Exclusive es el colchón para quienes priorizan calidad sin concesiones — fabricado para rendir al máximo día tras día.',
        'bullets': [
            'Espuma de poliuretano flexible de 30 kg/m³ — alta densidad',
            'Sistema flip: máxima durabilidad garantizada',
            'Tela Jackard matelaseado de alta calidad',
            'Sensación de apoyo firme con distribución uniforme del peso',
            'Soporte recomendado hasta 100 kg',
            'Altura 25 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'exclusive pillow': {
        'bajada': 'Todo el rigor del Exclusive con un plus de suavidad en la superficie. El Pillow Top agrega una capa extra de confort sin sacrificar el soporte firme que te cuida la espalda.',
        'bullets': [
            'Espuma de alta densidad 30 kg/m³ con doble Pillow Top',
            'Sistema flip: rotación recomendada para mayor vida útil',
            'Tela Jackard matelaseado premium',
            'Sensación firme con capa superior suave — lo mejor de dos mundos',
            'Soporte recomendado hasta 100 kg',
            'Altura 29 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'renovation': {
        'bajada': 'El colchón de espuma más denso de la línea Cannon. Pensado para quienes exigen lo mejor: máxima durabilidad, soporte extra firme y una calidad que se mantiene inalterable con los años.',
        'bullets': [
            'Espuma de poliuretano flexible de 35 kg/m³ — altísima densidad',
            'Sistema flip para una durabilidad excepcional',
            'Tela tejido de punto matelaseado con gran transpirabilidad',
            'Sensación de apoyo extra firme — ideal para dolores de espalda',
            'Soporte recomendado hasta 120 kg',
            'Altura 26 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'renovation europillow': {
        'bajada': 'La máxima expresión de la línea Renovation. Incorpora un doble Pillow Top que suma suavidad a la firmeza extrema, para un descanso placentero y saludable en toda regla.',
        'bullets': [
            'Espuma de 35 kg/m³ con doble capa soft Euro Pillow',
            'Sistema flip doble — rotación en ambos lados para máxima duración',
            'Tela tejido de punto con excelente ventilación',
            'Extra firme con superficie acolchada — soporte y confort a la vez',
            'Soporte recomendado hasta 120 kg',
            'Altura 33 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'compac': {
        'bajada': 'Tecnología multicapa en caja. El Compac llega enrollado, listo para usar en minutos. Ideal para departamentos, escaleras complicadas o quienes buscan practicidad sin resignar calidad.',
        'bullets': [
            'Estructura multicapa con núcleo de espuma 30 kg/m³',
            'Sistema no flip — diseñado para usar siempre del mismo lado',
            'Tela tejido de punto elástico y transpirable',
            'Sensación de apoyo firme y adaptable',
            'Soporte recomendado hasta 100 kg',
            'Altura 21 cm — se despliega en pocas horas',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'soñar': {
        'bajada': 'El clásico de resortes Cannon. El Soñar combina un sistema de resortes bicónicos reforzados con una construcción probada que brinda comodidad y amortiguación para el descanso diario.',
        'bullets': [
            'Resortes bicónicos Bonnell ultra reforzados',
            'Doble marco perimetral y estabilizadores perimetrales',
            'Sistema flip para mayor durabilidad',
            'Tela sábana matelaseada suave',
            'Sensación de apoyo suave y amortiguada',
            'Soporte recomendado hasta 80 kg',
            'Altura 23 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'doral': {
        'bajada': 'Resortes continuos para un soporte parejo en cada centímetro. El sistema Ultracoil distribuye el peso uniformemente, eliminando los puntos de presión para que te despiertes sin molestias.',
        'bullets': [
            'Sistema de resortes continuos Ultracoil',
            'Doble marco perimetral con estabilizadores internos',
            'Tela tejido de punto con aireadores — máxima transpirabilidad',
            'Sensación de apoyo firme y envolvente',
            'Soporte recomendado hasta 100 kg',
            'Altura 27 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'doral pillow': {
        'bajada': 'El Doral llevado al siguiente nivel. El doble Pillow Top agrega una capa de suavidad que abraza el cuerpo, mientras los resortes continuos mantienen el soporte firme que necesitás.',
        'bullets': [
            'Resortes continuos Ultracoil + doble Pillow Top',
            'Doble marco perimetral reforzado',
            'Tela tejido de punto con aireadores',
            'Firme por dentro, suave en la superficie — combinación ideal',
            'Soporte recomendado hasta 100 kg',
            'Altura 33 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'sublime': {
        'bajada': 'Resortes de bolsillo (Pocket) para un descanso sin interrupciones. Cada resorte actúa de forma independiente, adaptándose a tu cuerpo y absorbiendo el movimiento de tu compañero de cama.',
        'bullets': [
            'Resortes individuales Pocket — acción independiente',
            'Agarraderas laterales para facilitar el manejo',
            'Tela tejido de punto con aireadores',
            'Sensación de apoyo firme con adaptación personalizada',
            'Soporte recomendado hasta 120 kg',
            'Altura 32 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
    'sublime europillow': {
        'bajada': 'El summum del descanso Cannon. Resortes Pocket + doble Euro Pillow para una experiencia de hotelería cinco estrellas en tu propio hogar. Firmeza, suavidad y tecnología en un solo colchón.',
        'bullets': [
            'Resortes individuales Pocket + doble Euro Pillow',
            'Sistema flip doble para máxima vida útil',
            'Tela tejido de punto con aireadores premium',
            'Firmeza profunda con suavidad envolvente en la superficie',
            'Soporte recomendado hasta 120 kg',
            'Altura 35 cm',
            'Garantía oficial Cannon: 6 meses + 5 años',
        ],
    },
}

# Specs técnicas por modelo
SPECS_MODELO = {
    'tropical':             {'material': 'Espuma', 'densidad': '22 kg/m³', 'sistema': 'Flip', 'altura_col': 18},
    'princess 20cm':        {'material': 'Espuma', 'densidad': '24 kg/m³', 'sistema': 'Flip', 'altura_col': 20},
    'princess 23cm':        {'material': 'Espuma', 'densidad': '24 kg/m³', 'sistema': 'Flip', 'altura_col': 23},
    'exclusive':            {'material': 'Espuma', 'densidad': '30 kg/m³', 'sistema': 'Flip', 'altura_col': 25},
    'exclusive pillow':     {'material': 'Espuma', 'densidad': '30 kg/m³', 'sistema': 'Flip', 'altura_col': 29},
    'renovation':           {'material': 'Espuma', 'densidad': '35 kg/m³', 'sistema': 'Flip', 'altura_col': 26},
    'renovation europillow':{'material': 'Espuma', 'densidad': '35 kg/m³', 'sistema': 'Flip doble', 'altura_col': 33},
    'compac':               {'material': 'Espuma multicapa', 'densidad': '30 kg/m³', 'sistema': 'No flip', 'altura_col': 21},
    'soñar':                {'material': 'Resortes Bonnell', 'densidad': '—', 'sistema': 'Flip', 'altura_col': 23},
    'doral':                {'material': 'Resortes Ultracoil', 'densidad': '—', 'sistema': 'Flip', 'altura_col': 27},
    'doral pillow':         {'material': 'Resortes Ultracoil', 'densidad': '—', 'sistema': 'Flip doble', 'altura_col': 33},
    'sublime':              {'material': 'Resortes Pocket', 'densidad': '—', 'sistema': 'Flip', 'altura_col': 32},
    'sublime europillow':   {'material': 'Resortes Pocket', 'densidad': '—', 'sistema': 'Flip doble', 'altura_col': 35},
}

BASE_ALTURA_CM  = 22   # altura de la base/sommier
PATAS_ALTURA_CM = 12   # altura de las patas

def get_patas_sommier(medida):
    """Retorna cantidad de patas según medida del sommier."""
    if not medida:
        return None
    ancho = int(medida.split('x')[0])
    if ancho <= 100:
        return 6
    elif ancho <= 150:
        return 7
    else:
        return '6 patas por base (2 bases)'

def get_dimensions(sku):
    """Retorna dict con length, width, height (cm) y weight (kg). Solo para SKUs que van por ME2."""
    if sku == 'PRUEBA':
        return {'length': 20, 'width': 20, 'height': 10, 'weight': 0.2}
    if sku in almohadas_list:
        return {'length': 62, 'width': 40, 'height': 12, 'weight': 1.8}
    sku_base = sku.split('_')[0]
    if sku_base.startswith('CCO') or sku_base.startswith('CCP'):
        medida = sku_base[3:]
        weights = {'80': 14.8, '100': 19.2, '140': 23, '160': 24.5}
        return {'length': 115, 'width': 45, 'height': 45, 'weight': weights.get(medida, 20)}
    return None  # Zipnova / sin envío ME2

def calculate_package_dimensions(carrito):
    """Calcula dimensiones totales para ME2. Retorna string LxWxH,grams para MP."""
    total_weight = max_length = max_width = total_height = 0
    for item in carrito:
        dims = get_dimensions(item['sku'])
        if not dims:
            return None
        total_weight += dims['weight'] * item['cantidad']
        max_length    = max(max_length, dims['length'])
        max_width     = max(max_width,  dims['width'])
        total_height += dims['height']  * item['cantidad']
    total_height = min(total_height, 105)
    return f"{int(max_length)}x{int(max_width)}x{int(total_height)},{int(total_weight * 1000)}"

def get_shipping_info(carrito):
    """
    Clasifica el carrito:
      - 'me2_paid': SOLO almohadas (hasta 6u) o SOLO Compac (CCO/CCP)
      - 'zipnova':  cualquier colchon/sommier, o mezcla colchon+almohadas
                    (las almohadas viajan junto con el colchon via Zipnova)
      - 'mixed':    mezcla invalida (ej: almohadas + compac, no deberia ocurrir)

    Con flag shipping_unificado_zipnova='1', todo carrito devuelve 'zipnova'.
    """
    if _shipping_unificado():
        return 'zipnova', None
    tipos = set()
    for item in carrito:
        sku = item['sku']
        sku_base = sku.split('_')[0]
        if sku in ('PRUEBA',) or sku in almohadas_list:
            tipos.add('me2_paid')
        elif sku_base.startswith('CCO') or sku_base.startswith('CCP'):
            tipos.add('me2_paid')
        else:
            tipos.add('zipnova')
    # Si hay zipnova en el carrito, todo va por zipnova
    # (las almohadas viajan en el bulto de patas del sommier, o en bulto separado con el colchon)
    if 'zipnova' in tipos:
        return 'zipnova', None
    if len(tipos) > 1:
        return 'mixed', None
    return (tipos.pop(), None) if tipos else (None, None)

# ── ZIPNOVA ────────────────────────────────────────────────────────────────────

ZIPNOVA_ACCOUNT_ID = os.getenv('ZIPNOVA_ACCOUNT_ID', '5786')
ZIPNOVA_ORIGIN_ID  = os.getenv('ZIPNOVA_ORIGIN_ID',  '374397')
ZIPNOVA_API_KEY    = os.getenv('ZIPNOVA_API_KEY', '')
ZIPNOVA_API_SECRET = os.getenv('ZIPNOVA_API_SECRET', '')
ZIPNOVA_BASE_URL   = 'https://api.zipnova.com.ar/v2'
ZIPNOVA_PATAS_PESO = 1000  # gramos


def _zipnova_auth():
    return (ZIPNOVA_API_KEY, ZIPNOVA_API_SECRET)


def armar_bultos_zipnova(carrito, db):
    """
    Dado el carrito, arma la lista de paquetes para Zipnova.
    Retorna lista de dicts: {sku, weight(kg), height, width, length, description}
    Lógica:
      - Sommier (compuesto): 1 bulto colchon + 1 bulto por cada base + 1 bulto patas
          (los sommiers 160+ tienen 2 bases = 4 bultos en total)
          Las almohadas del combo van dentro del bulto patas.
      - Colchon simple: 1 bulto con sus dimensiones
      - Almohadas sueltas: se ignoran (van por ME2)
      - Con flag shipping_unificado_zipnova='1': almohadas sueltas se agrupan
          en 1 (1-10 u) ó 2 (11-20 u) bultos, y los Compac CC[OP]* se procesan
          como colchones simples (1 bulto por unidad).
    """
    flag_unificado = _shipping_unificado()
    cur = db.cursor(pymysql.cursors.DictCursor)
    bultos = []

    skus_carrito = list({item['sku'] for item in carrito})
    placeholders = ','.join(['%s'] * len(skus_carrito))
    cur.execute(
        f"SELECT id, sku FROM productos_compuestos WHERE sku IN ({placeholders})",
        skus_carrito
    )
    compuestos_map = {row['sku']: row['id'] for row in cur.fetchall()}

    # Detector de almohadas que no depende de _tipo_envio_sku (con flag activo
    # ese helper devuelve 'zipnova' para todo, así que detectamos por SKU directo).
    def _es_almohada_sku(s):
        return s in SKUS_ALMOHADA

    # Pre-calcular almohadas sueltas del carrito
    hay_sommier = any(item['sku'] in compuestos_map for item in carrito)
    peso_almohadas_sueltas = 0
    desc_almohadas_sueltas = []
    info_almohadas = []  # detalle por item — usado para agrupar en bultos cuando flag activo
    for item in carrito:
        if _es_almohada_sku(item['sku']):
            cur.execute("SELECT nombre, peso_gramos, alto_cm, ancho_cm, largo_cm FROM productos_base WHERE activo = 1 AND sku = %s", (item['sku'],))
            pb_alm = cur.fetchone()
            if pb_alm:
                peso_unit = pb_alm['peso_gramos'] or 1000
                peso_almohadas_sueltas += peso_unit * item['cantidad']
                desc_almohadas_sueltas.append(f"{item['cantidad']}x {pb_alm['nombre']}")
                info_almohadas.append({
                    'sku':       item['sku'],
                    'cantidad':  item['cantidad'],
                    'peso_unit': peso_unit,
                    'nombre':    pb_alm['nombre'],
                    'alto':      pb_alm.get('alto_cm')  or 12,
                    'ancho':     pb_alm.get('ancho_cm') or 40,
                    'largo':     pb_alm.get('largo_cm') or 70,
                })

    # Acumulador único de patas para todos los sommiers del carrito
    peso_patas_acum = 0  # se llena durante el loop, se agrega al final
    hay_patas = False

    for item in carrito:
        sku      = item['sku']
        cantidad = item.get('cantidad', 1)
        tipo_env = _tipo_envio_sku(sku)

        # Flag activo: las almohadas se procesan en el bloque agrupado de abajo
        # (o se fusionan en PATAS si hay sommier). No generamos bulto por unidad.
        if flag_unificado and _es_almohada_sku(sku):
            continue

        if tipo_env == 'me2':
            continue
        if tipo_env == 'almohada':
            # Si no hay sommier, van en bulto propio; si hay sommier, se fusionan con patas
            if not hay_sommier and peso_almohadas_sueltas > 0:
                cur.execute("SELECT alto_cm, ancho_cm, largo_cm FROM productos_base WHERE activo = 1 AND sku = %s", (sku,))
                pb_alm = cur.fetchone() or {}
                bultos.append({
                    'sku':         'ALMOHADAS',
                    'description': ', '.join(desc_almohadas_sueltas),
                    'weight':      max(10, int(peso_almohadas_sueltas)),
                    'height':      pb_alm.get('alto_cm')  or 12,
                    'width':       pb_alm.get('ancho_cm') or 40,
                    'length':      pb_alm.get('largo_cm') or 70,
                })
                peso_almohadas_sueltas = 0  # evitar duplicados si hay varios SKUs almohada
            continue

        if tipo_env != 'zipnova':
            continue

        for _ in range(cantidad):
            if sku in compuestos_map:
                # ── Sommier ───────────────────────────────────────────────────
                comp_id = compuestos_map[sku]
                cur.execute("""
                    SELECT pb.sku, pb.nombre, pb.alto_cm, pb.ancho_cm, pb.largo_cm,
                           pb.peso_gramos, c.cantidad_necesaria
                    FROM componentes c
                    JOIN productos_base pb ON c.producto_base_id = pb.id
                    WHERE c.producto_compuesto_id = %s
                """, (comp_id,))
                componentes = cur.fetchall()

                for comp in componentes:
                    csku = comp['sku']
                    cant = comp['cantidad_necesaria']

                    if csku in SKUS_ALMOHADA:
                        # Almohadas del combo van a las patas
                        peso_patas_acum += (comp['peso_gramos'] or 0) * cant

                    elif csku.startswith('BASE_'):
                        for __ in range(cant):
                            bultos.append({
                                'sku':         csku,
                                'description': comp['nombre'],
                                'weight':      max(10, comp['peso_gramos'] or 20000),
                                'height':      comp['alto_cm']  or 21,
                                'width':       comp['ancho_cm'] or 100,
                                'length':      comp['largo_cm'] or 190,
                            })
                    else:
                        for __ in range(cant):
                            bultos.append({
                                'sku':         csku,
                                'description': comp['nombre'],
                                'weight':      max(10, comp['peso_gramos'] or 20000),
                                'height':      comp['alto_cm']  or 27,
                                'width':       comp['ancho_cm'] or 100,
                                'length':      comp['largo_cm'] or 190,
                            })

                # Sumar patas de este sommier al acumulador (1kg por sommier)
                peso_patas_acum += ZIPNOVA_PATAS_PESO
                hay_patas = True

            else:
                # ── Colchon simple ────────────────────────────────────────────
                cur.execute(
                    "SELECT nombre, alto_cm, ancho_cm, largo_cm, peso_gramos FROM productos_base WHERE activo = 1 AND sku = %s",
                    (sku,)
                )
                pb = cur.fetchone()
                if pb:
                    bultos.append({
                        'sku':         sku,
                        'description': pb['nombre'],
                        'weight':      max(10, pb['peso_gramos'] or 20000),
                        'height':      pb['alto_cm']  or 27,
                        'width':       pb['ancho_cm'] or 100,
                        'length':      pb['largo_cm'] or 190,
                    })

    # Agregar bulto único de patas (todos los sommiers comparten uno)
    if hay_patas:
        peso_patas_total = peso_patas_acum + peso_almohadas_sueltas
        desc_patas = 'Patas y accesorios'
        if desc_almohadas_sueltas:
            desc_patas += ' + ' + ', '.join(desc_almohadas_sueltas)
        bultos.append({
            'sku':         'PATAS',
            'description': desc_patas,
            'weight':      max(10, int(peso_patas_total)),
            'height':      30,
            'width':       20,
            'length':      10,
        })

    # ── Almohadas sueltas agrupadas (flag activo, sin sommier) ──────────────
    # Regla: 1-10 unidades → 1 bulto; 11-20 unidades → 2 bultos iguales.
    # Las almohadas pueden ser de varios modelos en el mismo carrito.
    if flag_unificado and info_almohadas and not hay_sommier:
        cantidad_total_almohadas = sum(a['cantidad'] for a in info_almohadas)
        partes = 1 if cantidad_total_almohadas <= 10 else 2
        peso_total_g = sum(a['peso_unit'] * a['cantidad'] for a in info_almohadas)
        # Dimensiones del bulto = de la almohada más grande del lote
        max_alto  = max(a['alto']  for a in info_almohadas)
        max_ancho = max(a['ancho'] for a in info_almohadas)
        max_largo = max(a['largo'] for a in info_almohadas)
        desc_lote = ', '.join(f"{a['cantidad']}x {a['nombre']}" for a in info_almohadas)
        # Repartir peso en partes iguales (el resto va en el primer bulto)
        peso_por_parte = peso_total_g // partes
        peso_resto     = peso_total_g - peso_por_parte * partes
        for idx in range(partes):
            peso_parte = peso_por_parte + (peso_resto if idx == 0 else 0)
            bultos.append({
                'sku':         'ALMOHADAS' if partes == 1 else f'ALMOHADAS_{idx+1}',
                'description': desc_lote if partes == 1 else f'{desc_lote} (lote {idx+1}/{partes})',
                'weight':      max(10, int(peso_parte)),
                'height':      max_alto,
                'width':       max_ancho,
                'length':      max_largo,
            })

    cur.close()
    return bultos


def zipnova_cotizar(bultos, cp_destino, ciudad_destino, provincia_destino, declared_value):
    """Llama a Zipnova API para cotizar. Retorna lista de opciones."""
    payload = {
        'account_id':      ZIPNOVA_ACCOUNT_ID,
        'origin_id':       ZIPNOVA_ORIGIN_ID,
        'declared_value':  declared_value,
        'destination': {
            'zipcode': cp_destino,
            'city':    ciudad_destino,
            'state':   provincia_destino,
        },
        'items': bultos,
    }
    logger.info(f'Zipnova quote payload: {payload}')
    resp = http_requests.post(
        f"{ZIPNOVA_BASE_URL}/shipments/quote",
        json=payload,
        auth=_zipnova_auth(),
        timeout=15,
    )
    logger.info(f'Zipnova quote response {resp.status_code}: {resp.text[:500]}')
    resp.raise_for_status()
    data = resp.json()
    return data.get('all_results') or data.get('results') or []


def zipnova_crear_envio(bultos, cliente, numero_venta, declared_value):
    """Crea el envío en Zipnova post-pago. Retorna dict con id y tracking o None."""
    quote = cliente.get('zipnova_quote', {})

    # carrier_id debe ser int
    carrier_id = quote.get('carrier_id', '')
    try:
        carrier_id = int(carrier_id)
    except (ValueError, TypeError):
        carrier_id = carrier_id

    # service_type: si es dict guardar el code, sino usar el string
    service_type = quote.get('service_type', '')
    if isinstance(service_type, dict):
        service_type = service_type.get('code', '')

    payload = {
        'account_id':      ZIPNOVA_ACCOUNT_ID,
        'origin_id':       ZIPNOVA_ORIGIN_ID,
        'logistic_type':   quote.get('logistic_type', 'crossdock'),
        'service_type':    service_type,
        'carrier_id':      carrier_id,
        'declared_value':  declared_value,
        'external_id':     numero_venta,
        'destination': {
            'name':          cliente.get('nombre', ''),
            'street':        cliente.get('calle', ''),
            'street_number': str(cliente.get('altura', '')),
            'document':      cliente.get('dni', ''),
            'email':         cliente.get('email', ''),
            'phone':         str(cliente.get('telefono', '')),
            'state':         quote.get('provincia', cliente.get('provincia', '')),
            'city':          quote.get('ciudad', ''),
            'zipcode':       str(quote.get('cp_destino', cliente.get('cp', ''))),
        },
        'items': bultos,
    }
    logger.warning(f"[zipnova_crear_envio] payload: {json.dumps(payload, default=str)}")
    resp = http_requests.post(
        f'{ZIPNOVA_BASE_URL}/shipments',
        json=payload,
        auth=_zipnova_auth(),
        timeout=20,
    )
    if not resp.ok:
        logger.error(f"[zipnova_crear_envio] 400 response: {resp.text}")
    resp.raise_for_status()
    return resp.json()


@tienda_bp.route('/localidades')
def localidades():
    """Devuelve lista de localidades para un CP dado, usando dict estático."""
    cp = request.args.get('cp', '').strip().lstrip('0') or request.args.get('cp', '').strip()
    # Normalizar: probar con y sin ceros a la izquierda
    nombres = CP_LOCALIDADES.get(cp, [])
    if not nombres:
        # Probar rellenando con ceros hasta 4 dígitos
        cp4 = cp.zfill(4)
        nombres = CP_LOCALIDADES.get(cp4, [])
    return jsonify(sorted(nombres))


@tienda_bp.route('/cotizar-envio', methods=['POST'])
def cotizar_envio():
    """
    AJAX: cotiza envío Zipnova para el carrito actual.
    Body JSON: {cp, ciudad, provincia}
    Responde JSON: {precio, precio_fmt, dias, carrier, bultos, ok} o {error}
    """
    carrito = session.get('carrito', [])
    if not carrito:
        return jsonify({'error': 'Carrito vacío'}), 400

    data      = request.get_json() or {}
    cp        = (data.get('cp') or '').strip()
    ciudad    = (data.get('ciudad') or '').strip()
    provincia = (data.get('provincia') or 'Buenos Aires').strip()

    # Si no hay ciudad, usar la provincia como fallback (Zipnova la requiere)
    if not ciudad:
        ciudad = provincia

    if not cp:
        return jsonify({'error': 'Ingresá el código postal'}), 400

    shipping_tipo, _ = get_shipping_info(carrito)
    if shipping_tipo != 'zipnova':
        return jsonify({'error': 'Este carrito no usa Zipnova'}), 400

    db = get_db()
    try:
        bultos = armar_bultos_zipnova(carrito, db)
    finally:
        db.close()

    if not bultos:
        return jsonify({'error': 'No se pudieron determinar los bultos del pedido'}), 500

    total = int(sum(float(i['precio']) * i['cantidad'] for i in carrito))

    try:
        logger.warning(f"[zipnova_cotizar] CP={cp} ciudad={ciudad} provincia={provincia} total={total} bultos={json.dumps(bultos, default=str)}")
        resultados = zipnova_cotizar(bultos, cp, ciudad, provincia, total)
        logger.warning(f"[zipnova_cotizar] resultados: {json.dumps(resultados, default=str)}")
    except Exception as e:
        logger.error(f'Error Zipnova cotizar: {e}')
        return jsonify({'error': 'No se pudo obtener la cotización. Intentá de nuevo.'}), 502

    if not resultados:
        return jsonify({'error': 'No hay opciones de envío disponibles para ese código postal'}), 200

    # Filtrar solo entrega a domicilio (excluir retiro en sucursal)
    CODIGOS_DOMICILIO = {'standard_delivery', 'express_delivery', 'same_day', 'next_day'}
    resultados_domicilio = [
        r for r in resultados
        if (r.get('service_type') or {}).get('code', 'standard_delivery') in CODIGOS_DOMICILIO
        or isinstance(r.get('service_type'), str) and 'pickup' not in r.get('service_type', '').lower()
    ]
    if resultados_domicilio:
        resultados = resultados_domicilio

    # Opción más barata
    mejor = min(resultados, key=lambda r: float(r.get('amounts', {}).get('price_incl_tax', 999999)))
    precio = float(mejor.get('amounts', {}).get('price_incl_tax', 0)) + 10000
    dt     = mejor.get('delivery_time', {})
    if isinstance(dt, dict):
        dias = dt.get('max') or dt.get('min') or '?'
    else:
        dias = dt or '?'

    session['zipnova_quote'] = {
        'carrier_id':    int(mejor.get('carrier', {}).get('id') or mejor.get('carrier_id') or 0),
        'carrier_name':  mejor.get('carrier', {}).get('name', '') or str(mejor.get('carrier_id', '')),
        'service_type':  mejor.get('service_type', {}).get('code', '') if isinstance(mejor.get('service_type'), dict) else str(mejor.get('service_type', '')),
        'logistic_type': mejor.get('logistic_type', ''),
        'precio':        precio,
        'dias':          dias,
        'cp_destino':    cp,
        'ciudad':        ciudad,
        'provincia':     provincia,
        'bultos_count':  len(bultos),
    }

    # Sumar demora sin stock si aplica
    demora_dias = get_demora_sin_stock()
    carrito_items = session.get('carrito', [])
    hay_demora = False
    if demora_dias and carrito_items:
        db2 = get_db()
        cur2 = db2.cursor()
        for item in carrito_items:
            if _get_stock_real(cur2, item['sku']) <= 0:
                hay_demora = True
                break
        cur2.close()
        db2.close()

    dias_total = dias
    fecha_entrega_str = None
    if hay_demora and demora_dias:
        try:
            dias_envio = int(dias) if str(dias).isdigit() else 0
            dias_total = dias_envio + demora_dias
            from datetime import date, timedelta
            fecha_entrega_str = (date.today() + timedelta(days=dias_total)).strftime('%d/%m/%Y')
        except Exception:
            pass

    return jsonify({
        'precio':          precio,
        'precio_fmt':      '$ {:,.0f}'.format(precio).replace(',', '.'),
        'dias':            dias_total,
        'dias_envio':      dias,
        'demora_dias':     demora_dias if hay_demora else 0,
        'fecha_estimada':  fecha_entrega_str,
        'carrier':         session['zipnova_quote']['carrier_name'],
        'bultos':          len(bultos),
        'ok':              True,
    })


@tienda_bp.route('/datos-envio', methods=['GET'])
def datos_envio():
    """Pantalla de datos del cliente antes de ir a MP."""
    carrito = session.get('carrito', [])
    if not carrito:
        return redirect(url_for('tienda.ver_carrito'))
    carrito_count  = sum(i['cantidad'] for i in carrito)
    total          = sum(float(i['precio']) * i['cantidad'] for i in carrito)
    shipping_tipo, _ = get_shipping_info(carrito)
    zipnova_quote  = session.get('zipnova_quote')

    # Cupón aplicado en carrito: mantenerlo visible en datos-envio
    cupon = session.get('cupon')
    descuento_monto = 0
    if cupon:
        if cupon['tipo'] == 'pct':
            descuento_monto = round(total * float(cupon['valor']) / 100)
        else:
            descuento_monto = min(float(cupon['valor']), total)

    # Para zipnova: precargar localidades desde georef server-side
    localidades_precargadas = []
    if shipping_tipo == 'zipnova' and zipnova_quote and zipnova_quote.get('cp_destino'):
        try:
            resp = http_requests.get(
                'https://apis.datos.gob.ar/georef/api/localidades',
                params={'codigo_postal': zipnova_quote['cp_destino'], 'campos': 'nombre', 'max': 50},
                timeout=5,
            )
            data = resp.json()
            localidades_precargadas = sorted(set(
                l['nombre'] for l in data.get('localidades', []) if l.get('nombre')
            ))
        except Exception:
            pass

    demora_dias = get_demora_sin_stock()
    hay_demora = False
    fecha_disponible = None
    if demora_dias and carrito:
        db2 = get_db()
        cur2 = db2.cursor()
        for item in carrito:
            if _get_stock_real(cur2, item['sku']) <= 0:
                hay_demora = True
                break
        cur2.close()
        db2.close()
        if hay_demora:
            fecha_disponible = calcular_fecha_demora(demora_dias)

    return render_template('tienda/datos_envio.html',
        carrito                = carrito,
        carrito_count          = carrito_count,
        total                  = total,
        cupon                  = cupon,
        descuento_monto        = descuento_monto,
        shipping_tipo          = shipping_tipo,
        zipnova_quote          = zipnova_quote,
        localidades_precargadas = localidades_precargadas,
        forzar_retiro          = request.args.get('retiro') == '1',
        demora_dias            = demora_dias,
        hay_demora             = hay_demora,
        fecha_disponible       = fecha_disponible,
    )


def _validar_cuit(cuit):
    """Valida un CUIT/CUIL argentino: 11 dígitos + dígito verificador (módulo 11)."""
    c = ''.join(ch for ch in str(cuit or '') if ch.isdigit())
    if len(c) != 11:
        return False
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(c[i]) * mult[i] for i in range(10))
    dv = 11 - (suma % 11)
    if dv == 11:
        dv = 0
    if dv == 10:
        return False
    return dv == int(c[10])


def _factura_fields(cli):
    """(doc_type, doc_number, taxpayer_type) para las columnas factura_* de ventas.
    Factura A -> CUIT + Responsable Inscripto; Consumidor Final -> None (sin cambios)."""
    if (cli.get('tipo_factura') or '').upper() == 'A' and cli.get('cuit'):
        cuit_limpio = ''.join(ch for ch in str(cli.get('cuit')) if ch.isdigit())
        return ('CUIT', cuit_limpio, 'IVA Responsable Inscripto')
    return (None, None, None)


def _importe_total_venta(numero_venta):
    """Total numérico de una venta por numero_venta (para el evento purchase del dataLayer). 0 si no existe."""
    if not numero_venta:
        return 0
    try:
        _db = get_db(); _cur = _db.cursor()
        _cur.execute("SELECT importe_total FROM ventas WHERE numero_venta=%s LIMIT 1", (numero_venta,))
        _r = _cur.fetchone()
        _cur.close(); _db.close()
        return float(_r['importe_total'] or 0) if _r else 0
    except Exception:
        return 0


@tienda_bp.route('/checkout', methods=['POST'])
def checkout():
    carrito = session.get('carrito', [])
    if not carrito:
        return redirect(url_for('tienda.ver_carrito'))

    # ── Datos del cliente desde el formulario de datos-envio ─────────────────
    tipo_entrega = request.form.get('tipo_entrega', 'envio').strip()
    calle       = request.form.get('calle', '').strip()
    altura      = request.form.get('altura', '').strip()
    piso_depto  = request.form.get('piso_depto', '').strip()
    cp          = request.form.get('cp', '').strip()
    tipo_factura = request.form.get('tipo_factura', 'consumidor_final').strip().lower()
    cuit_form    = ''.join(ch for ch in request.form.get('cuit', '') if ch.isdigit())
    # Armar dirección completa con ciudad y provincia
    ciudad_form   = request.form.get('ciudad', '').strip()
    provincia_form = (request.form.get('provincia_hidden') or request.form.get('provincia', 'Capital Federal')).strip()
    if piso_depto:
        direccion_completa = f"{calle} {altura} {piso_depto}".strip()
    else:
        direccion_completa = f"{calle} {altura}".strip()
    if ciudad_form:
        direccion_completa += f", {ciudad_form}"
    if provincia_form:
        direccion_completa += f", {provincia_form}"
    if cp:
        direccion_completa += f" CP {cp}"

    cliente = {
        'nombre':       request.form.get('nombre', '').strip(),
        'telefono':     request.form.get('telefono', '').strip(),
        'dni':          request.form.get('dni', '').strip(),
        'email':        request.form.get('email', '').strip(),
        'calle':        calle,
        'altura':       altura,
        'piso_depto':   piso_depto,
        'direccion':    direccion_completa,
        'cp':           cp,
        'ciudad':       request.form.get('ciudad', '').strip(),
        'provincia':    request.form.get('provincia_hidden') or request.form.get('provincia', 'Capital Federal').strip(),
        'tipo_entrega': tipo_entrega,
        'tipo_factura': 'A' if tipo_factura == 'factura_a' else 'CF',
        'cuit':         cuit_form if tipo_factura == 'factura_a' else '',
    }
    if not cliente['nombre'] or not cliente['telefono']:
        return redirect(url_for('tienda.datos_envio'))
    # Factura A requiere CUIT válido (dígito verificador, módulo 11)
    if tipo_factura == 'factura_a' and not _validar_cuit(cuit_form):
        return redirect(url_for('tienda.datos_envio'))

    session['cliente_checkout'] = cliente

    # Guardar cupón en cliente para que el webhook lo pueda registrar
    cupon = session.get('cupon')
    if cupon:
        cliente['cupon'] = cupon

    # Guardar demora si aplica (para notificar en el webhook)
    # Aplica si el stock disponible es menor a la cantidad pedida (incluye stock=0 y stock parcial)
    _demora_dias = get_demora_sin_stock()
    if _demora_dias and carrito:
        _db_dem = get_db()
        _cur_dem = _db_dem.cursor()
        for _item in carrito:
            if _get_stock_real(_cur_dem, _item['sku']) < _item['cantidad']:
                cliente['demora_dias'] = _demora_dias
                cliente['fecha_disponible'] = calcular_fecha_demora(_demora_dias)
                break
        _cur_dem.close()
        _db_dem.close()

    sdk      = get_mp_sdk()
    base_url = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')

    # ── Señales del navegador para Meta CAPI (las usa webhook_mp al disparar) ──
    try:
        cliente['_fbp'] = request.cookies.get('_fbp')
        cliente['_fbc'] = request.cookies.get('_fbc')
        cliente['_capi_ip'] = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        cliente['_capi_ua'] = request.headers.get('User-Agent')
        # Origen de tráfico (cookies del landing) — JSON limpio para persistir en la venta
        _of = request.cookies.get('mm_origen_first'); _ol = request.cookies.get('mm_origen_last')
        cliente['_origen_first'] = urllib.parse.unquote(_of) if _of else None
        cliente['_origen_last']  = urllib.parse.unquote(_ol) if _ol else None
    except Exception:
        pass

    # ── Guardar pedido pendiente en DB con ID corto ──────────────────────────
    pedido_ref = str(uuid.uuid4())[:16].replace('-', '')  # ID corto único
    db_tmp = get_db()
    cur_tmp = db_tmp.cursor()
    try:
        cur_tmp.execute("""
            CREATE TABLE IF NOT EXISTS pedidos_pendientes (
                ref         VARCHAR(32) PRIMARY KEY,
                carrito_json TEXT NOT NULL,
                cliente_json TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur_tmp.execute(
            "INSERT INTO pedidos_pendientes (ref, carrito_json, cliente_json) VALUES (%s, %s, %s)",
            (pedido_ref,
             json.dumps(carrito, ensure_ascii=False),
             json.dumps(cliente, ensure_ascii=False))
        )
        db_tmp.commit()
    finally:
        cur_tmp.close()
        db_tmp.close()

    # ── Items para MP con category_id y description ───────────────────────────
    cupon = session.get('cupon')
    subtotal_carrito = sum(float(i['precio']) * int(i['cantidad']) for i in carrito)
    if cupon:
        if cupon['tipo'] == 'pct':
            factor_cupon = 1 - cupon['valor'] / 100
        else:
            descuento_fijo = min(cupon['valor'], subtotal_carrito)
            factor_cupon = (subtotal_carrito - descuento_fijo) / subtotal_carrito if subtotal_carrito else 1
    else:
        factor_cupon = 1

    items_mp = []
    for item in carrito:
        precio_ajustado = round(float(item['precio']) * factor_cupon)
        items_mp.append({
            'id':          item['sku'],
            'title':       item['nombre'],
            'description': item['nombre'],
            'category_id': 'HOME_APPLIANCES',
            'quantity':    item['cantidad'],
            'unit_price':  max(1.0, float(precio_ajustado)),
            'currency_id': 'ARS',
        })

    shipping_tipo, _ = get_shipping_info(carrito)
    flag_unificado_ckt = _shipping_unificado()

    # ── Defensa upstream: flag activo + envío sin cotización Zipnova ─────────
    # Sin zipnova_quote la venta entraría con costo_flete=0. Los endpoints de
    # pago ya validan esto, pero acá redirigimos a datos-envio para mejor UX.
    if flag_unificado_ckt and tipo_entrega == 'envio' and not session.get('zipnova_quote'):
        return redirect(url_for('tienda.datos_envio'))

    shipments      = None
    dimensions_str = calculate_package_dimensions(carrito)
    # Con flag activo, get_shipping_info nunca devuelve 'me2_paid'/'me2_free',
    # así que este bloque queda inactivo. Lo dejamos para flag='0' (rollback).
    if tipo_entrega == 'envio' and shipping_tipo in ('me2_paid', 'me2_free') and dimensions_str:
        shipments = {
            'mode':          'me2',
            'free_shipping': shipping_tipo == 'me2_free',
            'dimensions':    dimensions_str,
            'receiver_address': {
                'zip_code':    cliente['cp'] or '1407',
                'street_name': cliente['calle'] or '',
                'street_number': str(cliente['altura'] or ''),
                'city_name':   cliente.get('ciudad', '') or '',
                'state_name':  cliente.get('provincia', '') or '',
                'floor':       cliente.get('piso', '') or '',
            },
        }
    elif tipo_entrega == 'envio' and shipping_tipo in ('me2_paid', 'me2_free'):
        logger.warning(f"ME2 sin dimensions para carrito: {carrito}")

    # ── Zipnova: agregar flete como ítem en MP ────────────────────────────────
    zipnova_quote = session.get('zipnova_quote') if tipo_entrega == 'envio' and shipping_tipo == 'zipnova' else None
    if zipnova_quote:
        precio_flete = float(zipnova_quote.get('precio', 0))
        if precio_flete > 0:
            items_mp.append({
                'id':          'FLETE_ZIPNOVA',
                'title':       'Envío a domicilio',
                'description': f"Envío a CP {zipnova_quote.get('cp_destino', '')}",
                'category_id': 'SERVICES',
                'quantity':    1,
                'unit_price':  precio_flete,
                'currency_id': 'ARS',
            })
        # Guardar quote en cliente para usarlo en el webhook
        cliente['zipnova_quote'] = zipnova_quote
        # Actualizar pedido_pendiente con cliente actualizado (tiene el quote)
        db_upd = get_db()
        cur_upd = db_upd.cursor()
        try:
            cur_upd.execute(
                "UPDATE pedidos_pendientes SET cliente_json = %s WHERE ref = %s",
                (json.dumps(cliente, ensure_ascii=False), pedido_ref)
            )
            db_upd.commit()
        finally:
            cur_upd.close()
            db_upd.close()

    payer_data = {
        'name':  cliente['nombre'],
        'phone': {'number': cliente['telefono']},
    }
    if cliente['email']:
        payer_data['email'] = cliente['email']
    if cliente['dni']:
        payer_data['identification'] = {'type': 'DNI', 'number': cliente['dni']}
    if cliente['calle'] and tipo_entrega == 'envio':
        payer_data['address'] = {
            'street_name':   cliente['calle'],
            'street_number': cliente['altura'],
            'zip_code':      cliente['cp'],
        }

    preference_data = {
        'items': items_mp,
        'back_urls': {
            'success': f"{base_url}/tienda/pago/exito",
            'failure': f"{base_url}/tienda/pago/error",
            'pending': f"{base_url}/tienda/pago/pendiente",
        },
        'auto_return': 'approved',
        'notification_url': f"{base_url}/tienda/webhook/mp",
        'statement_descriptor': 'MERCADOMUEBLES',
        'external_reference': pedido_ref,
        'payer': payer_data,
        # MP limitado a 1 cuota: con "cuotas sin interés" activo a nivel cuenta,
        # ofrecer >1 cuota le cobraría el costo de financiación al vendedor.
        'payment_methods': {'installments': 1},
    }

    if shipments:
        preference_data['shipments'] = shipments
    else:
        # wallet_purchase solo cuando no hay envío ME2 (incompatible con shipments)
        preference_data['purpose'] = 'wallet_purchase'

    logger.info(f"[checkout] preference_data: {json.dumps(preference_data, ensure_ascii=False, default=str)}")
    result     = sdk.preference().create(preference_data)
    preference = result.get('response', {})
    logger.info(f"[checkout] MP response: {json.dumps(preference, ensure_ascii=False, default=str)[:500]}")

    # Si ME2 no está activo (ej: credenciales de prueba), reintentar sin shipments
    if 'id' not in preference:
        err = result.get('response', {}).get('error', '')
        if 'me2' in result.get('response', {}).get('message', '').lower() or err == 'invalid_shipments':
            logger.warning("ME2 no disponible, reintentando sin shipments (modo prueba)")
            preference_data.pop('shipments', None)
            result     = sdk.preference().create(preference_data)
            preference = result.get('response', {})

    if 'id' not in preference:
        logger.error(f"Error creando preferencia MP: {result}")
        return redirect(url_for('tienda.ver_carrito'))

    session['mp_preference_id'] = preference['id']
    session['pedido_ref_bricks'] = pedido_ref  # usado por /pago/ejecutar

    # ── Feature flag: Bricks (embebido) vs Checkout Pro (redirect) ───────────
    checkout_v = 'pro'
    try:
        _db_cv  = get_db()
        _cur_cv = _db_cv.cursor()
        _cur_cv.execute("SELECT valor FROM configuracion WHERE clave = 'checkout_version'")
        _row_cv = _cur_cv.fetchone()
        if _row_cv:
            checkout_v = _row_cv['valor']
        _cur_cv.close()
        _db_cv.close()
    except Exception:
        pass  # Si falla la lectura, cae al comportamiento actual

    if checkout_v == 'bricks':
        total_a_pagar    = sum(float(i['unit_price']) * int(i['quantity']) for i in items_mp)
        coef_3, coef_6   = get_coeficientes_cuotas()
        total_pw_3       = round(total_a_pagar * coef_3)
        total_pw_6       = round(total_a_pagar * coef_6)
        payway_api_url = os.getenv('PAYWAY_API_URL', 'https://live.decidir.com/api/v2')
        # SDK JS de Payway: sandbox usa developers.decidir.com, prod usa live.decidir.com
        payway_sdk_url = 'https://developers.decidir.com/static/v2.6.4/decidir.js' \
                         if 'developers' in payway_api_url \
                         else 'https://live.decidir.com/static/v2.6.4/decidir.js'

        # Feature flag GetNet (default off). Asegura la fila en configuracion.
        getnet_enabled = False
        try:
            _db_gn  = get_db()
            _cur_gn = _db_gn.cursor()
            _cur_gn.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('getnet_enabled', '0')")
            _db_gn.commit()
            _cur_gn.execute("SELECT valor FROM configuracion WHERE clave = 'getnet_enabled'")
            _row_gn = _cur_gn.fetchone()
            getnet_enabled = bool(_row_gn and _row_gn['valor'] == '1')
            _cur_gn.close()
            _db_gn.close()
        except Exception:
            pass  # si falla la lectura, queda la card oculta

        # Feature flag Payway 6 cuotas (default off). Asegura la fila en configuracion.
        payway_6_enabled = False
        try:
            _db_p6  = get_db()
            _cur_p6 = _db_p6.cursor()
            _cur_p6.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('payway_6_enabled', '0')")
            _db_p6.commit()
            _cur_p6.execute("SELECT valor FROM configuracion WHERE clave = 'payway_6_enabled'")
            _row_p6 = _cur_p6.fetchone()
            payway_6_enabled = bool(_row_p6 and _row_p6['valor'] == '1')
            _cur_p6.close()
            _db_p6.close()
        except Exception:
            pass  # si falla la lectura, queda la card oculta

        # Feature flag Payway 3 cuotas (default ON: siempre se mostró).
        payway_enabled = True
        try:
            _db_pw  = get_db()
            _cur_pw = _db_pw.cursor()
            _cur_pw.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('payway_enabled', '1')")
            _db_pw.commit()
            _cur_pw.execute("SELECT valor FROM configuracion WHERE clave = 'payway_enabled'")
            _row_pw = _cur_pw.fetchone()
            payway_enabled = bool(_row_pw and _row_pw['valor'] == '1')
            _cur_pw.close()
            _db_pw.close()
        except Exception:
            payway_enabled = True  # ante error, mostrar (comportamiento actual)

        # ── MP 12 cuotas (recargo) — flag + coeficiente + preference para mobile ──
        mp_12_enabled = False
        try:
            _db_m12  = get_db()
            _cur_m12 = _db_m12.cursor()
            _cur_m12.execute("INSERT IGNORE INTO configuracion (clave, valor) VALUES ('mp_12_enabled', '0')")
            _db_m12.commit()
            _cur_m12.execute("SELECT valor FROM configuracion WHERE clave = 'mp_12_enabled'")
            _row_m12 = _cur_m12.fetchone()
            mp_12_enabled = bool(_row_m12 and _row_m12['valor'] == '1')
            _cur_m12.execute("SELECT valor FROM configuracion WHERE clave = 'cuotas_12_coef'")
            _row_c12 = _cur_m12.fetchone()
            _cur_m12.close()
            _db_m12.close()
        except Exception:
            _row_c12 = None
        coef_12  = float(_row_c12['valor']) if _row_c12 and _row_c12['valor'] else 1.6
        total_12 = round(total_a_pagar * coef_12)
        session['total_mp12'] = total_12  # monto autoritativo para /pago/ejecutar-12

        # Preference dedicada de 12 cuotas (solo si está activo) — para redirect mobile
        preference_id_12 = None
        init_point_12    = None
        if mp_12_enabled:
            pref_12 = {
                'items': [{
                    'title':       'Compra en 12 cuotas',
                    'quantity':    1,
                    'unit_price':  float(total_12),
                    'currency_id': 'ARS',
                }],
                'back_urls': {
                    'success': f"{base_url}/tienda/pago/exito",
                    'failure': f"{base_url}/tienda/pago/error",
                    'pending': f"{base_url}/tienda/pago/pendiente",
                },
                'auto_return':          'approved',
                'notification_url':     f"{base_url}/tienda/webhook/mp",
                'statement_descriptor': 'MERCADOMUEBLES',
                'external_reference':   pedido_ref,
                'payer':                payer_data,
                'payment_methods': {
                    'installments':         12,
                    'default_installments': 12,
                    'excluded_payment_types': [
                        {'id': 'ticket'}, {'id': 'atm'}, {'id': 'debit_card'},
                        {'id': 'bank_transfer'}, {'id': 'prepaid_card'},
                    ],
                    'excluded_payment_methods': [
                        {'id': 'amex'}, {'id': 'naranja'}, {'id': 'cabal'}, {'id': 'maestro'},
                        {'id': 'cencosud'}, {'id': 'cordobesa'}, {'id': 'argencard'},
                        {'id': 'diners'}, {'id': 'tarshop'}, {'id': 'cmr'},
                    ],
                },
            }
            try:
                _res_12  = sdk.preference().create(pref_12)
                _pref_12 = _res_12.get('response', {}) or {}
                preference_id_12 = _pref_12.get('id')
                init_point_12    = _pref_12.get('init_point')
            except Exception as _e12:
                logger.warning(f"[checkout] no se pudo crear preference 12 cuotas: {_e12}")

        return render_template(
            'tienda/checkout_bricks.html',
            preference_id    = preference['id'],
            mp_init_point    = preference['init_point'],
            mp_public_key    = os.getenv('MP_PUBLIC_KEY', ''),
            payway_public_key= os.getenv('PAYWAY_PUBLIC_KEY', ''),
            payway_api_url   = payway_api_url,
            payway_sdk_url   = payway_sdk_url,
            items            = items_mp,
            cliente          = cliente,
            total            = total_a_pagar,
            cuota_3_fmt      = format_price(total_pw_3 / 3),
            cuota_6_fmt      = format_price(total_pw_6 / 6),
            total_3_fmt      = format_price(total_pw_3),
            total_6_fmt      = format_price(total_pw_6),
            total_pw_3       = total_pw_3,
            total_pw_6       = total_pw_6,
            getnet_enabled   = getnet_enabled,
            payway_6_enabled = payway_6_enabled,
            payway_enabled   = payway_enabled,
            mp_12_enabled    = mp_12_enabled,
            total_12         = total_12,
            cuota_12_fmt     = format_price(total_12 / 12),
            total_12_fmt     = format_price(total_12),
            preference_id_12 = preference_id_12,
            init_point_12    = init_point_12,
        )

    return redirect(preference['init_point'])


@tienda_bp.route('/pago/ejecutar', methods=['POST'])
def pago_ejecutar():
    """
    Endpoint para Checkout Bricks (Opción A).
    Recibe formData del onSubmit del Brick, llama a la API de MP y devuelve
    la URL a la que debe redirigir el frontend.
    El webhook /webhook/mp sigue siendo el que registra la venta en DB.
    """
    data = request.get_json() or {}

    sdk      = get_mp_sdk()
    base_url = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')

    # external_reference para que el webhook encuentre el pedido_pendiente
    pedido_ref = session.get('pedido_ref_bricks', '')

    # ── Defensa: no permitir cobrar si falta la cotización de envío ──────────
    # Sin zipnova_quote la venta entraría con metodo_envio=None (panel la
    # mostraría como "Retiro") y costo_flete=0 (cliente no paga el envío).
    if pedido_ref:
        _db_chk  = get_db()
        _cur_chk = _db_chk.cursor()
        _cur_chk.execute(
            "SELECT cliente_json FROM pedidos_pendientes WHERE ref = %s",
            (pedido_ref,)
        )
        _row_chk = _cur_chk.fetchone()
        _cur_chk.close()
        _db_chk.close()
        if _row_chk:
            _cli_chk = json.loads(_row_chk['cliente_json'])
            if _cli_chk.get('tipo_entrega', 'envio') == 'envio' and not _cli_chk.get('zipnova_quote'):
                return jsonify({
                    'ok': False,
                    'error': 'No se encontró la cotización de envío. Volvé al paso '
                             'de datos y cotizá el envío antes de pagar.',
                    'redirect': '/datos-envio'
                }), 400

    payment_data = {
        'transaction_amount': float(data.get('transaction_amount', 0)),
        'payment_method_id':  data.get('payment_method_id', ''),
        # Candado server-side: MP siempre 1 cuota (protege contra requests
        # armadas que pidan >1 y disparen el costo de cuotas sin interés).
        'installments':       1,
        'payer':              data.get('payer', {}),
        'external_reference': pedido_ref,
        'notification_url':   f"{base_url}/tienda/webhook/mp",
        'statement_descriptor': 'MERCADOMUEBLES',
    }

    # Token solo para pagos con tarjeta (no para efectivo/QR)
    if data.get('token'):
        payment_data['token'] = data['token']
    if data.get('issuer_id'):
        payment_data['issuer_id'] = data['issuer_id']

    try:
        result     = sdk.payment().create(payment_data)
        http_code  = result.get('status')
        payment    = result.get('response', {}) or {}
        status     = payment.get('status', 'error')
        pid        = payment.get('id', '')

        logger.info(f"[pago_ejecutar] http={http_code} status={status} payment_id={pid} ref={pedido_ref} pmid={payment_data.get('payment_method_id')}")

        if status == 'approved':
            session.pop('carrito', None)
            session.pop('mp_preference_id', None)
            session.pop('pedido_ref_bricks', None)
            return jsonify({
                'status':       'approved',
                'redirect_url': f"{base_url}/tienda/pago/exito?payment_id={pid}&status=approved",
            })
        elif status in ('in_process', 'pending', 'authorized'):
            return jsonify({
                'status':       'pending',
                'redirect_url': f"{base_url}/tienda/pago/pendiente?payment_id={pid}&status={status}",
            })
        else:
            detail = payment.get('status_detail', '')
            # Log ampliado para diagnosticar rechazos de MP (especialmente 400 Bad Request)
            safe_payload = {k: v for k, v in payment_data.items() if k not in ('token',)}
            logger.warning(
                f"[pago_ejecutar] Pago no aprobado: http={http_code} status={status} detail={detail} pid={pid} "
                f"mp_response={json.dumps(payment, ensure_ascii=False, default=str)[:1500]} "
                f"payload={json.dumps(safe_payload, ensure_ascii=False, default=str)[:1000]}"
            )
            return jsonify({
                'status':       status,
                'redirect_url': f"{base_url}/tienda/pago/error",
            }), 400

    except Exception as e:
        safe_payload = {k: v for k, v in payment_data.items() if k not in ('token',)}
        logger.error(f"[pago_ejecutar] Excepcion: {e} payload={json.dumps(safe_payload, ensure_ascii=False, default=str)[:1000]}", exc_info=True)
        return jsonify({
            'status':       'error',
            'redirect_url': f"{base_url}/tienda/pago/error",
        }), 500


@tienda_bp.route('/pago/ejecutar-12', methods=['POST'])
def pago_ejecutar_12():
    """Checkout Bricks — pago MP en 12 cuotas (con recargo). El monto y las
    cuotas son autoritativos del server. Registra por el webhook /webhook/mp."""
    data       = request.get_json() or {}
    sdk        = get_mp_sdk()
    base_url   = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')
    pedido_ref = session.get('pedido_ref_bricks', '')
    total_12   = float(session.get('total_mp12', 0) or 0)

    if total_12 <= 0:
        return jsonify({'ok': False,
                        'error': 'Sesión sin total; volvé a iniciar el checkout.',
                        'redirect': '/carrito'}), 400

    # Defensa: no cobrar si falta la cotización de envío (igual que pago_ejecutar)
    if pedido_ref:
        _db_chk  = get_db()
        _cur_chk = _db_chk.cursor()
        _cur_chk.execute("SELECT cliente_json FROM pedidos_pendientes WHERE ref = %s", (pedido_ref,))
        _row_chk = _cur_chk.fetchone()
        _cur_chk.close()
        _db_chk.close()
        if _row_chk:
            _cli_chk = json.loads(_row_chk['cliente_json'])
            if _cli_chk.get('tipo_entrega', 'envio') == 'envio' and not _cli_chk.get('zipnova_quote'):
                return jsonify({'ok': False,
                    'error': 'No se encontró la cotización de envío. Volvé al paso de datos y cotizá el envío antes de pagar.',
                    'redirect': '/datos-envio'}), 400

    payment_data = {
        'transaction_amount':   total_12,    # autoritativo del server (con recargo)
        'payment_method_id':    data.get('payment_method_id', ''),
        'installments':         12,          # forzado
        'payer':                data.get('payer', {}),
        'external_reference':   pedido_ref,
        'notification_url':     f"{base_url}/tienda/webhook/mp",
        'statement_descriptor': 'MERCADOMUEBLES',
    }
    if data.get('token'):
        payment_data['token'] = data['token']
    if data.get('issuer_id'):
        payment_data['issuer_id'] = data['issuer_id']

    try:
        result    = sdk.payment().create(payment_data)
        http_code = result.get('status')
        payment   = result.get('response', {}) or {}
        status    = payment.get('status', 'error')
        pid       = payment.get('id', '')
        logger.info(f"[pago_ejecutar_12] http={http_code} status={status} pid={pid} ref={pedido_ref} monto={total_12}")

        if status == 'approved':
            session.pop('carrito', None)
            session.pop('mp_preference_id', None)
            session.pop('pedido_ref_bricks', None)
            session.pop('total_mp12', None)
            return jsonify({
                'status':       'approved',
                'redirect_url': f"{base_url}/tienda/pago/exito?payment_id={pid}&status=approved",
            })
        elif status in ('in_process', 'pending', 'authorized'):
            return jsonify({
                'status':       'pending',
                'redirect_url': f"{base_url}/tienda/pago/pendiente?payment_id={pid}&status={status}",
            })
        else:
            detail = payment.get('status_detail', '')
            safe_payload = {k: v for k, v in payment_data.items() if k not in ('token',)}
            logger.warning(
                f"[pago_ejecutar_12] no aprobado: http={http_code} status={status} detail={detail} pid={pid} "
                f"mp_response={json.dumps(payment, ensure_ascii=False, default=str)[:1500]} "
                f"payload={json.dumps(safe_payload, ensure_ascii=False, default=str)[:1000]}"
            )
            return jsonify({'status': status, 'redirect_url': f"{base_url}/tienda/pago/error"}), 400
    except Exception as e:
        safe_payload = {k: v for k, v in payment_data.items() if k not in ('token',)}
        logger.error(f"[pago_ejecutar_12] Excepcion: {e} payload={json.dumps(safe_payload, ensure_ascii=False, default=str)[:1000]}", exc_info=True)
        return jsonify({'status': 'error', 'redirect_url': f"{base_url}/tienda/pago/error"}), 500


# ── GATE ANTIFRAUDE PROPIO (blocklist + velocidad) ─────────────────────────────
# Chequeos previos al cobro en Payway y a la creación del intent en GetNet.
# FAIL-OPEN: cualquier excepción en el gate deja pasar el pago (nunca puede
# bloquear una venta legítima por un error técnico). Se gestiona desde
# /intentos-pago (solapa Blocklist) en el sistema.

def _fraude_norm(s):
    """Normaliza para comparar: minúsculas, sin tildes, espacios colapsados."""
    import unicodedata
    s = str(s or '').strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return ' '.join(s.split())


# ── Meta Conversions API (CAPI) ───────────────────────────────────────────
META_DATASET_ID = '5994867780529728'
META_GRAPH_VER  = 'v25.0'

def _capi_sha256(v):
    if not v:
        return None
    return hashlib.sha256(str(v).strip().lower().encode('utf-8')).hexdigest()

def _capi_phone(tel):
    if not tel:
        return None
    d = ''.join(ch for ch in str(tel) if ch.isdigit())
    if not d:
        return None
    if not d.startswith('54'):
        d = '54' + d
    return hashlib.sha256(d.encode('utf-8')).hexdigest()

def enviar_capi_purchase(*, numero_venta, email='', telefono='', nombre='',
                         dni='', ciudad='', provincia='', cp='', total=0,
                         items=None, client_ip=None, user_agent=None,
                         fbp=None, fbc=None, source_url=None):
    """Envía Purchase a la Meta CAPI. No bloquea ni lanza: corre en thread daemon."""
    token = os.getenv('CAPI', '')
    if not token:
        return
    test_code = os.getenv('CAPI_TEST_CODE', '')
    items = items or []
    fn = ln = None
    if nombre:
        partes = str(nombre).strip().split()
        if partes:
            fn = _capi_sha256(partes[0])
            if len(partes) > 1:
                ln = _capi_sha256(' '.join(partes[1:]))
    user_data = {}
    if email:     user_data['em'] = [_capi_sha256(email)]
    ph = _capi_phone(telefono)
    if ph:        user_data['ph'] = [ph]
    if fn:        user_data['fn'] = [fn]
    if ln:        user_data['ln'] = [ln]
    if ciudad:    user_data['ct'] = [_capi_sha256(ciudad)]
    if provincia: user_data['st'] = [_capi_sha256(provincia)]
    if cp:        user_data['zp'] = [_capi_sha256(cp)]
    user_data['country'] = [_capi_sha256('ar')]
    ext = email or dni
    if ext:        user_data['external_id'] = [_capi_sha256(ext)]
    if client_ip:  user_data['client_ip_address'] = client_ip
    if user_agent: user_data['client_user_agent'] = user_agent
    if fbp:        user_data['fbp'] = fbp
    if fbc:        user_data['fbc'] = fbc

    contents, content_ids, num_items = [], [], 0
    for it in items:
        sku = it.get('sku') or it.get('item_id')
        qty = int(it.get('cantidad') or it.get('quantity') or 1)
        pr  = float(it.get('precio') or it.get('price') or 0)
        if sku:
            contents.append({'id': sku, 'quantity': qty, 'item_price': pr})
            content_ids.append(sku)
            num_items += qty

    custom_data = {'currency': 'ARS', 'value': float(total or 0),
                   'content_type': 'product', 'order_id': numero_venta}
    if contents:
        custom_data['contents'] = contents
        custom_data['content_ids'] = content_ids
        custom_data['num_items'] = num_items

    event = {'event_name': 'Purchase', 'event_time': int(time.time()),
             'event_id': numero_venta, 'action_source': 'website',
             'user_data': user_data, 'custom_data': custom_data}
    if source_url:
        event['event_source_url'] = source_url

    payload = {'data': [event]}
    if test_code:
        payload['test_event_code'] = test_code

    url = (f'https://graph.facebook.com/{META_GRAPH_VER}/'
           f'{META_DATASET_ID}/events?access_token={token}')

    def _post():
        try:
            r = http_requests.post(url, json=payload, timeout=6)
            if r.status_code != 200:
                print(f"[CAPI] {numero_venta} status={r.status_code} {r.text[:300]}")
            else:
                print(f"[CAPI] {numero_venta} OK")
        except Exception as e:
            print(f"[CAPI] {numero_venta} ERROR {e}")

    threading.Thread(target=_post, daemon=True).start()


_FRAUDE_VELOCIDAD_ACTIVA = True  # kill-switch de las reglas de velocidad (blocklist siempre activa)


def _fraude_gate(cli, bin_num='', last4=''):
    """Devuelve (bloqueado, motivo). Reglas:
    1) blocklist (direccion/dni/email/telefono/nombre/tarjeta)
    2) velocidad por tarjeta: bin+last4 con >=2 rechazos en 24h
    3) velocidad por datos de envío: misma direccion/email/dni con >=3 rechazos en 48h
    El caller debe envolver la llamada en try/except (fail-open)."""
    db  = get_db()
    cur = db.cursor()
    try:
        nd = {
            'direccion': _fraude_norm(cli.get('direccion')),
            'dni':       _fraude_norm(cli.get('dni')),
            'email':     _fraude_norm(cli.get('email')),
            'telefono':  _fraude_norm(cli.get('telefono')),
            'nombre':    _fraude_norm(cli.get('nombre')),
        }

        # 1) Blocklist (entradas lista='block')
        cur.execute("SELECT tipo, valor FROM fraude_blocklist WHERE activo = 1 AND lista = 'block'")
        for e in cur.fetchall():
            t, v = e['tipo'], _fraude_norm(e['valor'])
            if not v:
                continue
            if t == 'tarjeta':
                if last4 and v in (str(last4), f"{bin_num}{last4}"):
                    return True, 'blocklist:tarjeta'
            elif t in ('direccion', 'nombre'):
                if nd.get(t) and v in nd[t]:
                    return True, f'blocklist:{t}'
            else:
                if nd.get(t) and v == nd[t]:
                    return True, f'blocklist:{t}'

        # Kill-switch de las reglas de velocidad (la blocklist sigue activa arriba).
        if not _FRAUDE_VELOCIDAD_ACTIVA:
            return False, ''

        # Whitelist (lista='allow'): exime de las reglas de velocidad por
        # email/dni/telefono/direccion. La blocklist de arriba no se ve afectada.
        cur.execute("SELECT tipo, valor FROM fraude_blocklist WHERE activo = 1 AND lista = 'allow'")
        for e in cur.fetchall():
            t, v = e['tipo'], _fraude_norm(e['valor'])
            if not v:
                continue
            if t == 'direccion':
                if nd.get('direccion') and v in nd['direccion']:
                    return False, ''
            elif t in ('dni', 'email', 'telefono'):
                if nd.get(t) and v == nd[t]:
                    return False, ''

        # 2) Velocidad por tarjeta (necesita bin Y last4 para evitar falsos positivos)
        if bin_num and last4:
            cur.execute("""SELECT COUNT(*) AS c FROM payway_intentos
                           WHERE bin = %s AND last4 = %s AND status = 'rejected'
                             AND fecha > DATE_SUB(NOW(), INTERVAL 24 HOUR)""",
                        (str(bin_num), str(last4)))
            r = cur.fetchone()
            if r and int(r['c'] or 0) >= 2:
                return True, 'velocidad_tarjeta'

        # 3) Velocidad por datos de envío (cruza rechazos recientes con pedidos)
        cur.execute("""SELECT ref FROM payway_intentos
                       WHERE status = 'rejected' AND ref IS NOT NULL AND ref != ''
                         AND fecha > DATE_SUB(NOW(), INTERVAL 48 HOUR)""")
        refs = [r['ref'] for r in cur.fetchall()]
        if refs:
            fmt = ','.join(['%s'] * len(refs))
            cur.execute(f"SELECT cliente_json FROM pedidos_pendientes WHERE ref IN ({fmt})", refs)
            hits = 0
            for row in cur.fetchall():
                try:
                    c2 = json.loads(row['cliente_json'])
                except Exception:
                    continue
                if ((nd['direccion'] and _fraude_norm(c2.get('direccion')) == nd['direccion'])
                        or (nd['email'] and _fraude_norm(c2.get('email')) == nd['email'])
                        or (nd['dni'] and _fraude_norm(c2.get('dni')) == nd['dni'])):
                    hits += 1
            if hits >= 3:
                return True, 'velocidad_envio'

        return False, ''
    finally:
        cur.close()
        db.close()


def _fraude_registrar_bloqueo(cli, motivo, bin_num='', last4='', ref=''):
    """Registra un bloqueo del gate en fraude_bloqueos (para verlo en /intentos-pago).
    Fail-silent: nunca debe afectar el flujo de pago."""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO fraude_bloqueos (motivo, dni, email, telefono, direccion, bin, last4, ref) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (motivo, cli.get('dni'), cli.get('email'), cli.get('telefono'),
             cli.get('direccion'), bin_num or None, last4 or None, ref or None))
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        logger.warning(f"[FRAUDE] no se pudo registrar bloqueo: {e}")


@tienda_bp.route('/pago/payway/token', methods=['POST'])
def payway_token():
    """
    Proxy de tokenizacion para Payway.
    El browser no puede llamar directamente a Payway por CORS,
    entonces el JS llama a este endpoint y este lo retransmite server-to-server.
    """
    import requests as req_lib
    data = request.get_json() or {}
    payway_api_url    = os.getenv('PAYWAY_API_URL', 'https://live.decidir.com/api/v2')
    payway_public_key = os.getenv('PAYWAY_PUBLIC_KEY', '')
    # Device fingerprint en la tokenización (CyberSource retail asocia el device acá):
    # el frontend manda fraud_detection.device_unique_identifier; sumamos la IP real.
    try:
        ip_tok = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        if ip_tok:
            data.setdefault('ip_address', ip_tok)
    except Exception:
        pass
    try:
        resp = req_lib.post(
            f"{payway_api_url}/tokens",
            json=data,
            headers={
                'apikey':       payway_public_key,
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache',
            },
            timeout=15
        )
        tok_data = resp.json()
        # Guardar bin/last4 en sesión para el gate antifraude (no es PAN completo)
        try:
            if resp.status_code in (200, 201):
                session['pw_bin']   = str(tok_data.get('bin') or '')
                session['pw_last4'] = str(tok_data.get('last_four_digits') or '')
        except Exception:
            pass
        return jsonify(tok_data), resp.status_code
    except Exception as e:
        logger.error(f"[payway_token] Error: {e}")
        return jsonify({'error_type': 'proxy_error', 'message': str(e)}), 500


@tienda_bp.route('/pago/payway', methods=['POST'])
def pago_payway():
    """
    Recibe token de Payway JS SDK + cuotas elegidas.
    Ejecuta el pago contra la API de Payway, registra la venta y devuelve redirect_url.
    No hay webhook de Payway: el registro ocurre aquí de forma síncrona.
    """
    import requests as req_lib

    data                  = request.get_json() or {}
    token                 = data.get('token', '')
    payment_method_id     = int(data.get('payment_method_id', 1))
    bin_numero            = data.get('bin', '')
    installments          = int(data.get('installments', 3))
    device_fingerprint_id = data.get('device_fingerprint_id', '')

    pedido_ref = session.get('pedido_ref_bricks', '')
    if not token or not pedido_ref:
        return jsonify({'status': 'error', 'msg': 'Datos incompletos'}), 400

    # ── Recuperar carrito y cliente ───────────────────────────────────────────
    db  = get_db()
    cur = db.cursor()
    cur.execute("SELECT carrito_json, cliente_json FROM pedidos_pendientes WHERE ref = %s", (pedido_ref,))
    row = cur.fetchone()
    cur.close()
    if not row:
        db.close()
        return jsonify({'status': 'error', 'msg': 'Pedido no encontrado'}), 400

    cart_items = json.loads(row['carrito_json'])
    cli        = json.loads(row['cliente_json'])

    # ── Defensa: no permitir cobrar si falta la cotización de envío ──────────
    # Sin zipnova_quote la venta entraría con metodo_envio=None (panel la
    # mostraría como "Retiro") y costo_flete=0 (cliente no paga el envío).
    if cli.get('tipo_entrega', 'envio') == 'envio' and not cli.get('zipnova_quote'):
        db.close()
        return jsonify({
            'ok': False,
            'error': 'No se encontró la cotización de envío. Volvé al paso '
                     'de datos y cotizá el envío antes de pagar.',
            'redirect': '/datos-envio'
        }), 400

    # ── Gate antifraude propio (blocklist + velocidad) — FAIL-OPEN ───────────
    try:
        _blk, _blk_motivo = _fraude_gate(cli, bin_numero, session.get('pw_last4', ''))
    except Exception as e_gate:
        _blk, _blk_motivo = False, ''
        logger.warning(f"[FRAUDE] gate error (fail-open): {e_gate}")
    if _blk:
        db.close()
        logger.warning(f"[FRAUDE] Pago Payway BLOQUEADO ref={pedido_ref} motivo={_blk_motivo} "
                       f"dni={cli.get('dni')} dir={str(cli.get('direccion'))[:60]!r}")
        _fraude_registrar_bloqueo(cli, _blk_motivo, bin_numero, session.get('pw_last4', ''), pedido_ref)
        _base_url = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')
        # Misma respuesta que un rechazo del banco (indistinguible para el atacante)
        return jsonify({'status': 'rejected', 'redirect_url': f"{_base_url}/tienda/pago/error"}), 400

    # ── Calcular monto con coeficiente de cuotas y cupón ─────────────────────
    coef_3, coef_6    = get_coeficientes_cuotas()
    coef              = coef_3 if installments == 3 else coef_6
    total_productos   = sum(float(it['precio']) * int(it['cantidad']) for it in cart_items)

    # Cupón aplica solo a productos (no al flete)
    cupon = cli.get('cupon')
    if cupon:
        if cupon['tipo'] == 'pct':
            factor_cupon = 1 - float(cupon['valor']) / 100
        else:
            descuento_fijo = min(float(cupon['valor']), total_productos)
            factor_cupon = (total_productos - descuento_fijo) / total_productos if total_productos else 1
    else:
        factor_cupon = 1

    zipnova_quote     = cli.get('zipnova_quote')
    costo_flete       = float(zipnova_quote.get('precio', 0)) if zipnova_quote else 0.0
    total_base        = (total_productos * factor_cupon) + costo_flete
    total_con_coef    = round(total_base * coef)
    amount_centavos   = int(total_con_coef * 100)  # Payway espera centavos

    # Items con precio ajustado por cupón + coeficiente
    # Se usan para guardar en la DB y en los emails — el cliente ve el precio real pagado
    cart_items_adj = [
        dict(it, precio=round(float(it['precio']) * factor_cupon * coef))
        for it in cart_items
    ]
    costo_flete_adj = round(costo_flete * coef) if costo_flete else 0.0

    # ── Llamar a API de Payway ────────────────────────────────────────────────
    payway_private_key = os.getenv('PAYWAY_PRIVATE_KEY', '')
    payway_url         = os.getenv("PAYWAY_API_URL", "https://live.decidir.com/api/v2")
    site_tx_id         = f"PW-{pedido_ref}"

    # ── Datos para CyberSource (antifraude — obligatorio en produccion) ─────────
    ip_cliente     = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    nombre_split   = cli.get('nombre', 'Comprador Web').split(' ', 1)
    def _cs_clean(s, fallback='NA'):
        # CyberSource exige first_name/last_name sin caracteres especiales ni tildes
        import unicodedata, re as _re_cs
        s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode('ascii')
        s = _re_cs.sub(r'[^A-Za-z ]', '', s).strip()
        return s or fallback
    cs_first_name  = _cs_clean(nombre_split[0], 'Cliente')
    cs_last_name   = _cs_clean(nombre_split[1] if len(nombre_split) > 1 else nombre_split[0], 'Web')
    cs_email       = cli.get('email', '') or 'sin_email@mercadomuebles.com.ar'

    # Dirección normalizada (street1 = calle, street2 = barrio/complemento opcional)
    cs_street1 = (cli.get('calle') or cli.get('direccion') or 'Sin direccion')[:60]
    cs_city    = (cli.get('ciudad') or 'Buenos Aires') or 'Buenos Aires'
    cs_cp      = str(cli.get('cp') or '1000')[:10]
    cs_phone   = str(cli.get('telefono') or '0')[:15]
    cs_dni     = str(cli.get('dni') or '00000000')

    # Estructura RETAIL de CyberSource (spec oficial Payway, requiere template_id=2)
    fraud_detection = {
        "send_to_cs": True,
        "channel": "Web",
        "device_unique_identifier": device_fingerprint_id or ip_cliente,
        "bill_to": {
            "city":         cs_city,
            "country":      "AR",
            "customer_id":  cs_dni,
            "email":        cs_email,
            "first_name":   cs_first_name,
            "last_name":    cs_last_name,
            "phone_number": cs_phone,
            "postal_code":  cs_cp,
            "state":        "BA",
            "street1":      cs_street1,
        },
        "purchase_totals": {
            "currency": "ARS",
            "amount":   amount_centavos,
        },
        "customer_in_site": {
            "days_in_site":        1,
            "is_guest":            True,
            "num_of_transactions": 1,
            "cellphone_number":    cs_phone,
            "street":              cs_street1,
        },
        "dispatch_method":  "delivery" if cli.get('tipo_entrega') == 'envio' else "storepickup",
        "retail_transaction_data": {
            "ship_to": {
                "city":         cs_city,
                "country":      "AR",
                "email":        cs_email,
                "first_name":   cs_first_name,
                "last_name":    cs_last_name,
                "phone_number": cs_phone,
                "postal_code":  cs_cp,
                "state":        "BA",
                "street1":      cs_street1,
            },
            "days_to_delivery": "2",
            "items": [
                {
                    "code":         it.get('sku', 'PROD'),
                    "description":  (it.get('nombre') or it.get('sku') or 'Producto')[:100],
                    "name":         (it.get('nombre') or it.get('sku') or 'Producto')[:50],
                    "sku":          it.get('sku', 'PROD'),
                    "total_amount": int(float(it.get('precio', 0)) * int(it.get('cantidad', 1)) * 100),
                    "quantity":     int(it.get('cantidad', 1)),
                    "unit_price":   int(float(it.get('precio', 0)) * 100),
                }
                for it in cart_items
            ],
        },
    }

    payment_body = {
        "user_id":             cs_dni,
        "customer": {
            "id":         cs_dni,
            "email":      cs_email,
            "ip_address": ip_cliente,
        },
        "site_transaction_id": site_tx_id,
        "token":               token,
        "payment_method_id":   payment_method_id,
        "bin":                 bin_numero,
        "amount":              amount_centavos,
        "currency":            "ARS",
        "installments":        installments,
        "payment_type":        "single",
        "establishment_name":  "MERCADOMUEBLES",
        "plan_gobierno":        False,
        "sub_payments":        [],
        "template_id":         2,
        "fraud_detection":     fraud_detection,
    }

    logger.info(f"[pago_payway] device_fp={device_fingerprint_id!r} ship_street={cli.get('calle')!r} ship_city={cli.get('ciudad')!r}")

    try:
        headers = {
            "apikey":        payway_private_key,
            "Content-Type":  "application/json",
            "Cache-Control": "no-cache"
        }
        pw_resp = req_lib.post(
            f"{payway_url}/payments",
            json=payment_body,
            headers=headers,
            timeout=30
        )
        pw_data = pw_resp.json()
    except Exception as e:
        logger.error(f"[pago_payway] Error llamando Payway: {e}")
        log_evento('ERROR', 'webhook', 'error_webhook_payway',
            f"Error procesando webhook Payway. Error: {str(e)}")
        base_url = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')
        return jsonify({'status': 'error', 'redirect_url': f"{base_url}/tienda/pago/error"}), 500

    pw_status = pw_data.get('status', '')
    pw_id     = str(pw_data.get('id', ''))
    base_url  = os.getenv('APP_BASE_URL', 'https://sistema.mercadomuebles.com.ar')

    logger.info(f"[pago_payway] status={pw_status} id={pw_id} ref={pedido_ref}")

    # ── Log del intento en payway_intentos (tiempo real, para gate/monitoreo) ──
    # Fail-silent: un error acá jamás afecta el resultado del pago.
    try:
        if pw_data.get('id'):
            op_log = dict(pw_data)
            # completar last4 desde la sesión si la API no lo devuelve
            if not op_log.get('pan') and session.get('pw_last4'):
                op_log['pan'] = session.get('pw_last4')
            from app import _payway_upsert_intento
            _payway_upsert_intento(op_log)
    except Exception as e_log:
        logger.warning(f"[FRAUDE] log intento error (ignorado): {e_log}")

    if pw_status != 'approved':
        logger.warning(f"[pago_payway] No aprobado: {pw_data}")
        return jsonify({'status': pw_status, 'redirect_url': f"{base_url}/tienda/pago/error"}), 400

    # ── Evitar duplicados ─────────────────────────────────────────────────────
    numero_venta = f"PW-{pw_id}"
    cur2 = db.cursor()
    cur2.execute("SELECT id FROM ventas WHERE numero_venta = %s", (numero_venta,))
    if cur2.fetchone():
        cur2.close()
        db.close()
        session.pop('carrito', None)
        session.pop('pedido_ref_bricks', None)
        return jsonify({'status': 'approved', 'redirect_url': f"{base_url}/tienda/pago/exito?payment_id={pw_id}&status=approved&canal=payway"})

    # ── Datos del cliente ─────────────────────────────────────────────────────
    nombre_cliente   = cli.get('nombre', 'Comprador web')
    telefono_cliente = cli.get('telefono', '')
    dni_cliente      = cli.get('dni', '')
    email_cliente    = cli.get('email', '')
    direccion        = cli.get('direccion', '')
    provincia        = cli.get('provincia', 'Capital Federal')
    tipo_entrega_val = cli.get('tipo_entrega', 'envio')

    if tipo_entrega_val == 'retiro':
        metodo_envio_val = None
    elif zipnova_quote:
        carrier_name     = zipnova_quote.get('carrier_name', '')
        metodo_envio_val = 'Flete Propio' if 'propio' in carrier_name.lower() else 'Zippin'
    else:
        metodo_envio_val = None

    tz_ar     = timezone(timedelta(hours=-3))
    fecha_now = datetime.now(tz_ar).replace(tzinfo=None)

    notas_parts = [f"PWID: {pw_id}", f"OP_PAYWAY: {site_tx_id}", f"Cuotas: {installments}", f"Coef: {coef}"]
    if cli.get('demora_dias'):
        notas_parts.append(f"DEMORA: {cli['demora_dias']} dias ({cli.get('fecha_disponible','')})")
    notas_extra = "\n".join(notas_parts)

    # Origen de tráfico (cookies del landing) — JSON limpio para la columna
    _origen_first = urllib.parse.unquote(request.cookies.get('mm_origen_first') or '') or None
    _origen_last  = urllib.parse.unquote(request.cookies.get('mm_origen_last') or '') or None

    # ── INSERT ventas ─────────────────────────────────────────────────────────
    cur2.execute("""
        INSERT INTO ventas (
            numero_venta, canal, nombre_cliente, telefono_cliente,
            dni_cliente, provincia_cliente, importe_total, importe_abonado,
            metodo_pago, tipo_entrega, metodo_envio,
            direccion_entrega, estado_pago, estado_entrega,
            estado, costo_flete, pago_mercadopago,
            stock_descontado, notas, origen_first, origen_last, fecha_venta, fecha_registro
        ) VALUES (
            %s, 'tienda_web', %s, %s,
            %s, %s, %s, %s,
            'Payway', %s, %s,
            %s, 'pagado', 'pendiente',
            'ACTIVA', %s, 0,
            0, %s, %s, %s, %s, %s
        )
    """, (
        numero_venta,
        nombre_cliente, telefono_cliente,
        dni_cliente, provincia,
        total_con_coef, total_con_coef,  # importe_total e importe_abonado con coef
        tipo_entrega_val, metodo_envio_val,
        direccion,
        costo_flete_adj,  # flete tambien con coef embebido
        notas_extra, _origen_first, _origen_last, fecha_now, fecha_now,
    ))
    venta_id = cur2.lastrowid

    # ── Datos de factura (Factura A) ──────────────────────────────────────────
    _fdt, _fdn, _ftt = _factura_fields(cli)
    if _fdt:
        cur2.execute(
            "UPDATE ventas SET factura_doc_type=%s, factura_doc_number=%s, factura_taxpayer_type=%s WHERE id=%s",
            (_fdt, _fdn, _ftt, venta_id)
        )

    # ── Costo comisión Payway (6.91%) ─────────────────────────────────────────
    cur2.execute(
        "UPDATE ventas SET costo_comision = ROUND(importe_total * 0.0691, 2), costo_envio_vendedor = 0 WHERE id = %s",
        (venta_id,)
    )

    # ── Items + stock (precios con coeficiente embebido) ─────────────────────
    for it in cart_items_adj:
        cur2.execute(
            "INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
            (venta_id, it['sku'], it['cantidad'], it['precio'])
        )
    db.commit()
    cur2.close()
    try:
        from app import enviar_whatsapp
        tel = (telefono_cliente or '').strip().replace('+','').replace(' ','').replace('-','')
        if tel:
            if tel.startswith('0'):
                tel = '54' + tel[1:]
            elif not tel.startswith('54'):
                tel = '549' + tel
            enviar_whatsapp(tel, 'tienda_confirmacion', componentes=[{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": nombre_cliente or 'Cliente'},
                    {"type": "text", "text": str(numero_venta)}
                ]
            }])
    except Exception:
        pass

    logger.info(f"Venta Payway registrada: id={venta_id} numero={numero_venta} cliente={nombre_cliente}")
    log_evento('INFO', 'webhook', 'nueva_venta_payway',
        f"Venta tienda web registrada por webhook Payway. Número: {numero_venta}. Cliente: {nombre_cliente}. Total: ${total_con_coef}.",
        venta_id=venta_id)

    # ── Meta CAPI Purchase (server-side) ──────────────────────────────────────
    try:
        _ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        enviar_capi_purchase(
            numero_venta=numero_venta, email=email_cliente, telefono=telefono_cliente,
            nombre=nombre_cliente, dni=dni_cliente,
            provincia=cli.get('provincia',''), ciudad=cli.get('ciudad',''), cp=cli.get('cp',''),
            total=total_con_coef, items=cart_items_adj,
            client_ip=_ip, user_agent=request.headers.get('User-Agent'),
            fbp=request.cookies.get('_fbp'), fbc=request.cookies.get('_fbc'),
            source_url=request.url)
    except Exception as _e:
        print(f"[CAPI] payway: {_e}")

    # ── Cupón ─────────────────────────────────────────────────────────────────
    cupon_session = cli.get('cupon')
    if cupon_session and cupon_session.get('id'):
        try:
            cc = db.cursor()
            cc.execute(
                "INSERT INTO cupones_uso (cupon_id, email, telefono, venta_numero) VALUES (%s,%s,%s,%s)",
                (cupon_session['id'], email_cliente, telefono_cliente, numero_venta)
            )
            cc.execute("UPDATE cupones SET usos_actuales = usos_actuales + 1 WHERE id = %s", (cupon_session['id'],))
            db.commit()
            cc.close()
        except Exception as e:
            logger.warning(f"[pago_payway] Error cupon: {e}")

    # ── Limpiar pedido pendiente ───────────────────────────────────────────────
    try:
        cc2 = db.cursor()
        cc2.execute("DELETE FROM pedidos_pendientes WHERE ref = %s", (pedido_ref,))
        db.commit()
        cc2.close()
    except Exception:
        pass

    # ── Zipnova si corresponde ────────────────────────────────────────────────
    zn_tracking_url = ''
    if metodo_envio_val == 'Zippin' and zipnova_quote:
        try:
            db_zn    = get_db()
            bultos   = armar_bultos_zipnova(cart_items, db_zn)
            db_zn.close()
            zn_resp  = zipnova_crear_envio(bultos, cli, numero_venta, int(total_productos))
            if isinstance(zn_resp, dict):
                zn_tracking_url = zn_resp.get('tracking_url') or zn_resp.get('label_url') or ''
                if zn_tracking_url:
                    try:
                        cc3 = db.cursor()
                        notas_new = notas_extra + f"\nZIPNOVA: {zn_tracking_url}"
                        cc3.execute("UPDATE ventas SET notas = %s WHERE id = %s", (notas_new, venta_id))
                        db.commit()
                        cc3.close()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"[pago_payway] Error Zipnova: {e}")

    # ── Emails ────────────────────────────────────────────────────────────────
    try:
        enviar_email_confirmacion(
            pw_id, nombre_cliente, email_cliente, cart_items_adj,
            tipo_entrega_val, direccion, None, total_con_coef, costo_flete_adj,
            zipnova_tracking_url=zn_tracking_url, canal="payway",
            demora_dias=cli.get('demora_dias', 0),
            fecha_disponible=cli.get('fecha_disponible', ''),
        )
    except Exception as e:
        logger.warning(f"[pago_payway] Error email cliente: {e}")

    try:
        enviar_email_vendedor(
            pw_id, nombre_cliente, email_cliente, telefono_cliente,
            cart_items_adj, tipo_entrega_val, direccion, total_con_coef,
            metodo_envio=metodo_envio_val,
            demora_dias=cli.get('demora_dias', 0),
            fecha_disponible=cli.get('fecha_disponible', ''),
            canal='payway',
        )
    except Exception as e:
        logger.warning(f"[pago_payway] Error email vendedor: {e}")

    # ── Limpiar session ────────────────────────────────────────────────────────
    session.pop('carrito', None)
    session.pop('mp_preference_id', None)
    session.pop('pedido_ref_bricks', None)
    session.pop('cupon', None)
    session.pop('zipnova_quote', None)
    db.close()

    # ── Sincronizar publicaciones ML en background ────────────────────────────
    try:
        import threading
        from app import actualizar_publicaciones_ml_con_progreso, _extraer_skus_base_de_items
        skus_afectados = _extraer_skus_base_de_items(
            [{'sku': it['sku'], 'cantidad': it['cantidad']} for it in cart_items] if cart_items else []
        )
        if skus_afectados:
            def _sync_ml_payway():
                try:
                    actualizar_publicaciones_ml_con_progreso(skus_afectados)
                except Exception as e_ml:
                    logger.warning(f"[TIENDA-ML] Error sync ML Payway: {e_ml}")
            threading.Thread(target=_sync_ml_payway, daemon=True).start()
    except Exception as e_sync:
        logger.warning(f"[TIENDA-ML] No se pudo iniciar sync ML Payway: {e_sync}")

    return jsonify({
        'status':       'approved',
        'redirect_url': f"{base_url}/tienda/pago/exito?payment_id={pw_id}&status=approved&canal=payway"
    })


# ── GETNET CHECKOUT ────────────────────────────────────────────────────────────
# PROVISORIO: solo crea el payment_intent y redirige. El webhook y pago_exito
# de GetNet NO registran venta todavía (ver "SEGUNDA ITERACIÓN" cuando GetNet
# entregue credenciales prod).

_getnet_token_cache = {'token': None, 'expires_at': 0}


def _getnet_get_token(force_uat=False):
    """Obtiene access_token de GetNet (OAuth2 client_credentials) con cache.

    force_uat=True fuerza el ambiente sandbox (UAT) y NO usa el cache de prod
    (lo usa solo la página de prueba /test-getnet). El camino de producción
    (force_uat=False) queda idéntico al original."""
    import time
    cache = _getnet_token_cache
    if not force_uat and cache['token'] and time.time() < cache['expires_at']:
        return cache['token']

    use_uat       = force_uat or not os.getenv('GETNET_CLIENT_ID', '').strip()
    client_id     = os.getenv('GETNET_CLIENT_ID_UAT' if use_uat else 'GETNET_CLIENT_ID')
    client_secret = os.getenv('GETNET_CLIENT_SECRET_UAT' if use_uat else 'GETNET_CLIENT_SECRET')
    base_url      = os.getenv('GETNET_BASE_URL_UAT' if use_uat else 'GETNET_BASE_URL')

    import requests as req_lib
    resp = req_lib.post(
        f"{base_url}/authentication/oauth2/access_token",
        data={
            'grant_type':    'client_credentials',
            'client_id':     client_id,
            'client_secret': client_secret,
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    # En modo sandbox forzado no contaminamos el cache de producción.
    if force_uat:
        return data['access_token']
    cache['token']      = data['access_token']
    cache['expires_at'] = time.time() + data.get('expires_in', 3600) - 50
    return cache['token']


@tienda_bp.route('/pago/getnet/crear', methods=['POST'])
def pago_getnet_crear():
    """
    PROVISORIO: crea un payment-intent en GetNet (digital-checkout) y devuelve
    la redirect_url para que el frontend redirija al checkout hospedado.
    No registra venta — eso lo hará el webhook cuando GetNet entregue prod.
    """
    import requests as req_lib

    pedido_ref = session.get('pedido_ref_bricks', '')
    if not pedido_ref:
        return jsonify(error='Sesión expirada. Volvé al carrito.'), 400

    # Recuperar carrito y cliente desde pedidos_pendientes (mismo patrón que /pago/payway)
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT carrito_json, cliente_json FROM pedidos_pendientes WHERE ref = %s", (pedido_ref,))
    row = cur.fetchone()
    cur.close()
    db.close()
    if not row:
        return jsonify(error='Pedido no encontrado. Volvé al carrito.'), 400

    cart_items = json.loads(row['carrito_json'])
    cli        = json.loads(row['cliente_json'])

    # ── Defensa: no permitir cobrar si falta la cotización de envío ──────────
    # Sin zipnova_quote la venta entraría con metodo_envio=None (panel la
    # mostraría como "Retiro") y costo_flete=0 (cliente no paga el envío).
    if cli.get('tipo_entrega', 'envio') == 'envio' and not cli.get('zipnova_quote'):
        return jsonify({
            'ok': False,
            'error': 'No se encontró la cotización de envío. Volvé al paso '
                     'de datos y cotizá el envío antes de pagar.',
            'redirect': '/datos-envio'
        }), 400

    # ── Gate antifraude propio (blocklist + velocidad envío) — FAIL-OPEN ─────
    try:
        _blk, _blk_motivo = _fraude_gate(cli)
    except Exception as e_gate:
        _blk, _blk_motivo = False, ''
        logger.warning(f"[FRAUDE] gate getnet error (fail-open): {e_gate}")
    if _blk:
        logger.warning(f"[FRAUDE] Intent GetNet BLOQUEADO ref={pedido_ref} motivo={_blk_motivo} "
                       f"dni={cli.get('dni')} dir={str(cli.get('direccion'))[:60]!r}")
        _fraude_registrar_bloqueo(cli, _blk_motivo, '', '', pedido_ref)
        # Mismo mensaje que un error genérico de GetNet (indistinguible)
        return jsonify(error='No se pudo iniciar el pago con GetNet. Intentá con otro método.'), 500

    # Mismo coef que Payway 6c (también usado por la card de checkout)
    _, coef_6 = get_coeficientes_cuotas()
    total_productos = sum(float(it['precio']) * int(it['cantidad']) for it in cart_items)

    # Cupón aplica solo a productos (no al flete)
    cupon = cli.get('cupon')
    if cupon:
        if cupon['tipo'] == 'pct':
            factor_cupon = 1 - float(cupon['valor']) / 100
        else:
            descuento_fijo = min(float(cupon['valor']), total_productos)
            factor_cupon = (total_productos - descuento_fijo) / total_productos if total_productos else 1
    else:
        factor_cupon = 1

    zipnova_quote   = cli.get('zipnova_quote')
    costo_flete     = float(zipnova_quote.get('precio', 0)) if zipnova_quote else 0.0
    total_con_coef  = round(((total_productos * factor_cupon) + costo_flete) * coef_6)
    costo_flete_adj = round(costo_flete * coef_6) if costo_flete else 0

    # Derivar metodo_envio para el snapshot (mismo criterio que webhook_getnet)
    tipo_entrega_val = cli.get('tipo_entrega', 'envio')
    if tipo_entrega_val == 'retiro':
        metodo_envio_snap = None
    elif zipnova_quote:
        carrier_name      = zipnova_quote.get('carrier_name', '')
        metodo_envio_snap = 'Flete Propio' if 'propio' in carrier_name.lower() else 'Zippin'
    else:
        metodo_envio_snap = None

    # Snapshot del pedido en pedidos_pendientes_getnet (antes del POST a GetNet).
    # La venta NO se registra acá; eso lo hace /webhook/getnet con status APPROVED.
    try:
        db_pp  = get_db()
        cur_pp = db_pp.cursor()
        cur_pp.execute("""
            INSERT INTO pedidos_pendientes_getnet
                (pedido_ref, datos_cliente, datos_carrito, total, costo_flete,
                 metodo_envio, direccion, fecha_expiracion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))
            ON DUPLICATE KEY UPDATE
                datos_cliente    = VALUES(datos_cliente),
                datos_carrito    = VALUES(datos_carrito),
                total            = VALUES(total),
                costo_flete      = VALUES(costo_flete),
                metodo_envio     = VALUES(metodo_envio),
                direccion        = VALUES(direccion),
                fecha_creacion   = NOW(),
                fecha_expiracion = DATE_ADD(NOW(), INTERVAL 24 HOUR),
                estado           = 'pendiente'
        """, (
            pedido_ref,
            json.dumps(cli, ensure_ascii=False, default=str),
            json.dumps(cart_items, ensure_ascii=False, default=str),
            total_con_coef,
            costo_flete_adj,
            metodo_envio_snap or '',
            cli.get('direccion', '') or '',
        ))
        db_pp.commit()
        cur_pp.close()
        db_pp.close()
    except Exception as e_pp:
        logger.warning(f'[getnet_crear] Error guardando pedido pendiente: {e_pp}')

    use_uat  = not os.getenv('GETNET_CLIENT_ID', '').strip()
    base_url = os.getenv('GETNET_BASE_URL_UAT' if use_uat else 'GETNET_BASE_URL')

    try:
        token        = _getnet_get_token()
        nombre       = cli.get('nombre', 'Cliente Web') or 'Cliente Web'
        nombre_split = nombre.split(' ', 1)

        # product[]: aplicar cupón + coef a cada ítem; flete como ítem extra si aplica
        product = []
        for it in cart_items:
            product.append({
                'title':    (it.get('nombre') or it.get('sku') or 'Producto')[:50],
                'value':    int(round(float(it['precio']) * factor_cupon * coef_6) * 100),
                'quantity': int(it['cantidad']),
            })
        if costo_flete > 0:
            product.append({
                'title':    'Envio a domicilio',
                'value':    int(round(costo_flete * coef_6) * 100),
                'quantity': 1,
            })

        body = {
            'order_id': pedido_ref,
            'redirect_urls': {
                # GetNet strippea query params al redirigir → usar pedido_ref en el path
                'success': url_for('tienda.pago_exito_getnet', pedido_ref=pedido_ref, _external=True),
                'failed':  url_for('tienda.pago_error', _external=True) + "?canal=getnet",
            },
            'payment': {
                'amount':   int(total_con_coef * 100),
                'currency': 'ARS',
            },
            'product': product,
            'customer': {
                'customer_id':     cli.get('dni', 'guest') or 'guest',
                'first_name':      nombre_split[0],
                'last_name':       nombre_split[1] if len(nombre_split) > 1 else nombre_split[0],
                'name':            nombre,
                'email':           cli.get('email', '') or 'sin_email@mercadomuebles.com.ar',
                'document_type':   'dni',
                'document_number': cli.get('dni', '') or '00000000',
                'phone_number':    cli.get('telefono', '') or '0',
            },
        }

        logger.info(f"[getnet_crear] REQUEST body: {json.dumps(body, ensure_ascii=False, default=str)}")

        resp = req_lib.post(
            f"{base_url}/digital-checkout/v1/payment-intent",
            json=body,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            },
            timeout=15,
        )
        logger.info(f"[getnet_crear] RESPONSE status={resp.status_code} body={resp.text[:1000]}")
        resp.raise_for_status()
        data = resp.json()
        session['getnet_payment_intent_id'] = data.get('payment_intent_id')
        session['getnet_pedido_ref']        = pedido_ref
        logger.info(f"[getnet_crear] payment_intent_id={data.get('payment_intent_id')} pedido={pedido_ref}")

        # Guardar payment_intent_id en pedidos_pendientes_getnet
        try:
            db_pi  = get_db()
            cur_pi = db_pi.cursor()
            cur_pi.execute(
                "UPDATE pedidos_pendientes_getnet SET payment_intent_id = %s WHERE pedido_ref = %s",
                (data.get('payment_intent_id'), pedido_ref)
            )
            db_pi.commit()
            cur_pi.close()
            db_pi.close()
        except Exception as e_pi:
            logger.warning(f'[getnet_crear] Error guardando payment_intent_id: {e_pi}')

        return jsonify(redirect_url=data['redirect_url'])

    except Exception as e:
        logger.error(f"[getnet_crear] Error: {e}")
        logger.error(f"[getnet_crear] ERROR response: status={getattr(getattr(e, 'response', None), 'status_code', '?')} body={getattr(getattr(e, 'response', None), 'text', str(e))[:1000]}")
        return jsonify(error='No se pudo iniciar el pago con GetNet. Intentá con otro método.'), 500


@tienda_bp.route('/pago/getnet/webhook', methods=['POST'])
def getnet_webhook():
    """PROVISORIO: solo loggea el payload, no registra venta."""
    data = request.get_json(silent=True) or {}
    logger.info(f"[getnet_webhook] PROVISORIO payload: {data}")
    return jsonify(ok=True), 200


@tienda_bp.route('/pago/exito-getnet/<pedido_ref>', methods=['GET'])
def pago_exito_getnet(pedido_ref):
    """Página de éxito específica para GetNet con pedido_ref en el path.
    Esto evita que GetNet strippee query params al hacer el redirect."""
    numero_pedido = f"GN-{pedido_ref}" if pedido_ref else ""
    print(f"[pago_exito_getnet] pedido_ref={pedido_ref}", flush=True)
    # Limpiar carrito (mismo comportamiento que /pago/exito)
    session.pop('carrito', None)
    session.pop('mp_preference_id', None)
    # Reintento corto contra la carrera con el webhook async de GetNet:
    # si la venta aún no existe (importe_abonado<=0), esperar y reintentar.
    importe_abonado = 0
    for _intento in range(3):
        try:
            _db = get_db(); _cur = _db.cursor()
            _cur.execute("SELECT importe_abonado FROM ventas WHERE numero_venta=%s LIMIT 1", (numero_pedido,))
            _r = _cur.fetchone()
            _cur.close(); _db.close()
            if _r:
                importe_abonado = float(_r['importe_abonado'] or 0)
        except Exception:
            pass
        if importe_abonado > 0:
            break
        time.sleep(0.4)
    ga_value = importe_abonado   # alineado al monto pagado (GA4 = Pixel = CAPI)
    return render_template(
        'tienda/pago_exito_getnet.html',
        payment_id=pedido_ref,
        numero_pedido=numero_pedido,
        ga_value=ga_value,
        importe_abonado=importe_abonado,
    )


@tienda_bp.route('/pago/exito')
def pago_exito():
    payment_id     = request.args.get('payment_id')
    status         = request.args.get('status')
    preference_id  = request.args.get('preference_id')
    canal          = request.args.get('canal', 'mp')  # 'mp', 'payway' o 'getnet'

    # Limpiar carrito
    session.pop('carrito', None)
    session.pop('mp_preference_id', None)

    # GetNet: la venta la registra el webhook (POST /webhook/getnet) cuando llega
    # APPROVED. Esta página es solo confirmación visual con el número de pedido.
    if canal == 'getnet':
        # GetNet a veces strippea el query param payment_id al redirigir.
        # Fallback 1: leer pedido_ref guardado en sesión por /pago/getnet/crear
        if not payment_id:
            payment_id = session.get('getnet_pedido_ref', '')

        # Fallback 2: buscar la última venta GetNet del cliente (nombre+telefono
        # de session['cliente_checkout']) registrada en los últimos 30 minutos
        numero_pedido = f"GN-{payment_id}" if payment_id else ''
        if not numero_pedido:
            cli_chk = session.get('cliente_checkout', {}) or {}
            nombre  = cli_chk.get('nombre', '')
            tel     = cli_chk.get('telefono', '')
            if nombre and tel:
                try:
                    db_chk  = get_db()
                    cur_chk = db_chk.cursor()
                    cur_chk.execute("""
                        SELECT numero_venta FROM ventas
                        WHERE metodo_pago='GetNet'
                          AND nombre_cliente=%s AND telefono_cliente=%s
                          AND fecha_venta > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                        ORDER BY id DESC LIMIT 1
                    """, (nombre, tel))
                    row_chk = cur_chk.fetchone()
                    cur_chk.close()
                    db_chk.close()
                    if row_chk:
                        numero_pedido = row_chk['numero_venta']
                        payment_id    = numero_pedido.replace('GN-', '')
                except Exception as e_chk:
                    logger.warning(f"[getnet_exito] fallback DB falló: {e_chk}")

        print(f"[getnet_exito] payment_id={payment_id} numero={numero_pedido}", flush=True)
        # Reintento corto contra la carrera con el webhook async de GetNet.
        importe_abonado_gn = 0
        for _intento in range(3):
            try:
                _db = get_db(); _cur = _db.cursor()
                _cur.execute("SELECT importe_abonado FROM ventas WHERE numero_venta=%s LIMIT 1", (numero_pedido,))
                _r = _cur.fetchone()
                _cur.close(); _db.close()
                if _r:
                    importe_abonado_gn = float(_r['importe_abonado'] or 0)
            except Exception:
                pass
            if importe_abonado_gn > 0:
                break
            time.sleep(0.4)
        ga_value = importe_abonado_gn   # alineado al monto pagado (GA4 = Pixel = CAPI)
        return render_template(
            'tienda/pago_exito_getnet.html',
            payment_id=payment_id or '',
            numero_pedido=numero_pedido,
            ga_value=ga_value,
            importe_abonado=importe_abonado_gn,
        )

    # Numero de venta segun canal
    if canal == 'payway':
        prefix = 'PW'
    else:
        prefix = 'MP'
    numero_venta = f"{prefix}-{payment_id}"

    # Obtener datos de la venta para GA4. Reintento corto contra la carrera con
    # el webhook async (la venta MP puede crearse después del redirect; Payway la
    # encuentra al primer intento). Una vez que aparece, ga_items sale de items_venta.
    ga_items  = []
    ga_value  = 0
    importe_abonado = 0
    for _intento in range(3):
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                SELECT v.importe_total, v.importe_abonado, iv.sku, iv.cantidad, iv.precio_unitario,
                       COALESCE(pb.nombre, pc.nombre, iv.sku) as nombre
                FROM ventas v
                JOIN items_venta iv ON iv.venta_id = v.id
                LEFT JOIN productos_base pb ON pb.sku = iv.sku
                LEFT JOIN productos_compuestos pc ON pc.sku = iv.sku
                WHERE v.numero_venta = %s
            """, (numero_venta,))
            rows = cur.fetchall()
            if rows:
                importe_abonado = float(rows[0]['importe_abonado'] or 0)
                ga_value = importe_abonado   # alineado al monto pagado (GA4 = Pixel = CAPI)
                ga_items = []
                for r in rows:
                    ga_items.append({
                        'item_id':   r['sku'],
                        'item_name': r['nombre'],
                        'price':     float(r['precio_unitario'] or 0),
                        'quantity':  int(r['cantidad'] or 1),
                    })
            cur.close()
            db.close()
        except Exception:
            pass
        if importe_abonado > 0:
            break
        time.sleep(0.4)

    # Fallback race-free SOLO para MP: si la venta async aún no existe en DB,
    # traer monto e items directo de MP por payment_id (mismo patrón que verificar_pago).
    if canal == 'mp' and payment_id and importe_abonado <= 0:
        try:
            sdk = get_mp_sdk()
            mp = sdk.payment().get(payment_id).get('response', {}) or {}
            ta = float(mp.get('transaction_amount') or 0)
            if ta > 0:
                ga_value = ta
                importe_abonado = ta
                ga_items = [{'item_id': it.get('id', ''), 'item_name': it.get('title', ''),
                             'price': float(it.get('unit_price') or 0),
                             'quantity': int(it.get('quantity') or 1)}
                            for it in ((mp.get('additional_info') or {}).get('items') or [])]
        except Exception:
            pass

    return render_template('tienda/pago_exito.html',
        payment_id    = payment_id,
        carrito_count = 0,
        ga_value      = ga_value,
        ga_items      = ga_items,
        importe_abonado = importe_abonado,
        numero_venta  = numero_venta,
    )


@tienda_bp.route('/pago/pendiente')
def pago_pendiente():
    """
    Con tarjeta de crédito, MP redirige acá con status=in_process.
    Mostramos la página con auto-refresh cada 5 segundos.
    El JS llama a /tienda/verificar-pago?payment_id=xxx y redirige si está aprobado.
    """
    payment_id    = request.args.get('payment_id', '')
    preference_id = request.args.get('preference_id', '')
    return render_template('tienda/pago_pendiente.html',
        carrito_count=0,
        payment_id=payment_id,
        preference_id=preference_id,
    )


@tienda_bp.route('/verificar-pago')
def verificar_pago():
    """API JSON: consulta el estado real de un pago en MP. Usado por el auto-refresh."""
    payment_id = request.args.get('payment_id')
    if not payment_id:
        return jsonify({'status': 'unknown'}), 400
    try:
        sdk    = get_mp_sdk()
        resp   = sdk.payment().get(payment_id)
        status = resp.get('response', {}).get('status', 'unknown')
        if status == 'approved':
            session.pop('carrito', None)
            session.pop('mp_preference_id', None)
        return jsonify({'status': status})
    except Exception as e:
        logger.error(f"Error verificar_pago: {e}")
        return jsonify({'status': 'error'}), 500


@tienda_bp.route('/pago/error')
def pago_error():
    return render_template('tienda/pago_error.html', carrito_count=0)



# ── EMAIL CONFIRMACIÓN DE COMPRA ───────────────────────────────────────────────

def enviar_email_confirmacion(payment_id, nombre_cliente, email_cliente, items,
                               tipo_entrega, direccion, fecha_entrega, importe_total, costo_flete,
                               zipnova_tracking_url=None, canal="mp",
                               demora_dias=0, fecha_disponible=''):
    """Envía email de confirmación al cliente cuando se aprueba el pago."""
    if not email_cliente:
        return
    try:
        smtp_host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_SMTP_PORT', '587'))
        smtp_user = os.getenv('MAIL_SMTP_USER', '')
        smtp_pass = os.getenv('MAIL_SMTP_PASS', '')
        mail_from = os.getenv('MAIL_FROM', smtp_user)

        if not smtp_user or not smtp_pass:
            logger.warning("Email no configurado (MAIL_SMTP_USER/MAIL_SMTP_PASS vacíos)")
            return

        # Armar tabla de items
        items_html = ""
        for it in items:
            subtotal = float(it.get('precio', 0)) * int(it.get('cantidad', 1))
            items_html += f"""
            <tr>
              <td style="padding:8px 12px; border-bottom:1px solid #f0f0f0;">{it.get('cantidad')}× {it.get('nombre', it.get('sku',''))}</td>
              <td style="padding:8px 12px; border-bottom:1px solid #f0f0f0; text-align:right;">${subtotal:,.0f}</td>
            </tr>"""

        entrega_html = ""
        if tipo_entrega == 'retiro':
            entrega_html = """
            <p style="margin:4px 0;"><strong>Tipo de entrega:</strong> Retiro en local</p>
            <p style="margin:4px 0;"><strong>Dirección:</strong> Bahía Blanca 1777, Floresta, CABA</p>
            <p style="margin:4px 0;"><strong>Horario:</strong> Lunes a Viernes 8-12hs y 14-16:30hs</p>"""
        else:
            entrega_html = f"""
            <p style="margin:4px 0;"><strong>Tipo de entrega:</strong> Envío a domicilio</p>
            <p style="margin:4px 0;"><strong>Dirección:</strong> {direccion}</p>"""
            if fecha_entrega:
                entrega_html += f"""<p style="margin:4px 0;"><strong>Entrega estimada:</strong> {fecha_entrega}</p>"""

        flete_html = ""
        if costo_flete > 0:
            flete_html = f'<tr><td style="padding:6px 12px; color:#666;">Envío</td><td style="padding:6px 12px; text-align:right; color:#666;">${costo_flete:,.0f}</td></tr>'

        # Bloque de seguimiento: Zipnova si hay URL, sino nuestro sistema
        if zipnova_tracking_url:
            seguimiento_html = f'''<a href="{zipnova_tracking_url}"
               style="display:inline-block; padding:12px 24px; background:#1a1a2e; color:#fff;
                      border-radius:8px; text-decoration:none; font-weight:700; font-size:0.9rem;">
              Seguir mi envío →
            </a>
            <p style="font-size:0.78rem; color:#aaa; margin:10px 0 0;">
              También podés ver el estado del pedido en
              <a href="https://www.mercadomuebles.com.ar/tienda/seguimiento?numero={prefijo_email}-{payment_id}" style="color:#aaa;">nuestra web</a>.
            </p>'''
        else:
            prefijo_link = "PW" if canal == "payway" else ("GN" if canal == "getnet" else "MP")
            seguimiento_html = f'''<a href="https://www.mercadomuebles.com.ar/tienda/seguimiento?numero={prefijo_link}-{payment_id}"
               style="display:inline-block; padding:12px 24px; background:#1a1a2e; color:#fff;
                      border-radius:8px; text-decoration:none; font-weight:700; font-size:0.9rem;">
              Ver estado de mi pedido →
            </a>'''

        prefijo_email = "PW" if canal == "payway" else ("GN" if canal == "getnet" else "MP")
        html = f"""
        <div style="font-family:Arial,sans-serif; max-width:560px; margin:0 auto; color:#1a1a2e;">
          <div style="background:#1a1a2e; padding:24px; text-align:center; border-radius:10px 10px 0 0;">
            <h1 style="color:#fff; margin:0; font-size:1.4rem;">¡Gracias por tu compra!</h1>
          </div>
          <div style="background:#fff; padding:28px; border:1px solid #e8e8e8; border-top:none; border-radius:0 0 10px 10px;">

            <p style="margin:0 0 20px;">Hola <strong>{nombre_cliente}</strong>, tu pago fue procesado correctamente.</p>

            <div style="background:#f8f8f8; border-radius:8px; padding:14px 16px; margin-bottom:20px;">
              <p style="margin:0; font-size:0.85rem; color:#666;">Número de pedido</p>
              <p style="margin:4px 0 0; font-size:1.1rem; font-weight:800; letter-spacing:1px;">{prefijo_email}-{payment_id}</p>
            </div>

            <h3 style="font-size:0.95rem; margin:0 0 10px;">Productos</h3>
            <table style="width:100%; border-collapse:collapse; margin-bottom:16px;">
              {items_html}
              {flete_html}
              <tr style="font-weight:700; font-size:1rem;">
                <td style="padding:10px 12px; border-top:2px solid #e8e8e8;">Total</td>
                <td style="padding:10px 12px; border-top:2px solid #e8e8e8; text-align:right;">${importe_total:,.0f}</td>
              </tr>
            </table>

            {f'''<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
              <strong>&#9203; Pedido con demora de entrega</strong><br>
              Este producto no tiene stock inmediato y estará disponible en <strong>{demora_dias} días</strong>
              {f"(a partir del <strong>{fecha_disponible}</strong>)" if fecha_disponible else ""}.
              Te avisaremos cuando esté listo para enviarse o retirarse.
            </div>''' if demora_dias else ''}
            <h3 style="font-size:0.95rem; margin:0 0 10px;">Entrega</h3>
            <div style="background:#f0f7ff; border-radius:8px; padding:14px 16px; margin-bottom:20px; font-size:0.9rem;">
              {entrega_html}
            </div>

            <p style="font-size:0.88rem; color:#666; margin:0 0 16px;">
              Nos pondremos en contacto a la brevedad para coordinar los detalles.
            </p>
            {seguimiento_html}

            <hr style="border:none; border-top:1px solid #f0f0f0; margin:24px 0;">
            <p style="font-size:0.78rem; color:#aaa; text-align:center; margin:0;">
              Mercadomuebles · Bahía Blanca 1777, Floresta, CABA · contacto@mercadomuebles.com.ar
            </p>
          </div>
        </div>"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Pedido confirmado {prefijo_email}-{payment_id} — Mercadomuebles"
        msg['From']    = f"Mercadomuebles <{mail_from}>"
        msg['To']      = email_cliente
        msg.attach(MIMEText(html, 'html'))

        if smtp_port == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, email_cliente, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, email_cliente, msg.as_string())

        logger.info(f"Email de confirmación enviado a {email_cliente} para MP-{payment_id}")

    except Exception as e:
        logger.error(f"Error enviando email confirmación: {e}")

def enviar_email_vendedor(payment_id, nombre_cliente, email_cliente, telefono,
                          items, tipo_entrega, direccion, importe_total, metodo_envio,
                          demora_dias=0, fecha_disponible='', canal='mp'):
    """Notifica al vendedor cuando entra una venta nueva."""
    try:
        smtp_host   = os.getenv('MAIL_SMTP_HOST', '')
        smtp_port   = int(os.getenv('MAIL_SMTP_PORT', '465'))
        smtp_user   = os.getenv('MAIL_SMTP_USER', '')
        smtp_pass   = os.getenv('MAIL_SMTP_PASS', '')
        mail_from   = os.getenv('MAIL_FROM', smtp_user)
        mail_vend   = os.getenv('MAIL_VENDEDOR', smtp_user)
        if not smtp_user or not smtp_pass or not mail_vend:
            return

        items_txt = ''.join(
            f"<tr><td style='padding:6px 12px;border-bottom:1px solid #f0f0f0;'>{it.get('cantidad')}× {it.get('nombre', it.get('sku',''))}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0;text-align:right;'>${float(it.get('precio',0))*int(it.get('cantidad',1)):,.0f}</td></tr>"
            for it in items
        )
        entrega = 'Retiro en local' if tipo_entrega == 'retiro' else f'Envío — {direccion}'

        demora_html = ''
        if demora_dias:
            demora_html = f"""
            <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin:12px 0;">
              <strong>⏳ VENTA CON DEMORA</strong><br>
              Producto sin stock — disponible en <strong>{demora_dias} días</strong>
              {f'(a partir del {fecha_disponible})' if fecha_disponible else ''}
            </div>"""

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;color:#1a1a2e;">
          <div style="background:#1a7fe8;padding:20px;border-radius:10px 10px 0 0;text-align:center;">
            <h2 style="color:#fff;margin:0;font-size:1.2rem;">🛒 Nueva venta — {("PW" if canal == "payway" else ("GN" if canal == "getnet" else "MP"))}-{payment_id}</h2>
          </div>
          <div style="background:#fff;padding:24px;border:1px solid #e8e8e8;border-top:none;border-radius:0 0 10px 10px;">
            {demora_html}
            <p><strong>Cliente:</strong> {nombre_cliente}</p>
            <p><strong>Email:</strong> {email_cliente or '—'}</p>
            <p><strong>Teléfono:</strong> {telefono or '—'}</p>
            <p><strong>Entrega:</strong> {entrega}</p>
            <p><strong>Método envío:</strong> {metodo_envio}</p>
            <table style="width:100%;border-collapse:collapse;margin:12px 0;">
              {items_txt}
              <tr style="font-weight:700;">
                <td style="padding:8px 12px;border-top:2px solid #e8e8e8;">TOTAL</td>
                <td style="padding:8px 12px;border-top:2px solid #e8e8e8;text-align:right;">${importe_total:,.0f}</td>
              </tr>
            </table>
            <a href="https://sistema.mercadomuebles.com.ar/ventas"
               style="display:inline-block;padding:10px 20px;background:#1a1a2e;color:#fff;border-radius:8px;text-decoration:none;font-weight:700;">
              Ver en el sistema →
            </a>
          </div>
        </div>"""

        msg = MIMEMultipart('alternative')
        prefijo_vend = 'PW' if canal == 'payway' else ('GN' if canal == 'getnet' else 'MP')
        msg['Subject'] = f"🛒 Nueva venta {prefijo_vend}-{payment_id} — ${importe_total:,.0f}"
        msg['From']    = f"Mercadomuebles <{mail_from}>"
        msg['To']      = mail_vend
        msg.attach(MIMEText(html, 'html'))

        if smtp_port == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, mail_vend, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, mail_vend, msg.as_string())

        logger.info(f"Email vendedor enviado para MP-{payment_id}")
    except Exception as e:
        logger.error(f"Error enviando email vendedor: {e}")


# ── WEBHOOK MERCADO PAGO ───────────────────────────────────────────────────────


# ── NEWSLETTER / SUSCRIPTORES ────────────────────────────────────────────────

def _crear_tabla_suscriptores():
    """Crea la tabla suscriptores si no existe."""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS suscriptores (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                email       VARCHAR(255) NOT NULL UNIQUE,
                cupon_id    INT NULL,
                fecha       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        logger.warning(f"No se pudo crear tabla suscriptores: {e}")

_crear_tabla_suscriptores()


def _get_nl_config():
    """Lee monto y mínimo del cupón newsletter desde la tabla configuracion."""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT clave, valor FROM configuracion WHERE clave IN ('nl_monto','nl_minimo')")
        rows = {r['clave']: int(r['valor'] or 0) for r in cur.fetchall()}
        cur.close(); db.close()
        return rows.get('nl_monto', 5000), rows.get('nl_minimo', 200000)
    except Exception:
        return 5000, 200000


def _enviar_email_bienvenida(email_dest, codigo_cupon, monto_desc, minimo_compra):
    """Envía el cupón de bienvenida al suscriptor."""
    try:
        smtp_host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_SMTP_PORT', '587'))
        smtp_user = os.getenv('MAIL_SMTP_USER', '')
        smtp_pass = os.getenv('MAIL_SMTP_PASS', '')
        mail_from = os.getenv('MAIL_FROM', smtp_user)
        if not smtp_user or not smtp_pass:
            return

        monto_fmt   = f'${monto_desc:,.0f}'.replace(',', '.')
        minimo_fmt  = f'${minimo_compra:,.0f}'.replace(',', '.')
        from datetime import datetime, timedelta
        venc_fmt = (datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
          <div style="background:#1a2744;padding:28px;text-align:center;">
            <img src="https://www.mercadomuebles.com.ar/static/img/logo_mercadomuebles_white.png"
                 alt="Mercadomuebles" style="height:48px;">
          </div>
          <div style="padding:32px;background:#fff;">
            <h2 style="color:#1a2744;margin-top:0;">¡Bienvenido/a! 🎉</h2>
            <p style="color:#444;font-size:15px;">
              Gracias por suscribirte. Como regalo de bienvenida, te enviamos este cupón exclusivo
              con <strong>{monto_fmt} de descuento</strong> en tu próxima compra:
            </p>
            <div style="background:#f8f9fa;border:2px dashed #1a2744;border-radius:8px;
                        padding:20px;text-align:center;margin:24px 0;">
              <p style="margin:0 0 6px;color:#888;font-size:13px;">TU CÓDIGO DE DESCUENTO</p>
              <p style="margin:0;font-size:2rem;font-weight:900;color:#1a2744;
                        letter-spacing:4px;">{codigo_cupon}</p>
              <p style="margin:8px 0 0;color:#888;font-size:12px;">{monto_fmt} OFF · Compra mínima {minimo_fmt}</p>
              <p style="margin:6px 0 0;color:#e53e3e;font-size:12px;font-weight:700;">⏳ Válido hasta el {venc_fmt}</p>
            </div>
            <p style="color:#444;font-size:14px;">
              Ingresá el código al momento de finalizar tu compra en
              <a href="https://www.mercadomuebles.com.ar" style="color:#1a2744;">mercadomuebles.com.ar</a>
            </p>
          </div>
          <div style="background:#f0f0f0;padding:16px;text-align:center;">
            <p style="margin:0;color:#999;font-size:12px;">
              Mercadomuebles y Colchones · Distribuidores oficiales Cannon
            </p>
          </div>
        </div>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🎁 Tu cupón de bienvenida — {monto_fmt} OFF en Mercadomuebles'
        msg['From']    = f'Mercadomuebles <{mail_from}>'
        msg['To']      = email_dest
        msg.attach(MIMEText(html, 'html'))

        if smtp_port == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, email_dest, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(mail_from, email_dest, msg.as_string())
        logger.info(f'Email bienvenida enviado a {email_dest}')
    except Exception as e:
        logger.warning(f'Error enviando email bienvenida a {email_dest}: {e}')


@tienda_bp.route('/suscribirse', methods=['POST'])
def suscribirse():
    """Registra el email, genera un cupón único y envía el mail de bienvenida."""
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': 'Email inválido'})

    try:
        db  = get_db()
        cur = db.cursor()

        # Verificar si ya está suscripto
        cur.execute("SELECT id FROM suscriptores WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close(); db.close()
            return jsonify({'ok': False, 'error': 'Este email ya está suscripto'})

        # Generar cupón único
        import random, string
        codigo = 'BIENVENIDO' + ''.join(random.choices(string.digits, k=4))
        monto_desc, minimo_compra = _get_nl_config()

        # Insertar cupón tipo 'fijo' con monto mínimo de compra y vencimiento 7 días
        cur.execute("""
            INSERT INTO cupones (codigo, tipo, valor, activo, usos_maximos, usos_actuales, minimo_compra, fecha_vencimiento)
            VALUES (%s, 'fijo', %s, 1, 1, 0, %s, DATE_ADD(NOW(), INTERVAL 7 DAY))
        """, (codigo, monto_desc, minimo_compra))
        cupon_id = cur.lastrowid

        # Registrar suscriptor
        cur.execute(
            "INSERT INTO suscriptores (email, cupon_id) VALUES (%s, %s)",
            (email, cupon_id)
        )
        db.commit()
        cur.close()
        db.close()

        # Enviar email directamente (SMTP es rápido, thread daemon es matado por gunicorn)
        _enviar_email_bienvenida(email, codigo, monto_desc, minimo_compra)

        monto_fmt = f'${monto_desc:,.0f}'.replace(',', '.')
        return jsonify({'ok': True, 'monto': monto_desc, 'monto_fmt': monto_fmt})

    except Exception as e:
        logger.error(f'Error suscribirse: {e}')
        return jsonify({'ok': False, 'error': 'Error interno, intentá de nuevo'})


@tienda_bp.route('/webhook/mp', methods=['POST'])
def webhook_mp():
    """
    Recibe notificaciones de MP.
    - Si el pago está aprobado: registra la venta en DB y descuenta stock.
    - Usa external_reference para conocer los items del carrito.
    - Usa merchant_order para obtener datos del comprador y envío.
    """
    # ── Verificación de firma MP ──────────────────────────────────────────────
    mp_secret = os.getenv('MP_WEBHOOK_SECRET', '')
    if mp_secret:
        import hmac, hashlib
        x_signature  = request.headers.get('x-signature', '')
        x_request_id = request.headers.get('x-request-id', '')
        data_id      = (request.get_json() or {}).get('data', {}).get('id', '') or request.args.get('data.id', '')

        # Armar el string a firmar según docs de MP
        signed_template = f"id:{data_id};request-id:{x_request_id};ts:{x_signature.split(',')[0].split('=')[-1] if ',' in x_signature else ''};"
        ts   = ''
        v1   = ''
        for part in x_signature.split(','):
            part = part.strip()
            if part.startswith('ts='):
                ts = part[3:]
            elif part.startswith('v1='):
                v1 = part[3:]
        signed_template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(mp_secret.encode(), signed_template.encode(), hashlib.sha256).hexdigest()
        if v1 and not hmac.compare_digest(expected, v1):
            ip = request.headers.get('x-forwarded-for', request.remote_addr or '').split(',')[0].strip()
            ua = request.headers.get('user-agent', '')[:80]
            logger.warning(
                f"Webhook MP: firma inválida ip={ip} x-request-id={x_request_id} data_id={data_id} ua={ua}"
            )
            return jsonify({'error': 'invalid signature'}), 401

    data        = request.get_json() or {}
    topic       = data.get('type') or request.args.get('topic')
    resource_id = data.get('data', {}).get('id') or request.args.get('id')

    logger.info(f"Webhook MP: topic={topic} id={resource_id}")

    if topic not in ('payment', 'merchant_order'):
        return jsonify({'ok': True}), 200

    db     = None
    cursor = None
    try:
        sdk     = get_mp_sdk()
        payment = None
        order   = None
        payment_id = None

        if topic == 'payment':
            resp    = sdk.payment().get(resource_id)
            payment = resp.get('response', {})
            if payment.get('status') != 'approved':
                return jsonify({'ok': True}), 200
            # Rechazar pagos con monto 0 (validaciones de tarjeta, intentos fallidos)
            if float(payment.get('transaction_amount', 0)) == 0:
                logger.warning(f"Pago {resource_id} rechazado: transaction_amount=0 (validación de tarjeta)")
                return jsonify({'ok': True}), 200
            payment_id = int(resource_id)
            # Buscar el merchant_order asociado
            mo_resp  = sdk.merchant_order().search({'payment_id': payment_id})
            elements = mo_resp.get('response', {}).get('elements', [])
            if elements:
                order = elements[0]

        elif topic == 'merchant_order':
            mo_resp = sdk.merchant_order().get(resource_id)
            order   = mo_resp.get('response', {})
            approved = [p for p in order.get('payments', []) if p.get('status') == 'approved']
            if not approved:
                return jsonify({'ok': True}), 200
            payment_id = approved[0]['id']
            resp    = sdk.payment().get(payment_id)
            payment = resp.get('response', {})

        if not payment or not payment_id:
            return jsonify({'ok': True}), 200

        # Evitar procesar el mismo pago dos veces
        db     = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM ventas WHERE numero_venta = %s", (f"MP-{payment_id}",))
        if cursor.fetchone():
            logger.info(f"Pago {payment_id} ya registrado, ignorando")
            return jsonify({'ok': True}), 200

        # ── Recuperar carrito y cliente desde pedidos_pendientes ────────────────
        pedido_ref = payment.get('external_reference') or (order or {}).get('external_reference', '')
        cart_items = []
        cli        = {}
        if pedido_ref:
            try:
                cur_ped = db.cursor()
                cur_ped.execute(
                    "SELECT carrito_json, cliente_json FROM pedidos_pendientes WHERE ref = %s",
                    (pedido_ref,)
                )
                row_ped = cur_ped.fetchone()
                cur_ped.close()
                if row_ped:
                    cart_items = json.loads(row_ped['carrito_json'])
                    cli        = json.loads(row_ped['cliente_json'])
                    # NO borrar todavía — puede llegar otro webhook (merchant_order) que necesita los datos
                    # Se limpia sola por ser tabla temporal (o podemos limpiar viejas periódicamente)
                else:
                    logger.warning(f"pedido_ref no encontrado en DB: {pedido_ref}")
            except Exception as e:
                logger.warning(f"Error recuperando pedido_pendiente {pedido_ref}: {e}")

        # ── Datos del cliente: primero external_reference, luego merchant_order ─
        nombre_cliente   = cli.get('nombre') or 'Comprador web'
        telefono_cliente = cli.get('telefono', '')
        dni_cliente      = cli.get('dni', '')
        email_cliente    = cli.get('email', '')
        direccion        = cli.get('direccion', '')
        cp_cliente       = cli.get('cp', '')
        provincia        = cli.get('provincia', 'Capital Federal')

        shipment_id   = None
        costo_flete   = 0.0
        fecha_entrega = None

        # Completar/actualizar con datos del merchant_order (shipment tiene dirección verificada por ME2)
        if order:
            # Verificar que el merchant_order corresponde al pago actual
            order_payments = order.get('payments', [])
            payment_ids_order = [str(p.get('id', '')) for p in order_payments]
            if payment_id and str(payment_id) not in payment_ids_order and order_payments:
                logger.warning(f"[webhook] merchant_order no corresponde al pago {payment_id} — payments: {payment_ids_order}. Ignorando shipment.")
                order = None  # No usar este merchant_order

        # Con flag shipping_unificado_zipnova='1' no se mandan shipments al
        # preference de MP, así que cualquier shipment_id en el webhook es
        # residual o de otro flujo: lo ignoramos y caemos al path zipnova.
        flag_unificado_wh = _shipping_unificado()

        if order and not flag_unificado_wh:
            shipments = order.get('shipments', [])
            if shipments:
                sh          = shipments[0]
                logger.warning(f"[webhook] SHIPMENT FULL: {json.dumps(sh, default=str)}")
                shipment_id = sh.get('id')
                costo_flete = float(sh.get('shipping_option', {}).get('cost', 0))
                recv        = sh.get('receiver_address', {})
                # Si ME2 tiene datos de contacto, los preferimos (son los validados)
                # Solo usar datos de ME2 si el formulario no los tenía
                if recv.get('contact') and not cli.get('nombre'):
                    nombre_cliente   = recv['contact']
                if recv.get('phone') and not cli.get('telefono'):
                    telefono_cliente = recv['phone']
                if recv.get('address_line'):
                    direccion = f"{recv['address_line']} CP {recv.get('zip_code', '')}"
                if recv.get('state', {}).get('name'):
                    provincia = recv['state']['name']
                est = sh.get('shipping_option', {}).get('estimated_delivery', {})
                if est.get('date'):
                    fecha_entrega = est['date'][:10]
        elif order and flag_unificado_wh and order.get('shipments'):
            logger.warning(f"[webhook] flag shipping_unificado_zipnova activo — ignorando shipment_id en pedido {pedido_ref}")

        importe_producto  = float(payment.get('transaction_amount', 0))
        total_paid        = float(payment.get('total_paid_amount', 0))
        # Si MP cobró el flete al comprador, total_paid incluye todo
        importe_total     = total_paid if total_paid > 0 else importe_producto + costo_flete

        # Notas: solo shipment info (payment_id ya está en numero_venta)
        # order_id = "Venta ID" que figura en la etiqueta de Correo Argentino
        order_id = (order or {}).get('id')

        notas_parts = [f"MPID: {payment_id}"]
        if order_id:
            notas_parts.append(f"VEID: {order_id}")
        if shipment_id:
            notas_parts.append(f"SHID: {shipment_id}")
        if cli.get('demora_dias'):
            fecha_disp = cli.get('fecha_disponible', '')
            notas_parts.append(f"DEMORA: {cli['demora_dias']} días (disponible {fecha_disp})")
        # Cuotas: distingue el pago en 12 cuotas (recargo) del MP normal en 1 cuota
        _inst = int(payment.get('installments', 1) or 1)
        if _inst > 1:
            _nota_cuotas = f"CUOTAS: {_inst}"
            if _inst == 12:
                try:
                    _dbc = get_db(); _cc = _dbc.cursor()
                    _cc.execute("SELECT valor FROM configuracion WHERE clave='cuotas_12_coef'")
                    _rc = _cc.fetchone()
                    _cc.close(); _dbc.close()
                    if _rc and _rc['valor']:
                        _nota_cuotas += f" (recargo coef {float(_rc['valor'])})"
                except Exception:
                    pass
            notas_parts.append(_nota_cuotas)
        notas_extra = "\n".join(notas_parts)

        # ── Tipo de entrega según si hubo shipment ME2 ───────────────────────
        if shipment_id:
            tipo_entrega_val  = 'envio'
            metodo_envio_val  = 'ME2'
        elif cli.get('tipo_entrega') == 'retiro':
            tipo_entrega_val  = 'retiro'
            metodo_envio_val  = None
        elif cli.get('zipnova_quote'):
            tipo_entrega_val  = 'envio'
            costo_flete = float(cli['zipnova_quote'].get('precio', 0))
            carrier_name = cli['zipnova_quote'].get('carrier_name', '')
            if 'flete' in carrier_name.lower() and 'propio' in carrier_name.lower():
                metodo_envio_val = 'Flete Propio'
            else:
                metodo_envio_val = 'Zippin'
        else:
            tipo_entrega_val  = 'envio'
            # Defensa en profundidad: si llega un webhook con envio pero sin
            # shipment ME2 ni zipnova_quote (edge case, pedidos pre-fix), no
            # registrar la venta con metodo_envio=None — el panel la mostraría
            # como "Retiro". Default a 'Flete Propio' + marcar para revisión.
            metodo_envio_val  = 'Flete Propio'
            notas_extra       = (notas_extra + "\nFLETE_SIN_COTIZAR") if notas_extra else "FLETE_SIN_COTIZAR"

        # numero_venta como variable para usarlo en Zipnova y emails
        numero_venta = f"MP-{payment_id}"

        # importe_total = solo productos (sin flete), igual que ventas ML
        importe_solo_productos = sum(float(it.get('precio', 0)) * int(it.get('cantidad', 1)) for it in cart_items) if cart_items else importe_producto

        # Monto realmente cobrado por MP, neto de cupón. transaction_amount incluye el flete.
        _mp_charged = float(payment.get('transaction_amount', 0) or 0)
        if _mp_charged > 0:
            importe_abonado_real = _mp_charged
            importe_total_mp     = max(0.0, round(_mp_charged - costo_flete, 2))
        else:
            # Fallback al comportamiento previo si MP no devolviera transaction_amount
            importe_abonado_real = importe_solo_productos + costo_flete
            importe_total_mp     = importe_solo_productos

        # ── INSERT ventas ─────────────────────────────────────────────────────
        # Fecha en zona horaria Argentina (UTC-3)
        tz_ar     = timezone(timedelta(hours=-3))
        fecha_now = datetime.now(tz_ar).replace(tzinfo=None)

        cursor.execute("""
            INSERT INTO ventas (
                numero_venta, canal, nombre_cliente, telefono_cliente,
                dni_cliente, provincia_cliente, importe_total, importe_abonado,
                metodo_pago, tipo_entrega, metodo_envio,
                direccion_entrega, estado_pago, estado_entrega,
                estado, costo_flete, pago_mercadopago,
                stock_descontado, fecha_entrega_estimada, notas,
                origen_first, origen_last, fecha_venta, fecha_registro
            ) VALUES (
                %s, 'tienda_web', %s, %s,
                %s, %s, %s, %s,
                'MercadoPago', %s, %s,
                %s, 'pagado', 'pendiente',
                'ACTIVA', %s, %s,
                0, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            numero_venta,
            nombre_cliente, telefono_cliente,
            dni_cliente, provincia, importe_total_mp, importe_abonado_real,
            tipo_entrega_val, metodo_envio_val,
            direccion,
            costo_flete, importe_abonado_real,
            fecha_entrega, notas_extra,
            cli.get('_origen_first'), cli.get('_origen_last'),
            fecha_now, fecha_now,
        ))
        venta_id = cursor.lastrowid

        # ── Datos de factura (Factura A) ──────────────────────────────────────
        _fdt, _fdn, _ftt = _factura_fields(cli)
        if _fdt:
            cursor.execute(
                "UPDATE ventas SET factura_doc_type=%s, factura_doc_number=%s, factura_taxpayer_type=%s WHERE id=%s",
                (_fdt, _fdn, _ftt, venta_id)
            )

        # ── Costo comisión MercadoPago (1.5%) ─────────────────────────────────
        cursor.execute(
            "UPDATE ventas SET costo_comision = ROUND(importe_total * 0.015, 2), costo_envio_vendedor = 0 WHERE id = %s",
            (venta_id,)
        )

        # ── INSERT items_venta + descontar stock ──────────────────────────────
        # Ajustar el precio de cada item al neto realmente cobrado (cupón + recargo
        # de cuotas), para que las líneas reflejen lo pagado y sumen el importe_total
        # de la venta. Sin cupón ni recargo el factor es 1 (no cambia nada).
        _factor_item = (importe_total_mp / importe_solo_productos) if importe_solo_productos else 1.0
        if cart_items:
            for it in cart_items:
                _precio_aj = round(float(it['precio']) * _factor_item)
                cursor.execute("""
                    INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (venta_id, it['sku'], it['cantidad'], _precio_aj))
        db.commit()
        # ── Meta CAPI Purchase (server-side) ──────────────────────────────────
        try:
            enviar_capi_purchase(
                numero_venta=numero_venta, email=email_cliente, telefono=telefono_cliente,
                nombre=nombre_cliente, dni=dni_cliente,
                provincia=cli.get('provincia',''), ciudad=cli.get('ciudad',''), cp=cli.get('cp',''),
                total=importe_abonado_real, items=cart_items,
                client_ip=cli.get('_capi_ip'), user_agent=cli.get('_capi_ua'),
                fbp=cli.get('_fbp'), fbc=cli.get('_fbc'),
                source_url=(os.getenv('APP_BASE_URL','') + '/pago/exito'))
        except Exception as _e:
            print(f"[CAPI] webhook_mp: {_e}")
        try:
            from app import enviar_whatsapp
            tel = (telefono_cliente or '').strip().replace('+','').replace(' ','').replace('-','')
            if tel:
                if tel.startswith('0'):
                    tel = '54' + tel[1:]
                elif not tel.startswith('54'):
                    tel = '549' + tel
                enviar_whatsapp(tel, 'tienda_confirmacion', componentes=[{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nombre_cliente or 'Cliente'},
                        {"type": "text", "text": str(numero_venta)}
                    ]
                }])
        except Exception:
            pass

        logger.info(f"Venta registrada: id={venta_id} numero=MP-{payment_id} cliente={nombre_cliente}")
        log_evento('INFO', 'webhook', 'nueva_venta_mp',
            f"Venta tienda web registrada por webhook MP. Número: {numero_venta}. Cliente: {nombre_cliente}. Total: ${importe_solo_productos}. MP Payment ID: {payment_id}",
            venta_id=venta_id)

        # ── Registrar uso de cupón si había uno ──────────────────────────────
        cupon_session = cli.get('cupon')
        if cupon_session and cupon_session.get('id'):
            try:
                cur_cup = db.cursor()
                cur_cup.execute("""
                    INSERT INTO cupones_uso (cupon_id, email, telefono, venta_numero)
                    VALUES (%s, %s, %s, %s)
                """, (cupon_session['id'], email_cliente, telefono_cliente, numero_venta))
                cur_cup.execute(
                    "UPDATE cupones SET usos_actuales = usos_actuales + 1 WHERE id = %s",
                    (cupon_session['id'],)
                )
                db.commit()
                cur_cup.close()
            except Exception as e:
                logger.warning(f"Error registrando uso cupón: {e}")

        # Limpiar pedido pendiente ahora que la venta está confirmada en DB
        if pedido_ref:
            try:
                cur_clean = db.cursor()
                cur_clean.execute("DELETE FROM pedidos_pendientes WHERE ref = %s", (pedido_ref,))
                db.commit()
                cur_clean.close()
            except Exception:
                pass

        # ── Crear envío en Zipnova si corresponde ─────────────────────────────
        zn_tracking_url = ''  # inicializar siempre
        if metodo_envio_val == 'Zippin' and cli.get('zipnova_quote'):
            try:
                db_zn = get_db()
                bultos_zn = armar_bultos_zipnova(cart_items, db_zn)
                db_zn.close()
                total_productos = sum(float(i['precio']) * i['cantidad'] for i in cart_items)
                zn_resp = zipnova_crear_envio(bultos_zn, cli, numero_venta, int(total_productos))
                if not isinstance(zn_resp, dict):
                    logger.warning(f"[zipnova_crear_envio] respuesta inesperada (no dict): {zn_resp}")
                    zn_resp = {}
                zn_id = zn_resp.get('id') or zn_resp.get('shipment_id', '')
                zn_tracking_url = (
                    zn_resp.get('tracking_url') or
                    zn_resp.get('label_url') or
                    zn_resp.get('tracking', {}).get('url', '') or
                    ''
                )
                logger.info(f"Zipnova envío creado: {zn_id} tracking: {zn_tracking_url} para {numero_venta}")
                # Agregar ID y tracking a notas de la venta
                if zn_id:
                    notas_zn = f"\nZNID: {zn_id}"
                    if zn_tracking_url:
                        notas_zn += f"\nZN_URL: {zn_tracking_url}"
                    cursor2 = db.cursor()
                    cursor2.execute(
                        "UPDATE ventas SET notas = CONCAT(notas, %s) WHERE numero_venta = %s",
                        (notas_zn, numero_venta)
                    )
                    db.commit()
                    cursor2.close()
            except Exception as e_zn:
                logger.error(f"Error creando envío Zipnova para {numero_venta}: {e_zn}")
                zn_tracking_url = ''
                # No falla el webhook, solo logueamos

        # Enviar email de confirmación al cliente
        enviar_email_confirmacion(
            payment_id           = payment_id,
            nombre_cliente       = nombre_cliente,
            email_cliente        = email_cliente,
            items                = cart_items,
            tipo_entrega         = cli.get('tipo_entrega', 'envio'),
            direccion            = direccion,
            fecha_entrega        = fecha_entrega,
            importe_total        = importe_total,
            costo_flete          = costo_flete,
            zipnova_tracking_url = zn_tracking_url if metodo_envio_val == 'Zippin' else None,
            demora_dias          = cli.get('demora_dias', 0),
            fecha_disponible     = cli.get('fecha_disponible', ''),
        )

        # Enviar notificación al vendedor
        enviar_email_vendedor(
            payment_id        = payment_id,
            nombre_cliente    = nombre_cliente,
            email_cliente     = email_cliente,
            telefono          = telefono_cliente,
            items             = cart_items,
            tipo_entrega      = cli.get('tipo_entrega', 'envio'),
            direccion         = direccion,
            importe_total     = importe_total,
            metodo_envio      = metodo_envio_val,
            demora_dias       = cli.get('demora_dias', 0),
            fecha_disponible  = cli.get('fecha_disponible', ''),
        )

    except Exception as e:
        logger.error(f"Error webhook MP: {e}", exc_info=True)
        log_evento('ERROR', 'webhook', 'error_webhook_mp',
            f"Error procesando webhook MP. Payment ID: {payment_id}. Error: {str(e)}")
        if db:
            db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

    # ── Sincronizar publicaciones ML en background ────────────────────────────
    try:
        import threading
        from app import actualizar_publicaciones_ml_con_progreso, _extraer_skus_base_de_items
        skus_afectados = _extraer_skus_base_de_items(
            [{'sku': it['sku'], 'cantidad': it['cantidad']} for it in cart_items] if cart_items else []
        )
        if skus_afectados:
            def _sync_ml():
                try:
                    actualizar_publicaciones_ml_con_progreso(skus_afectados)
                except Exception as e_ml:
                    logger.warning(f"[TIENDA-ML] Error sync ML: {e_ml}")
            threading.Thread(target=_sync_ml, daemon=True).start()
    except Exception as e_sync:
        logger.warning(f"[TIENDA-ML] No se pudo iniciar sync ML: {e_sync}")

    return jsonify({'ok': True}), 200


# ── WEBHOOK GETNET ─────────────────────────────────────────────────────────────

@tienda_bp.route('/webhook/getnet', methods=['POST'])
def webhook_getnet():
    """
    Recibe notificaciones de GetNet cuando el pago es aprobado.
    Registra la venta en DB siguiendo el mismo patrón que webhook_mp.
    Prefijo de venta: GN-{pedido_ref} (usando merchant_reference como ID).
    """
    import base64

    # Validación Basic Auth — GetNet envía credenciales configuradas en su portal
    expected_user = os.getenv('GETNET_WEBHOOK_USER', '').strip()
    expected_pass = os.getenv('GETNET_WEBHOOK_PASS', '').strip()

    if expected_user and expected_pass:
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Basic '):
            print(f'[webhook_getnet] AUTH FAIL: header missing or invalid format', flush=True)
            return jsonify(ok=False, error='unauthorized'), 401

        try:
            encoded_creds = auth_header.split(' ', 1)[1]
            decoded = base64.b64decode(encoded_creds).decode('utf-8')
            recv_user, recv_pass = decoded.split(':', 1)
        except Exception as e:
            print(f'[webhook_getnet] AUTH FAIL: cannot decode credentials: {e}', flush=True)
            return jsonify(ok=False, error='unauthorized'), 401

        if recv_user != expected_user or recv_pass != expected_pass:
            print(f'[webhook_getnet] AUTH FAIL: credentials mismatch (recv_user={recv_user})', flush=True)
            return jsonify(ok=False, error='unauthorized'), 401

        print(f'[webhook_getnet] AUTH OK: user={recv_user}', flush=True)
    else:
        # Si las vars no están configuradas, loggear warning pero permitir
        # (modo desarrollo / UAT donde no se configuró Basic Auth)
        print(f'[webhook_getnet] WARNING: GETNET_WEBHOOK_USER/PASS no configurados — sin validación de auth', flush=True)

    data = request.get_json() or {}
    print(f'[webhook_getnet] Payload completo: {json.dumps(data, ensure_ascii=False, default=str)}', flush=True)

    # Estructura real del webhook GetNet:
    # { "order_id": "...", "payment": { "brand": ..., "last_four_digits": ...,
    #   "installment": {...}, "result": { "payment_id": ..., "status": "Authorized",
    #   "authorization_code": ..., ... } }, ... }
    pay_info    = data.get('payment') or {}
    pay_result  = pay_info.get('result') or {}
    installment = pay_info.get('installment') or {}

    status = pay_result.get('status', '')

    if status != 'Authorized':
        print(f'[webhook_getnet] Status "{status}" — no se registra venta.', flush=True)
        return jsonify(ok=True), 200

    # Datos del pago para guardar en notas
    pedido_ref    = data.get('order_id', '')
    gn_payment_id = pay_result.get('payment_id', '')
    auth_code     = pay_result.get('authorization_code', '')
    brand         = pay_info.get('brand', '')
    last_four     = pay_info.get('last_four_digits', '')
    cuotas_gn     = installment.get('number', '')

    if not pedido_ref:
        print(f'[webhook_getnet] Sin order_id en payload: {data}', flush=True)
        return jsonify({'error': 'Sin referencia de pedido'}), 400

    db     = None
    cursor = None
    try:
        db     = get_db()
        cursor = db.cursor()

        # Evitar duplicados
        numero_venta = f"GN-{pedido_ref}"
        cursor.execute("SELECT id FROM ventas WHERE numero_venta = %s", (numero_venta,))
        if cursor.fetchone():
            logger.info(f'[webhook_getnet] Venta ya registrada: {numero_venta}')
            return jsonify({'ok': True}), 200

        # Recuperar pedido desde pedidos_pendientes_getnet (snapshot creado por
        # /pago/getnet/crear). NO usamos la tabla legacy pedidos_pendientes.
        cursor.execute("""
            SELECT pedido_ref, payment_intent_id, datos_cliente, datos_carrito,
                   total, costo_flete, metodo_envio, direccion, estado
            FROM pedidos_pendientes_getnet
            WHERE pedido_ref = %s
        """, (pedido_ref,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f'[webhook_getnet] Pedido pendiente no encontrado: {pedido_ref} — webhook ignorado.')
            return jsonify({'ok': False, 'error': 'pedido_not_found'}), 404
        if row['estado'] == 'procesado':
            logger.info(f'[webhook_getnet] Pedido ya procesado: {pedido_ref}')
            return jsonify({'ok': True}), 200

        cart_items       = json.loads(row['datos_carrito'])
        cli              = json.loads(row['datos_cliente'])
        total_con_coef   = float(row['total'])
        costo_flete_adj  = float(row['costo_flete'] or 0)
        metodo_envio_val = row['metodo_envio'] or None
        direccion        = row['direccion'] or cli.get('direccion', '') or ''

        # Datos derivados del cliente (solo lectura)
        nombre_cliente   = cli.get('nombre', 'Comprador web')
        telefono_cliente = cli.get('telefono', '')
        dni_cliente      = cli.get('dni', '')
        email_cliente    = cli.get('email', '')
        provincia        = cli.get('provincia', 'Capital Federal')
        tipo_entrega_val = cli.get('tipo_entrega', 'envio')

        # Defensa en profundidad: si llega un webhook con envio pero sin
        # metodo_envio en el snapshot (edge case, pedidos pre-fix), no registrar
        # la venta como "Retiro". Default a 'Flete Propio' + marcar para revisión.
        _flete_sin_cotizar_flag = False
        if tipo_entrega_val == 'envio' and not metodo_envio_val:
            metodo_envio_val = 'Flete Propio'
            _flete_sin_cotizar_flag = True

        _, coef_6 = get_coeficientes_cuotas()  # solo para la nota informativa

        # Recalcular factor_cupon para que items_venta coincida con el total guardado
        cupon_cli = cli.get('cupon')
        subtotal_carrito = sum(float(it['precio']) * int(it['cantidad']) for it in cart_items)
        if cupon_cli:
            if cupon_cli['tipo'] == 'pct':
                factor_cupon = 1 - float(cupon_cli['valor']) / 100
            else:
                desc_fijo = min(float(cupon_cli['valor']), subtotal_carrito)
                factor_cupon = (subtotal_carrito - desc_fijo) / subtotal_carrito if subtotal_carrito else 1
        else:
            factor_cupon = 1

        tz_ar     = timezone(timedelta(hours=-3))
        fecha_now = datetime.now(tz_ar).replace(tzinfo=None)

        # importe_total = solo productos (sin flete), igual que ventas ML/MP
        importe_solo_productos = total_con_coef - costo_flete_adj
        # importe_abonado = monto real cobrado por GetNet (productos + flete) → flete verde
        importe_abonado_real = float(pay_info.get('amount', 0)) / 100

        notas_parts = [
            f"GN_PID: {gn_payment_id}",
            f"AUTH: {auth_code}",
            f"Tarjeta: {brand} ****{last_four}",
            f"Cuotas: {cuotas_gn} (MiPyme)",
            f"Coef: {coef_6}",
        ]
        if cli.get('demora_dias'):
            notas_parts.append(f"DEMORA: {cli['demora_dias']} dias ({cli.get('fecha_disponible','')})")
        if _flete_sin_cotizar_flag:
            notas_parts.append("FLETE_SIN_COTIZAR")
        notas_extra = "\n".join(notas_parts)

        # INSERT ventas
        cursor.execute("""
            INSERT INTO ventas (
                numero_venta, canal, nombre_cliente, telefono_cliente,
                dni_cliente, provincia_cliente, importe_total, importe_abonado,
                metodo_pago, tipo_entrega, metodo_envio,
                direccion_entrega, estado_pago, estado_entrega,
                estado, costo_flete, pago_mercadopago,
                stock_descontado, notas, origen_first, origen_last, fecha_venta, fecha_registro
            ) VALUES (
                %s, 'tienda_web', %s, %s,
                %s, %s, %s, %s,
                'GetNet', %s, %s,
                %s, 'pagado', 'pendiente',
                'ACTIVA', %s, 0,
                0, %s, %s, %s, %s, %s
            )
        """, (
            numero_venta,
            nombre_cliente, telefono_cliente,
            dni_cliente, provincia,
            importe_solo_productos, importe_abonado_real,
            tipo_entrega_val, metodo_envio_val,
            direccion,
            costo_flete_adj,
            notas_extra, cli.get('_origen_first'), cli.get('_origen_last'), fecha_now, fecha_now,
        ))
        venta_id = cursor.lastrowid

        # ── Datos de factura (Factura A) ──────────────────────────────────────
        _fdt, _fdn, _ftt = _factura_fields(cli)
        if _fdt:
            cursor.execute(
                "UPDATE ventas SET factura_doc_type=%s, factura_doc_number=%s, factura_taxpayer_type=%s WHERE id=%s",
                (_fdt, _fdn, _ftt, venta_id)
            )

        # ── Costo comisión GetNet (13.82%) ────────────────────────────────────
        cursor.execute(
            "UPDATE ventas SET costo_comision = ROUND(importe_total * 0.1382, 2), costo_envio_vendedor = 0 WHERE id = %s",
            (venta_id,)
        )

        # Items con precio ajustado por cupón + coeficiente
        # cart_items_adj se reutiliza más abajo para los emails (mismo patrón que Payway)
        cart_items_adj = [
            dict(it, precio=round(float(it['precio']) * factor_cupon * coef_6))
            for it in cart_items
        ]
        for it in cart_items_adj:
            cursor.execute(
                "INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
                (venta_id, it['sku'], int(it['cantidad']), it['precio'])
            )

        db.commit()
        # ── Meta CAPI Purchase (server-side) ──────────────────────────────────
        try:
            enviar_capi_purchase(
                numero_venta=numero_venta, email=email_cliente, telefono=telefono_cliente,
                nombre=nombre_cliente, dni=dni_cliente,
                provincia=cli.get('provincia',''), ciudad=cli.get('ciudad',''), cp=cli.get('cp',''),
                total=importe_abonado_real, items=cart_items_adj,
                client_ip=cli.get('_capi_ip'), user_agent=cli.get('_capi_ua'),
                fbp=cli.get('_fbp'), fbc=cli.get('_fbc'),
                source_url=(os.getenv('APP_BASE_URL','') + '/pago/exito'))
        except Exception as _e:
            print(f"[CAPI] webhook_getnet: {_e}")
        try:
            from app import enviar_whatsapp
            tel = (telefono_cliente or '').strip().replace('+','').replace(' ','').replace('-','')
            if tel:
                if tel.startswith('0'):
                    tel = '54' + tel[1:]
                elif not tel.startswith('54'):
                    tel = '549' + tel
                enviar_whatsapp(tel, 'tienda_confirmacion', componentes=[{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nombre_cliente or 'Cliente'},
                        {"type": "text", "text": str(numero_venta)}
                    ]
                }])
        except Exception:
            pass

        logger.info(f'[webhook_getnet] Venta registrada: id={venta_id} numero={numero_venta} cliente={nombre_cliente}')
        log_evento('INFO', 'webhook', 'nueva_venta_getnet',
            f"Venta tienda web registrada por webhook GetNet. Número: {numero_venta}. Cliente: {nombre_cliente}. Total: ${total_con_coef}.",
            venta_id=venta_id)

        # Registrar uso de cupón si había uno
        cupon_session = cli.get('cupon')
        if cupon_session and cupon_session.get('id'):
            try:
                cur_cup = db.cursor()
                cur_cup.execute(
                    "INSERT INTO cupones_uso (cupon_id, email, telefono, venta_numero) VALUES (%s,%s,%s,%s)",
                    (cupon_session['id'], email_cliente, telefono_cliente, numero_venta)
                )
                cur_cup.execute(
                    "UPDATE cupones SET usos_actuales = usos_actuales + 1 WHERE id = %s",
                    (cupon_session['id'],)
                )
                db.commit()
                cur_cup.close()
            except Exception as e:
                logger.warning(f'[webhook_getnet] Error cupon: {e}')

        # Marcar pedido pendiente como procesado (no eliminar — se mantiene para auditoría)
        try:
            cur_clean = db.cursor()
            cur_clean.execute(
                "UPDATE pedidos_pendientes_getnet SET estado = 'procesado' WHERE pedido_ref = %s",
                (pedido_ref,)
            )
            db.commit()
            cur_clean.close()
        except Exception as e_clean:
            logger.warning(f'[webhook_getnet] Error marcando pedido procesado: {e_clean}')

        # Emails — usar cart_items_adj (precios con cupón + coef ya aplicados)
        try:
            enviar_email_confirmacion(
                payment_id       = pedido_ref,
                nombre_cliente   = nombre_cliente,
                email_cliente    = email_cliente,
                items            = cart_items_adj,
                tipo_entrega     = tipo_entrega_val,
                direccion        = direccion,
                fecha_entrega    = None,
                importe_total    = total_con_coef,
                costo_flete      = costo_flete_adj,
                canal            = 'getnet',
                demora_dias      = cli.get('demora_dias', 0),
                fecha_disponible = cli.get('fecha_disponible', ''),
            )
        except Exception as e:
            logger.warning(f'[webhook_getnet] Error email cliente: {e}')

        try:
            enviar_email_vendedor(
                payment_id       = pedido_ref,
                nombre_cliente   = nombre_cliente,
                email_cliente    = email_cliente,
                telefono         = telefono_cliente,
                items            = cart_items_adj,
                tipo_entrega     = tipo_entrega_val,
                direccion        = direccion,
                importe_total    = total_con_coef,
                metodo_envio     = metodo_envio_val,
                demora_dias      = cli.get('demora_dias', 0),
                fecha_disponible = cli.get('fecha_disponible', ''),
                canal            = 'getnet',
            )
        except Exception as e:
            logger.warning(f'[webhook_getnet] Error email vendedor: {e}')

    except Exception as e:
        logger.error(f'[webhook_getnet] Error: {e}', exc_info=True)
        log_evento('ERROR', 'webhook', 'error_webhook_getnet',
            f"Error procesando webhook GetNet. Pedido: {pedido_ref}. Error: {str(e)}")
        if db:
            db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

    # ── Sincronizar publicaciones ML en background ────────────────────────────
    try:
        import threading
        from app import actualizar_publicaciones_ml_con_progreso, _extraer_skus_base_de_items
        skus_afectados = _extraer_skus_base_de_items(
            [{'sku': it['sku'], 'cantidad': it['cantidad']} for it in cart_items] if cart_items else []
        )
        if skus_afectados:
            def _sync_ml_getnet():
                try:
                    actualizar_publicaciones_ml_con_progreso(skus_afectados)
                except Exception as e_ml:
                    logger.warning(f"[TIENDA-ML] Error sync ML GetNet: {e_ml}")
            threading.Thread(target=_sync_ml_getnet, daemon=True).start()
    except Exception as e_sync:
        logger.warning(f"[TIENDA-ML] No se pudo iniciar sync ML GetNet: {e_sync}")

    return jsonify({'ok': True}), 200


def _descontar_stock_por_sku(cart_items, cursor):
    """Descuenta stock usando los SKUs reales del carrito."""
    for item in cart_items:
        sku = item['sku']
        qty = int(item['cantidad'])
        cursor.execute("""
            UPDATE productos_base SET stock_actual = GREATEST(0, stock_actual - %s)
            WHERE sku = %s
        """, (qty, sku))
        logger.info(f"Stock descontado: {sku} x{qty}")


def _descontar_stock(items):
    """Fallback público (compatibilidad). Abre su propia conexión."""
    db     = get_db()
    cursor = db.cursor()
    try:
        _descontar_stock_fallback(items, cursor)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error _descontar_stock: {e}")
    finally:
        cursor.close()
        db.close()


def _descontar_stock_fallback(items, cursor):
    """Descuenta stock buscando SKU por título (cuando no hay external_reference)."""
    for item in items:
        titulo = item.get('title', '')
        qty    = int(item.get('quantity', 1))
        # Intentar usar item id como SKU primero
        sku_directo = item.get('id')
        if sku_directo:
            cursor.execute("""
                SELECT sku FROM productos_base WHERE activo = 1 AND sku = %s LIMIT 1
            """, (sku_directo,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE productos_base SET stock_actual = GREATEST(0, stock_actual - %s)
                    WHERE sku = %s
                """, (qty, sku_directo))
                continue
        # Fallback por nombre
        cursor.execute("""
            SELECT sku FROM productos_base WHERE activo = 1 AND nombre LIKE %s LIMIT 1
        """, (f'%{titulo}%',))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE productos_base SET stock_actual = GREATEST(0, stock_actual - %s)
                WHERE sku = %s
            """, (qty, row['sku']))


# ── SITEMAP ───────────────────────────────────────────────────────────────────

@tienda_bp.route('/sitemap.xml')
def sitemap():
    from flask import Response
    BASE = 'https://www.mercadomuebles.com.ar'

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT p.sku, p.modelo, p.medida,
               COALESCE(p.fecha_actualizacion, p.fecha_creacion) as lastmod
        FROM productos_base p
        WHERE p.tipo = 'colchon' AND p.precio_base > 0
          AND p.medida IS NOT NULL AND p.stock_actual > 0
          AND p.sku NOT LIKE '%_FULL%'
        ORDER BY p.modelo, p.medida
    """)
    colchones = cursor.fetchall()

    cursor.execute("SELECT colchon_sku FROM conjunto_configuracion WHERE activo=1")
    conjuntos_skus = {r['colchon_sku'] for r in cursor.fetchall()}
    cursor.close()
    db.close()

    urls = []
    urls.append(f'  <url><loc>{BASE}/tienda/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
    for linea in ['espuma', 'resortes', 'box']:
        urls.append(f'  <url><loc>{BASE}/tienda/?linea={linea}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')

    for col in colchones:
        modelo  = col['modelo'] or ''
        medida  = col['medida'] or ''
        lastmod = col['lastmod'].strftime('%Y-%m-%d') if col['lastmod'] else '2026-01-01'
        slug_c  = slugify(f"Colchón Cannon {modelo} {medida}cm")
        urls.append(f'  <url><loc>{BASE}/tienda/producto/{slug_c}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>')
        if col['sku'] in conjuntos_skus:
            slug_s = slugify(f"Sommier y Colchón Cannon {modelo} {medida}cm")
            urls.append(f'  <url><loc>{BASE}/tienda/producto/{slug_s}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>')

    xml  = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join(urls)
    xml += '\n</urlset>'
    return Response(xml, mimetype='application/xml')


# ── SEGUIMIENTO DE PEDIDO ──────────────────────────────────────────────────────

@tienda_bp.route('/seguimiento')
def seguimiento():
    """
    El cliente ingresa su número de venta (MP-XXXXXXX) o payment_id.
    Muestra estado del pago y del envío (consultando ME2 si aplica).
    """
    numero = request.args.get('numero', '').strip()
    venta  = None
    items  = []
    shipment_info = None
    error  = None
    mpid   = None
    trid   = None
    estado_especial = None
    fecha_pendiente = None
    demora_dias_seg      = 0
    fecha_disponible_seg = ''

    if numero:
        db     = get_db()
        cursor = db.cursor()
        try:
            # Buscar por numero_venta (MP-/GN-/PW-...) o por payment_id si son solo dígitos
            if numero.startswith('MP-') or numero.startswith('GN-') or numero.startswith('PW-'):
                busqueda = numero
            else:
                busqueda = f"MP-{numero}"
            cursor.execute("""
                SELECT v.*, GROUP_CONCAT(CONCAT(i.cantidad,'x ',i.sku) SEPARATOR ', ') AS productos_str
                FROM ventas v
                LEFT JOIN items_venta i ON i.venta_id = v.id
                WHERE v.numero_venta = %s AND v.canal = 'tienda_web'
                GROUP BY v.id
            """, (busqueda,))
            venta = cursor.fetchone()

            if venta:
                # Items detallados
                cursor.execute("""
                    SELECT iv.sku, iv.cantidad, iv.precio_unitario, pb.nombre
                    FROM items_venta iv
                    LEFT JOIN productos_base pb ON pb.sku = iv.sku
                    WHERE iv.venta_id = %s
                """, (venta['id'],))
                items = cursor.fetchall()

                # Parsear notas: SHID, ZNID, ZN_URL
                notas = venta.get('notas', '') or ''
                shid = None
                znid = None
                zn_url = None
                # Las notas pueden tener \n literal o salto de línea real
                notas_norm = notas.replace('\\n', '\n')
                logger.warning(f"[seguimiento] notas raw: {repr(notas)}")
                logger.warning(f"[seguimiento] notas norm: {repr(notas_norm)}")
                trid = None
                mpid = None
                demora_dias_seg = 0
                fecha_disponible_seg = ''
                for linea in notas_norm.split('\n'):
                    linea = linea.strip()
                    if linea.startswith('SHID:'):
                        try: shid = int(linea.split(':', 1)[1].strip())
                        except Exception: pass
                    elif linea.startswith('ZNID:'):
                        znid = linea.split(':', 1)[1].strip()
                    elif linea.startswith('ZN_URL:'):
                        zn_url = linea.split(':', 1)[1].strip()
                    elif linea.startswith('TRID:'):
                        trid = linea.split(':', 1)[1].strip()
                    elif linea.startswith('MPID:'):
                        mpid = linea.split(':', 1)[1].strip()
                    elif linea.startswith('DEMORA:'):
                        # Formato: "DEMORA: 10 dias (disponible 23/04/2026)" o "DEMORA: 10 días (disponible 23/04/2026)"
                        import re as _re
                        _m = _re.search(r'(\d+)\s+d[ií]as?.*?(\d{2}/\d{2}/\d{4})', linea)
                        if _m:
                            demora_dias_seg = int(_m.group(1))
                            fecha_disponible_seg = _m.group(2)
                        else:
                            _m2 = _re.search(r'(\d+)', linea)
                            if _m2:
                                demora_dias_seg = int(_m2.group(1))

                metodo_envio = venta.get('metodo_envio', '') or ''
                logger.warning(f"[seguimiento] shid={shid} znid={znid} metodo_envio={metodo_envio!r}")

                if shid and metodo_envio == 'ME2':
                    trid_numeric = trid.lstrip('HC').rstrip('AR') if trid else ''
                    shipment_info = {
                        'status':          'Envío generado',
                        'tracking_number': str(shid),
                        'correo_url':      f'https://www.correoargentino.com.ar/formularios/ondnc?id={trid_numeric}' if trid_numeric else '',
                        'trid':            trid or '',
                        'estimated_delivery': '',
                        'tipo': 'me2',
                    }

                elif znid and metodo_envio in ('ZIPNOVA', 'Zippin', 'Flete Propio'):
                    # Info del envío Zipnova
                    shipment_info = {
                        'status':      'Envío generado',
                        'tracking_number': znid,
                        'correo_url':  zn_url or '',
                        'tipo':        'zipnova',
                    }
            else:
                # Si es un GN-, todavía puede estar en pedidos_pendientes_getnet
                # (pago iniciado pero webhook todavía no llegó / no aprobado).
                if busqueda.startswith('GN-'):
                    pedido_ref_seg = busqueda[3:]
                    cursor.execute("""
                        SELECT pedido_ref, fecha_creacion, estado
                        FROM pedidos_pendientes_getnet
                        WHERE pedido_ref = %s
                    """, (pedido_ref_seg,))
                    pendiente = cursor.fetchone()
                    if pendiente and pendiente['estado'] == 'pendiente':
                        estado_especial = 'verificando_pago'
                        fecha_pendiente = pendiente['fecha_creacion']
                    else:
                        error = 'No encontramos ningún pedido con ese número.'
                else:
                    error = 'No encontramos ningún pedido con ese número.'

        except Exception as e:
            logger.error(f"Error seguimiento: {e}")
            error = 'Error al buscar el pedido. Intentá de nuevo.'
        finally:
            cursor.close()
            db.close()

    carrito_count = sum(i['cantidad'] for i in session.get('carrito', []))
    return render_template('tienda/seguimiento.html',
        numero=numero,
        venta=venta,
        items=items,
        shipment_info=shipment_info,
        error=error,
        carrito_count=carrito_count,
        mpid=mpid,
        demora_dias=demora_dias_seg if numero else 0,
        fecha_disponible=fecha_disponible_seg if numero else '',
        estado_especial=estado_especial,
        fecha_pendiente=fecha_pendiente,
    )

@tienda_bp.route('/privacidad')
def privacidad():
    from flask import render_template
    return render_template('tienda/privacidad.html', carrito_count=len(session.get('carrito', [])))

@tienda_bp.route('/devoluciones')
def devoluciones():
    from flask import render_template
    return render_template('tienda/devoluciones.html', carrito_count=len(session.get('carrito', [])))


@tienda_bp.route('/test-getnet', methods=['GET', 'POST'])
def test_getnet():
    """Página de prueba del iframe GetNet — sin auth (URL no publicada). No registra venta."""
    import time

    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT sku, nombre, precio_base AS precio
        FROM productos_base
        WHERE activo = 1 AND precio_base > 0
        ORDER BY nombre
        LIMIT 50
    """)
    productos = cur.fetchall()
    cur.close()
    db.close()

    iframe_url        = None
    payment_intent_id = None
    error             = None
    producto_sel      = None

    if request.method == 'POST':
        sku    = request.form.get('sku')
        nombre = request.form.get('nombre') or ''
        precio = float(request.form.get('precio', 0) or 0)
        cuotas = int(request.form.get('cuotas', 6) or 6)

        coef_3, coef_6 = get_coeficientes_cuotas()
        coef  = coef_3 if cuotas == 3 else coef_6
        total = round(precio * coef)

        producto_sel = {'sku': sku, 'nombre': nombre, 'precio': precio, 'total': total, 'cuotas': cuotas}

        try:
            import requests as req_lib
            # /test-getnet SIEMPRE pega al sandbox (UAT), nunca a producción,
            # aunque las credenciales de prod estén cargadas.
            base_url = os.getenv('GETNET_BASE_URL_UAT')
            token    = _getnet_get_token(force_uat=True)

            test_ref = f"TEST-{sku}-{int(time.time())}"
            body = {
                "order_id": test_ref,
                "redirect_urls": {
                    # GetNet strippea query params al redirigir → usar pedido_ref en el path
                    "success": url_for('tienda.pago_exito_getnet', pedido_ref=test_ref, _external=True),
                    "failed":  url_for('tienda.pago_error', _external=True) + "?canal=getnet"
                },
                "payment": {"amount": int(total * 100), "currency": "ARS"},
                "product": [{"title": (nombre or sku or 'Producto')[:50], "value": int(total * 100), "quantity": 1}],
                "customer": {
                    "customer_id":     "test-admin",
                    "first_name":      "Admin",
                    "last_name":       "Test",
                    "name":            "Admin Test",
                    "email":           "admin@mercadomuebles.com.ar",
                    "document_type":   "dni",
                    "document_number": "00000000",
                    "phone_number":    "5491100000000"
                }
            }

            resp = req_lib.post(
                f"{base_url}/digital-checkout/v1/payment-intent",
                json=body,
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            iframe_url        = data['redirect_url']
            payment_intent_id = data.get('payment_intent_id')
            print(f"[test_getnet] payment_intent_id={payment_intent_id} total={total} cuotas={cuotas}", flush=True)

        except Exception as e:
            error = str(e)
            print(f"[test_getnet] ERROR: {e}", flush=True)

    return render_template(
        'tienda/test_getnet.html',
        productos=productos,
        iframe_url=iframe_url,
        payment_intent_id=payment_intent_id,
        producto_sel=producto_sel,
        error=error,
        getnet_env='UAT (sandbox)',
        getnet_base_url=os.getenv('GETNET_BASE_URL_UAT'),
    )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA DE PRUEBA — MERCADO PAGO (sandbox aislado, NO registra venta)
# Valida: 12 cuotas fijas + whitelist de marcas + 3DS. URL no publicada.
# Usa SOLO credenciales de test (MP_*_TEST). No afecta el checkout real.
# ════════════════════════════════════════════════════════════════════════════
TEST_MP_RECARGO = 1.60  # recargo de prueba: 60%


@tienda_bp.route('/test-mp', methods=['GET'])
def test_mp():
    """Página de prueba MP — sin auth (URL no publicada). No registra venta."""
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT sku, nombre, precio_base AS precio
        FROM productos_base
        WHERE activo = 1 AND precio_base > 0
        ORDER BY nombre
        LIMIT 50
    """)
    productos = cur.fetchall()
    cur.close()
    db.close()

    cred_ok = bool(os.environ.get('MP_ACCESS_TOKEN_TEST', '').strip())
    return render_template(
        'tienda/test_mp.html',
        productos=productos,
        mp_public_key_test=os.getenv('MP_PUBLIC_KEY_TEST', ''),
        recargo_pct=int(round((TEST_MP_RECARGO - 1) * 100)),
        cred_ok=cred_ok,
    )


@tienda_bp.route('/test-mp/preparar', methods=['POST'])
def test_mp_preparar():
    """Calcula total con recargo + cupón y crea una preference de PRUEBA."""
    data   = request.get_json() or {}
    sku    = (data.get('sku') or '').strip()
    nombre = (data.get('nombre') or 'Producto')[:60]
    precio = float(data.get('precio', 0) or 0)
    cupon  = (data.get('cupon') or '').strip().upper()

    if precio <= 0:
        return jsonify({'ok': False, 'error': 'Elegí un producto válido'}), 400

    # Cupón opcional — mismo criterio que validar_cupon, sin tocar la sesión real
    descuento   = 0
    cupon_label = None
    if cupon:
        db = get_db(); cur = db.cursor()
        try:
            cur.execute("SELECT * FROM cupones WHERE codigo=%s AND activo=1", (cupon,))
            c = cur.fetchone()
            if not c:
                return jsonify({'ok': False, 'error': 'Cupón inválido o inactivo'}), 400
            from datetime import date
            if c['fecha_vencimiento'] and c['fecha_vencimiento'] < date.today():
                return jsonify({'ok': False, 'error': 'Cupón vencido'}), 400
            if c['tipo'] == 'pct':
                descuento   = round(precio * float(c['valor']) / 100)
                cupon_label = f"-{int(c['valor'])}%"
            else:
                descuento   = min(float(c['valor']), precio)
                cupon_label = f"-{format_price(c['valor'])}"
        finally:
            cur.close(); db.close()

    base  = max(0, precio - descuento)
    total = round(base * TEST_MP_RECARGO)
    if total <= 0:
        return jsonify({'ok': False, 'error': 'Total inválido'}), 400

    try:
        sdk = get_mp_sdk_test()
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Credenciales de prueba: {e}'}), 500

    import time as _t
    pref = {
        'items': [{
            'title':       nombre,
            'quantity':    1,
            'unit_price':  float(total),
            'currency_id': 'ARS',
        }],
        # default_installments=12 hace que mobile venga ya con 12 preseleccionado
        'payment_methods':    {'installments': 12, 'default_installments': 12},
        'external_reference': f"TESTMP-{sku}-{int(_t.time())}",
    }
    result     = sdk.preference().create(pref)
    preference = result.get('response', {}) or {}
    if 'id' not in preference:
        logger.error(f"[test_mp] error preference: {result}")
        return jsonify({'ok': False, 'error': 'No se pudo crear la preferencia de prueba'}), 500

    # Total autoritativo del server para /test-mp/pagar (no confío en el cliente)
    session['test_mp_total'] = total
    session.modified = True

    return jsonify({
        'ok':            True,
        'preference_id': preference['id'],
        'total':         total,
        'total_fmt':     format_price(total),
        'cuota_fmt':     format_price(round(total / 12)),
        'descuento':     descuento,
        'descuento_fmt': format_price(descuento) if descuento else None,
        'cupon_label':   cupon_label,
    })


@tienda_bp.route('/test-mp/pagar', methods=['POST'])
def test_mp_pagar():
    """Ejecuta el pago de PRUEBA con installments=12 forzado + 3DS. NO registra venta."""
    data  = request.get_json() or {}
    total = float(session.get('test_mp_total', 0) or 0)
    if total <= 0:
        return jsonify({'ok': False, 'error': 'Sesión sin total; volvé a preparar el pago'}), 400

    try:
        sdk = get_mp_sdk_test()
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Credenciales de prueba: {e}'}), 500

    payment_data = {
        'transaction_amount':   total,            # autoritativo del server, no del cliente
        'token':                data.get('token'),
        'payment_method_id':    data.get('payment_method_id', ''),
        'installments':         12,               # FORZADO server-side
        'payer':                data.get('payer', {}),
        'statement_descriptor': 'MM TEST',
        'three_d_secure_mode':  'optional',       # habilita 3DS
    }
    if data.get('issuer_id'):
        payment_data['issuer_id'] = data['issuer_id']

    try:
        result  = sdk.payment().create(payment_data)
        payment = result.get('response', {}) or {}
        status  = payment.get('status', 'error')
        detail  = payment.get('status_detail', '')
        pid     = payment.get('id', '')
        logger.info(f"[test_mp_pagar] status={status} detail={detail} pid={pid} inst={payment.get('installments')}")

        resp = {
            'ok':            True,
            'status':        status,
            'status_detail': detail,
            'payment_id':    pid,
            'installments':  payment.get('installments'),
            'amount':        payment.get('transaction_amount'),
        }
        if status == 'pending' and detail == 'pending_challenge':
            tds = payment.get('three_ds_info', {}) or {}
            resp['three_ds_info'] = {
                'external_resource_url': tds.get('external_resource_url'),
                'creq':                  tds.get('creq'),
            }
        return jsonify(resp)
    except Exception as e:
        logger.error(f"[test_mp_pagar] excepcion: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500
