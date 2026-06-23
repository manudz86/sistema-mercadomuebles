# -*- coding: utf-8 -*-
"""
Módulo COCINAR · app de comidas + lista de compras.

ACCESO: PÚBLICO por URL. Se entra solo conociendo /cocinar.
  - NO usa el login del sistema ni se enlaza desde el panel.
  - IMPORTANTE: si app.py tiene un guard global de login (un before_request que
    exige sesión), hay que EXIMIR el prefijo /cocinar para que entre sin loguearse.

BASE DE DATOS: PROPIA y SEPARADA (schema `cocina`). No toca inventario_cannon.

INTEGRACIÓN en app.py (solo 2 líneas):
    from cocinar_bp import cocinar_bp
    app.register_blueprint(cocinar_bp)
"""
import os
import json
from flask import Blueprint, render_template, request, jsonify, Response

cocinar_bp = Blueprint("cocinar", __name__, template_folder="templates")


# ============================================================
# Conexión a su PROPIO schema `cocina` (no toca inventario_cannon).
# Usa las credenciales del servidor MySQL ya existentes (DB_HOST/DB_USER/DB_PASS)
# pero apunta SIEMPRE a la base `cocina`. Se puede sobreescribir con COCINA_DB_*.
# El usuario MySQL necesita permiso sobre el schema `cocina`.
# ============================================================
def _conn():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("COCINA_DB_HOST", os.environ.get("DB_HOST", "127.0.0.1")),
        user=os.environ.get("COCINA_DB_USER", os.environ.get("DB_USER")),
        password=os.environ.get("COCINA_DB_PASS",
                                os.environ.get("DB_PASS") or os.environ.get("DB_PASSWORD")),
        database=os.environ.get("COCINA_DB_NAME", "cocina"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


PROVIDERS = [
    {"key": "tony",       "label": "Tony",       "note": "carnicería"},
    {"key": "fabio",      "label": "Fabio",      "note": "verdurita p/ sopa"},
    {"key": "verduleria", "label": "Verdulería", "note": ""},
    {"key": "super",      "label": "Súper",      "note": "Sofi"},
    {"key": "amparo",     "label": "Amparo",     "note": "dietética"},
    {"key": "vacalin",    "label": "Vacalin",    "note": "quesería"},
    {"key": "propio",     "label": "Nosotros",   "note": "lo traemos aparte"},
]


# CATÁLOGO BASE (se siembra una sola vez si la tabla está vacía)
# ing: (nombre, proveedor, cantidad, unidad, escala_bool, esc_dict_o_None)
CATALOGO = [
 ("Tartas y soufflés", [
   ("Tarta de atún", True, False, [
     ("Tapa para tarta","super",1,"u",False,None),("Atún al natural","super",2,"lata",False,None),
     ("Huevos","verduleria",2,"u",True,None),("Cebolla","verduleria",1,"u",False,None),
     ("Morrón rojo","verduleria",1,"u",False,None)]),
   ("Tarta de cebolla", True, False, [
     ("Tapa para tarta","super",1,"u",False,None),("Cebolla","verduleria",3,"u",True,None),
     ("Huevos","verduleria",2,"u",True,None),("Crema de leche","super",1,"u",False,None),
     ("Queso muzzarella","vacalin",150,"g",True,None)]),
   ("Tarta de choclo", True, False, [
     ("Tapa para tarta","super",1,"u",False,None),("Choclo congelado","super",1,"paq",False,None),
     ("Huevos","verduleria",2,"u",True,None),("Cebolla","verduleria",1,"u",False,None),
     ("Queso muzzarella","vacalin",150,"g",True,None)]),
   ("Tarta de espinaca y ricota", True, False, [
     ("Tapa para tarta","super",1,"u",False,None),("Espinaca congelada","super",1,"paq",False,None),
     ("Ricota verde","super",1,"u",False,None),("Huevos","verduleria",2,"u",True,None),
     ("Cebolla","verduleria",1,"u",False,None)]),
   ("Soufflé de espinaca", False, False, [
     ("Espinaca congelada","super",1,"paq",False,None),("Huevos","verduleria",3,"u",False,None),
     ("Queso muzzarella","vacalin",120,"g",False,None),("Cebolla","verduleria",1,"u",False,None)]),
   ("Soufflé de choclo", False, False, [
     ("Choclo congelado","super",1,"paq",False,None),("Huevos","verduleria",3,"u",False,None),
     ("Queso muzzarella","vacalin",120,"g",False,None)]),
 ]),
 ("Sopa", [
   ("Sopa de pollo", True, False, [
     ("Verdurita para sopa","fabio",1,"u",False,None),("Pechuga sin filetear","tony",1,"u",True,None)]),
   ("Sopa con caracú", True, False, [
     ("Verdurita para sopa","fabio",1,"u",False,None),("Caracú u osobuco para sopa","tony",1,"u",True,None)]),
 ]),
 ("Pescado", [
   ("Salmón con naranja y soja", True, False, [
     ("Salmón","propio",1,"u",True,None),("Naranja","verduleria",1,"u",False,None),
     ("Salsa de soja","amparo",1,"u",False,None)]),
 ]),
 ("Carne vacuna", [
   ("Vacío a la cacerola", False, False, [
     ("Vacío","tony",800,"g",False,None),("Morrón rojo","verduleria",1,"u",False,None),
     ("Cebolla","verduleria",2,"u",False,None)]),
   ("Carne con tuco", False, False, [
     ("Paleta o roast beef","tony",600,"g",False,None),("Puré de tomate","super",1,"u",False,None),
     ("Cebolla","verduleria",1,"u",False,None),("Morrón rojo","verduleria",1,"u",False,None)]),
   ("Carne al horno c/ cebolla morada", False, False, [
     ("Colita de cuadril o lomo","tony",800,"g",False,None),("Cebolla morada","verduleria",2,"u",False,None),
     ("Papines","verduleria",0.5,"kg",False,None)]),
   ("Matambre tiernizado", False, False, [
     ("Matambre tiernizado","tony",1,"u",False,None),("Leche (p/ tiernizar)","super",1,"u",False,None)]),
   ("Lomo al horno", False, False, [
     ("Lomo","tony",800,"g",False,None),("Morrón rojo","verduleria",1,"u",False,None),
     ("Cebolla","verduleria",2,"u",False,None)]),
   ("Peceto al horno c/ papines", False, False, [
     ("Peceto","tony",800,"g",False,None),("Papines","verduleria",0.5,"kg",False,None)]),
   ("Milanesa de carne", False, True, [
     ("Peceto para milanesas","tony",1,"kg",False,None),("Pan rallado","super",1,"u",False,None),
     ("Huevos","verduleria",3,"u",False,None),("Queso rallado","super",1,"u",False,None),
     ("Perejil","verduleria",1,"atado",False,None)]),
   ("Costillitas al horno", False, False, [
     ("Costillitas (ya preparadas)","tony",1,"u",False,None)]),
 ]),
 ("Cerdo", [
   ("Solomillo de cerdo a la mostaza", False, False, [
     ("Solomillo de cerdo","tony",1,"u",False,None),("Mostaza","super",1,"u",False,None),
     ("Cebolla","verduleria",1,"u",False,None)]),
 ]),
 ("Pollo", [
   ("Arroz con pollo", True, False, [
     ("Arroz jazmín o basmati","amparo",1,"u",False,None),
     ("Pata y muslo deshuesada","tony",1,"u",False,{"chico":1,"mediano":3,"grande":3}),
     ("Arvejas congeladas","super",1,"u",False,None),("Morrón rojo","verduleria",1,"u",False,None),
     ("Cebolla","verduleria",1,"u",False,None),("Azafrán","super",2,"u",False,None)]),
   ("Pollo al verdeo", True, False, [
     ("Suprema sin filetear","tony",1,"u",True,None),("Cebolla de verdeo","verduleria",2,"u",False,None),
     ("Crema de leche","super",1,"u",False,None)]),
   ("Pata y muslo al horno", False, False, [
     ("Pata y muslo c/ piel","tony",2,"u",False,None),("Papines","verduleria",0.5,"kg",False,None),
     ("Limón","verduleria",1,"u",False,None)]),
 ]),
 ("Pastas y legumbres", [
   ("Lasagna", True, False, [
     ("Tapa para lasaña","super",1,"u",False,None),("Carne picada especial","tony",500,"g",True,None),
     ("Puré de tomate","super",1,"u",False,None),("Queso muzzarella","vacalin",300,"g",True,None),
     ("Espinaca congelada","super",1,"paq",False,None)]),
   ("Guiso de lentejas", True, False, [
     ("Lentejones","amparo",1,"u",False,None),
     ("Paleta o roast beef","tony",400,"g",False,{"chico":400,"mediano":600,"grande":850}),
     ("Cebolla","verduleria",1,"u",False,None),("Papa","verduleria",2,"u",False,None),
     ("Zanahoria","verduleria",1,"u",False,None),("Calabaza o boniato","verduleria",1,"u",False,None),
     ("Morrón rojo","verduleria",1,"u",False,None),("Arvejas congeladas","super",1,"u",False,None)]),
 ]),
 ("Vegetales como plato", [
   ("Zapallitos rellenos c/ quinoa", False, False, [
     ("Zapallitos","verduleria",4,"u",False,None),("Quinoa","amparo",1,"u",False,None),
     ("Cebolla","verduleria",1,"u",False,None),("Queso muzzarella","vacalin",150,"g",False,None),
     ("Queso rallado","super",1,"u",False,None)]),
   ("Calabaza rellena con choclo", False, False, [
     ("Calabaza mediana","verduleria",1,"u",False,None),("Choclo congelado","super",1,"paq",False,None),
     ("Queso muzzarella","vacalin",150,"g",False,None)]),
   ("Milanesas de berenjena", False, True, [
     ("Berenjena","verduleria",1,"u",False,None),("Pan rallado","super",1,"u",False,None),
     ("Huevos","verduleria",2,"u",False,None),("Queso rallado","super",1,"u",False,None)]),
   ("Revuelto de zapallitos", False, False, [
     ("Zapallitos","verduleria",4,"u",False,None),("Cebolla","verduleria",1,"u",False,None),
     ("Morrón rojo","verduleria",1,"u",False,None),("Huevos","verduleria",3,"u",False,None),
     ("Queso muzzarella","vacalin",100,"g",False,None)]),
   ("Buñuelos de coliflor", False, False, [
     ("Coliflor","verduleria",1,"u",False,None),("Harina","super",1,"u",False,None),
     ("Huevos","verduleria",2,"u",False,None)]),
 ]),
 ("A base de papa", [
   ("Pastel de papa", True, False, [
     ("Papa","verduleria",1,"kg",False,None),("Carne picada","tony",500,"g",True,None),
     ("Cebolla","verduleria",1,"u",False,None),("Morrón rojo","verduleria",1,"u",False,None)]),
   ("Tortilla de papa", True, False, [
     ("Papa","verduleria",0.75,"kg",False,None),("Huevos","verduleria",4,"u",True,None),
     ("Cebolla","verduleria",1,"u",False,None)]),
   ("Mil hojas de papa", True, False, [
     ("Papa","verduleria",1,"kg",False,None),("Crema de leche","super",1,"u",False,None),
     ("Queso muzzarella","vacalin",200,"g",True,None),("Queso rallado","super",1,"u",False,None)]),
 ]),
 ("Empanadas", [
   ("Empanadas de carne", False, True, [
     ("Tapas de empanada","super",1,"paq",False,None),("Carne picada","tony",500,"g",False,None),
     ("Cebolla","verduleria",2,"u",False,None),("Huevos","verduleria",1,"u",False,None)]),
   ("Empanadas de queso", False, True, [
     ("Tapas de empanada","super",1,"paq",False,None),("Queso muzzarella","vacalin",300,"g",False,None)]),
 ]),
]


def _seed_if_empty():
    con = _conn(); cur = con.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM cocina_recetas")
    if cur.fetchone()["c"] > 0:
        cur.close(); con.close(); return
    orden_cat = 0
    for categoria, recetas in CATALOGO:
        for nombre, sized, freezer, ings in recetas:
            cur.execute(
                "INSERT INTO cocina_recetas (nombre,categoria,sized,freezer,es_custom,orden) "
                "VALUES (%s,%s,%s,%s,0,%s)",
                (nombre, categoria, int(sized), int(freezer), orden_cat))
            rid = cur.lastrowid
            for oi, (n, p, q, u, esc, escd) in enumerate(ings):
                cur.execute(
                    "INSERT INTO cocina_receta_ingredientes "
                    "(receta_id,nombre,proveedor,cantidad,unidad,escala,esc_chico,esc_mediano,esc_grande,orden) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (rid, n, p, q, u, int(esc),
                     (escd or {}).get("chico"), (escd or {}).get("mediano"), (escd or {}).get("grande"), oi))
            orden_cat += 1
    con.commit(); cur.close(); con.close()


