# ============================================================================
# FASE 1: CONECTAR CON MERCADO LIBRE Y VER QUÉ DATOS TRAE
# ============================================================================

# OBJETIVO:
# Solo conectar, traer órdenes, y mostrarlas en pantalla
# NO importar nada todavía - solo explorar qué información está disponible

# ============================================================================
# PASO 1: INSTALAR LIBRERÍAS
# ============================================================================

# En la terminal (con el venv activado):
# pip install requests --break-system-packages

# ============================================================================
# PASO 2: CREAR APP EN MERCADO LIBRE
# ============================================================================

# 1. Ir a: https://developers.mercadolibre.com.ar/
# 2. Login con tu cuenta de ML
# 3. Ir a "Tus aplicaciones" → "Crear nueva aplicación"
# 4. Completar:
#    - Nombre: "Inventario Cannon"
#    - Descripción: "Sistema de gestión de inventario"
#    - Redirect URI: http://localhost:5000/ml/callback
#    - Temas: Gestión de Órdenes
# 5. COPIAR:
#    - APP_ID (número largo)
#    - SECRET_KEY (texto largo)

# ============================================================================
# PASO 3: AGREGAR CONFIGURACIÓN
# ============================================================================

# Crear archivo: config/ml_config.py

ML_CONFIG = {
    'APP_ID': '1234567890',  # ← TU APP_ID de ML
    'SECRET_KEY': 'abcdef123456',  # ← TU SECRET_KEY de ML
    'REDIRECT_URI': 'http://localhost:5000/ml/callback',
    'AUTH_URL': 'https://auth.mercadolibre.com.ar/authorization',
    'TOKEN_URL': 'https://api.mercadolibre.com/oauth/token',
    'API_BASE': 'https://api.mercadolibre.com'
}

# ============================================================================
# PASO 4: AGREGAR RUTAS EN app.py
# ============================================================================

import requests
from flask import session, redirect, request, render_template
from config.ml_config import ML_CONFIG

# ========================================
# RUTA 1: Botón para conectar con ML
# ========================================

@app.route('/ml/conectar')
def ml_conectar():
    """Redirige a Mercado Libre para autorizar la app"""
    
    auth_url = (
        f"{ML_CONFIG['AUTH_URL']}"
        f"?response_type=code"
        f"&client_id={ML_CONFIG['APP_ID']}"
        f"&redirect_uri={ML_CONFIG['REDIRECT_URI']}"
    )
    
    return redirect(auth_url)


# ========================================
# RUTA 2: Callback de ML (recibe el código)
# ========================================

@app.route('/ml/callback')
def ml_callback():
    """Recibe el código de autorización y obtiene el token"""
    
    code = request.args.get('code')
    
    if not code:
        flash('Error al conectar con Mercado Libre', 'error')
        return redirect(url_for('index'))
    
    # Obtener token
    response = requests.post(ML_CONFIG['TOKEN_URL'], data={
        'grant_type': 'authorization_code',
        'client_id': ML_CONFIG['APP_ID'],
        'client_secret': ML_CONFIG['SECRET_KEY'],
        'code': code,
        'redirect_uri': ML_CONFIG['REDIRECT_URI']
    })
    
    if response.status_code == 200:
        token_data = response.json()
        
        # Guardar token en sesión (temporalmente)
        session['ml_access_token'] = token_data['access_token']
        session['ml_refresh_token'] = token_data['refresh_token']
        session['ml_user_id'] = token_data['user_id']
        
        flash('✅ Conectado con Mercado Libre exitosamente', 'success')
        return redirect(url_for('ml_ver_ordenes'))
    else:
        flash('❌ Error al obtener token de ML', 'error')
        return redirect(url_for('index'))


# ========================================
# RUTA 3: Ver órdenes de ML
# ========================================

