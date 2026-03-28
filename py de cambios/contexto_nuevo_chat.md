# Contexto Sistema Cannon — Mercadomuebles
## Para continuar desde donde dejamos

> **INSTRUCCIÓN IMPORTANTE**: Este es un contexto de continuación. NO es un chat nuevo. Manu y yo venimos trabajando juntos hace semanas en este sistema. Si algo no queda claro de este documento, debés leer el historial completo de la conversación anterior antes de preguntar. El historial está en el transcript de la sesión anterior.

---

## IDENTIDAD DEL PROYECTO

**Manu** — dueño de Mercadomuebles / Grupo Piero, Buenos Aires. Distribuidor oficial Cannon.
- Comunicación: español rioplatense informal, respuestas concisas
- Trabaja desde Windows CMD, gestiona VPS via SSH / FileZilla / git

**Sistema:** Flask + MySQL — "Sistema Cannon" — panel admin + tienda web

---

## INFRAESTRUCTURA VPS

- **VPS:** Hostinger KVM1, IP `72.61.134.243`, user `root`
- **App:** `/home/cannon/app/` · venv en `/home/cannon/app/venv/`
- **Servicio:** `systemctl restart cannon` (gunicorn, 3 workers, puerto 5000)
- **DB:** MySQL · `inventario_cannon` · user: `cannon` · pass: `Sistema@32267845`
- **Admin:** `sistema.mercadomuebles.com.ar` (app.py, ~11.800 líneas)
- **Tienda:** `www.mercadomuebles.com.ar` (tienda_bp.py)

## DEPLOY

- **Sistema admin:** `deploy_vps.bat` (git push + pull VPS + restart)
  - GitHub: https://github.com/manudz86/sistema-mercadomuebles
- **Tienda:** SCP directo — `tienda_bp.py` y `templates/tienda/` **NO están en git**
- **base.html admin:** está en git
- **ventas_activas.html:** NO está en git — SCP directo

## METODOLOGÍA DE TRABAJO

1. Manu sube el archivo del VPS acá
2. Yo lo trabajo localmente en `/home/claude/`
3. Entrego con `present_files` → `/mnt/user-data/outputs/`
4. Manu descarga y hace deploy
5. **NUNCA** tocar el VPS directamente — siempre pasar por el archivo
6. Código completo, nunca fragmentos
7. Identificar causa raíz antes de proponer fix
8. Comandos numerados para pasos en VPS
9. Outputs siempre con `present_files`

---

## USUARIOS Y ROLES

Tabla `usuarios` con `rol ENUM('admin','vendedor','viewer')`:
- `manu` → admin (ve todo)
- `romi` → vendedor (no ve costos, precios, catálogo)
- `mercadomuebles` → viewer (igual que vendedor)

Decoradores en app.py: `@admin_required` (solo admin), `@vendedor_required` (admin+vendedor)

---

## MÓDULO COSTOS (reciente)

**Tablas DB:**
- `cannon_productos` (codigo_material, descripcion, sku, activo)
- `cannon_lista_precios` (codigo_material, precio_lista, vigencia)
- `cannon_descuentos` (clave, descripcion, valor, desc_adicional, tipo)
- `cannon_costos_envio` (sku, tipo colecta/flex, costo)

**Fórmula precio lista:**
```
precio = precio_cannon × (1-desc_linea/100) × (1-desc_cliente/100) × (1-desc_adicional/100) × 1/(1+pp/100) × multiplicador
```

**Fórmula cuotas ML:**
```
precio_Xc = precio_sin_cuotas × 0.76 / (0.76 - coef/100)
```

**Descuentos actuales en DB:**
- Bases: 40% · Almohadas: 0% · Doral: 30% · Sublime: 30% · Exclusive: 40%
- Renovation: 40% · Princess 20/23: 35% · Tropical: 30%
- Desc. cliente: 10% · Prontopago: 5% · Multiplicador: 1.85

**Importador:** siempre usa columna D (precio neto) del Excel Cannon

**Detección de clave por descripción** — orden importante (bases ANTES que sublime):
```python
if sku.startswith('BASE_') or desc.startswith('SOM '): clave = 'bases'
elif 'SUBLIME' in desc: clave = 'sublime'  # etc.
```

**Rutas costos:** `/costos`, `/costos/calcular`, `/costos/descuentos`, `/costos/importar`, `/costos/productos`, `/costos/envio`, `/costos/envio/barrido-ml`, `/costos/aplicar`
— Todas protegidas con `@admin_required`

---

## TIENDA WEB

**Demora sin stock:**
- Config en DB: `INSERT INTO configuracion VALUES ('demora_sin_stock', '7')`
- Productos sin stock muestran "Disponible en X días" y permiten agregar
- **Excepciones** (sin demora, bloqueo normal): `linea='box'`, `linea='almohadas'`, `modelo='Compac'`, `tipo='almohada'`
- Lógica en `tienda_bp.py`: función `aplica_demora(linea, tipo, modelo)`

**Envío:**
- Colecta: colchones ≤100cm sin Z
- Flex: colchones >100cm sin Z, sommiers
- ME1/Flex propio: SKUs con Z
- Zipnova API para cotización

---

## PAPEL AZUL PDF

Ruta: `/ventas/<id>/papel-azul`
- Medidas: 165×215mm · Márgenes: top 70mm, bottom 27mm, left/right 7mm
- Flex → saldo $0 · Flete Propio → max(0, total + flete - abonado)
- Patas: ≤100cm → x6, >100cm → x7
- Botón 🖨️ en ventas_activas.html para ventas Flex/Flete Propio con dirección

---

## PENDIENTE AL CIERRE DE ESTA SESIÓN

### 🔴 URGENTE: Catálogo `/productos` da 404
Las rutas del catálogo de productos **nunca llegaron al VPS** correctamente. Están en el app.py local pero no se deployaron. Las rutas son:
```
/productos          → productos_lista()
/productos/toggle/<id>
/productos/nuevo
/productos/editar/<id>
/productos/<sku>/fotos
/productos/<sku>/fotos/subir
/productos/<sku>/fotos/eliminar
/productos/<sku>/fotos/reordenar
```
Templates: `productos_lista.html`, `productos_form.html`, `productos_fotos.html`
**Acción:** Manu debe subir el `app.py` del VPS y yo agrego las rutas del catálogo.

### 🟡 Pendientes costos
- Verificar que todos los precios de bases en P.Costos de tienda_precios sean correctos tras el fix de orden de detección (bases antes que sublime)
- Cargar costos de envío flex manualmente en `/costos/envio`

### 🟡 Pendientes tienda
- Template `detalle.html` del producto: mostrar "Disponible en X días" en vez de sin stock (solo se hizo en home.html)
- Confirmar SMTP puerto 465

### 🟡 Roles
- Panel de gestión de usuarios (cambiar roles desde UI) — por ahora solo por DB

---

## TOKENS ML

```python
# Token ML guardado en DB:
SELECT valor FROM configuracion WHERE clave = 'ml_token'
# → json.loads(row['valor']).get('access_token')
ML_SELLER_ID = 29563319
```

---

## DATOS CONEXIÓN RÁPIDA

```
SSH: ssh root@72.61.134.243
DB: mysql -u cannon -p'Sistema@32267845' inventario_cannon
Deploy: git push → VPS pull → systemctl restart cannon
SCP tienda: scp archivo.py root@72.61.134.243:/home/cannon/app/tienda_bp.py
SCP template: scp archivo.html root@72.61.134.243:/home/cannon/app/templates/tienda/archivo.html
```
