# 🗄️ DB_SCHEMA — Schema completo de la BD

Generado automáticamente por `scripts/generar_db_schema.py` el 2026-05-21 12:38. **No editar a mano.**

Base de datos: `inventario_cannon` — 44 tablas

Cada tabla muestra: cantidad de filas, todas las columnas con tipo, y los **valores típicos** de columnas que parecen enum implícito (útil para conocer estados, canales, métodos, etc.).

---

## `alertas_stock`  _(filas: 565)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | MUL |  |  |
| `nombre_producto` | `varchar(255)` | YES |  |  |  |
| `stock_fisico` | `int` | YES |  | `0` |  |
| `stock_vendido` | `int` | YES |  | `0` |  |
| `stock_disponible` | `int` | YES |  | `0` |  |
| `tipo_alerta` | `varchar(50)` | YES |  | `SIN_STOCK` |  |
| `estado` | `varchar(20)` | YES | MUL | `pendiente` |  |
| `mlas_afectados` | `varchar(255)` | YES |  |  |  |
| `fecha_creacion` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_procesada` | `datetime` | YES |  |  |  |
| `tipo_procesado` | `varchar(20)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo_alerta`** → `COMBO_SIN_COMPONENTE` (315), `SIN_STOCK` (250)
- **`estado`** → `procesada` (471), `pendiente` (94)
- **`tipo_procesado`** → `ambos` (128), `normal` (8), `z` (4)

---

## `auto_import_log`  _(filas: 1)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `ventas_nuevas` | `int` | YES |  | `0` |  |
| `ultima_ejecucion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `errores` | `text` | YES |  |  |  |
| `ventas_no_mapeadas` | `int` | YES |  | `0` |  |

---

## `cannon_costos_envio`  _(filas: 19)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | UNI |  |  |
| `tipo` | `enum('colecta','flex')` | NO |  |  |  |
| `costo` | `decimal(10,2)` | NO |  | `0.00` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`sku`** → `CPR8020` (1), `CTR80` (1), `CSO80` (1), `CSO100` (1), `CREP80` (1), `CREP100` (1), `CRE80` (1), `CPR9023` (1), `CPR9020` (1), `CPR8023` (1), `CDO100` (1), `CPR10023` (1), `CPR10020` (1), `CEXP90` (1), `CEXP80` (1), `CEXP100` (1), `CEX80` (1), `CEX100` (1), `CDO80` (1)
- **`tipo`** → `colecta` (19)

---

## `cannon_descuentos`  _(filas: 19)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `clave` | `varchar(100)` | NO | UNI |  |  |
| `descripcion` | `varchar(255)` | NO |  |  |  |
| `valor` | `decimal(8,4)` | NO |  | `0.0000` |  |
| `desc_adicional` | `decimal(8,4)` | NO |  | `0.0000` |  |
| `tipo` | `enum('descuento_linea','descuento_adicional','prontopago','multiplicador')` | NO |  |  |  |

**Valores típicos (enums implícitos):**

- **`clave`** → `platino` (1), `tropical` (1), `sublime_europillow` (1), `sublime` (1), `sonar` (1), `renovation_europillow` (1), `renovation` (1), `prontopago` (1), `princess_23` (1), `princess_20` (1), `almohadas` (1), `multiplicador` (1), `exclusive_pillow` (1), `exclusive` (1), `especial_de_lujo` (1), `doral_pillow` (1), `doral` (1), `cliente` (1), `bases` (1)
- **`tipo`** → `descuento_linea` (17), `prontopago` (1), `multiplicador` (1)

---

