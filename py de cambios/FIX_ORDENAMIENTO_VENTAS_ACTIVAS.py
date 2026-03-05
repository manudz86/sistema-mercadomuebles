# ============================================================================
# CORRECCIÓN: ORDENAMIENTO EN VENTAS ACTIVAS
# ============================================================================

# PROBLEMA:
# Cuando se edita una venta o vuelve desde proceso/entregada,
# cambia fecha_modificacion y la venta se reordena.

# SOLUCIÓN:
# Cambiar el ORDER BY para usar solo fecha_venta e id

# ============================================================================
# EN LA FUNCIÓN ventas_activas() de app.py
# ============================================================================

# BUSCAR esta línea (puede estar de cualquiera de estas dos formas):
query += ' ORDER BY fecha_modificacion DESC, id DESC'
# O:
query += ' ORDER BY fecha_venta DESC, fecha_modificacion DESC, id DESC'

# REEMPLAZAR por:
query += ' ORDER BY fecha_venta DESC, id DESC'

# ============================================================================
# RESULTADO:
# ============================================================================

# ✅ Las ventas mantienen su orden original basado en fecha_venta
# ✅ Si dos ventas tienen la misma fecha → usa el ID como desempate
# ✅ Editar una venta NO la mueve de posición
# ✅ Volver desde proceso/entregada NO la mueve de posición

# ============================================================================
# EJEMPLO DE LA FUNCIÓN COMPLETA:
# ============================================================================

@app.route('/ventas/activas')
def ventas_activas():
    """Lista de ventas activas con filtros"""
    try:
        # ... código de filtros ...
        
        query = '''
            SELECT 
                id, numero_venta, fecha_venta, ...
            FROM ventas
            WHERE estado_entrega = 'pendiente'
        '''
        
        # ... aplicar filtros ...
        
        # ✅ ORDENAR POR FECHA DE VENTA (NO por fecha_modificacion)
        query += ' ORDER BY fecha_venta DESC, id DESC'
        
        # Ejecutar query
        ventas = query_db(query, tuple(params) if params else None)
        
        # ... resto del código ...
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))
