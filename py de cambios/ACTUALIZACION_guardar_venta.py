# ============================================================================
# ACTUALIZACIÓN: RUTA guardar_venta CON DETECCIÓN DE ALERTAS
# Reemplazar el final de la ruta guardar_venta() en app.py
# ============================================================================

# ... (todo el código anterior de guardar_venta se mantiene igual hasta el final)

        conn.commit()
        
        # ========================================
        # DETECTAR ALERTAS DE STOCK BAJO
        # ========================================
        productos_sin_stock = detectar_alertas_stock_bajo(cursor)
        
        cursor.close()
        conn.close()
        
        # ========================================
        # MENSAJE Y REDIRECCIÓN
        # ========================================
        if productos_sin_stock:
            # HAY PRODUCTOS SIN STOCK - Mostrar modal
            mensaje_html = f'''
                <div class="alert alert-success mb-3">
                    <strong>✅ Venta {numero_venta} registrada correctamente</strong>
                </div>
                <div class="alert alert-warning">
                    <h5><i class="bi bi-exclamation-triangle-fill"></i> ⚠️ Alerta de Stock</h5>
                    <p class="mb-2">Los siguientes productos <strong>quedaron sin stock disponible</strong>:</p>
                    <ul class="mb-3">
            '''
            
            for prod in productos_sin_stock:
                mensaje_html += f'''
                    <li><strong>{prod['nombre']}</strong> (SKU: {prod['sku']})<br>
                        <small>Stock físico: {prod['stock_fisico']} | Vendido: {prod['vendido']} | Disponible: <span class="text-danger">{prod['stock_disponible']}</span></small>
                    </li>
                '''
            
            mensaje_html += '''
                    </ul>
                    <p class="mb-0">
                        <strong>Recordá:</strong> Pausá las publicaciones en ML o cargá más stock.
                    </p>
                </div>
            '''
            
            flash(mensaje_html, 'alerta_stock')
            
        else:
            # NO HAY ALERTAS - Mensaje normal
            mensaje = f'✅ Venta {numero_venta} registrada'
            if ubicacion_despacho == 'FULL':
                mensaje += ' - Se despachará desde FULL ML'
            else:
                mensaje += ' - Se despachará desde Depósito'
            
            flash(mensaje, 'success')
        
        return redirect(url_for('ventas_activas'))
        
    except Exception as e:
        conn.rollback()
        import traceback
        error_completo = traceback.format_exc()
        print(f"ERROR al guardar venta:\n{error_completo}")
        flash(f'❌ Error al guardar venta: {str(e)}', 'error')
        return redirect(url_for('nueva_venta'))
    # cursor.close() y conn.close() ya se hicieron arriba