## `cannon_facturas`  _(filas: 76)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `nro_comprobante` | `varchar(30)` | NO |  |  |  |
| `fecha_comprobante` | `date` | NO |  |  |  |
| `fecha_recepcion` | `date` | NO |  |  |  |
| `importe_total` | `decimal(14,2)` | NO |  |  |  |
| `descuento_pp_pct` | `decimal(5,2)` | NO |  | `5.00` |  |
| `importe_pp` | `int` | NO |  |  |  |
| `descuento_pp_monto` | `int` | NO |  |  |  |
| `fecha_pago` | `date` | NO |  |  |  |
| `pago_id` | `int` | YES |  |  |  |
| `tiene_error` | `tinyint(1)` | YES |  | `0` |  |
| `notas` | `text` | YES |  |  |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `cannon_lista_precios`  _(filas: 163)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `codigo_material` | `bigint` | NO | UNI |  |  |
| `precio_lista` | `decimal(12,2)` | NO |  |  |  |
| `vigencia` | `date` | YES |  |  |  |
| `fecha_carga` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `cannon_pagos`  _(filas: 21)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha_pago` | `date` | NO |  |  |  |
| `monto_abonado` | `decimal(14,2)` | YES |  |  |  |
| `fecha_abono` | `date` | YES |  |  |  |
| `pp_recibido` | `tinyint(1)` | YES |  | `0` |  |
| `fecha_pp` | `date` | YES |  |  |  |
| `notas` | `text` | YES |  |  |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `cannon_productos`  _(filas: 184)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `codigo_material` | `bigint` | NO | UNI |  |  |
| `descripcion` | `varchar(255)` | NO |  |  |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `ean` | `bigint` | YES |  |  |  |
| `activo` | `tinyint(1)` | NO |  | `1` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `cannon_reclamos`  _(filas: 7)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `factura_id` | `int` | NO | MUL |  |  |
| `detalle_error` | `text` | NO |  |  |  |
| `fecha_reclamo` | `date` | NO |  |  |  |
| `nro_nc_resolucion` | `varchar(30)` | YES |  |  |  |
| `resuelto` | `tinyint(1)` | YES |  | `0` |  |
| `fecha_resolucion` | `date` | YES |  |  |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`nro_nc_resolucion`** → `NC75A12690` (1), `NC75A12689` (1)

---

## `competencia_snapshots`  _(filas: 29,557)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `timestamp` | YES | MUL | `CURRENT_TIMESTAMP` |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `tipo` | `varchar(10)` | YES |  | `colchon` |  |
| `modelo` | `varchar(60)` | YES |  | `` |  |
| `medida` | `smallint` | YES |  | `0` |  |
| `catalog_product_id` | `varchar(30)` | YES |  |  |  |
| `cp` | `varchar(10)` | YES |  |  |  |
| `cp_label` | `varchar(20)` | YES |  |  |  |
| `seller_id` | `int` | YES | MUL |  |  |
| `seller_nick` | `varchar(100)` | YES |  |  |  |
| `item_id` | `varchar(20)` | YES |  |  |  |
| `precio` | `decimal(12,2)` | YES |  |  |  |
| `cuotas_publi` | `varchar(30)` | YES |  |  |  |
| `cuotas_efectivas` | `varchar(30)` | YES |  |  |  |
| `envio_tipo` | `varchar(20)` | YES |  |  |  |
| `envio_gratis` | `tinyint(1)` | YES |  | `0` |  |
| `envio_costo` | `decimal(10,2)` | YES |  | `0.00` |  |
| `es_propio` | `tinyint(1)` | YES |  | `0` |  |
| `pausada_sin_stock` | `tinyint(1)` | YES |  | `0` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (18,148), `sommier` (11,409)
- **`modelo`** → `Exclusive Pillow` (4,705), `Exclusive` (4,524), `Doral Pillow` (3,916), `Doral` (3,660), `Princess` (3,630), `Soñar` (2,614), `Sublime Pillow` (2,238), `Renovation` (2,058), `Renovation Euro Pillow` (1,765), `Tropical` (447)
- **`cp`** → `1425` (29,557)
- **`cp_label`** → `CABA` (29,557)
- **`seller_nick`** → `MERCADOMUEBLES` (14,163), `TMS` (7,523), `COLCHONERIA IVANA` (4,288), `MUEBLESLANUS` (3,569), `MERCADOMUEBLES (pausada)` (14)
- **`cuotas_publi`** → `Sin cuotas` (8,011), `6 cuotas s/interés` (6,795), `9 cuotas s/interés` (4,756), `3 cuotas s/interés` (4,484), `12 cuotas s/interés` (4,359), `Cuota Simple` (1,152)
- **`cuotas_efectivas`** → `Sin cuotas` (8,011), `6 cuotas s/interés` (6,795), `9 cuotas s/interés` (4,756), `3 cuotas s/interés` (4,484), `12 cuotas s/interés` (4,359), `Cuota Simple` (1,152)
- **`envio_tipo`** → `ME1` (20,110), `FLEX` (7,203), `COLECTA` (2,204), `OTRO` (40)

---

## `competencia_sondas`  _(filas: 10)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `item_id_ml` | `varchar(20)` | NO | UNI |  |  |
| `tipo` | `enum('colchon','sommier')` | NO | MUL |  |  |
| `cuotas_reales` | `int` | NO |  |  |  |
| `sku_referencia` | `varchar(20)` | YES |  |  |  |
| `url` | `text` | NO |  |  |  |
| `activa` | `tinyint(1)` | YES |  | `1` |  |
| `fecha_alta` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |
| `cuotas_mostradas_ultimo` | `int` | YES |  |  |  |
| `fecha_ultimo_scrape` | `datetime` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (5), `sommier` (5)
- **`sku_referencia`** → `CEX80` (5), `SEXP140` (5)

---

## `componentes`  _(filas: 163)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `producto_compuesto_id` | `int` | NO | MUL |  |  |
| `producto_base_id` | `int` | NO | MUL |  |  |
| `cantidad_necesaria` | `int` | YES |  | `1` |  |

---

## `configuracion`  _(filas: 28)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `clave` | `varchar(100)` | NO | PRI |  |  |
| `valor` | `text` | YES |  |  |  |
| `actualizado_at` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `conjunto_configuracion`  _(filas: 62)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `colchon_sku` | `varchar(50)` | NO | UNI |  |  |
| `base_sku_default` | `varchar(50)` | NO | MUL |  |  |
| `cantidad_bases` | `tinyint` | YES |  | `1` |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |

---

## `cupones`  _(filas: 91)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `codigo` | `varchar(50)` | NO | UNI |  |  |
| `tipo` | `enum('pct','fijo')` | NO |  | `pct` |  |
| `valor` | `decimal(10,2)` | NO |  |  |  |
| `minimo_compra` | `decimal(10,2)` | YES |  | `0.00` |  |
| `usos_maximos` | `int` | YES |  |  |  |
| `usos_actuales` | `int` | YES |  | `0` |  |
| `fecha_vencimiento` | `date` | YES |  |  |  |
| `solo_un_uso` | `tinyint` | YES |  | `0` |  |
| `activo` | `tinyint` | YES |  | `1` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `fijo` (91)

---

## `cupones_uso`  _(filas: 16)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `cupon_id` | `int` | NO |  |  |  |
| `email` | `varchar(255)` | YES |  |  |  |
| `telefono` | `varchar(50)` | YES |  |  |  |
| `venta_numero` | `varchar(100)` | YES |  |  |  |
| `fecha_uso` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`venta_numero`** → `MP-153525353148` (1), `MP-153262940295` (1), `MP-154547806056` (1), `MP-153838512893` (1), `MP-153972975503` (1), `MP-154181352617` (1), `MP-154469627549` (1), `MP-154620847181` (1), `MP-155287347205` (1), `MP-155363650953` (1), `GN-c3e29cbb7ce34e` (1), `MP-156913076919` (1), `MP-157091352237` (1), `MP-157869869164` (1), `MP-157672077543` (1), `GN-0353de63803344` (1)

---

## `fletero_zonas`  _(filas: 7)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fletero_id` | `int` | NO | MUL |  |  |
| `nombre_zona` | `varchar(50)` | NO |  |  |  |
| `largo_cm` | `int` | NO |  |  |  |
| `ancho_cm` | `int` | NO |  |  |  |
| `alto_cm` | `int` | NO |  |  |  |
| `orden` | `int` | YES |  | `1` |  |

