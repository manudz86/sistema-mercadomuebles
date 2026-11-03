# 🗄️ DB_SCHEMA — Schema completo de la BD

Generado automáticamente por `scripts/generar_db_schema.py` el 2026-11-03 21:22. **No editar a mano.**

Base de datos: `inventario_cannon` — 58 tablas

Cada tabla muestra: cantidad de filas, todas las columnas con tipo, y los **valores típicos** de columnas que parecen enum implícito (útil para conocer estados, canales, métodos, etc.).

---

## `alertas_stock`  _(filas: 607)_

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

- **`tipo_alerta`** → `COMBO_SIN_COMPONENTE` (325), `SIN_STOCK` (282)
- **`estado`** → `procesada` (471), `pendiente` (136)
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

## `bot_precios_log`  _(filas: 0)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `mla_id` | `varchar(20)` | YES |  |  |  |
| `titulo` | `varchar(255)` | YES |  |  |  |
| `listing_type` | `varchar(50)` | YES |  |  |  |
| `precio_anterior` | `int` | YES |  |  |  |
| `precio_nuevo` | `int` | YES |  |  |  |
| `ok` | `tinyint(1)` | YES |  | `1` |  |
| `usuario` | `varchar(50)` | YES |  | `bot_precios` |  |

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

- **`tipo`** → `colecta` (19)

---

## `cannon_descuentos`  _(filas: 20)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `clave` | `varchar(100)` | NO | UNI |  |  |
| `descripcion` | `varchar(255)` | NO |  |  |  |
| `valor` | `decimal(8,4)` | NO |  | `0.0000` |  |
| `desc_adicional` | `decimal(8,4)` | NO |  | `0.0000` |  |
| `tipo` | `enum('descuento_linea','descuento_adicional','prontopago','multiplicador')` | NO |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `descuento_linea` (18), `prontopago` (1), `multiplicador` (1)

---

## `cannon_facturas`  _(filas: 310)_

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

## `cannon_lista_precios`  _(filas: 175)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `codigo_material` | `bigint` | NO | UNI |  |  |
| `precio_lista` | `decimal(12,2)` | NO |  |  |  |
| `vigencia` | `date` | YES |  |  |  |
| `fecha_carga` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `cannon_lista_precios_hist`  _(filas: 175)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `codigo_material` | `bigint` | NO | MUL |  |  |
| `precio_lista` | `decimal(12,2)` | NO |  |  |  |
| `vigencia` | `date` | NO | MUL |  |  |
| `tipo` | `varchar(20)` | YES |  | `lista` |  |
| `fecha_carga` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `lista` (155), `almohadas` (20)

---

## `cannon_pagos`  _(filas: 93)_

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

## `cannon_productos`  _(filas: 199)_

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

## `cannon_reclamos`  _(filas: 15)_

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

---

## `competencia_cat_cache`  _(filas: 210)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `catalog_id` | `varchar(30)` | NO | PRI |  |  |
| `fecha` | `date` | YES |  |  |  |
| `data` | `mediumtext` | YES |  |  |  |

---

## `competencia_precios_hist`  _(filas: 19,896)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `date` | NO | MUL |  |  |
| `tienda` | `varchar(40)` | NO | MUL |  |  |
| `sku` | `varchar(40)` | NO |  |  |  |
| `bucket` | `varchar(8)` | NO |  |  |  |
| `precio` | `int` | NO |  |  |  |
| `n` | `int` | YES |  | `1` |  |

**Valores típicos (enums implícitos):**

- **`tienda`** → `TMS` (7,393), `Lanus` (6,101), `Ivana` (4,836), `Metymas` (864), `Ballester` (641), `Bedpoint` (41), `SanMartin` (20)
- **`bucket`** → `sin` (7,407), `6` (4,503), `9` (2,871), `3` (2,482), `12` (2,038), `simple` (595)

---

## `competencia_snapshots`  _(filas: 316,675)_

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
| `seller_id` | `bigint` | YES | MUL |  |  |
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