def _recetas_payload():
    con = _conn(); cur = con.cursor()
    cur.execute("SELECT * FROM cocina_recetas WHERE activo=1 ORDER BY orden, id")
    recetas = cur.fetchall()
    cur.execute("SELECT * FROM cocina_receta_ingredientes ORDER BY receta_id, orden, id")
    ings = cur.fetchall()
    cur.close(); con.close()
    by_rec = {}
    for i in ings:
        esc = None
        if i["esc_chico"] is not None:
            esc = {"chico": float(i["esc_chico"]),
                   "mediano": float(i["esc_mediano"]) if i["esc_mediano"] is not None else float(i["esc_chico"]),
                   "grande": float(i["esc_grande"]) if i["esc_grande"] is not None else float(i["esc_chico"])}
        by_rec.setdefault(i["receta_id"], []).append({
            "n": i["nombre"], "p": i["proveedor"], "q": float(i["cantidad"]),
            "u": i["unidad"], "scale": bool(i["escala"]), "esc": esc})
    out = []
    for r in recetas:
        out.append({
            "id": r["id"], "nombre": r["nombre"], "categoria": r["categoria"],
            "sized": bool(r["sized"]), "freezer": bool(r["freezer"]),
            "es_custom": bool(r["es_custom"]), "ing": by_rec.get(r["id"], [])})
    return out