**Valores típicos (enums implícitos):**

- **`nombre_zona`** → `Caja` (3), `Adentro` (1), `Arriba` (1), `Tapa rueda` (1), `Buche` (1)

---

## `fleteros`  _(filas: 6)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `nombre` | `varchar(100)` | NO | UNI |  |  |
| `activo` | `tinyint` | YES |  | `1` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `notas` | `text` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`nombre`** → `Angel` (1), `Ezequiel` (1), `Federico` (1), `Horacio` (1), `Lean` (1), `Leo` (1)

---

## `fletes_registros`  _(filas: 113)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fletero_id` | `int` | NO | MUL |  |  |
| `fecha` | `date` | NO |  |  |  |
| `descripcion` | `varchar(200)` | YES |  | `` |  |
| `monto` | `decimal(10,2)` | NO |  |  |  |
| `pagado` | `tinyint` | YES |  | `0` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `domicilios` | `int` | YES |  | `0` |  |
| `fecha_pago` | `date` | YES |  |  |  |

---

## `items_venta`  _(filas: 3,110)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `venta_id` | `int` | NO | MUL |  |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `cantidad` | `int` | NO |  |  |  |
| `precio_unitario` | `decimal(10,2)` | NO |  |  |  |

---

## `movimientos_stock`  _(filas: 2,530)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | MUL |  |  |
| `nombre_producto` | `varchar(255)` | YES |  |  |  |
| `tipo_movimiento` | `enum('carga','baja','venta','ajuste')` | NO | MUL |  |  |
| `cantidad` | `int` | NO |  |  |  |
| `stock_anterior` | `int` | NO |  |  |  |
| `stock_nuevo` | `int` | NO |  |  |  |
| `motivo` | `text` | YES |  |  |  |
| `usuario` | `varchar(100)` | YES |  | `Sistema` |  |
| `fecha_movimiento` | `datetime` | YES | MUL | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo_movimiento`** → `venta` (1,585), `carga` (890), `baja` (55)
- **`usuario`** → `Sistema` (2,530)

---

## `ofertas_home`  _(filas: 23)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `descuento_pct` | `decimal(5,2)` | YES |  | `8.00` |  |
| `orden` | `int` | YES |  | `0` |  |
| `activo` | `tinyint` | YES |  | `1` |  |

---

## `pedidos_pendientes`  _(filas: 380)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `ref` | `varchar(32)` | NO | PRI |  |  |
| `carrito_json` | `text` | NO |  |  |  |
| `cliente_json` | `text` | NO |  |  |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `pedidos_pendientes_getnet`  _(filas: 52)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `pedido_ref` | `varchar(64)` | NO | PRI |  |  |
| `payment_intent_id` | `varchar(64)` | YES | MUL |  |  |
| `datos_cliente` | `json` | YES |  |  |  |
| `datos_carrito` | `json` | YES |  |  |  |
| `total` | `decimal(12,2)` | YES |  |  |  |
| `costo_flete` | `decimal(12,2)` | YES |  | `0.00` |  |
| `metodo_envio` | `varchar(50)` | YES |  |  |  |
| `direccion` | `varchar(500)` | YES |  |  |  |
| `fecha_creacion` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_expiracion` | `datetime` | YES |  |  |  |
| `estado` | `varchar(20)` | YES | MUL | `pendiente` |  |