- **`tipo`** → `colchon` (210,771), `sommier` (105,904)
- **`modelo`** → `Princess` (49,623), `Exclusive` (48,760), `Exclusive Pillow` (44,689), `Doral` (36,779), `Soñar` (31,498), `Doral Pillow` (29,200), `Renovation` (22,439), `Renovation Euro Pillow` (20,106), `Sublime Pillow` (18,070), `Otro` (8,335), `Tropical` (7,176)
- **`cp`** → `1425` (316,675)
- **`cp_label`** → `CABA` (316,675)
- **`cuotas_publi`** → `Sin cuotas` (107,422), `6 cuotas s/interés` (70,804), `3 cuotas s/interés` (42,444), `9 cuotas s/interés` (41,249), `12 cuotas s/interés` (38,713), `Cuota Simple` (16,043)
- **`cuotas_efectivas`** → `Sin cuotas` (107,422), `6 cuotas s/interés` (70,804), `3 cuotas s/interés` (42,444), `9 cuotas s/interés` (41,249), `12 cuotas s/interés` (38,713), `Cuota Simple` (16,043)
- **`envio_tipo`** → `ME1` (163,041), `FLEX` (83,940), `ACORDAR` (46,291), `COLECTA` (12,735), `OTRO` (10,668)

---

## `competencia_sondas`  _(filas: 13)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `item_id_ml` | `varchar(20)` | NO | UNI |  |  |
| `tipo` | `enum('colchon','sommier','almohada')` | NO | MUL |  |  |
| `cuotas_reales` | `int` | NO |  |  |  |
| `sku_referencia` | `varchar(20)` | YES |  |  |  |
| `url` | `text` | NO |  |  |  |
| `activa` | `tinyint(1)` | YES |  | `1` |  |
| `fecha_alta` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |
| `cuotas_mostradas_ultimo` | `int` | YES |  |  |  |
| `fecha_ultimo_scrape` | `datetime` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (5), `sommier` (5), `almohada` (3)

---

## `componentes`  _(filas: 168)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `producto_compuesto_id` | `int` | NO | MUL |  |  |
| `producto_base_id` | `int` | NO | MUL |  |  |
| `cantidad_necesaria` | `int` | YES |  | `1` |  |

---

## `configuracion`  _(filas: 56)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `clave` | `varchar(100)` | NO | PRI |  |  |
| `valor` | `text` | YES |  |  |  |
| `actualizado_at` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `conjunto_configuracion`  _(filas: 63)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `colchon_sku` | `varchar(50)` | NO | UNI |  |  |
| `base_sku_default` | `varchar(50)` | NO | MUL |  |  |
| `cantidad_bases` | `tinyint` | YES |  | `1` |  |
| `activo` | `tinyint(1)` | YES |  | `1` |  |

---

## `cupones`  _(filas: 1,030)_

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

- **`tipo`** → `fijo` (1,027), `pct` (3)

---

## `cupones_uso`  _(filas: 73)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `cupon_id` | `int` | NO |  |  |  |
| `email` | `varchar(255)` | YES |  |  |  |
| `telefono` | `varchar(50)` | YES |  |  |  |
| `venta_numero` | `varchar(100)` | YES |  |  |  |
| `fecha_uso` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

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

---

## `fleteros`  _(filas: 7)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `nombre` | `varchar(100)` | NO | UNI |  |  |
| `activo` | `tinyint` | YES |  | `1` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `notas` | `text` | YES |  |  |  |

---

## `fletes_registros`  _(filas: 398)_

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

## `fraude_blocklist`  _(filas: 23)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `tipo` | `varchar(20)` | NO | MUL |  |  |
| `lista` | `varchar(10)` | NO |  | `block` |  |
| `valor` | `varchar(255)` | NO |  |  |  |
| `motivo` | `varchar(255)` | YES |  |  |  |
| `activo` | `tinyint(1)` | NO | MUL | `1` |  |
| `fecha_alta` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `direccion` (10), `dni` (9), `telefono` (3), `email` (1)
- **`lista`** → `block` (18), `allow` (5)
- **`motivo`** → `Ataque card-testing may-jun 2026 — drop cluster G1` (4), `Excepción manual` (4), `Ataque card-testing may-jun 2026 — drop cluster...` (3), `Ataque card-testing — Badeigts (Trujui), compar...` (1), `Ataque card-testing — cluster G2 (Granada/Ely, ...` (1), `Card-testing — Giometti (acreditada fraude + re...` (1), `Card-testing — Falciglia (autorizada fraude)` (1), `Card-testing — Mondolo (acreditada fraude + rec...` (1), `Card-testing — Perelroisen (2 acreditadas fraude)` (1), `Card-testing — Coderch (acreditada fraude)` (1), `Card-testing — Altieri (acreditada + rechazo RE...` (1), `Card-testing — Badeigts (multiples rechazos, dr...` (1), `Card-testing — cluster G2 (Granada / Ely, Asamb...` (1), `Card-testing — drop Libano 4263 (intento GetNet...` (1)

