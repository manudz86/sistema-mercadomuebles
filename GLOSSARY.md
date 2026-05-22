# 📖 GLOSSARY — Convenciones del Sistema Cannon

Glosario de prefijos, estados, métodos y reglas del dominio. **Mantener a mano cuando los valores reales cambien.** (A diferencia de los otros .md, este no se autogenera.)

---

## Índice

1. [Prefijos de número de venta](#1-prefijos-de-número-de-venta)
2. [Convenciones de SKU](#2-convenciones-de-sku)
3. [Estados de venta y transiciones](#3-estados-de-venta-y-transiciones)
4. [Canales y métodos](#4-canales-y-métodos-de-venta)
5. [Stock: ubicaciones y movimientos](#5-stock)
6. [Productos: tipos y líneas](#6-productos)
7. [Roles y permisos](#7-roles-y-permisos)
8. [Pagos Cannon](#8-pagos-cannon)
9. [Cupones y descuentos](#9-cupones)
10. [Alertas de stock](#10-alertas-de-stock)
11. [Schedulers / jobs](#11-schedulers)
12. [Logs y WhatsApp](#12-logs-y-whatsapp)

---

## 1. Prefijos de número de venta

Cada venta tiene un `numero_venta` con un prefijo que identifica su origen. **Importante:** al derivar el "próximo número" hay que filtrar por formato. Mezclar prefijos rompió la numeración manual una vez (bug ya corregido en `nueva_venta()` con regex `^VENTA-[0-9]+$`).

| Prefijo | Origen | Generado por |
|---|---|---|
| `VENTA-NNN` | Manual (panel admin) | `app.py`: `nueva_venta()` / `guardar_venta()` |
| `ML-XXXXX` | MercadoLibre (auto-import + manual desde orden) | `app.py`: `_importar_orden_automatica()`, `nueva_venta_desde_ml()` |
| `MP-XXXXX` | Tienda web → MercadoPago | `tienda_bp.py`: `webhook_mp()` |
| `GN-XXXXX` | Tienda web → GetNet | `tienda_bp.py`: `webhook_getnet()` |
| `PW-XXXXX` | Tienda web → Payway | `tienda_bp.py`: `pago_payway()` |

---

## 2. Convenciones de SKU

### Prefijos por tipo de producto

| Prefijo | Tipo | Ejemplos |
|---|---|---|
| `C*` | Colchón | `CEX80`, `CDO140`, `CPR9020`, `CREP100`, `CTR80` |
| `S*` | Sommier (producto compuesto = colchón + base) | `SEX140`, `SDO80`, `SEXP100` |
| `BASE_*` | Base individual | `BASE_CHOC100`, `BASE_GRIS100` |
| (modelo) | Almohada | `PLATINO`, `EXCLUSIVE`, `CERVICAL`, `CLASICA` |

### Sufijos especiales

- **`+N`** (solo en sommiers) → cantidad de bases adicionales. Ej: `SEXP100+1` = 1 base extra.
- **`Z` al final** → publicación de ML con demora (`manufacturing_time`) configurada. Lógica de "publicaciones Z" en helpers `_aplica_logica_z()`, `_poner_demora_ml()`, `_quitar_demora_ml()`.

### Normalización

`normalizar_sku_ml()` (`app.py:L5882`) **quita la Z** y mapea diferencias entre el SKU de ML y el de la BD. Diccionario auxiliar: `SKU_MAP`. Helper para mapear conjunto ↔ colchón:

- `sku_colchon_a_conjunto()` (tienda) → `CEX140` ↔ `SEX140`
- `sku_conjunto_a_colchon()` (tienda) → limpia el `+N` también

---

## 3. Estados de venta y transiciones

Una venta tiene **tres campos de estado** en `ventas`:

### 3.1 `estado` (enum nativo)

Declaración del DDL: `enum('ACTIVA','EN_PROCESO','ENTREGADA','CANCELADA')`. Default: `ACTIVA`.

⚠️ **Atención:** la mayoría del flujo real usa `estado_entrega` y `estado_pago` por separado. El campo `estado` está casi siempre en `ACTIVA`.

### 3.2 `estado_entrega` (varchar — el realmente vivo)

Valores reales en uso:

| Valor | Significado |
|---|---|
| `pendiente` | Venta activa, no se despachó |
| `en_proceso` | Pasada a proceso de envío (stock descontado) |
| `entregada` | Entregada al cliente |
| `cancelada` | Cancelada (devolvió stock si estaba descontado) |

### 3.3 `estado_pago` (varchar)

| Valor | Significado |
|---|---|
| `pagado` | Cobro completo confirmado |
| `pago_pendiente` | Sin cobrar |
| `pago_parcial` | Parcialmente cobrado (importe_abonado < importe_total) |
| `pendiente` | Estado inicial |

### 3.4 Transiciones del flujo principal

```
   ACTIVAS                PROCESO              HISTÓRICAS
   ─────────              ────────             ──────────
   (pendiente) ──pasar──> (en_proceso) ──entregar──> (entregada)
        │                      │                          │
        │                      └──cancelar──> (cancelada) │
        │                                          ▲      │
        └────────cancelar────────────────────────  │      │
                                                          │
                       volver_a_activas <─────────────────┘
```

**Reglas:**

- Pasar a proceso: **descuenta stock** (con verificación de disponibilidad).
- Cancelar desde proceso: **devuelve stock** si estaba descontado.
- Marcar entregada desde activas: descuenta stock (si no se descontó).
- Volver a activas (desde histórica o proceso): devuelve stock si corresponde.

Endpoints principales: `/ventas/activas/<id>/proceso`, `/ventas/activas/<id>/entregada`, `/ventas/proceso/<id>/cancelar`, `/ventas/historicas/<id>/volver_activas`.

---

## 4. Canales y métodos de venta

### Canal (`ventas.canal`)

| Valor | Origen |
|---|---|
| `Mercado Libre` | Importadas desde ML |
| `tienda_web` | Tienda web propia |
| `Fuera de ML` | Cargadas manualmente desde el panel |

### Método de pago (`ventas.metodo_pago`)

`MercadoPago`, `Efectivo`, `GetNet`, `Transferencia`, `Payway`, `Mixto`, `Tarjeta`.

Para `Mixto` se usan los campos parciales: `pago_mercadopago`, `pago_efectivo`, `pago_transferencia`, `pago_tarjeta`.

### Tipo de entrega (`ventas.tipo_entrega`)

`Envío` o `Retiro` (también capitalizado como `envio`/`retiro` según donde se cargue — normalizar al comparar).

### Método de envío (`ventas.metodo_envio`)

`Colecta`, `Delega`, `Flex`, `Flete Propio`, `Full`, `Zippin`, `Mercadoenvios`, `Turbo`, `ME2`.

### Ubicación de despacho (`ventas.ubicacion_despacho`)

Enum nativo: `DEP` (depósito propio) o `FULL` (Full ML).

### Zona de envío (`ventas.zona_envio`)

`Capital`, `Sur`, `Oeste`, `Norte-Noroeste` (más vacío para los que no aplica).

---

## 5. Stock

### Ubicaciones (en `productos_base`)

- `stock_actual` → depósito propio
- `stock_full` → Full ML

### Operaciones

| Operación | Helper | Efecto |
|---|---|---|
| Cargar stock | `cargar_stock()` + `guardar_stock()` | SUMA al actual |
| Bajar stock | `bajar_stock_guardar()` | Resta del actual |
| Transferir | `transferir_stock_guardar()` | Dep ↔ Full (Compac y Almohadas) |
| Descontar por venta | `descontar_stock_item()` / `descontar_stock_simple()` | Por venta |
| Devolver | `devolver_stock_item()` / `devolver_stock_simple()` | Por cancelación |

### Movimientos (`movimientos_stock.tipo_movimiento`)

Enum nativo: `carga`, `baja`, `venta`, `ajuste`.

### Cálculo de disponibilidad

- `calcular_stock_por_sku()` y `obtener_stock_disponible()` — para base.
- `get_stock_disponible_sku()` (tienda) — incluye stock comprometido por ventas pendientes.
- `verificar_stock_disponible()` — antes de descontar.

Para **compuestos** (sommiers), el stock disponible se calcula a partir de los componentes base vía tabla `componentes`.

### Umbrales en `productos_base`

- `stock_minimo_pausar` → si baja de acá, pausar publicaciones ML
- `stock_minimo_reactivar` → si vuelve a estar arriba, reactivar

---

## 6. Productos

### Tipo (`productos_base.tipo`)

`colchon`, `base`, `almohada`, `servicio`.

### Línea (`productos_base.linea`)

`espuma`, `resortes`, `box`.

### Modelos de colchón

`Exclusive`, `Exclusive Pillow`, `Doral`, `Doral Pillow`, `Princess 20cm`, `Princess 23cm`, `Sublime Europillow`, `Renovation`, `Renovation Europillow`, `Soñar`, `Tropical`, `Compac`, `Compac Plus Pocket`.

### Compuestos

Tabla `productos_compuestos` (sommiers). Su composición se define en `componentes` (relación many-to-many con `productos_base` y cantidad). Configuración de defaults en `conjunto_configuracion` (colchón + base default + cantidad bases).

### Tipos de envío ML (`competencia_snapshots.envio_tipo`)

`ME1`, `FLEX`, `COLECTA`, `OTRO`.

---

## 7. Roles y permisos

### Roles (`usuarios.rol`)

Enum nativo: `admin`, `vendedor`, `viewer`, `agencia`.

- **admin** → acceso total al sistema.
- **vendedor** → puede operar ventas pero no toca configuración crítica.
- **viewer** → solo lectura.
- **agencia** → vista propia (`/agencia`), restringida a su panel.

---

## 8. Pagos Cannon

Módulo `pagos_cannon` — gestiona facturas a proveedor Cannon y pagos con pronto pago (PP).

### Tablas principales

| Tabla | Qué guarda |
|---|---|
| `cannon_facturas` | Comprobantes recibidos de Cannon (con descuento PP) |
| `cannon_pagos` | Pagos realizados (agrupados como "grupos") |
| `cannon_lista_precios` | Lista de precios oficial Cannon (por código_material) |
| `cannon_productos` | Mapeo código_material ↔ SKU interno |
| `cannon_costos_envio` | Costos colecta/flex por SKU (enum nativo `tipo`) |
| `cannon_descuentos` | Descuentos por modelo (ver tipos abajo) |
| `cannon_reclamos` | Reclamos por errores en facturas |

### Reglas del dominio

- **Pronto Pago (PP):** descuento por pago anticipado. Default `descuento_pp_pct = 5.00`. Cálculo: `_calcular_importe_pp()` → `total / 1.05`, redondeado sin decimales.
- **Fecha de pago:** `fecha_recepcion + 6 días` (timedelta).
- **Grupos de pagos:** las facturas se agrupan por rango de fechas. Ordenamiento: impagos primero (asc por fecha, más imminente arriba) → pagados después (desc).
- **Regla de integridad:** si se edita una factura y la nueva fecha cae en el rango de un grupo **ya pagado**, NO se absorbe ahí — se crea un **grupo nuevo impago**.

### Tipos de descuento (`cannon_descuentos.tipo`, enum nativo)

`descuento_linea`, `descuento_adicional`, `prontopago`, `multiplicador`.

---

## 9. Cupones

### Tipos (`cupones.tipo`, enum nativo)

| Valor | Significado |
|---|---|
| `pct` | Porcentaje (`valor` se interpreta como %) |
| `fijo` | Monto fijo en pesos |

Otros campos relevantes: `minimo_compra`, `usos_maximos`, `solo_un_uso`, `fecha_vencimiento`, `activo`.

Cupones de **newsletter** se generan en `suscribirse()` (tienda). Configuración del monto/mínimo: keys `nl_monto` y `nl_minimo` en `configuracion` (ver `CONFIG_MAP.md`).

---

## 10. Alertas de stock

Tabla `alertas_stock` — detección automática de problemas de stock vs publicaciones ML.

### Tipos (`tipo_alerta`)

- `SIN_STOCK` → el SKU base se quedó sin stock.
- `COMBO_SIN_COMPONENTE` → un compuesto no puede armarse porque le falta algún componente.

### Estados (`estado`)

`pendiente` o `procesada`.

### Tipo procesado (`tipo_procesado`)

Cuando se procesa, se registra qué se hizo en ML:

| Valor | Significado |
|---|---|
| `normal` | Bajaron a 0 las publicaciones normales (sin Z) |
| `z` | Configuraron demora en publicaciones Z |
| `ambos` | Las dos cosas |

---

## 11. Schedulers

3 jobs activos (definidos en `iniciar_scheduler()` — `app.py:L12549`):

| Job | Frecuencia | Qué hace |
|---|---|---|
| `job_auto_importar_ml` | 120s | Auto-importa órdenes nuevas de ML (controlado por flag `auto_import_activo`) |
| `job_verificar_cancelaciones_ml` | 10min | Detecta órdenes canceladas en ML y actualiza ventas |
| `job_completar_notas_mp` | 10min | Completa notas de MercadoPago en ventas |

Progreso del proceso pesado de actualización ML compartido entre workers vía key `ml_progress` en tabla `configuracion`.

---

## 12. Logs y WhatsApp

### `sistema_logs.nivel`

Enum nativo: `INFO`, `WARNING`, `ERROR`.

### `sistema_logs.modulo`

`entrega`, `webhook`, `venta`, `stock`.

### `wa_mensajes.rol`

Enum nativo: `user`, `assistant`. Conversaciones del bot WhatsApp (cliente vs bot).

---

## Apéndice: cosas a tener en cuenta

- **Provincia default:** `Capital Federal` (en `ventas.provincia_cliente`).
- **`cancelada_en_ml`** (en `ventas`) → flag separado, sincronizado por `job_verificar_cancelaciones_ml`.
- **`ventas_activas`, `stock_compuestos`, `stock_disponible_ml`, `stock_disponible_real`** son **VIEWS** (no tablas reales) que materializan cálculos comunes. No insertar/updatear directamente.
- **`pedidos_pendientes`** (MP) y **`pedidos_pendientes_getnet`** son tablas de "staging" del checkout antes de que llegue el webhook. La venta real se crea en `ventas` solo cuando el webhook confirma el pago.