**Valores típicos (enums implícitos):**

- **`metodo_envio`** → `Flete Propio` (29), `` (21), `Zippin` (2)
- **`estado`** → `pendiente` (43), `procesado` (9)

---

## `productos_base`  _(filas: 126)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | UNI |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `tipo` | `varchar(50)` | NO |  |  |  |
| `linea` | `varchar(50)` | YES |  |  |  |
| `modelo` | `varchar(100)` | YES |  |  |  |
| `medida` | `varchar(50)` | YES |  |  |  |
| `tipo_base` | `varchar(50)` | YES |  |  |  |
| `modelo_almohada` | `varchar(100)` | YES |  |  |  |
| `stock_actual` | `int` | YES |  | `0` |  |
| `stock_full` | `int` | YES |  | `0` |  |
| `stock_minimo_pausar` | `int` | YES |  | `0` |  |
| `stock_minimo_reactivar` | `int` | YES |  | `1` |  |
| `precio_base` | `decimal(10,2)` | YES |  | `0.00` |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `peso_gramos` | `int` | YES |  |  |  |
| `alto_cm` | `int` | YES |  |  |  |
| `ancho_cm` | `int` | YES |  |  |  |
| `largo_cm` | `int` | YES |  |  |  |
| `descuento_catalogo` | `decimal(5,2)` | YES |  |  |  |
| `activo` | `tinyint(1)` | NO |  | `1` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (81), `base` (26), `servicio` (10), `almohada` (9)
- **`linea`** → `espuma` (44), `resortes` (22), `box` (8), `` (1)
- **`modelo`** → `Exclusive` (8), `Exclusive Pillow` (8), `Renovation` (8), `Renovation Europillow` (8), `Doral` (8), `Doral Pillow` (5), `Sublime Europillow` (5), `Princess 20cm` (4), `Princess 23cm` (4), `Compac` (4), `Compac Plus Pocket` (4), `Soñar` (4), `Tropical` (3), `Prueba` (1), `` (1)
- **`modelo_almohada`** → `Platino` (1), `Doral` (1), `Exclusive` (1), `Visco Clásica` (1), `Visco Cervical` (1), `Sublime` (1), `Renovation` (1), `Dual Refreshing` (1), `None` (1)

---