---

## `fraude_bloqueos`  _(filas: 47)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `datetime` | YES | MUL | `CURRENT_TIMESTAMP` |  |
| `motivo` | `varchar(30)` | YES |  |  |  |
| `dni` | `varchar(30)` | YES |  |  |  |
| `email` | `varchar(150)` | YES |  |  |  |
| `telefono` | `varchar(50)` | YES |  |  |  |
| `direccion` | `varchar(255)` | YES |  |  |  |
| `bin` | `varchar(10)` | YES |  |  |  |
| `last4` | `varchar(4)` | YES |  |  |  |
| `ref` | `varchar(40)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`motivo`** → `blocklist:direccion` (29), `velocidad_envio` (10), `velocidad_tarjeta` (8)
- **`dni`** → `23221868` (29), `22447593` (7), `37008225` (3), `41048647` (2), `42004392` (2), `40316362` (1), `30703138` (1), `24197596` (1), `30647683` (1)
- **`bin`** → `454832` (6), `493715` (2), `450815` (2), `416417` (1), `402918` (1), `423985` (1), `459354` (1), `454846` (1), `541646` (1), `433826` (1), `405071` (1)
- **`last4`** → `9639` (6), `2482` (2), `6850` (1), `3944` (1), `1143` (1), `0968` (1), `9789` (1), `5100` (1), `0876` (1), `3465` (1), `3380` (1), `6615` (1)
- **`ref`** → `88c38465714a46` (29), `34fb3807229c4d` (1), `0939e78d28f74c` (1), `e56e3e95a88f4a` (1), `203bf566435a48` (1), `cfae88dfa4ed42` (1), `f6fcbdc910a347` (1), `30ee2d54f01d40` (1), `d3e7f2c2a47446` (1), `a805bad43d1e45` (1), `595303d5def24e` (1), `1d159013566541` (1), `03dd85ffacc44e` (1), `b9245365e4204f` (1), `6daeb37708c644` (1), `e2b1ad318b3f46` (1), `83c77261323947` (1), `c9ab9c9a069141` (1), `b4609c94307b40` (1)

---

## `items_venta`  _(filas: 7,974)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `venta_id` | `int` | NO | MUL |  |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `cantidad` | `int` | NO |  |  |  |
| `precio_unitario` | `decimal(10,2)` | NO |  |  |  |

---

## `ml_preguntas`  _(filas: 1,086)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `question_id` | `bigint` | NO | PRI |  |  |
| `item_id` | `varchar(20)` | YES | MUL |  |  |
| `item_titulo` | `varchar(255)` | YES |  |  |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `precio` | `decimal(12,2)` | YES |  |  |  |
| `stock` | `int` | YES |  |  |  |
| `tipo_publi` | `varchar(20)` | YES |  |  |  |
| `cuotas` | `varchar(30)` | YES |  |  |  |
| `texto` | `text` | YES |  |  |  |
| `comprador_id` | `varchar(30)` | YES |  |  |  |
| `comprador_nick` | `varchar(255)` | YES |  |  |  |
| `fecha_pregunta` | `datetime` | YES |  |  |  |
| `status` | `varchar(20)` | YES | MUL | `UNANSWERED` |  |
| `respuesta_sugerida` | `text` | YES |  |  |  |
| `respuesta_final` | `text` | YES |  |  |  |
| `historial` | `text` | YES |  |  |  |
| `respondida_at` | `datetime` | YES |  |  |  |
| `synced_at` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`tipo_publi`** → `Catálogo` (737), `Listado general` (348)
- **`cuotas`** → `Sin cuotas propias` (760), `6 cuotas s/interés` (126), `12 cuotas s/interés` (88), `9 cuotas s/interés` (58), `3 cuotas s/interés` (51), `Cuota Simple` (2)
- **`status`** → `ANSWERED` (1,086)

---

## `ml_reclamos`  _(filas: 195)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `claim_id` | `bigint` | NO | PRI |  |  |
| `order_id` | `varchar(40)` | YES |  |  |  |
| `pack_id` | `varchar(40)` | YES |  |  |  |
| `resource` | `varchar(30)` | YES |  |  |  |
| `resource_id` | `varchar(40)` | YES |  |  |  |
| `stage` | `varchar(20)` | YES |  |  |  |
| `status` | `varchar(30)` | YES |  |  |  |
| `tipo` | `varchar(40)` | YES |  |  |  |
| `reason_id` | `varchar(40)` | YES |  |  |  |
| `reason_prefix` | `varchar(10)` | YES |  |  |  |
| `affects_reputation` | `varchar(30)` | YES |  |  |  |
| `has_incentive` | `tinyint(1)` | YES |  | `0` |  |
| `due_date` | `datetime` | YES |  |  |  |
| `action_responsible` | `varchar(20)` | YES |  |  |  |
| `title` | `varchar(255)` | YES |  |  |  |
| `description` | `text` | YES |  |  |  |
| `problem` | `text` | YES |  |  |  |
| `date_created` | `datetime` | YES |  |  |  |
| `last_updated` | `datetime` | YES |  |  |  |
| `nota_interna` | `text` | YES |  |  |  |
| `visto` | `tinyint(1)` | YES |  | `0` |  |
| `synced_at` | `datetime` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`resource`** → `order` (132), `shipment` (63)
- **`stage`** → `claim` (115), `dispute` (44), `none` (34), `recontact` (2)
- **`status`** → `closed` (194), `opened` (1)
- **`tipo`** → `mediations` (159), `cancel_purchase` (34), `returns` (2)
- **`reason_prefix`** → `PNR` (121), `PDD` (74)
- **`affects_reputation`** → `not_affected` (176), `affected` (19)
- **`action_responsible`** → `respondent` (1)
- **`title`** → `Reclamo cerrado con reembolso al comprador` (65), `` (53), `Venta entregada` (22), `Mediación finalizada. Te dimos el dinero.` (14), `Mediación finalizada con reembolso al comprador` (12), `Reclamo cerrado` (10), `Devolución en camino` (10), `Devolución finalizada con reembolso al comprador` (3), `Devolución finalizada. Te dimos el dinero.` (2), `Devolución en camino. Revisaremos el producto` (1), `Reclamo cerrado con reembolso parcial` (1), `Reclamo abierto para resolver hasta el martes 6...` (1), `Mediación con Mercado Libre` (1)

---

## `mla_catalogo`  _(filas: 1,507)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `mla_id` | `varchar(20)` | NO | PRI |  |  |
| `catalog_product_id` | `varchar(30)` | YES | MUL |  |  |
| `status` | `varchar(20)` | YES |  |  |  |
| `actualizado_at` | `timestamp` | YES | MUL | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`status`** → `active` (1,214), `paused` (278), `under_review` (14), `unknown` (1)

---

## `mla_excluidos`  _(filas: 15)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `mla_id` | `varchar(20)` | NO | PRI |  |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `titulo` | `varchar(255)` | YES |  |  |  |
| `motivo` | `varchar(100)` | YES |  |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`motivo`** → `no agregar - decision usuario` (15)

---

## `movimientos_stock`  _(filas: 9,100)_

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

- **`tipo_movimiento`** → `venta` (7,192), `carga` (1,807), `baja` (96), `ajuste` (5)
- **`usuario`** → `Sistema` (9,100)

---

## `ofertas_home`  _(filas: 25)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `descuento_pct` | `decimal(5,2)` | YES |  | `8.00` |  |
| `orden` | `int` | YES |  | `0` |  |
| `activo` | `tinyint` | YES |  | `1` |  |

---

## `payway_intentos`  _(filas: 220)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `payment_id` | `bigint` | NO | PRI |  |  |
| `site_transaction_id` | `varchar(40)` | YES |  |  |  |
| `ref` | `varchar(40)` | YES | MUL |  |  |
| `fecha` | `datetime` | YES | MUL |  |  |
| `amount` | `decimal(14,2)` | YES |  |  |  |
| `installments` | `int` | YES |  |  |  |
| `status` | `varchar(20)` | YES | MUL |  |  |
| `status_es` | `varchar(20)` | YES |  |  |  |
| `motivo` | `varchar(120)` | YES |  |  |  |
| `motivo_id` | `int` | YES |  |  |  |
| `card_brand` | `varchar(30)` | YES |  |  |  |
| `bin` | `varchar(10)` | YES |  |  |  |
| `last4` | `varchar(4)` | YES |  |  |  |
| `tid` | `varchar(40)` | YES |  |  |  |
| `payment_method_id` | `int` | YES |  |  |  |
| `raw_json` | `json` | YES |  |  |  |
| `fecha_sync` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

**Valores típicos (enums implícitos):**

- **`status`** → `rejected` (161), `accredited` (43), `annulment_approved` (10), `refund_approved` (4), `approved` (2)
- **`status_es`** → `Rechazada` (161), `Acreditada` (45), `annulment_approved` (10), `refund_approved` (4)
- **`motivo`** → `DENEGADA` (113), `` (67), `CUENTA INEXISTENTE` (13), `SERVICIO INVALIDO` (6), `RETENER TARJETA` (5), `FONDOS INSUFICIENTES` (5), `TRANSAC. INVALIDA` (4), `TARJETA INVALIDA` (2), `Terminal no disponible` (2), `TRANS. NO PERMITIDA` (2), `EMISOR FUERA LINEA` (1)
- **`card_brand`** → `Visa` (184), `MasterCard Payway` (36)

---

## `pedidos_pendientes`  _(filas: 1,430)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `ref` | `varchar(32)` | NO | PRI |  |  |
| `carrito_json` | `text` | NO |  |  |  |
| `cliente_json` | `text` | NO |  |  |  |
| `fecha_creacion` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `pedidos_pendientes_getnet`  _(filas: 282)_

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

- **`metodo_envio`** → `Flete Propio` (160), `` (83), `Zippin` (39)
- **`estado`** → `pendiente` (251), `procesado` (31)

---

## `preguntas_ejemplos`  _(filas: 985)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `pregunta` | `text` | YES |  |  |  |
| `respuesta` | `text` | YES |  |  |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `fecha` | `datetime` | YES | MUL | `CURRENT_TIMESTAMP` |  |

---

## `productos_base`  _(filas: 130)_

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

- **`tipo`** → `colchon` (82), `base` (26), `almohada` (11), `servicio` (11)
- **`linea`** → `espuma` (45), `resortes` (22), `box` (8), `` (1)
- **`modelo`** → `Exclusive` (8), `Exclusive Pillow` (8), `Renovation` (8), `Renovation Europillow` (8), `Doral` (8), `Doral Pillow` (5), `Sublime Europillow` (5), `Princess 20cm` (4), `Princess 23cm` (4), `Compac` (4), `Compac Plus Pocket` (4), `Soñar` (4), `Tropical` (3), `Prueba` (1), `` (1), `Exclusive Europillow` (1)

---

## `productos_compuestos`  _(filas: 82)_

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

## `productos_fotos`  _(filas: 596)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | NO | MUL |  |  |
| `filename` | `varchar(255)` | NO |  |  |  |
| `orden` | `int` | YES |  | `0` |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `promos_ml_historial`  _(filas: 1,453)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `datetime` | YES | MUL | `CURRENT_TIMESTAMP` |  |
| `accion` | `varchar(20)` | NO |  |  |  |
| `origen` | `varchar(30)` | YES |  | `panel` |  |
| `mla_id` | `varchar(20)` | NO | MUL |  |  |
| `sku` | `varchar(50)` | YES |  |  |  |
| `campania_id` | `varchar(40)` | YES | MUL |  |  |
| `campania_nombre` | `varchar(120)` | YES |  |  |  |
| `tipo` | `varchar(30)` | YES |  |  |  |
| `mostrado_pct` | `decimal(7,3)` | YES |  |  |  |
| `mostrado_precio` | `int` | YES |  |  |  |
| `mostrado_original` | `int` | YES |  |  |  |
| `aplicado_pct` | `decimal(7,3)` | YES |  |  |  |
| `aplicado_meli_pct` | `decimal(7,3)` | YES |  |  |  |
| `aplicado_precio` | `int` | YES |  |  |  |
| `aplicado_original` | `int` | YES |  |  |  |
| `coincide` | `tinyint(1)` | YES | MUL |  |  |
| `delta_pct` | `decimal(7,3)` | YES |  |  |  |
| `supero_limite` | `tinyint(1)` | YES | MUL | `0` |  |
| `revertida` | `tinyint(1)` | YES |  | `0` |  |
| `ok` | `tinyint(1)` | YES |  | `1` |  |
| `error` | `varchar(255)` | YES |  |  |  |
| `usuario` | `varchar(100)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`accion`** → `aplicar` (1,359), `rechequeo` (94)
- **`origen`** → `lote` (1,352), `job` (94), `individual` (6), `manual` (1)
- **`tipo`** → `SMART` (1,169), `PRE_NEGOTIATED` (274), `LIGHTNING` (8), `PRICE_MATCHING` (2)

