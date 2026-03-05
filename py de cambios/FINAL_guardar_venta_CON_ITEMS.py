# ============================================================================
# ACTUALIZACIÓN: FINAL DE guardar_venta CON ITEMS VENDIDOS
# Reemplazar desde "DETECTAR ALERTAS" hasta el final
# ============================================================================

        # ========================================
        # DETECTAR ALERTAS ANTES DEL COMMIT
        # Solo de productos vendidos en ESTA venta
        # ========================================
        productos_sin_stock = []
        try:
            # Pasar lista de items vendidos a la función
            items_vendidos_lista = []
            for item in items_venta:
                items_vendidos_lista.append({
                    'sku': item['sku'],
                    'cantidad': item['cantidad']
                })
            
            productos_sin_stock = detectar_alertas_stock_bajo(cursor, items_vendidos_lista)
        except Exception as e_alertas:
            # Si falla detección de alertas, solo logear pero continuar
            print(f"⚠️ Error al detectar alertas (no crítico): {str(e_alertas)}")
            import traceback
            traceback.print_exc()
        
        # ========================================
        # COMMIT DE LA VENTA
        # ========================================
        conn.commit()
        cursor.close()
        conn.close()
        
        # ========================================
        # MENSAJE Y REDIRECCIÓN
        # ========================================
        if productos_sin_stock:
            # HAY PRODUCTOS SIN STOCK - Mostrar modal
            
            # Separar productos base y combos
            productos_base = [p for p in productos_sin_stock if p.get('tipo_producto') == 'base']
            combos_afectados = [p for p in productos_sin_stock if p.get('tipo_producto') == 'combo']
            
            mensaje_html = f'''
                <div class="alert alert-success mb-3">
                    <strong>✅ Venta {numero_venta} registrada correctamente</strong>
                </div>
                <div class="alert alert-warning">
                    <h5><i class="bi bi-exclamation-triangle-fill"></i> ⚠️ Alerta de Stock ML</h5>
            '''
            
            # Mostrar productos base sin stock
            if productos_base:
                mensaje_html += '''
                    <p class="mb-2"><strong>Productos base sin stock disponible:</strong></p>
                    <ul class="mb-3">
                '''
                
                for prod in productos_base:
                    mensaje_html += f'''
                        <li><strong>{prod['nombre']}</strong> (SKU: {prod['sku']})<br>
                            <small>Stock físico: {prod['stock_fisico']} | Vendido: {prod['vendido']} | Disponible: <span class="text-danger">{prod['stock_disponible']}</span></small>
                        </li>
                    '''
                
                mensaje_html += '</ul>'
            
            # Mostrar combos afectados
            if combos_afectados:
                mensaje_html += '''
                    <p class="mb-2"><strong>Combos/Sommiers que NO se pueden armar:</strong></p>
                    <ul class="mb-3">
                '''
                
                for combo in combos_afectados:
                    mensaje_html += f'''
                        <li><strong>{combo['nombre']}</strong> (SKU: {combo['sku']})<br>
                            <small class="text-muted">Falta componente: {combo.get('componente_faltante', 'N/A')}</small>
                        </li>
                    '''
                
                mensaje_html += '</ul>'
            
            mensaje_html += '''
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
        cursor.close()
        conn.close()
        import traceback
        error_completo = traceback.format_exc()
        print(f"ERROR al guardar venta:\n{error_completo}")
        flash(f'❌ Error al guardar venta: {str(e)}', 'error')
        return redirect(url_for('nueva_venta'))