## `productos_compuestos`  _(filas: 79)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | UNI |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `descripcion` | `text` | YES |  |  |  |
| `precio_base` | `decimal(10,2)` | YES |  |  |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `descuento_catalogo` | `decimal(5,2)` | YES |  |  |  |

---

## `productos_fotos`  _(filas: 555)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | MUL |  |  |
| `filename` | `varchar(255)` | NO |  |  |  |
| `orden` | `int` | YES |  | `0` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`filename`** → `1.jpg` (130), `2.jpg` (123), `3.jpg` (122), `4.jpg` (84), `5.jpg` (44), `6.jpg` (15), `2.png` (9), `1.png` (9), `4.png` (5), `5.png` (5), `6.png` (3), `7.jpg` (3), `3.png` (3)

---

## `sistema_logs`  _(filas: 738)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `timestamp` | `datetime` | YES | MUL | `CURRENT_TIMESTAMP` |  |
| `nivel` | `enum('INFO','WARNING','ERROR')` | YES | MUL | `INFO` |  |
| `modulo` | `varchar(50)` | YES | MUL |  |  |
| `accion` | `varchar(100)` | YES |  |  |  |
| `detalle` | `text` | YES |  |  |  |
| `sku` | `varchar(50)` | YES | MUL |  |  |
| `venta_id` | `int` | YES |  |  |  |
| `usuario` | `varchar(100)` | YES |  |  |  |
| `ip` | `varchar(50)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`nivel`** → `INFO` (738)
- **`modulo`** → `entrega` (638), `webhook` (59), `venta` (29), `stock` (12)
- **`accion`** → `venta_entregada` (638), `nueva_venta_mp` (44), `nueva_venta` (29), `baja_stock` (12), `nueva_venta_getnet` (9), `nueva_venta_payway` (6)
- **`sku`** → `CERVICAL` (3), `BASE_CHOC100` (1), `BASE_CHOC140` (1), `BASE_GRIS100` (1), `CCO160_DEP` (1), `CDO140` (1), `CEX100` (1), `CLASICA` (1), `CPR9020` (1), `CREP140` (1)
- **`usuario`** → `romi` (425), `manu` (236), `mercadomuebles` (18)
- **`ip`** → `127.0.0.1` (29)

---

## `sku_catalog_map`  _(filas: 88)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | YES | UNI |  |  |
| `catalog_product_id` | `varchar(30)` | YES |  |  |  |
| `category_id` | `varchar(20)` | YES |  |  |  |
| `mla_ref` | `varchar(20)` | YES |  |  |  |
| `actualizado_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `sku_mla_mapeo`  _(filas: 980)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | MUL |  |  |
| `mla_id` | `varchar(20)` | NO | MUL |  |  |
| `titulo_ml` | `varchar(255)` | YES |  |  |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `permalink` | `varchar(500)` | YES |  |  |  |

---

## `sku_tiendanube_mapeo`  _(filas: 139)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku_interno` | `varchar(50)` | NO | MUL |  |  |
| `tiendanube_product_id` | `bigint` | NO | MUL |  |  |
| `tiendanube_variant_id` | `bigint` | NO | UNI |  |  |
| `tipo` | `enum('colchon','conjunto','almohada','base')` | NO |  | `colchon` |  |
| `base_sku` | `varchar(50)` | YES |  |  |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (71), `conjunto` (60), `almohada` (8)

---

## `stock_comprometido_ventas`  _(filas: 38)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `sku` | `varchar(50)` | NO |  |  |  |
| `cantidad` | `decimal(32,0)` | YES |  |  |  |

---

## `stock_compuestos`  _(filas: 79)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `producto_compuesto_id` | `int` | NO |  | `0` |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `precio_base` | `decimal(10,2)` | YES |  |  |  |
| `stock_disponible` | `bigint` | YES |  |  |  |
| `componentes_detalle` | `text` | YES |  |  |  |

---