---

## `push_subscriptions`  _(filas: 2)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `endpoint` | `text` | NO |  |  |  |
| `endpoint_hash` | `char(64)` | NO | UNI |  |  |
| `p256dh` | `varchar(255)` | NO |  |  |  |
| `auth` | `varchar(255)` | NO |  |  |  |
| `ua` | `varchar(255)` | YES |  |  |  |
| `created_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |

---

## `sistema_logs`  _(filas: 4,146)_

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

- **`nivel`** → `INFO` (4,136), `WARNING` (10)
- **`modulo`** → `entrega` (3,352), `webhook` (302), `venta` (256), `clearsale` (190), `stock` (46)
- **`accion`** → `venta_entregada` (3,352), `nueva_venta` (256), `nueva_venta_mp` (226), `webhook_test` (131), `cambio_estado` (47), `baja_stock` (46), `nueva_venta_payway` (45), `nueva_venta_getnet` (31), `venta_cancelada` (9), `venta_reactivada` (2), `despacho_bloqueado` (1)
- **`usuario`** → `romi` (2,902), `manu` (713), `mercadomuebles` (40)
- **`ip`** → `127.0.0.1` (256)

---

## `sku_catalog_map`  _(filas: 131)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `sku` | `varchar(50)` | YES | UNI |  |  |
| `catalog_product_id` | `varchar(30)` | YES |  |  |  |
| `category_id` | `varchar(60)` | YES |  |  |  |
| `mla_ref` | `varchar(20)` | YES |  |  |  |
| `actualizado_at` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `manual` | `tinyint` | YES |  | `0` |  |

---

## `sku_mla_mapeo`  _(filas: 1,590)_

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

## `stock_comprometido_ventas`  _(filas: 55)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `sku` | `varchar(50)` | NO |  |  |  |
| `cantidad` | `decimal(32,0)` | YES |  |  |  |

---

## `stock_compuestos`  _(filas: 82)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `producto_compuesto_id` | `int` | NO |  | `0` |  |
| `sku` | `varchar(50)` | NO |  |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `precio_base` | `decimal(10,2)` | YES |  |  |  |
| `stock_disponible` | `bigint` | YES |  |  |  |
| `componentes_detalle` | `text` | YES |  |  |  |

---

## `stock_disponible_ml`  _(filas: 212)_

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

- **`tipo`** → `colchon` (85), `sommier` (73), `base` (26), `almohada` (17), `servicio` (11)
- **`tipo_producto`** → `BASE` (130), `COMPUESTO` (82)
- **`modelo`** → `Exclusive` (8), `Exclusive Pillow` (8), `Renovation` (8), `Renovation Europillow` (8), `Doral` (8), `Doral Pillow` (5), `Sublime Europillow` (5), `Princess 20cm` (4), `Princess 23cm` (4), `Compac` (4), `Compac Plus Pocket` (4), `Soñar` (4), `Tropical` (3), `Prueba` (1), `` (1), `Exclusive Europillow` (1)
- **`estado_stock`** → `DISPONIBLE` (161), `SIN_STOCK` (51)

---

## `stock_disponible_real`  _(filas: 130)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `sku` | `varchar(50)` | NO |  |  |  |
| `nombre` | `varchar(255)` | NO |  |  |  |
| `tipo` | `varchar(50)` | NO |  |  |  |
| `stock_fisico` | `int` | YES |  | `0` |  |
| `cantidad_vendida` | `decimal(32,0)` | NO |  | `0` |  |
| `stock_disponible` | `decimal(33,0)` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`tipo`** → `colchon` (82), `base` (26), `almohada` (11), `servicio` (11)

---

## `suscriptores`  _(filas: 977)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `email` | `varchar(255)` | NO | UNI |  |  |
| `cupon_id` | `int` | YES |  |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `ip` | `varchar(45)` | YES |  |  |  |

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

- **`rol`** → `admin` (1), `vendedor` (1), `viewer` (1), `agencia` (1)

---

## `ventas`  _(filas: 7,369)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `numero_venta` | `varchar(100)` | NO | UNI |  |  |
| `mla_code` | `varchar(50)` | YES |  |  |  |
| `canal` | `varchar(50)` | NO |  |  |  |
| `nombre_cliente` | `varchar(255)` | NO |  |  |  |
| `telefono_cliente` | `varchar(50)` | NO |  |  |  |
| `email_cliente` | `varchar(255)` | YES |  |  |  |
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
| `clearsale_estado` | `varchar(3)` | YES | MUL |  |  |
| `clearsale_order_id` | `varchar(60)` | YES |  |  |  |
| `clearsale_score` | `varchar(20)` | YES |  |  |  |
| `clearsale_actualizado` | `datetime` | YES |  |  |  |
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
| `ml_entregado_at` | `datetime` | YES |  |  |  |
| `origen_first` | `text` | YES |  |  |  |
| `origen_last` | `text` | YES |  |  |  |

**Valores típicos (enums implícitos):**

- **`canal`** → `Mercado Libre` (6,852), `tienda_web` (337), `Fuera de ML` (180)
- **`metodo_pago`** → `MercadoPago` (7,097), `Efectivo` (140), `Payway` (47), `GetNet` (31), `Tarjeta` (23), `Transferencia` (17), `Mixto` (14)
- **`tipo_entrega`** → `Envío` (7,013), `Retiro` (356)
- **`metodo_envio`** → `Colecta` (1,892), `Flex` (1,785), `Delega` (1,686), `Flete Propio` (948), `` (258), `Zippin` (255), `Full` (227), `Turbo` (153), `Mercadoenvios` (61), `ME2` (4)
- **`ubicacion_despacho`** → `DEP` (7,142), `FULL` (227)
- **`zona_envio`** → `` (6,321), `Capital` (338), `Sur` (213), `Oeste` (195), `Norte-Noroeste` (189)
- **`responsable_entrega`** → `` (2,043)
- **`estado_pago`** → `pagado` (7,314), `pago_pendiente` (48), `pago_parcial` (6), `pendiente` (1)
- **`clearsale_estado`** → `APA` (8), `APM` (4), `ERR` (3), `SUS` (1)
- **`estado_entrega`** → `entregada` (6,947), `cancelada` (316), `pendiente` (81), `en_proceso` (25)
- **`estado`** → `ACTIVA` (7,368), `CANCELADA` (1)
- **`factura_doc_type`** → `DNI` (6,304), `CUIT` (546)
- **`factura_taxpayer_type`** → `Consumidor Final` (6,508), `Responsable Inscripto` (270), `IVA Responsable Inscripto` (72), `Responsable Monotributo` (27), `Exento` (6), `IVA Exento` (2), `Sujeto No Categorizado` (2), `Monotributo` (1), `IVA No Alcanzado` (1)

---

## `ventas_activas`  _(filas: 81)_

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

- **`canal`** → `Mercado Libre` (62), `tienda_web` (17), `Fuera de ML` (2)
- **`metodo_pago`** → `Mercadopago` (73), `Payway` (6), `Efectivo` (1), `Tarjeta` (1)
- **`tipo_entrega`** → `envio` (75), `retiro` (6)
- **`metodo_envio`** → `Flete Propio` (30), `Flex` (16), `Full` (13), `Delega` (6), `Colecta` (5), `Zippin` (5), `` (2)
- **`zona_envio`** → `` (48), `Capital` (14), `Oeste` (6), `Sur` (3), `Norte-Noroeste` (3)
- **`responsable_entrega`** → `` (25)
- **`estado_pago`** → `pagado` (81)
- **`estado_entrega`** → `pendiente` (81)

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

## `wa_mensajes`  _(filas: 9,975)_

| Columna | Tipo | Null | Key | Default | Comentario |
|---|---|---|---|---|---|
| `id` | `int` | NO | PRI |  |  |
| `fecha` | `timestamp` | YES |  | `CURRENT_TIMESTAMP` |  |
| `phone` | `varchar(30)` | YES | MUL |  |  |
| `rol` | `enum('user','assistant')` | YES |  |  |  |
| `contenido` | `text` | YES |  |  |  |
| `derivado` | `tinyint(1)` | YES |  | `0` |  |

**Valores típicos (enums implícitos):**

- **`rol`** → `user` (4,988), `assistant` (4,987)

---
