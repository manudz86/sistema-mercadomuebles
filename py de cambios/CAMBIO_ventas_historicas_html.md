# ============================================================================
# CAMBIO EN ventas_historicas.html
# ============================================================================

## BUSCAR en la columna de acciones (dentro del loop de ventas):

```html
<td>
    <!-- Botones de acción -->
    <button class="btn btn-sm btn-info" data-bs-toggle="modal" data-bs-target="#modalDetalle{{ venta.id }}">
        <i class="bi bi-eye"></i> Ver Detalle
    </button>
</td>
```

## REEMPLAZAR CON:

```html
<td>
    <!-- Botones de acción -->
    <div class="d-flex gap-2">
        <!-- Ver Detalle -->
        <button class="btn btn-sm btn-info" data-bs-toggle="modal" data-bs-target="#modalDetalle{{ venta.id }}">
            <i class="bi bi-eye"></i> Ver
        </button>
        
        <!-- Volver a Activas -->
        <form method="POST" action="{{ url_for('historicas_volver_activas', venta_id=venta.id) }}" style="display: inline;">
            <button type="submit" class="btn btn-sm btn-warning" 
                    onclick="return confirm('¿Volver esta venta a Ventas Activas?\n\n{% if venta.estado_entrega == 'entregada' %}Se devolverá el stock descontado.{% else %}No se modificará el stock.{% endif %}')">
                <i class="bi bi-arrow-counterclockwise"></i> Volver Activa
            </button>
        </form>
    </div>
</td>
```

---

## EXPLICACIÓN:

### Botón "Volver a Activas":
- Aparece en TODAS las ventas históricas (entregadas y canceladas)
- Confirmación diferente según estado:
  - **Entregada:** "Se devolverá el stock descontado"
  - **Cancelada:** "No se modificará el stock"
- Usa formulario POST para ejecutar la acción

---

## OPCIONAL - Color diferente según estado:

Si querés que el botón tenga color diferente según el estado:

```html
<!-- Volver a Activas -->
<form method="POST" action="{{ url_for('historicas_volver_activas', venta_id=venta.id) }}" style="display: inline;">
    <button type="submit" 
            class="btn btn-sm {% if venta.estado_entrega == 'entregada' %}btn-warning{% else %}btn-secondary{% endif %}" 
            onclick="return confirm('¿Volver esta venta a Ventas Activas?\n\n{% if venta.estado_entrega == 'entregada' %}Se devolverá el stock descontado.{% else %}No se modificará el stock.{% endif %}')">
        <i class="bi bi-arrow-counterclockwise"></i> Volver Activa
    </button>
</form>
```

**Resultado:**
- Entregadas: Botón amarillo (warning)
- Canceladas: Botón gris (secondary)
