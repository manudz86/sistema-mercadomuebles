# ============================================================================
# CAMBIO EN APP.PY - HABILITAR ACCESO EN RED
# ============================================================================

# BUSCAR al final de app.py:

if __name__ == '__main__':
    app.run(debug=True)

# ============================================================================

# REEMPLAZAR CON:

if __name__ == '__main__':
    # Configuración para red local
    app.run(
        host='0.0.0.0',      # Escuchar en todas las interfaces de red
        port=5000,            # Puerto del servidor
        debug=False,          # Desactivar debug en producción
        threaded=True         # Permitir múltiples usuarios simultáneos
    )

# ============================================================================

# EXPLICACIÓN:

# host='0.0.0.0'
#   → Flask escucha en TODAS las interfaces de red
#   → Permite acceso desde otras PCs
#   → Sin esto, solo funciona en localhost

# debug=False
#   → Desactiva el modo debug
#   → IMPORTANTE para multi-usuario
#   → En debug, recargas automáticas pueden causar problemas

# threaded=True
#   → Permite múltiples conexiones simultáneas
#   → Sin esto, si un usuario está usando el sistema, otro tiene que esperar

# ============================================================================

# RESULTADO:

# Al iniciar Flask verás:
#  * Running on http://0.0.0.0:5000
#  * Running on http://192.168.1.10:5000  ← IP local de tu PC

# Las otras PCs acceden a:
#  http://192.168.1.10:5000
