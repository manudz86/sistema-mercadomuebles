# 🔍 CÓMO USAR EL SCRIPT DE DEBUG

## ⚡ OPCIÓN 1: RUTA EN FLASK (MÁS FÁCIL)

### 1. Agregar la ruta al final de app.py:

```python
# Al final de app.py, ANTES del if __name__ == '__main__':

@app.route('/debug/ml/<orden_id>')
def debug_orden_ml_ruta(orden_id):
    """Ver todos los datos que trae ML de una orden"""
    access_token = cargar_ml_token()
    
    if not access_token:
        return "❌ No hay token de ML configurado", 400
    
    # Copiar la función debug_orden_ml_completa() aquí
    # (del archivo debug_orden_ml_completa.py)
    
    debug_orden_ml_completa(orden_id, access_token)
    
    return f"""
    <html>
    <body style="font-family: monospace; padding: 20px;">
        <h2>✅ Debug completado</h2>
        <p>Revisá la consola de Flask para ver toda la info.</p>
        <p>Se generaron archivos JSON en la raíz del proyecto.</p>
        <a href="/ventas/activas">← Volver a Ventas Activas</a>
    </body>
    </html>
    """
```

### 2. Copiar también la función debug_orden_ml_completa() en app.py

### 3. Reiniciar Flask

### 4. Usar desde el navegador:

```
http://localhost:5000/debug/ml/2000015193517850
```

Cambiá `2000015193517850` por una de tus órdenes reales (la que querés ver).

---

## ⚡ OPCIÓN 2: SCRIPT SEPARADO

### 1. Guardar debug_orden_ml_completa.py en tu carpeta del proyecto

### 2. Editar el archivo y poner tu token y orden:

```python
# Al final del archivo
ACCESS_TOKEN = "tu_access_token_real"
ORDEN_ID = "2000015193517850"  # Tu orden real
```

### 3. Ejecutar:

```bash
python debug_orden_ml_completa.py
```

---

## 📊 QUÉ VA A PASAR:

### En la consola verás:

```
================================================================================
🔍 DEBUG COMPLETO - ORDEN ML: 2000015193517850
================================================================================

📦 1. INFORMACIÓN COMPLETA DE LA ORDEN:
--------------------------------------------------------------------------------
✅ JSON completo guardado en: debug_orden_2000015193517850.json

📋 ESTRUCTURA PRINCIPAL:
   • id: int = 2000015193517850
   • date_created: str = 2026-02-18T...
   • buyer: dict {10 keys}
   • seller: dict {5 keys}
   • payments: list [1 items]
   • shipping: dict {8 keys}
   • order_items: list [1 items]
   • total_amount: float = 19499.0
   ...

👤 2. DATOS DEL COMPRADOR (buyer):
--------------------------------------------------------------------------------
{
  'id': 123456789,
  'nickname': 'VALDETTAROLUISI',
  'first_name': 'Luis Rafael',
  'last_name': 'Valdettaro',
  'email': 'usuario@email.com',
  'phone': {
    'area_code': '11',
    'number': '12345678'
  },
  ...
}

🧾 3. INFORMACIÓN DE FACTURACIÓN (billing_info):
--------------------------------------------------------------------------------
✅ BILLING INFO DISPONIBLE:
{
  'doc_type': 'DNI',
  'doc_number': '19131481',
  'additional_info': {
    'business_name': 'Carolina Karen Colmenares Sanchez',
    'address': {
      'zip_code': '1244',
      'street_name': 'La Rioja',
      'street_number': '1244'
    }
  }
}

📊 RESUMEN - DATOS ÚTILES PARA FACTURACIÓN:
================================================================================
👤 COMPRADOR:
   • First name: Luis Rafael
   • Last name: Valdettaro
   • Email: usuario@email.com
   • Phone: 11-12345678

🧾 FACTURACIÓN:
   • Doc type: DNI / CUIT / ...
   • Doc number: 19131481
   • Business name: Carolina Karen Colmenares Sanchez (si existe)
   • IVA Condition: Consumidor Final / Responsable Inscripto
```

### Archivos JSON generados:

```
debug_orden_2000015193517850.json     ← Orden completa
debug_billing_2000015193517850.json   ← Billing (si existe)
debug_shipment_2000015193517850.json  ← Envío completo (si existe)
```

---

## 🎯 OBJETIVO:

Con esto vamos a ver **EXACTAMENTE** qué datos trae ML para tus órdenes, incluyendo:

- ✅ Tipo de documento (DNI / CUIT)
- ✅ Número de documento
- ✅ Condición IVA (Consumidor Final / Responsable Inscripto / Monotributo)
- ✅ Razón social (si es empresa)
- ✅ Domicilio fiscal

Después de ejecutar el debug, **avisame qué campos aparecen** y armamos la BD para guardarlos automáticamente.

---

## 📋 SIGUIENTE PASO:

1. Ejecutá el debug con **una orden que tenga factura** (como las de las imágenes que pasaste)
2. Ejecutá el debug con **una orden sin factura** (consumidor final)
3. Pasame la info que sale en la consola o los archivos JSON
4. Con eso armamos la BD y el sistema completo

---

¿Probamos? 🚀