## `stock_disponible_ml`  _(filas: 205)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO |  | `0` |  |
| `sku` | `varchar(50)` | NO |  | `` |  |
| `nombre` | `varchar(255)` | NO |  | `` |  |
| `medida` | `varchar(7)` | YES |  |  |  |
| `tipo` | `varchar(50)` | NO |  | `` |  |
| `stock_fisico` | `int` | YES |  |  |  |
| `stock_comprometido` | `bigint` | NO |  | `0` |  |
| `stock_disponible` | `bigint` | YES |  |  |  |
| `stock_minimo_pausar` | `bigint` | YES |  |  |  |
| `stock_minimo_reactivar` | `bigint` | YES |  |  |  |
| `tipo_producto` | `varchar(9)` | NO |  | `` |  |
| `modelo` | `varchar(100)` | YES |  |  |  |
| `estado_stock` | `varchar(10)` | NO |  | `` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (83), `sommier` (72), `base` (26), `almohada` (14), `servicio` (10)
- **`tipo_producto`** → `BASE` (126), `COMPUESTO` (79)
- **`modelo`** → `Exclusive` (8), `Exclusive Pillow` (8), `Renovation` (8), `Renovation Europillow` (8), `Doral` (8), `Doral Pillow` (5), `Sublime Europillow` (5), `Princess 20cm` (4), `Princess 23cm` (4), `Compac` (4), `Compac Plus Pocket` (4), `Soñar` (4), `Tropical` (3), `Prueba` (1), `` (1)
- **`estado_stock`** → `DISPONIBLE` (135), `SIN_STOCK` (70)

---

