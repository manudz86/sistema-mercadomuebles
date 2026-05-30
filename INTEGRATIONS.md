# INTEGRATIONS.md — Integraciones externas (Sistema Cannon)

Referencia operativa de las integraciones con servicios externos. Una sección por
integración. Se documentan **ubicaciones en el código** (archivo + función + nº de
línea aproximado) y **cómo operar**, nunca valores de credenciales/tokens (esos
viven solo en la DB y en `config/`, fuera del repo).

> Las líneas son aproximadas: `app.py` es un monolito grande y se edita seguido.
> Ante la duda, buscar por el nombre de la función.

---

## Mercado Libre

Integración con la API de Mercado Libre (`https://api.mercadolibre.com`) para
publicaciones, órdenes, envíos y facturación. Todo el código vive en `app.py`.

### Token — dónde vive

- **Fuente de verdad (en vivo): tabla `configuracion`, key `ml_token`.** Es un JSON
  que contiene `access_token`, `refresh_token`, `client_id`, `client_secret` y
  `expires_at`. (Valores **no** documentados acá; mirar la DB.)
- **Leer el token en código:** `cargar_ml_token()` (`app.py:6782`). Lee la key
  `ml_token` de la DB y, si está vencido (`expires_at` pasado), lo renueva solo.
- **Guardar el token:** `guardar_ml_token()` (`app.py:6800`) — preserva
  `refresh_token`/`client_id`/`client_secret` existentes si el nuevo payload no los trae.
- **`config/ml_token.json` NO es la fuente de verdad.** Se lee en un único lugar
  (`app.py:7719`, ruta de configuración de token) y **solo** para mostrar en la UI si
  hay `refresh_token` y cuántas horas quedan. No alimenta las requests en vivo.
  (Archivo fuera del repo: está en `.gitignore`.)

### Refresh — cómo y cada cuánto

- **`refresh_ml_token()`** (`app.py:6736`): `POST https://api.mercadolibre.com/oauth/token`
  con `grant_type=refresh_token` (usa `client_id`/`client_secret`/`refresh_token` del
  JSON en DB). Persiste el nuevo `access_token`/`refresh_token` y recalcula `expires_at`
  (= ahora + `expires_in` − 300s de margen).
- **No hay scheduler/cron/thread** que lo refresque proactivamente. Es **lazy /
  on-demand**: se renueva en el primer uso después de vencido, vía `cargar_ml_token()`.
- El `access_token` de ML dura ~6 horas.

### Cómo hacer una consulta a ML (receta)

1. Obtener el token: `token = cargar_ml_token()` (devuelve `None` si no hay token /
   no se pudo renovar — chequear).
2. Hacer la request con el **helper canónico**:
   **`ml_request(method, url, access_token, json_data=None, params=None, max_retries=4)`**
   (`app.py:8645`). Ejemplo: `ml_request('get', 'https://api.mercadolibre.com/items/<MLA>', token)`.
3. `ml_request` aporta:
   - **Rate limiting global** (lock + intervalo mínimo entre requests, `app.py:22-24`),
     ~1.4 req/s.
   - **Retry exponencial ante HTTP 429** (esperas crecientes con tope) y retry ante
     excepción de red.
   - `timeout` por request.
- **URL base:** `https://api.mercadolibre.com`.
- **Seller ID:** constante `ML_SELLER_ID` (`app.py:26`) — usar la constante, no el número.

> ⚠️ **Gotcha — llamadas legacy directas.** El docstring de `ml_request` dice "toda
> llamada a ML debe pasar por acá", pero en la práctica hay **muchas** llamadas con
> `requests.get/post` directos (p. ej. `orders`, `shipments`, `billing_info`,
> `users/me`) que **no** pasan por `ml_request` → no tienen rate-limit ni retry. Para
> código nuevo, usar siempre `ml_request`.

### Gotchas de dominio

- **Normalización de SKU — `normalizar_sku_ml(sku)`** (`app.py:6879`): devuelve
  `(sku_normalizado, cantidad_override)`.
  - Quita la `Z` final: `CEX140Z → CEX140`.
  - Mapeos fijos: `RENOVATIONAL → RENOVATION`; `CLASICAX2 → (CLASICA, 2)` (el
    `cantidad_override` indica cuántas unidades representa un SKU de ML).
- **Lógica "Z" (publicaciones / demora)** (`app.py:1060-1118`):
  - Publicaciones **CON `Z` = ME1** (envío propio): cuando se quedan sin stock, se
    **mantienen activas** con un stock mínimo y días de demora.
  - Publicaciones **SIN `Z` = Flex (ME2 / self_service):** se **pausan** con stock 0.
  - Helper: `_get_ml_z_sin_stock_config()` (`app.py:1066`). Config en `configuracion`:
    `ml_z_sin_stock_unidades` y `ml_z_sin_stock_dias_demora` (con defaults y rangos de
    validación en el código).
  - El join SKU↔MLA contempla la Z: `WHERE (m.sku = a.sku OR m.sku = CONCAT(a.sku,'Z'))`.
- **Keys de `configuracion` que intervienen en ML:** `ml_token`, `ml_progress`,
  `ml_z_sin_stock_unidades`, `ml_z_sin_stock_dias_demora`, `porcentajes_ml`.
  (Detalle de lectura/escritura de cada una en `CONFIG_MAP.md`.)

---

## Mercado Pago

_(pendiente de documentar)_

---

## Payway

_(pendiente de documentar)_

---

## GetNet

_(pendiente de documentar)_

---

## Zipnova

_(pendiente de documentar)_

---

## WhatsApp

_(pendiente de documentar)_