# ============================================================
# RUTAS (todas PÚBLICAS, sin login)
# ============================================================
@cocinar_bp.route("/cocinar")
def cocinar_home():
    _seed_if_empty()
    return render_template("cocinar.html")


@cocinar_bp.route("/cocinar/manifest.webmanifest")
def cocinar_manifest():
    data = {
        "name": "Cocinar · Casa", "short_name": "Cocinar",
        "start_url": "/cocinar", "scope": "/cocinar/", "display": "standalone",
        "background_color": "#F4EDDF", "theme_color": "#1C3B2E",
        "icons": [{"src": "/cocinar/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    }
    return Response(json.dumps(data), mimetype="application/manifest+json")


@cocinar_bp.route("/cocinar/icon.svg")
def cocinar_icon():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        '<rect width="512" height="512" rx="104" fill="#1C3B2E"/>'
        '<path d="M196 150 q-18 -28 0 -56" stroke="#C28A2C" stroke-width="13" fill="none" stroke-linecap="round" opacity=".85"/>'
        '<path d="M256 150 q-18 -28 0 -56" stroke="#C28A2C" stroke-width="13" fill="none" stroke-linecap="round" opacity=".85"/>'
        '<path d="M316 150 q-18 -28 0 -56" stroke="#C28A2C" stroke-width="13" fill="none" stroke-linecap="round" opacity=".85"/>'
        '<rect x="96" y="242" width="46" height="30" rx="15" fill="#C28A2C"/>'
        '<rect x="370" y="242" width="46" height="30" rx="15" fill="#C28A2C"/>'
        '<rect x="136" y="200" width="240" height="172" rx="32" fill="#F4EDDF"/>'
        '<rect x="118" y="176" width="276" height="38" rx="19" fill="#C28A2C"/>'
        '<circle cx="256" cy="170" r="15" fill="#C28A2C"/>'
        '</svg>'
    )
    return Response(svg, mimetype="image/svg+xml")


@cocinar_bp.route("/cocinar/api/config")
def api_config():
    return jsonify({"providers": PROVIDERS, "recetas": _recetas_payload()})


@cocinar_bp.route("/cocinar/api/recetas", methods=["POST"])
def api_crear_receta():
    d = request.get_json(force=True) or {}
    nombre = (d.get("nombre") or "").strip()
    ings = d.get("ingredientes") or []
    if not nombre or not ings:
        return jsonify({"error": "Faltan nombre o ingredientes"}), 400
    con = _conn(); cur = con.cursor()
    cur.execute(
        "INSERT INTO cocina_recetas (nombre,categoria,sized,freezer,es_custom,orden) "
        "VALUES (%s,%s,%s,%s,1,999)",
        (nombre, d.get("categoria") or "Mis platos", int(bool(d.get("sized"))), int(bool(d.get("freezer")))))
    rid = cur.lastrowid
    for oi, ing in enumerate(ings):
        cur.execute(
            "INSERT INTO cocina_receta_ingredientes "
            "(receta_id,nombre,proveedor,cantidad,unidad,escala,orden) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (rid, (ing.get("nombre") or "").strip(), ing.get("proveedor") or "verduleria",
             float(ing.get("cantidad") or 1), ing.get("unidad") or "u", int(bool(ing.get("escala"))), oi))
    con.commit(); cur.close(); con.close()
    return jsonify({"ok": True, "id": rid})


@cocinar_bp.route("/cocinar/api/recetas/<int:rid>", methods=["DELETE"])
def api_borrar_receta(rid):
    con = _conn(); cur = con.cursor()
    cur.execute("SELECT es_custom FROM cocina_recetas WHERE id=%s", (rid,))
    row = cur.fetchone()
    if not row:
        cur.close(); con.close(); return jsonify({"error": "no existe"}), 404
    if not row["es_custom"]:
        cur.close(); con.close(); return jsonify({"error": "no se puede borrar el catálogo base"}), 403
    cur.execute("DELETE FROM cocina_recetas WHERE id=%s", (rid,))
    con.commit(); cur.close(); con.close()
    return jsonify({"ok": True})


@cocinar_bp.route("/cocinar/api/pedidos", methods=["POST"])
def api_guardar_pedido():
    d = request.get_json(force=True) or {}
    con = _conn(); cur = con.cursor()
    cur.execute(
        "INSERT INTO cocina_pedidos (fecha,mensaje_cocinera,lista_compras,seleccion,creado_por) "
        "VALUES (COALESCE(%s,CURDATE()),%s,%s,%s,%s)",
        (d.get("fecha"), d.get("mensaje"), d.get("compras"),
         json.dumps(d.get("seleccion") or {}, ensure_ascii=False), d.get("creado_por")))
    pid = cur.lastrowid
    con.commit(); cur.close(); con.close()
    return jsonify({"ok": True, "id": pid})


@cocinar_bp.route("/cocinar/api/pedidos", methods=["GET"])
def api_listar_pedidos():
    limit = min(int(request.args.get("limit", 50)), 200)
    con = _conn(); cur = con.cursor()
    cur.execute("SELECT id,fecha,mensaje_cocinera,creado_en FROM cocina_pedidos ORDER BY fecha DESC, id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close(); con.close()
    for r in rows:
        r["fecha"] = str(r["fecha"]); r["creado_en"] = str(r["creado_en"])
    return jsonify(rows)


@cocinar_bp.route("/cocinar/api/pedidos/<int:pid>", methods=["GET"])
def api_ver_pedido(pid):
    con = _conn(); cur = con.cursor()
    cur.execute("SELECT * FROM cocina_pedidos WHERE id=%s", (pid,))
    r = cur.fetchone()
    cur.close(); con.close()
    if not r:
        return jsonify({"error": "no existe"}), 404
    r["fecha"] = str(r["fecha"]); r["creado_en"] = str(r["creado_en"])
    if isinstance(r.get("seleccion"), str):
        try: r["seleccion"] = json.loads(r["seleccion"])
        except Exception: r["seleccion"] = {}
    return jsonify(r)
