# 🔧 CAMBIOS EXACTOS PARA ventas_activas.html

## 📍 CAMBIO 1: AGREGAR BOTÓN "EDITAR" EN ACCIONES

### UBICACIÓN:
Línea ~196-214 (donde están los botones Proceso/Entregada/Cancelar)

### BUSCAR:
```html
<!-- ACCIONES -->
<td>
    <div class="btn-group-vertical d-grid gap-1" style="font-size: 0.85em;">
        <!-- Pasar a Proceso -->
        <button type="button" 
```

### CAMBIAR TODO EL <td> DE ACCIONES POR:
```html
<!-- ACCIONES -->
<td>
    <div class="btn-group-vertical d-grid gap-1" style="font-size: 0.85em;">
        <!-- NUEVO: Botón Editar -->
        <a href="{{ url_for('editar_venta', venta_id=venta.id) }}" 
           class="btn btn-sm btn-warning"
           title="Editar venta">
            <i class="bi bi-pencil"></i> Editar
        </a>
        
        <!-- Pasar a Proceso -->
        <button type="button" 
                class="btn btn-sm btn-primary"
                onclick="confirmarAccion('{{ venta.id }}', 'proceso', '{{ venta.numero_venta }}')">
            <i class="bi bi-arrow-right-circle"></i> Proceso
        </button>
        
        <!-- Marcar Entregada -->
        <button type="button" 
                class="btn btn-sm btn-success"
                onclick="confirmarAccion('{{ venta.id }}', 'entregada', '{{ venta.numero_venta }}')">
            <i class="bi bi-check-circle"></i> Entregada
        </button>
        
        <!-- Cancelar -->
        <button type="button" 
                class="btn btn-sm btn-danger"
                onclick="confirmarAccion('{{ venta.id }}', 'cancelar', '{{ venta.numero_venta }}')">
            <i class="bi bi-x-circle"></i> Cancelar
        </button>
    </div>
</td>
```

---

## 📍 CAMBIO 2: BOTONES DE DIRECCIÓN (Copiar + Google Maps)

### UBICACIÓN:
Línea ~161-174 (donde muestra la dirección)

### BUSCAR:
```html
                        {% if venta.direccion_entrega %}
                            <br><small class="text-muted">{{ venta.direccion_entrega[:30] }}{% if venta.direccion_entrega|length > 30 %}...{% endif %}</small>
                        {% endif %}
```

### REEMPLAZAR POR:
```html
                        {% if venta.direccion_entrega %}
                            <br>
                            <div class="d-flex align-items-center gap-1 mt-1">
                                <small class="text-muted flex-grow-1" style="font-size: 0.75em;">
                                    {{ venta.direccion_entrega[:30] }}{% if venta.direccion_entrega|length > 30 %}...{% endif %}
                                </small>
                                
                                <!-- Botón copiar -->
                                <button type="button" 
                                        class="btn btn-sm btn-outline-secondary p-0" 
                                        style="width: 24px; height: 24px; font-size: 0.7em;"
                                        onclick="copiarDireccion('{{ venta.direccion_entrega }}')"
                                        title="Copiar dirección">
                                    <i class="bi bi-clipboard"></i>
                                </button>
                                
                                <!-- Botón Google Maps -->
                                <a href="https://www.google.com/maps/search/?api=1&query={{ venta.direccion_entrega|urlencode }}" 
                                   target="_blank" 
                                   class="btn btn-sm btn-outline-primary p-0"
                                   style="width: 24px; height: 24px; font-size: 0.7em;"
                                   title="Abrir en Google Maps">
                                    <i class="bi bi-geo-alt-fill"></i>
                                </a>
                            </div>
                        {% endif %}
```

---

## 📍 CAMBIO 3: AGREGAR FUNCIONES JAVASCRIPT

### UBICACIÓN:
Al final del archivo, ANTES de la última línea `{% endblock %}`

### AGREGAR:
```html
<!-- Funciones para copiar dirección -->
<script>
function copiarDireccion(direccion) {
    // Crear elemento temporal
    const textArea = document.createElement('textarea');
    textArea.value = direccion;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    
    // Seleccionar y copiar
    textArea.select();
    
    try {
        document.execCommand('copy');
        mostrarNotificacion('✅ Dirección copiada al portapapeles', 'success');
    } catch (err) {
        mostrarNotificacion('❌ Error al copiar dirección', 'error');
    }
    
    // Eliminar elemento temporal
    document.body.removeChild(textArea);
}

function mostrarNotificacion(mensaje, tipo) {
    // Crear elemento
    const notif = document.createElement('div');
    notif.className = `alert alert-${tipo} position-fixed`;
    notif.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; animation: slideIn 0.3s ease;';
    notif.innerHTML = mensaje;
    
    // Agregar al DOM
    document.body.appendChild(notif);
    
    // Eliminar después de 3 segundos
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}
</script>

<style>
@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}
</style>
```

---

## 📋 RESUMEN DE CAMBIOS:

1. **Línea ~196-214:** Agregar botón "Editar" en acciones
2. **Línea ~161-174:** Agregar botones copiar + maps en dirección
3. **Antes de {% endblock %}:** Agregar funciones JavaScript

---

## ✅ RESULTADO ESPERADO:

Después de los cambios, en cada fila de venta verás:

```
Entrega:
  Envío
  [Flete Propio]
  🔷 Depósito
  Calle 123, Barrio... [📋] [📍]
                        ↑    ↑
                     Copiar Maps

Acciones:
  [Editar]    ← Nuevo (amarillo)
  [Proceso]   ← Azul
  [Entregada] ← Verde
  [Cancelar]  ← Rojo
```

---

## 🎯 VERIFICACIÓN:

Después de hacer los cambios:
1. Guardar archivo
2. Recargar página de Ventas Activas
3. Verificar que aparece botón "Editar" amarillo
4. Verificar que aparecen iconos pequeños al lado de dirección
5. Probar copiar → Debe mostrar mensaje "Dirección copiada"
6. Probar maps → Debe abrir Google Maps

---

**¿Hacés estos 3 cambios y probás?** 🚀