## `stock_disponible_real`  _(filas: 126)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `sku` | `varchar(50)` | NO |  |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `tipo` | `varchar(50)` | NO |  |  |  |
| `stock_fisico` | `int` | YES |  | `0` |  |
| `cantidad_vendida` | `decimal(32,0)` | NO |  | `0` |  |
| `stock_disponible` | `decimal(33,0)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (81), `base` (26), `servicio` (10), `almohada` (9)

---

## `suscriptores`  _(filas: 86)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `email` | `varchar(255)` | NO | UNI |  |  |
| `cupon_id` | `int` | YES |  |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `tiendanube_config`  _(filas: 4)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `store_id` | `varchar(50)` | NO |  |  |  |
| `access_token` | `varchar(255)` | NO |  |  |  |
| `token_type` | `varchar(50)` | YES |  | `Bearer` |  |
| `scope` | `varchar(500)` | YES |  |  |  |
| `user_id` | `varchar(50)` | YES |  |  |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_actualizacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`scope`** → `write_products` (3), `write_products,write_orders_risk,read_orders_risk` (1)

---

## `tiendanube_ordenes`  _(filas: 0)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `tiendanube_order_id` | `bigint` | NO | UNI |  |  |
| `estado` | `varchar(50)` | NO |  |  |  |
| `payment_status` | `varchar(50)` | YES |  |  |  |
| `total` | `decimal(12,2)` | YES |  |  |  |
| `cliente_nombre` | `varchar(255)` | YES |  |  |  |
| `cliente_email` | `varchar(255)` | YES |  |  |  |
| `datos_json` | `longtext` | YES |  |  |  |
| `procesada` | `tinyint(1)` | YES |  | `0` |  |
| `fecha_orden` | `timestamp` | YES |  |  |  |
| `fecha_procesada` | `timestamp` | YES |  |  |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `usuarios`  _(filas: 4)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `username` | `varchar(50)` | NO | UNI |  |  |
| `password_hash` | `varchar(255)` | NO |  |  |  |
| `rol` | `enum('admin','vendedor','viewer','agencia')` | YES |  | `viewer` |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`username`** → `manu` (1), `mercadomuebles` (1), `milbrands` (1), `romi` (1)
- **`rol`** → `admin` (1), `vendedor` (1), `viewer` (1), `agencia` (1)

---

## `ventas`  _(filas: 2,928)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `numero_venta` | `varchar(100)` | NO | UNI |  |  |
| `mla_code` | `varchar(50)` | YES |  |  |  |
| `canal` | `varchar(50)` | NO |  |  |  |
| `nombre_cliente` | `varchar(255)` | NO |  |  |  |
| `telefono_cliente` | `varchar(50)` | NO |  |  |  |
| `dni_cliente` | `varchar(20)` | YES |  |  | DNI/CUIT del cliente |
| `provincia_cliente` | `varchar(100)` | YES |  | `Capital Federal` | Provincia del cliente |
| `fecha_venta` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_entrega_estimada` | `date` | YES |  |  |  |
| `fecha_entrega_real` | `datetime` | YES |  |  |  |
| `importe_total` | `decimal(10,2)` | NO |  |  |  |
| `importe_abonado` | `decimal(10,2)` | YES |  | `0.00` |  |
| `metodo_pago` | `varchar(100)` | YES |  |  |  |
| `tipo_entrega` | `varchar(50)` | YES |  |  |  |
| `metodo_envio` | `varchar(50)` | YES |  |  |  |
| `ubicacion_despacho` | `enum('DEP','FULL')` | YES |  | `DEP` | Ubicación desde donde se despachará (DEP=Depósito propio, FULL=Full ML) |
| `zona_envio` | `varchar(50)` | YES |  |  |  |
| `direccion_entrega` | `text` | YES |  |  |  |
| `responsable_entrega` | `varchar(100)` | YES |  |  |  |
| `estado_pago` | `varchar(50)` | YES |  | `pendiente` |  |
| `fecha_modificacion` | `timestamp` | YES |  |  |  |
| `fecha_entrega` | `datetime` | YES |  |  |  |
| `estado_entrega` | `varchar(50)` | YES |  | `pendiente` |  |
| `stock_descontado` | `tinyint(1)` | YES |  | `0` |  |
| `fecha_descuento_stock` | `datetime` | YES |  |  |  |
| `notas` | `text` | YES |  |  |  |
| `usuario_registro` | `varchar(100)` | YES |  |  |  |
| `fecha_registro` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `estado` | `enum('ACTIVA','EN_PROCESO','ENTREGADA','CANCELADA')` | YES |  | `ACTIVA` |  |
| `costo_flete` | `decimal(10,2)` | YES |  | `0.00` |  |
| `pago_mercadopago` | `decimal(10,2)` | YES |  | `0.00` |  |
| `pago_efectivo` | `decimal(10,2)` | YES |  | `0.00` |  |
| `pago_transferencia` | `decimal(10,2)` | YES |  | `0.00` |  |
| `pago_tarjeta` | `decimal(10,2)` | YES |  | `0.00` |  |
| `factura_business_name` | `varchar(255)` | YES |  |  | Razón social de ML |
| `factura_doc_type` | `varchar(50)` | YES |  |  | Tipo de documento |
| `factura_doc_number` | `varchar(50)` | YES |  |  | Número de documento/CUIT |
| `factura_taxpayer_type` | `varchar(100)` | YES |  |  | Tipo de contribuyente IVA |
| `factura_city` | `varchar(100)` | YES |  |  | Ciudad de facturación |
| `factura_street` | `varchar(255)` | YES |  |  | Dirección de facturación |
| `factura_state` | `varchar(100)` | YES |  |  | Provincia de facturación |
| `factura_zip_code` | `varchar(20)` | YES |  |  | Código postal |
| `factura_generada` | `tinyint(1)` | YES |  | `0` | Si ya se generó el Excel de facturación |
| `factura_fecha_generacion` | `datetime` | YES |  |  | Fecha de generación del Excel |
| `cancelada_en_ml` | `tinyint` | YES |  | `0` |  |
| `auto_imported_at` | `timestamp` | YES |  |  |  |
| `auto_rechecked` | `tinyint` | YES |  | `0` |  |
| `notas_auto_orig` | `text` | YES |  |  |  |
| `costo_comision` | `decimal(12,2)` | YES |  |  |  |
| `costo_envio_vendedor` | `decimal(12,2)` | YES |  |  |  |
| `costo_productos` | `decimal(12,2)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`canal`** → `Mercado Libre` (2,789), `tienda_web` (91), `Fuera de ML` (48)
- **`provincia_cliente`** → `Capital Federal` (2,866), `` (35), `Buenos Aires` (26), `Neuquén` (1)
- **`metodo_pago`** → `MercadoPago` (2,855), `Efectivo` (37), `GetNet` (9), `Transferencia` (8), `Payway` (8), `Mixto` (7), `Tarjeta` (4)
- **`tipo_entrega`** → `Envío` (2,804), `Retiro` (124)
- **`metodo_envio`** → `Colecta` (785), `Delega` (640), `Flex` (607), `Flete Propio` (413), `Full` (130), `Zippin` (113), `` (87), `Mercadoenvios` (61), `Turbo` (50), `ME2` (4)
- **`ubicacion_despacho`** → `DEP` (2,798), `FULL` (130)
- **`zona_envio`** → `` (2,475), `Capital` (127), `Sur` (113), `Oeste` (93), `Norte-Noroeste` (79)
- **`responsable_entrega`** → `` (1,249)
- **`estado_pago`** → `pagado` (2,901), `pago_pendiente` (25), `pago_parcial` (1), `pendiente` (1)
- **`estado_entrega`** → `entregada` (2,756), `pendiente` (91), `cancelada` (77), `en_proceso` (4)
- **`estado`** → `ACTIVA` (2,927), `CANCELADA` (1)
- **`factura_doc_type`** → `DNI` (2,539), `CUIT` (215)
- **`factura_taxpayer_type`** → `Consumidor Final` (2,598), `Responsable Inscripto` (97), `IVA Responsable Inscripto` (50), `Responsable Monotributo` (3), `IVA Exento` (2), `Sujeto No Categorizado` (2), `Monotributo` (1), `Exento` (1)

---

## `ventas_activas`  _(filas: 91)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | YES |  | `0` |  |
| `numero_venta` | `varchar(100)` | YES |  |  |  |
| `mla_code` | `varchar(50)` | YES |  |  |  |
| `canal` | `varchar(50)` | YES |  |  |  |
| `nombre_cliente` | `varchar(255)` | YES |  |  |  |
| `telefono_cliente` | `varchar(50)` | YES |  |  |  |
| `fecha_venta` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `fecha_entrega_estimada` | `date` | YES |  |  |  |
| `fecha_entrega_real` | `datetime` | YES |  |  |  |
| `importe_total` | `decimal(10,2)` | YES |  |  |  |
| `importe_abonado` | `decimal(10,2)` | YES |  | `0.00` |  |
| `metodo_pago` | `varchar(100)` | YES |  |  |  |
| `tipo_entrega` | `varchar(50)` | YES |  |  |  |
| `metodo_envio` | `varchar(50)` | YES |  |  |  |
| `zona_envio` | `varchar(50)` | YES |  |  |  |
| `direccion_entrega` | `text` | YES |  |  |  |
| `responsable_entrega` | `varchar(100)` | YES |  |  |  |
| `estado_pago` | `varchar(50)` | YES |  | `pendiente` |  |
| `estado_entrega` | `varchar(50)` | YES |  | `pendiente` |  |
| `stock_descontado` | `tinyint(1)` | YES |  | `0` |  |
| `fecha_descuento_stock` | `datetime` | YES |  |  |  |
| `notas` | `text` | YES |  |  |  |
| `usuario_registro` | `varchar(100)` | YES |  |  |  |
| `fecha_registro` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `cantidad_items` | `bigint` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`canal`** → `Mercado Libre` (79), `tienda_web` (9), `Fuera de ML` (3)
- **`metodo_pago`** → `Mercadopago` (87), `Efectivo` (3), `GetNet` (1)
- **`tipo_entrega`** → `envio` (82), `retiro` (9)
- **`metodo_envio`** → `Flete Propio` (27), `Delega` (24), `Zippin` (12), `Colecta` (11), `Flex` (7), `` (4), `Turbo` (1)
- **`zona_envio`** → `` (58), `Oeste` (11), `Capital` (8), `Sur` (4), `Norte-Noroeste` (4)
- **`responsable_entrega`** → `` (28)
- **`estado_pago`** → `pagado` (91)
- **`estado_entrega`** → `pendiente` (91)

---

## `viaje_paradas`  _(filas: 10)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `viaje_id` | `int` | NO | MUL |  |  |
| `orden_entrega` | `int` | NO |  |  |  |
| `venta_id` | `int` | YES | MUL |  |  |
| `cliente` | `varchar(150)` | YES |  |  |  |
| `direccion` | `varchar(255)` | YES |  |  |  |
| `notas` | `text` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`cliente`** → `marcelo martinez` (2), `Facundo Gonzalo Maciel` (2), `Ignacio Osvaldo Jose Calvo` (1), `Julian Tallarico` (1), `julia monzon` (1), `LORENA LOPEZ` (1), `vanesa cabrera` (1), `FLORENCIA FURIEUX` (1)

---

## `viajes`  _(filas: 2)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fletero_id` | `int` | NO | MUL |  |  |
| `fecha` | `date` | NO |  |  |  |
| `estado` | `enum('borrador','confirmado','en_ruta','entregado')` | YES |  | `borrador` |  |
| `notas` | `text` | YES |  |  |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`estado`** → `borrador` (2)

---

## `wa_mensajes`  _(filas: 1,546)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `phone` | `varchar(30)` | YES | MUL |  |  |
| `rol` | `enum('user','assistant')` | YES |  |  |  |
| `contenido` | `text` | YES |  |  |  |
| `derivado` | `tinyint(1)` | YES |  | `0` |  |

**Valores típicos (enums implícitos):**

- **`rol`** → `user` (773), `assistant` (773)

---