@app.route('/ml/ordenes')
def ml_ver_ordenes():
    """Muestra las últimas órdenes de ML (solo para ver qué trae)"""
    
    # Verificar que esté conectado
    if 'ml_access_token' not in session:
        flash('Primero debes conectar con Mercado Libre', 'warning')
        return redirect(url_for('ml_conectar'))
    
    access_token = session['ml_access_token']
    user_id = session['ml_user_id']
    
    # Traer órdenes de las últimas 24 horas
    url = f"{ML_CONFIG['API_BASE']}/orders/search"
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'seller': user_id,
        'sort': 'date_desc',
        'limit': 10  # Solo las últimas 10
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            ordenes = data.get('results', [])
            
            # Procesar órdenes para mostrar
            ordenes_procesadas = []
            
            for orden in ordenes:
                ordenes_procesadas.append({
                    'id': orden['id'],
                    'fecha': orden['date_created'],
                    'estado': orden['status'],
                    'total': orden['total_amount'],
                    'comprador': orden['buyer']['nickname'],
                    'items_count': len(orden.get('order_items', [])),
                    'shipping_type': orden.get('shipping', {}).get('shipping_option', {}).get('name', '-'),
                    'datos_completos': orden  # Guardar TODO para explorar
                })
            
            return render_template('ml_ordenes.html', ordenes=ordenes_procesadas)
        
        elif response.status_code == 401:
            # Token expirado
            flash('Token expirado, reconectando...', 'warning')
            return redirect(url_for('ml_conectar'))
        
        else:
            flash(f'Error al obtener órdenes: {response.status_code}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))


# ============================================================================
# PASO 5: CREAR TEMPLATE ml_ordenes.html
# ============================================================================

# Crear archivo: templates/ml_ordenes.html

"""
{% extends "base.html" %}

{% block title %}Órdenes de Mercado Libre{% endblock %}

{% block content %}
<div class="container">
    <h2>📦 Órdenes de Mercado Libre</h2>
    <p class="text-muted">Últimas 10 órdenes (solo visualización)</p>
    
    <div class="alert alert-info">
        <i class="bi bi-info-circle"></i>
        <strong>Fase 1:</strong> Solo estamos viendo qué datos trae ML. 
        Todavía NO importamos nada al sistema.
    </div>
    
    {% if ordenes %}
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>ID Orden</th>
                    <th>Fecha</th>
                    <th>Estado</th>
                    <th>Comprador</th>
                    <th>Total</th>
                    <th>Items</th>
                    <th>Envío</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                {% for orden in ordenes %}
                <tr>
                    <td><strong>{{ orden.id }}</strong></td>
                    <td>{{ orden.fecha[:10] }}</td>
                    <td>
                        {% if orden.estado == 'paid' %}
                            <span class="badge bg-success">Pagada</span>
                        {% elif orden.estado == 'confirmed' %}
                            <span class="badge bg-info">Confirmada</span>
                        {% else %}
                            <span class="badge bg-secondary">{{ orden.estado }}</span>
                        {% endif %}
                    </td>
                    <td>{{ orden.comprador }}</td>
                    <td>${{ "{:,.0f}".format(orden.total) }}</td>
                    <td>{{ orden.items_count }} items</td>
                    <td>{{ orden.shipping_type }}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" 
                                onclick="verDetalles({{ orden.datos_completos|tojson }})">
                            <i class="bi bi-eye"></i> Ver todo
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="alert alert-warning">
        No hay órdenes recientes
    </div>
    {% endif %}
    
    <div class="mt-4">
        <a href="{{ url_for('index') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Volver
        </a>
    </div>
</div>

<!-- Modal para ver detalles completos -->
<div class="modal fade" id="modalDetalles" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Datos completos de ML</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <pre id="datosJSON" style="max-height: 500px; overflow-y: auto;"></pre>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        </div>
    </div>
</div>

<script>
function verDetalles(datos) {
    // Mostrar JSON completo para explorar
    document.getElementById('datosJSON').textContent = JSON.stringify(datos, null, 2);
    const modal = new bootstrap.Modal(document.getElementById('modalDetalles'));
    modal.show();
}
</script>

{% endblock %}
"""

# ============================================================================
# PASO 6: AGREGAR BOTÓN EN EL MENÚ PRINCIPAL
# ============================================================================

# En templates/base.html o index.html, agregar:

"""
<a href="{{ url_for('ml_conectar') }}" class="btn btn-info">
    <i class="bi bi-box"></i> Conectar con Mercado Libre
</a>
"""

# ============================================================================
# VERIFICACIÓN FASE 1:
# ============================================================================

# 1. Reiniciar Flask
# 2. Click en "Conectar con Mercado Libre"
# 3. Login en ML
# 4. Autorizar la app
# 5. Ver lista de órdenes
# 6. Click en "Ver todo" → Ver JSON completo con TODOS los datos disponibles

# ============================================================================
# PRÓXIMOS PASOS (FASE 2):
# ============================================================================

# Una vez que veas qué datos trae ML, decidir:
# - ¿Qué campos querés importar?
# - ¿Cómo mapear productos ML → tus SKUs?
# - ¿Importar direcciones?
# - ¿Importar método de pago?

# Luego armamos la Fase 2: Botón "Importar esta orden"
