# ============================================================================
# INSTRUCCIONES PARA ACTUALIZAR EL INSERT DE VENTAS
# Buscá la función donde se hace el INSERT de la venta (probablemente en nueva_venta_desde_ml o guardar_venta_ml)
# ============================================================================

# ═══════════════════════════════════════════════════════════════════════════
# PASO 1: Obtener la fecha de la sesión
# ═══════════════════════════════════════════════════════════════════════════

# Al inicio de la función donde guardás la venta, ANTES del INSERT, agregá:

from flask import session
from datetime import datetime

# Obtener fecha real de ML desde sesión
fecha_venta_iso = session.get('ml_fecha_venta')
if fecha_venta_iso:
    fecha_venta = datetime.fromisoformat(fecha_venta_iso)
else:
    fecha_venta = datetime.now()  # Fallback por si algo falla

# ═══════════════════════════════════════════════════════════════════════════
# PASO 2: Actualizar el INSERT
# ═══════════════════════════════════════════════════════════════════════════

# ANTES (probablemente tenías algo así):
# execute_db('''
#     INSERT INTO ventas_activas (
#         cliente_nombre, metodo_envio, fecha_creacion, ...
#     ) VALUES (%s, %s, NOW(), ...)
# ''', (cliente_nombre, metodo_envio, ...))

# DESPUÉS (usar la variable fecha_venta):
execute_db('''
    INSERT INTO ventas_activas (
        cliente_nombre, metodo_envio, fecha_creacion, ...
    ) VALUES (%s, %s, %s, ...)
''', (cliente_nombre, metodo_envio, fecha_venta, ...))


# ═══════════════════════════════════════════════════════════════════════════
# PASO 3: Manejar costo de envío para Flete Propio/Flex
# ═══════════════════════════════════════════════════════════════════════════

# Obtener datos de shipping de sesión
ml_shipping = session.get('ml_shipping', {})
costo_envio = ml_shipping.get('costo_envio', 0)
metodo_envio = # ... tu lógica para determinar el método

# Si el método es Flete Propio o Flex, sumar el costo de envío al pago de mercadopago
pago_mercadopago = # ... tu valor base del formulario

if metodo_envio in ['Flete Propio', 'Flex'] and costo_envio > 0:
    pago_mercadopago += costo_envio


# ═══════════════════════════════════════════════════════════════════════════
# EJEMPLO COMPLETO DE CÓMO PODRÍA QUEDAR:
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/ventas/nueva/ml/guardar', methods=['POST'])
def guardar_venta_ml():
    from flask import session
    from datetime import datetime
    
    # Obtener fecha real de ML
    fecha_venta_iso = session.get('ml_fecha_venta')
    fecha_venta = datetime.fromisoformat(fecha_venta_iso) if fecha_venta_iso else datetime.now()
    
    # Obtener datos del formulario
    cliente_nombre = request.form.get('cliente_nombre')
    metodo_envio = request.form.get('metodo_envio')
    pago_mercadopago = float(request.form.get('pago_mercadopago', 0))
    
    # Obtener costo de envío de sesión
    ml_shipping = session.get('ml_shipping', {})
    costo_envio = ml_shipping.get('costo_envio', 0)
    
    # Sumar costo de envío si es Flete Propio o Flex
    if metodo_envio in ['Flete Propio', 'Flex'] and costo_envio > 0:
        pago_mercadopago += costo_envio
    
    # Insertar venta con fecha real
    venta_id = execute_db('''
        INSERT INTO ventas_activas (
            cliente_nombre,
            metodo_envio,
            fecha_creacion,
            pago_mercadopago,
            estado
        ) VALUES (%s, %s, %s, %s, %s)
    ''', (
        cliente_nombre,
        metodo_envio,
        fecha_venta,  # ✅ Fecha real de ML, no NOW()
        pago_mercadopago,  # ✅ Ya incluye costo de envío si corresponde
        'Pendiente'
    ))
    
    # ... resto del código
    
    return redirect(url_for('ventas_activas'))


# ═══════════════════════════════════════════════════════════════════════════
# NOTA IMPORTANTE:
# ═══════════════════════════════════════════════════════════════════════════

# Buscá en tu código la función que hace el INSERT de ventas.
# Probablemente se llame:
# - guardar_venta_ml
# - nueva_venta_desde_ml (el POST de esa ruta)
# - ml_guardar_venta
# - O algo similar

# Una vez que la encuentres, aplicá los cambios de arriba.
# Si no la encontrás, pasame el código de la ruta que renderiza nueva_venta_ml.html
# y te ayudo a encontrarla.
