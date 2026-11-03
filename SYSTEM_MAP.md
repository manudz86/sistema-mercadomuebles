# 📘 SYSTEM_MAP — Mapa del Sistema Cannon

Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**

---

## 🌐 Rutas HTTP — 233 endpoints

### `app.py`

#### `GET /` 🔒
- **Función:** `index()` (línea 801)
- **Descripción:** Dashboard principal — métricas operativas del día
- **Templates:** `dashboard.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /activar-mla` 🔒
- **Función:** `activar_mla()` (línea 12167)
- **Descripción:** Reactivar una publicación pausada manualmente (PUT status=active a ML).
- **Templates:** `cargar_stock_ml.html`

#### `POST /activar-pausadas-masivo` 🔒
- **Función:** `activar_pausadas_masivo()` (línea 12243)
- **Descripción:** Reactivar todas las publicaciones pausadas manualmente (status=paused + stock>0).
- **Templates:** `cargar_stock_ml.html`, `cargar_stock_ml.html`

#### `GET /admin/logs` 🔒
- **Función:** `admin_logs()` (línea 19339)
- **Templates:** `admin_logs.html`

#### `GET /agencia` 🔒
- **Función:** `agencia_dashboard()` (línea 17583)
- **Templates:** `agencia.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /alertas` 🔒
- **Función:** `alertas_ml()` (línea 4495)
- **Descripción:** Ver alertas de stock pendientes con info de publicaciones ML (normales y con Z)
- **Templates:** `alertas.html`

#### `POST /alertas/<int:alerta_id>/configurar-demora-ml` 🔒
- **Función:** `configurar_demora_ml_desde_alerta()` (línea 8242)
- **Descripción:** Configurar días de demora en las publicaciones CON Z

#### `POST /alertas/<int:alerta_id>/procesar` 🔒
- **Función:** `marcar_alerta_procesada()` (línea 4537)
- **Descripción:** Marcar una alerta como procesada

#### `POST /alertas/<int:alerta_id>/sincronizar-ml` 🔒
- **Función:** `sincronizar_ml_desde_alerta()` (línea 4401)
- **Descripción:** Poner stock en 0 en las publicaciones NORMALES (sin Z)

#### `POST /alertas/marcar-todas-procesadas` 🔒
- **Función:** `marcar_todas_procesadas()` (línea 4553)
- **Descripción:** Marcar TODAS las alertas pendientes como procesadas

#### `GET /api/productos` 🔒
- **Función:** `api_productos()` (línea 5839)
- **Descripción:** API para el buscador de productos en templates
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /auditoria-ml` 🔒
- **Función:** `auditoria_ml()` (línea 12943)
- **Descripción:** Renderiza la página de auditoría. Los datos se cargan vía AJAX por sección.
- **Templates:** `auditoria_ml.html`

#### `POST /auditoria-ml/activar` 🔒
- **Función:** `auditoria_activar_publicaciones()` (línea 13083)
- **Descripción:** Activar (despausar) publicaciones seleccionadas. Devuelve JSON.

#### `POST /auditoria-ml/bajar-cero` 🔒
- **Función:** `auditoria_bajar_cero()` (línea 13187)
- **Descripción:** Bajar stock a 0 en publicaciones seleccionadas. Para sección stock_en_ml.

#### `POST /auditoria-ml/cargar-stock` 🔒
- **Función:** `auditoria_cargar_stock()` (línea 13119)
- **Descripción:** Cargar stock en publicaciones seleccionadas. Devuelve JSON.

#### `POST /auditoria-ml/poner-demora` 🔒
- **Función:** `auditoria_poner_demora()` (línea 13217)
- **Descripción:** Poner X días de demora en publicaciones Z seleccionadas. Para sección stock_en_ml.

#### `POST /auditoria-ml/reducir-demora` 🔒
- **Función:** `auditoria_reducir_demora()` (línea 13157)
- **Descripción:** Quitar demora completamente en publicaciones seleccionadas. Devuelve JSON.

#### `GET /auditoria-ml/run/<tipo>` 🔒
- **Función:** `auditoria_ml_run()` (línea 12956)
- **Descripción:** Ejecuta un tipo específico de auditoría y devuelve JSON con los resultados.

#### `GET /bajar-stock` 🔒
- **Función:** `bajar_stock()` (línea 6218)
- **Descripción:** Formulario para dar de baja stock
- **Templates:** `bajar_stock.html`
- **Tablas:** `productos_base`

#### `POST /bajar-stock-cero-masivo` 🔒
- **Función:** `bajar_stock_cero_masivo()` (línea 12201)
- **Descripción:** Poner stock en 0 en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /bajar-stock-mla-cero` 🔒
- **Función:** `bajar_stock_mla_cero()` (línea 12134)
- **Descripción:** Poner stock en 0 en una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /bajar-stock/guardar` 🔒
- **Función:** `bajar_stock_guardar()` (línea 6243)
- **Descripción:** Guardar bajas de stock - acepta form o JSON
- **Tablas:** `productos_base`

#### `GET, POST /buscar-sku-ml` 🔒
- **Función:** `buscar_sku_ml()` (línea 10908)
- **Templates:** `cargar_stock_ml.html`, `cargar_stock_ml.html`, `cargar_stock_ml.html`
- **Tablas:** `configuracion`

#### `POST /cambiar-precio-masivo` 🔒
- **Función:** `cambiar_precio_masivo()` (línea 11884)
- **Descripción:** Cambiar el precio de todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /cambiar-precio-mla` 🔒
- **Función:** `cambiar_precio_mla()` (línea 11832)
- **Descripción:** Cambiar el precio de una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /cambiar-precios-individuales` 🔒
- **Función:** `cambiar_precios_individuales()` (línea 11944)
- **Descripción:** Actualizar precios individuales de múltiples MLAs de una vez
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-demora-masivo` 🔒
- **Función:** `cargar_demora_masivo()` (línea 12341)
- **Descripción:** Poner X días de MANUFACTURING_TIME en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-demora-mla` 🔒
- **Función:** `cargar_demora_mla()` (línea 12301)
- **Descripción:** Poner X días de MANUFACTURING_TIME en una publicación
- **Templates:** `cargar_stock_ml.html`

#### `GET, POST /cargar-stock` 🔒
- **Función:** `cargar_stock()` (línea 5871)
- **Descripción:** Formulario para cargar/agregar stock de productos
- **Templates:** `cargar_stock.html`
- **Tablas:** `productos_base`

#### `POST /cargar-stock-masivo` 🔒
- **Función:** `cargar_stock_masivo()` (línea 12766)
- **Descripción:** Cargar el mismo stock en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `GET /cargar-stock-ml` 🔒
- **Función:** `cargar_stock_ml()` (línea 9332)
- **Descripción:** Mostrar página para cargar stock en ML
- **Templates:** `cargar_stock_ml.html`
- **Tablas:** `configuracion`

#### `POST /cargar-stock-mla` 🔒
- **Función:** `cargar_stock_mla()` (línea 12679)
- **Descripción:** Cargar stock en una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-stock/escanear-remito` 🔒
- **Función:** `escanear_remito()` (línea 5966)
- **Descripción:** Escanea imágenes de remito con IA (Claude vision) y extrae productos/cantidades.
- **Tablas:** `productos_base`

#### `POST /cargar-stock/guardar` 🔒
- **Función:** `guardar_stock()` (línea 6143)
- **Descripción:** Agregar stock (SUMA al stock actual) y registrar movimientos
- **Tablas:** `productos_base`

#### `POST /cargar-stock/registrar-mapeo-remito` 🔒
- **Función:** `registrar_mapeo_remito()` (línea 6118)
- **Descripción:** Guarda el mapeo codigo_material → SKU en cannon_productos para futuros escaneos.
- **Tablas:** `productos_base`

#### `GET /configuracion/ml-z-sin-stock` 🔒
- **Función:** `get_ml_z_sin_stock()` (línea 1158)
- **Descripción:** Retorna stock y días de demora a aplicar en publicaciones Z sin stock.

#### `POST /configuracion/ml-z-sin-stock` 🔓
- **Función:** `guardar_ml_z_sin_stock()` (línea 1168)
- **Descripción:** Guarda stock y días de demora para publicaciones Z sin stock.
- **Tablas:** `configuracion`

#### `GET /configuracion/porcentajes-ml` 🔒
- **Función:** `get_porcentajes_ml()` (línea 1102)
- **Descripción:** Retorna los porcentajes de ML guardados en DB
- **Tablas:** `configuracion`

#### `POST /configuracion/porcentajes-ml` 🔒
- **Función:** `guardar_porcentajes_ml()` (línea 1114)
- **Descripción:** Guarda los porcentajes de ML en DB
- **Tablas:** `configuracion`

#### `GET /configuracion/resetear` 🔒
- **Función:** `resetear_sistema()` (línea 7324)
- **Descripción:** Página para resetear el sistema (requiere contraseña)
- **Templates:** `resetear_sistema.html`

#### `POST /configuracion/resetear/ejecutar` 🔒
- **Función:** `ejecutar_reseteo()` (línea 7331)
- **Descripción:** Ejecutar reseteo completo del sistema
- **Tablas:** `items_venta`, `productos_base`, `ventas`

#### `GET /costos` 🔓
- **Función:** `costos_index()` (línea 20051)
- **Descripción:** Calculadora de precios — vista principal.
- **Templates:** `costos.html`
- **Tablas:** `configuracion`

#### `POST /costos/aplicar` 🔓
- **Función:** `costos_aplicar()` (línea 21207)
- **Descripción:** Aplica precios calculados a productos_base.
- **Tablas:** `productos_base`

#### `GET /costos/calcular` 🔓
- **Función:** `costos_calcular()` (línea 20822)
- **Descripción:** Tabla de precios calculados con opción de aplicar a productos_base.
- **Templates:** `costos_calcular.html`
- **Tablas:** `configuracion`, `conjunto_configuracion`, `productos_base`

#### `GET, POST /costos/descuentos` 🔓
- **Función:** `costos_descuentos()` (línea 20547)
- **Descripción:** Configurar descuentos por modelo, prontopago y multiplicador.
- **Templates:** `costos_descuentos.html`
- **Tablas:** `configuracion`

#### `GET, POST /costos/envio` 🔓
- **Función:** `costos_envio()` (línea 20724)
- **Descripción:** Gestionar costos de envío colecta/flex por SKU.
- **Templates:** `costos_envio.html`
- **Tablas:** `productos_base`

#### `GET /costos/envio/barrido-ml` 🔓
- **Función:** `costos_envio_barrido_ml()` (línea 20761)
- **Descripción:** Consulta costos de colecta ML para los SKUs de barrido y compara con lo guardado.

#### `GET, POST /costos/importar` 🔓
- **Función:** `costos_importar()` (línea 20605)
- **Descripción:** Subir Excel de lista de precios Cannon.
- **Templates:** `costos_importar.html`

#### `GET /costos/lista-costos.pdf` 🔓
- **Función:** `costos_lista_costos_pdf()` (línea 20537)
- **Descripción:** Lista de COSTOS interna.

#### `GET /costos/lista-precios.pdf` 🔒
- **Función:** `costos_lista_precios_pdf()` (línea 20527)
- **Descripción:** Lista de PRECIOS de venta para mostrador.

#### `GET, POST /costos/productos` 🔓
- **Función:** `costos_productos()` (línea 20686)
- **Descripción:** Ver/editar SKU de productos Cannon y descuentos adicionales.
- **Templates:** `costos_productos.html`

#### `GET /cotizador-envio` 🔒
- **Función:** `cotizador_envio()` (línea 22038)
- **Descripción:** Página del cotizador de envíos Zipnova.
- **Templates:** `cotizador_envio.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /cotizador-envio/cotizar` 🔒
- **Función:** `cotizador_cotizar()` (línea 22064)
- **Descripción:** AJAX: cotiza envío Zipnova para los SKUs indicados.

#### `GET /cotizador-envio/localidades` 🔒
- **Función:** `cotizador_localidades()` (línea 22054)
- **Descripción:** Devuelve localidades para un CP dado.

#### `GET /dashboard-visual` 🔒
- **Función:** `dashboard_visual()` (línea 7133)
- **Descripción:** Dashboard visual - Stock Físico y Ventas Activas con lógica de bases grandes
- **Templates:** `dashboard_visual.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /debug-mla` 🔒
- **Función:** `debug_mla()` (línea 13873)

#### `GET /debug-token-temp` 🔒
- **Función:** `debug_token_temp()` (línea 11606)

#### `GET /debug/ml/<orden_id>` 🔒
- **Función:** `debug_ml_orden()` (línea 9180)
- **Descripción:** Ver qué datos trae ML de una orden

#### `GET /estadisticas` 🔒
- **Función:** `estadisticas()` (línea 13257)
- **Templates:** `estadisticas.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /estadisticas/exportar-reposicion` 🔒
- **Función:** `exportar_reposicion()` (línea 13481)
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /faltantes-catalogo-ml` 🔒
- **Función:** `faltantes_catalogo_ml()` (línea 11411)
- **Descripción:** Sirve siempre desde caché. El cómputo pesado corre en background.
- **Templates:** `faltantes_catalogo_ml.html`, `faltantes_catalogo_ml.html`
- **Tablas:** `configuracion`

#### `POST /faltantes-catalogo-ml/refresh` 🔒
- **Función:** `faltantes_catalogo_refresh()` (línea 11433)
- **Descripción:** Dispara el job en background y vuelve al instante.

#### `GET /fletes` 🔒
- **Función:** `fletes()` (línea 14499)
- **Templates:** `fletes.html`

#### `POST /fletes/guardar` 🔒
- **Función:** `fletes_guardar()` (línea 14546)

#### `GET /historial-stock` 🔒
- **Función:** `historial_stock()` (línea 6310)
- **Descripción:** Ver historial de movimientos de stock
- **Templates:** `historial_stock.html`

#### `GET /intentos-pago` 🔒
- **Función:** `intentos_pago()` (línea 18808)
- **Descripción:** Timeline de intentos de pago Payway (acreditados + rechazados + anulados),
- **Templates:** `intentos_pago.html`
- **Tablas:** `pedidos_pendientes`, `ventas`

#### `POST /intentos-pago/blocklist` 🔒
- **Función:** `intentos_pago_blocklist_add()` (línea 18900)
- **Descripción:** Alta en la blocklist: manual (tipo+valor) o desde una operación (payment_id,
- **Tablas:** `pedidos_pendientes`, `ventas`

#### `POST /intentos-pago/blocklist/<int:bl_id>/toggle` 🔒
- **Función:** `intentos_pago_blocklist_toggle()` (línea 18969)

#### `POST /intentos-pago/sync` 🔒
- **Función:** `intentos_pago_sync()` (línea 18888)

#### `GET, POST /login` 🔓
- **Función:** `login()` (línea 774)
- **Templates:** `login.html`
- **Tablas:** `usuarios`

#### `GET /logout` 🔒
- **Función:** `logout()` (línea 793)

#### `POST /mapeo-sku-mla/agregar` 🔒
- **Función:** `mapeo_sku_mla_agregar()` (línea 12572)
- **Descripción:** Alta manual de publicaciones al mapeo SKU↔MLA.

#### `GET /mapeo-sku-mla/listar` 🔒
- **Función:** `mapeo_sku_mla_listar()` (línea 12649)
- **Descripción:** Publicaciones mapeadas a un SKU (para ver/controlar desde la misma pantalla).

#### `POST /mapeo-sku-mla/quitar` 🔒
- **Función:** `mapeo_sku_mla_quitar()` (línea 12660)
- **Descripción:** Desactiva (no borra) una publicación del mapeo.

#### `GET /ml/callback` 🔒
- **Función:** `ml_callback()` (línea 13896)
- **Descripción:** Recibe el code de ML y lo canjea automáticamente por el token

#### `POST /ml/cambiar-envio-flex/<mla_id>` 🔒
- **Función:** `cambiar_envio_flex()` (línea 11143)
- **Descripción:** Cambia una publicación a ME2 self_service (Flex).

#### `POST /ml/cambiar-envio-me1/<mla_id>` 🔒
- **Función:** `cambiar_envio_me1()` (línea 11198)
- **Descripción:** Cambia una publicación a ME1 (logistic_type default).

#### `GET /nueva-venta` 🔒
- **Función:** `nueva_venta()` (línea 6589)
- **Descripción:** Formulario para registrar venta con stock disponible y ubicaciones
- **Templates:** `nueva_venta.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /nueva-venta/guardar` 🔒
- **Función:** `guardar_venta()` (línea 6813)
- **Descripción:** Guardar venta SIN descontar stock (solo registra la venta)
- **Tablas:** `items_venta`, `ventas`

#### `GET /pagos-cannon` 🔒
- **Función:** `pagos_cannon()` (línea 14147)
- **Templates:** `pagos_cannon.html`

#### `POST /pagos-cannon/escanear-factura` 🔒
- **Función:** `escanear_factura_cannon()` (línea 14388)
- **Descripción:** Extrae nro de comprobante, fecha de emisión e importe total de un PDF de factura Cannon.

#### `POST /pagos-cannon/guardar` 🔒
- **Función:** `pagos_cannon_guardar()` (línea 14217)

#### `GET /preguntas` 🔒
- **Función:** `preguntas()` (línea 18580)
- **Templates:** `preguntas.html`

#### `POST /preguntas/<question_id>/regenerar` 🔒
- **Función:** `preguntas_regenerar()` (línea 18652)

#### `POST /preguntas/<question_id>/responder` 🔒
- **Función:** `preguntas_responder()` (línea 18607)

#### `GET, POST /preguntas/reglas` 🔒
- **Función:** `preguntas_reglas()` (línea 18668)
- **Templates:** `preguntas_reglas.html`
- **Tablas:** `configuracion`

#### `POST /preguntas/sync` 🔒
- **Función:** `preguntas_sync()` (línea 18640)

#### `GET /productos` 🔓
- **Función:** `productos_lista()` (línea 21284)
- **Templates:** `productos_lista.html`
- **Tablas:** `configuracion`, `conjunto_configuracion`, `productos_base`, `productos_compuestos`, `productos_fotos`

#### `GET /productos/<sku>/fotos` 🔓
- **Función:** `productos_fotos()` (línea 21710)
- **Templates:** `productos_fotos.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /productos/<sku>/fotos/eliminar` 🔓
- **Función:** `productos_fotos_eliminar()` (línea 21773)
- **Tablas:** `productos_fotos`

#### `POST /productos/<sku>/fotos/reordenar` 🔓
- **Función:** `productos_fotos_reordenar()` (línea 21795)
- **Tablas:** `productos_fotos`

#### `POST /productos/<sku>/fotos/subir` 🔓
- **Función:** `productos_fotos_subir()` (línea 21727)
- **Tablas:** `productos_fotos`

#### `POST /productos/cuotas-coeficientes` 🔓
- **Función:** `productos_cuotas_coeficientes()` (línea 21526)
- **Tablas:** `configuracion`

#### `POST /productos/demora` 🔓
- **Función:** `productos_demora_guardar()` (línea 21485)
- **Tablas:** `configuracion`

#### `GET, POST /productos/editar/<sku>` 🔓
- **Función:** `productos_editar()` (línea 21861)
- **Templates:** `productos_form.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /productos/evento-guardar` 🔓
- **Función:** `productos_evento_guardar()` (línea 21595)
- **Descripción:** Panel del evento promocional (CYBERSALE, HOT SALE, etc).
- **Tablas:** `configuracion`

#### `POST /productos/flete-almohadas` 🔓
- **Función:** `productos_flete_almohadas()` (línea 21570)
- **Descripción:** Tarifa plana de envío para carritos de solo almohadas con destino CABA.
- **Tablas:** `configuracion`

#### `POST /productos/medio-toggle` 🔓
- **Función:** `productos_medio_toggle()` (línea 21665)
- **Descripción:** Prende/apaga un medio de pago desde el catálogo. Allowlist de claves.
- **Tablas:** `configuracion`

#### `POST /productos/newsletter-cupon` 🔓
- **Función:** `productos_newsletter_cupon()` (línea 21503)
- **Tablas:** `configuracion`

#### `GET, POST /productos/nuevo` 🔓
- **Función:** `productos_nuevo()` (línea 21809)
- **Templates:** `productos_form.html`, `productos_form.html`, `productos_form.html`
- **Tablas:** `productos_base`

#### `POST /productos/toggle/<sku>` 🔓
- **Función:** `productos_toggle()` (línea 21685)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /promociones-ml` 🔒
- **Función:** `promociones_ml()` (línea 9806)
- **Templates:** `promociones_ml.html`

#### `GET /promociones-ml/activas` 🔒
- **Función:** `promociones_ml_activas()` (línea 10770)
- **Descripción:** Devuelve JSON con TODAS las promos ya aplicadas (activas o pendientes).

#### `POST /promociones-ml/aplicar` 🔒
- **Función:** `promociones_ml_aplicar()` (línea 9952)
- **Descripción:** Aplica un PRICE_DISCOUNT (promo propia) a una publicación. Opcionalmente

#### `POST /promociones-ml/aplicar-lote` 🔒
- **Función:** `promociones_ml_aplicar_lote()` (línea 10456)
- **Descripción:** Participación MASIVA en una campaña de precio fijo (SMART / PRICE_MATCHING / LIGHTNING).

#### `POST /promociones-ml/buscar` 🔒
- **Función:** `promociones_ml_buscar()` (línea 9815)
- **Templates:** `promociones_ml.html`, `promociones_ml.html`, `promociones_ml.html`

#### `POST /promociones-ml/campania` 🔒
- **Función:** `promociones_ml_campania()` (línea 9879)
- **Templates:** `promociones_ml.html`, `promociones_ml.html`, `promociones_ml.html`

#### `GET /promociones-ml/historial` 🔒
- **Función:** `promociones_ml_historial()` (línea 10605)
- **Descripción:** Historial de promos: qué se mostró/aceptó vs qué aplicó ML.

#### `POST /promociones-ml/quitar` 🔒
- **Función:** `promociones_ml_quitar()` (línea 10521)
- **Descripción:** Sale/quita una promo de una publicación (DELETE). El borrado de ML es asíncrono.

#### `POST /promociones-ml/quitar-lote` 🔒
- **Función:** `promociones_ml_quitar_lote()` (línea 10568)
- **Descripción:** Sale de varias promos de una (DELETE en paralelo, pool interno).

#### `POST /publicar-catalogo-cuota` 🔒
- **Función:** `publicar_catalogo_cuota()` (línea 11613)
- **Descripción:** Crea un par de publis (listado general + catálogo) con una nueva cuota,

#### `POST /quitar-demora-masivo` 🔒
- **Función:** `quitar_demora_masivo()` (línea 12524)
- **Descripción:** Eliminar MANUFACTURING_TIME de todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /quitar-demora-mla` 🔒
- **Función:** `quitar_demora_mla()` (línea 12455)
- **Descripción:** Eliminar MANUFACTURING_TIME de una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `GET /reclamos` 🔒
- **Función:** `reclamos()` (línea 18088)
- **Templates:** `reclamos.html`

#### `GET /reclamos/<claim_id>` 🔒
- **Función:** `reclamo_detalle()` (línea 18113)
- **Templates:** `reclamo_detalle.html`

#### `POST /reclamos/<claim_id>/nota` 🔒
- **Función:** `reclamo_nota()` (línea 18193)

#### `POST /reclamos/<claim_id>/responder` 🔒
- **Función:** `reclamo_responder()` (línea 18159)

#### `POST /reclamos/sync` 🔒
- **Función:** `reclamos_sync()` (línea 18206)

#### `GET /rentabilidad` 🔒
- **Función:** `rentabilidad()` (línea 19782)
- **Templates:** `rentabilidad.html`, `rentabilidad.html`
- **Tablas:** `componentes`, `configuracion`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /rentabilidad/config` 🔒
- **Función:** `rentabilidad_config()` (línea 20032)
- **Descripción:** Guardar costos de envío editables desde el template de rentabilidad.
- **Tablas:** `configuracion`

#### `POST /rentabilidad/editar-costo` 🔒
- **Función:** `rentabilidad_editar_costo()` (línea 20015)
- **Descripción:** Editar costo_comision, costo_productos o costo_envio_vendedor de una venta.
- **Tablas:** `ventas`

#### `POST /rentabilidad/recalcular-costos` 🔒
- **Función:** `rentabilidad_recalcular_costos()` (línea 19951)
- **Descripción:** Recalcula costo_productos usando _build_precio_compra_map() oficial.
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /stock` 🔒
- **Función:** `ver_stock()` (línea 4567)
- **Descripción:** Ver stock disponible con filtros - PRODUCTOS BASE + COMBOS
- **Templates:** `stock.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /sw.js` 🔓
- **Función:** `_service_worker_root()` (línea 14000)
- **Descripción:** Sirve el service worker desde la raíz para que su scope sea '/' (controla

#### `GET /test/manufacturing-time` 🔒
- **Función:** `test_manufacturing_time()` (línea 13680)
- **Descripción:** Página de prueba para ver y modificar el MANUFACTURING_TIME
- **Templates:** `test_manufacturing_time.html`

#### `POST /test/manufacturing-time/poner` 🔒
- **Función:** `poner_manufacturing_time()` (línea 13808)
- **Descripción:** Pone o restaura el MANUFACTURING_TIME a un valor específico.

#### `POST /test/manufacturing-time/quitar` 🔒
- **Función:** `quitar_manufacturing_time()` (línea 13739)
- **Descripción:** Elimina el MANUFACTURING_TIME de una publicación enviando null.

#### `POST /test/manufacturing-time/ver` 🔒
- **Función:** `ver_manufacturing_time()` (línea 13690)
- **Descripción:** Consulta el estado actual de una publicación:

#### `GET /tienda-admin/cupones` 🔒
- **Función:** `tienda_cupones()` (línea 15566)
- **Templates:** `tienda_cupones.html`
- **Tablas:** `cupones`, `cupones_uso`, `suscriptores`

#### `POST /tienda-admin/cupones/guardar` 🔒
- **Función:** `tienda_cupones_guardar()` (línea 15618)
- **Tablas:** `cupones`

#### `GET, POST /tienda-admin/email-hot-masivo` 🔓
- **Función:** `email_hot_masivo()` (línea 15716)
- **Descripción:** Panel del envío masivo del email HOT MERCADOMUEBLES a suscriptores.
- **Templates:** `email_hot_masivo.html`
- **Tablas:** `configuracion`, `suscriptores`

#### `GET, POST /tienda-admin/email-hot-test` 🔓
- **Función:** `email_hot_test()` (línea 15689)
- **Descripción:** Página admin para enviar PRUEBAS del email del HOT MERCADOMUEBLES.
- **Templates:** `email_hot_test.html`

#### `GET /tienda-admin/ofertas` 🔒
- **Función:** `tienda_ofertas()` (línea 15109)
- **Templates:** `tienda_ofertas.html`
- **Tablas:** `ofertas_home`, `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/ofertas/guardar` 🔒
- **Función:** `tienda_ofertas_guardar()` (línea 15129)
- **Tablas:** `ofertas_home`

#### `GET /tienda-admin/precios` 🔓
- **Función:** `tienda_precios()` (línea 14990)
- **Templates:** `tienda_precios.html`
- **Tablas:** `conjunto_configuracion`, `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/precios/descuento` 🔓
- **Función:** `tienda_precios_descuento()` (línea 15076)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/precios/guardar` 🔓
- **Función:** `tienda_precios_guardar()` (línea 15047)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/suscriptores/eliminar` 🔒
- **Función:** `tienda_suscriptores_eliminar()` (línea 15650)
- **Tablas:** `suscriptores`

#### `GET /tienda-admin/suscriptores/exportar` 🔒
- **Función:** `tienda_suscriptores_exportar()` (línea 15661)
- **Descripción:** Exporta la lista de suscriptores a CSV (para enviar a una agencia).
- **Tablas:** `cupones`, `suscriptores`

#### `GET /transferir-stock` 🔒
- **Función:** `transferir_stock()` (línea 6386)
- **Descripción:** Formulario para transferir stock de Depósito a Full (Compac y Almohadas)
- **Templates:** `transferir_stock.html`
- **Tablas:** `productos_base`

#### `POST /transferir-stock/guardar` 🔒
- **Función:** `transferir_stock_guardar()` (línea 6421)
- **Descripción:** Procesar transferencia de stock de Depósito a Full (Compac y Almohadas)
- **Tablas:** `productos_base`

#### `GET /ventas/<int:venta_id>/nota-pedido` 🔒
- **Función:** `nota_pedido_pdf()` (línea 15161)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/<int:venta_id>/papel-azul` 🔒
- **Función:** `papel_azul_pdf()` (línea 15379)
- **Descripción:** Genera el papel azul de despacho para ventas Flex o Flete Propio.
- **Tablas:** `conjunto_configuracion`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/activas` 🔒
- **Función:** `ventas_activas()` (línea 1495)
- **Descripción:** Lista de ventas activas con filtros de búsqueda
- **Templates:** `ventas_activas.html`
- **Tablas:** `configuracion`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/cancelar` 🔒
- **Función:** `cancelar_venta()` (línea 2682)
- **Descripción:** Cancelar venta (NO descuenta stock)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/eliminar` 🔒
- **Función:** `eliminar_venta()` (línea 2779)
- **Descripción:** Eliminar venta completamente de la base de datos
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/entregada` 🔒
- **Función:** `marcar_entregada()` (línea 2595)
- **Descripción:** Marcar venta como entregada (descuenta stock si no se descontó, con verificación)
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/activas/<int:venta_id>/etiqueta-ml` 🔒
- **Función:** `etiqueta_ml()` (línea 1738)
- **Descripción:** Descarga etiqueta de envío ML (PDF o ZPL) para una venta.
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/activas/<int:venta_id>/orden-retiro` 🔒
- **Función:** `orden_retiro_pdf()` (línea 1914)
- **Descripción:** Generar PDF de orden de retiro (2 copias: cliente + archivo)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/proceso` 🔒
- **Función:** `pasar_a_proceso()` (línea 2504)
- **Descripción:** Pasar venta a proceso de envío (descuenta stock con verificación)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/quitar-demora` 🔒
- **Función:** `quitar_demora_venta()` (línea 2740)
- **Descripción:** Quita la línea 'DEMORA_ML: X días' de las notas de una venta.
- **Tablas:** `ventas`

#### `GET /ventas/activas/<int:venta_id>/remito` 🔒
- **Función:** `remito_conforme_pdf()` (línea 2233)
- **Descripción:** Remito / Conforme de entrega (A4, ORIGINAL + DUPLICADO).
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/whatsapp-enviar` 🔒
- **Función:** `whatsapp_enviar()` (línea 1656)
- **Descripción:** Envía mensaje de WhatsApp al cliente de una venta activa.
- **Tablas:** `ventas`

#### `POST /ventas/activas/cancelar-multiple` 🔒
- **Función:** `cancelar_ventas_multiple()` (línea 3106)
- **Descripción:** Cancelar múltiples ventas
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/activas/exportar-excel` 🔒
- **Función:** `exportar_ventas_activas_excel()` (línea 1419)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/marcar-entregadas-multiple` 🔒
- **Función:** `marcar_entregadas_multiple()` (línea 2977)
- **Descripción:** Marcar múltiples ventas como entregadas
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/pasar-proceso-multiple` 🔒
- **Función:** `pasar_a_proceso_multiple()` (línea 2853)
- **Descripción:** Pasar múltiples ventas a proceso de envío
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/auto-import-toggle` 🔒
- **Función:** `auto_import_toggle()` (línea 16835)
- **Tablas:** `configuracion`

#### `GET, POST /ventas/editar/<int:venta_id>` 🔒
- **Función:** `editar_venta()` (línea 3772)
- **Descripción:** Editar una venta activa
- **Templates:** `editar_venta.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/etiquetas-ml-masivo` 🔒
- **Función:** `etiquetas_ml_masivo()` (línea 1819)
- **Descripción:** Descarga etiquetas ML para múltiples ventas en un solo ZPL/PDF.
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/guardar-trid` 🔒
- **Función:** `guardar_trid()` (línea 13948)
- **Descripción:** Guardar o actualizar el TRID (código de tracking Correo Argentino) en notas
- **Tablas:** `ventas`

#### `GET /ventas/historicas` 🔒
- **Función:** `ventas_historicas()` (línea 4774)
- **Descripción:** Lista de ventas históricas (entregadas y canceladas) con filtros y paginación
- **Templates:** `ventas_historicas.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/historicas/<int:venta_id>/generar-factura-excel` 🔒
- **Función:** `generar_factura_excel()` (línea 5297)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/historicas/<int:venta_id>/marcar-entregado-ml` 🔒
- **Función:** `historicas_marcar_entregado_ml()` (línea 5053)
- **Descripción:** Reporta a ML la entrega de una venta para acelerar la acreditación.
- **Tablas:** `ventas`

#### `POST /ventas/historicas/<int:venta_id>/volver_activas` 🔒
- **Función:** `historicas_volver_activas()` (línea 4978)
- **Descripción:** Volver venta histórica (entregada o cancelada) a ventas activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/historicas/facturar-multiple` 🔒
- **Función:** `facturar_multiple()` (línea 5632)
- **Descripción:** Generar UN SOLO archivo .txt con TODAS las ventas seleccionadas
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/historicas/facturar-multiple-excel` 🔒
- **Función:** `facturar_multiple_excel()` (línea 5438)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/historicas/volver-activas-multiple` 🔒
- **Función:** `historicas_volver_activas_multiple()` (línea 5105)
- **Descripción:** Volver múltiples ventas históricas a ventas activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/ml-progress` 🔒
- **Función:** `ml_progress()` (línea 17123)

#### `GET, POST /ventas/ml/configurar_token` 🔒
- **Función:** `ml_configurar_token()` (línea 8341)
- **Descripción:** Página para configurar/actualizar el token de ML
- **Templates:** `ml_configurar_token.html`

#### `GET /ventas/ml/importar` 🔒
- **Función:** `ml_importar_ordenes()` (línea 8465)
- **Descripción:** Traer órdenes de ML - FILTRO ARREGLADO
- **Templates:** `ml_importar_ordenes.html`
- **Tablas:** `auto_import_log`, `ventas`

#### `POST /ventas/ml/mapear` 🔒
- **Función:** `ml_guardar_mapeo()` (línea 8698)
- **Descripción:** Guardar mapeo - Obtiene shipping completo y billing info

#### `GET /ventas/ml/seleccionar/<orden_id>` 🔒
- **Función:** `ml_seleccionar_orden()` (línea 8566)
- **Descripción:** Seleccionar orden - Con normalización automática de SKU (quita Z)
- **Templates:** `ml_mapear_productos.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /ventas/no-mapeadas-count` 🔒
- **Función:** `ventas_no_mapeadas_count()` (línea 17153)
- **Tablas:** `auto_import_log`

#### `GET /ventas/nueva/ml` 🔒
- **Función:** `nueva_venta_desde_ml()` (línea 8798)
- **Descripción:** Crear nueva venta con datos precargados desde ML
- **Templates:** `nueva_venta_ml.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /ventas/nuevas-count` 🔒
- **Función:** `ventas_nuevas_count()` (línea 17131)
- **Tablas:** `auto_import_log`

#### `POST /ventas/nuevas-reset` 🔒
- **Función:** `ventas_nuevas_reset()` (línea 17142)
- **Tablas:** `auto_import_log`

#### `GET /ventas/proceso` 🔒
- **Función:** `ventas_proceso()` (línea 3206)
- **Descripción:** Lista de ventas en proceso de envío con filtros
- **Templates:** `proceso_envio.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/proceso/<int:venta_id>/cancelar` 🔒
- **Función:** `proceso_cancelar_devolver()` (línea 3425)
- **Descripción:** Cancelar venta en proceso y DEVOLVER stock descontado (con motivo opcional)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/<int:venta_id>/entregada` 🔒
- **Función:** `proceso_marcar_entregada()` (línea 3370)
- **Descripción:** Marcar venta en proceso como entregada (stock ya descontado)
- **Tablas:** `ventas`

#### `POST /ventas/proceso/<int:venta_id>/volver_activas` 🔒
- **Función:** `proceso_volver_activas()` (línea 3319)
- **Descripción:** Volver venta de proceso a activas (devuelve stock)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/cancelar-multiple` 🔒
- **Función:** `proceso_cancelar_multiple()` (línea 3677)
- **Descripción:** Cancelar múltiples ventas en proceso y DEVOLVER stock
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/marcar-entregadas-multiple` 🔒
- **Función:** `proceso_marcar_entregadas_multiple()` (línea 3581)
- **Descripción:** Marcar múltiples ventas en proceso como entregadas
- **Tablas:** `ventas`

#### `POST /ventas/proceso/volver-activas-multiple` 🔒
- **Función:** `proceso_volver_activas_multiple()` (línea 3501)
- **Descripción:** Volver múltiples ventas en proceso a activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /viajes` 🔒
- **Función:** `viajes_lista()` (línea 14808)
- **Templates:** `viajes.html`
- **Tablas:** `viajes`

#### `GET /viajes/<int:viaje_id>` 🔒
- **Función:** `viaje_detalle()` (línea 14854)
- **Templates:** `viaje_detalle.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`, `viajes`

#### `POST /viajes/guardar` 🔒
- **Función:** `viajes_guardar()` (línea 14914)
- **Tablas:** `viajes`

#### `GET /viajes/nuevo` 🔒
- **Función:** `viaje_nuevo()` (línea 14824)
- **Templates:** `viaje_form.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /webhook/ml-claims` 🔓
- **Función:** `webhook_ml_claims()` (línea 18216)
- **Descripción:** Recibe notificaciones del topic marketplace_claims de ML.

### `tienda_bp.py`

#### `GET /` 🔓
- **Función:** `home()` (línea 2745)
- **Templates:** `tienda/home.html`
- **Tablas:** `conjunto_configuracion`, `items_venta`, `ofertas_home`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /carrito` 🔓
- **Función:** `ver_carrito()` (línea 4292)
- **Templates:** `tienda/carrito.html`
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /carrito/actualizar` 🔓
- **Función:** `actualizar_carrito()` (línea 4155)
- **Descripción:** Cambia la cantidad de un item (solo almohadas). delta = +1 o -1.
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /carrito/agregar` 🔓
- **Función:** `agregar_carrito()` (línea 4003)
- **Tablas:** `conjunto_configuracion`, `productos_base`, `productos_compuestos`

#### `POST /carrito/eliminar` 🔓
- **Función:** `eliminar_carrito()` (línea 4443)

#### `POST /carrito/quitar-cupon` 🔓
- **Función:** `quitar_cupon()` (línea 4436)

#### `POST /carrito/vaciar` 🔓
- **Función:** `vaciar_carrito()` (línea 4284)

#### `POST /carrito/validar-cupon` 🔓
- **Función:** `validar_cupon()` (línea 4372)
- **Tablas:** `cupones`, `cupones_uso`

#### `POST /checkout` 🔓
- **Función:** `checkout()` (línea 5327)
- **Templates:** `tienda/checkout_bricks.html`
- **Tablas:** `configuracion`, `pedidos_pendientes`

#### `POST /cotizar-envio` 🔓
- **Función:** `cotizar_envio()` (línea 5078)
- **Descripción:** AJAX: cotiza envío Zipnova para el carrito actual.

#### `GET /datos-envio` 🔓
- **Función:** `datos_envio()` (línea 5226)
- **Descripción:** Pantalla de datos del cliente antes de ir a MP.
- **Templates:** `tienda/datos_envio.html`

#### `GET /devoluciones` 🔓
- **Función:** `devoluciones()` (línea 10039)
- **Templates:** `tienda/devoluciones.html`

#### `GET /envios` 🔓
- **Función:** `envios()` (línea 10034)
- **Templates:** `tienda/envios.html`

#### `GET /feed/meta.json` 🔓
- **Función:** `feed_meta_stats()` (línea 9813)
- **Descripción:** Resumen del feed en JSON: para chequear de un vistazo qué se está publicando.

#### `GET /feed/meta.xml` 🔓
- **Función:** `feed_meta()` (línea 9793)
- **Descripción:** Feed de productos para el catálogo de Meta. Público (Meta lo baja sin login).

#### `GET /localidades` 🔓
- **Función:** `localidades()` (línea 5057)
- **Descripción:** Devuelve las localidades para un CP. En CABA, los 48 barrios.

#### `POST /pago/ejecutar` 🔓
- **Función:** `pago_ejecutar()` (línea 5821)
- **Descripción:** Endpoint para Checkout Bricks (Opción A).
- **Tablas:** `pedidos_pendientes`

#### `POST /pago/ejecutar-12` 🔓
- **Función:** `pago_ejecutar_12()` (línea 5923)
- **Descripción:** Checkout Bricks — pago MP en 12 cuotas (con recargo). El monto y las
- **Tablas:** `pedidos_pendientes`

#### `POST /pago/ejecutar-3-mp` 🔓
- **Función:** `pago_ejecutar_3_mp()` (línea 6004)
- **Descripción:** Checkout Bricks — pago MP en 3 cuotas (con recargo). El monto y las
- **Tablas:** `pedidos_pendientes`

#### `GET /pago/error` 🔓
- **Función:** `pago_error()` (línea 7495)
- **Templates:** `tienda/pago_error.html`

#### `GET /pago/exito` 🔓
- **Función:** `pago_exito()` (línea 7299)
- **Templates:** `tienda/pago_exito.html`, `tienda/pago_exito_getnet.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /pago/exito-getnet/<pedido_ref>` 🔓
- **Función:** `pago_exito_getnet()` (línea 7264)
- **Descripción:** Página de éxito específica para GetNet con pedido_ref en el path.
- **Templates:** `tienda/pago_exito_getnet.html`
- **Tablas:** `ventas`

#### `POST /pago/getnet/crear` 🔓
- **Función:** `pago_getnet_crear()` (línea 7058)
- **Descripción:** PROVISORIO: crea un payment-intent en GetNet (digital-checkout) y devuelve
- **Tablas:** `pedidos_pendientes`

#### `POST /pago/getnet/webhook` 🔓
- **Función:** `getnet_webhook()` (línea 7256)
- **Descripción:** PROVISORIO: solo loggea el payload, no registra venta.

#### `POST /pago/payway` 🔓
- **Función:** `pago_payway()` (línea 6372)
- **Descripción:** Recibe token de Payway JS SDK + cuotas elegidas.
- **Tablas:** `cupones`, `cupones_uso`, `items_venta`, `pedidos_pendientes`, `ventas`

#### `POST /pago/payway/token` 🔓
- **Función:** `payway_token()` (línea 6328)
- **Descripción:** Proxy de tokenizacion para Payway.

#### `GET /pago/pendiente` 🔓
- **Función:** `pago_pendiente()` (línea 7460)
- **Descripción:** Con tarjeta de crédito, MP redirige acá con status=in_process.
- **Templates:** `tienda/pago_pendiente.html`

#### `GET /premium` 🔓
- **Función:** `premium()` (línea 3302)
- **Descripción:** Landing de la línea premium: 4 modelos (2 de resortes, 2 de espuma) con
- **Templates:** `tienda/premium.html`
- **Tablas:** `conjunto_configuracion`, `productos_base`, `productos_compuestos`

#### `GET /privacidad` 🔓
- **Función:** `privacidad()` (línea 10029)
- **Templates:** `tienda/privacidad.html`

#### `GET /producto/<sku_url>` 🔓
- **Función:** `detalle()` (línea 3400)
- **Templates:** `tienda/detalle.html`, `tienda/detalle.html`
- **Tablas:** `conjunto_configuracion`, `ofertas_home`, `productos_base`, `productos_compuestos`

#### `GET /seguimiento` 🔓
- **Función:** `seguimiento()` (línea 9882)
- **Descripción:** El cliente ingresa su número de venta (MP-XXXXXXX) o payment_id.
- **Templates:** `tienda/seguimiento.html`
- **Tablas:** `items_venta`, `productos_base`, `ventas`

#### `GET /sitemap.xml` 🔓
- **Función:** `sitemap()` (línea 9834)
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /suscribirse` 🔓
- **Función:** `suscribirse()` (línea 8339)
- **Descripción:** Registra el email, genera un cupón único y envía el mail de bienvenida.
- **Tablas:** `cupones`, `suscriptores`

#### `GET, POST /test-getnet` 🔓
- **Función:** `test_getnet()` (línea 10045)
- **Descripción:** Página de prueba del iframe GetNet — sin auth (URL no publicada). No registra venta.
- **Templates:** `tienda/test_getnet.html`
- **Tablas:** `productos_base`

#### `GET /test-mp` 🔓
- **Función:** `test_mp()` (línea 10145)
- **Descripción:** Página de prueba MP — sin auth (URL no publicada). No registra venta.
- **Templates:** `tienda/test_mp.html`
- **Tablas:** `productos_base`

#### `POST /test-mp/pagar` 🔓
- **Función:** `test_mp_pagar()` (línea 10249)
- **Descripción:** Ejecuta el pago de PRUEBA con installments=12 forzado + 3DS. NO registra venta.

#### `POST /test-mp/preparar` 🔓
- **Función:** `test_mp_preparar()` (línea 10171)
- **Descripción:** Calcula total con recargo + cupón y crea una preference de PRUEBA.
- **Tablas:** `cupones`

#### `GET /test-payway` 🔒
- **Función:** `test_payway()` (línea 10333)
- **Descripción:** Página de prueba Payway MiPyME. Requiere sesión del panel: cobra con
- **Templates:** `tienda/test_payway.html`

#### `POST /test-payway/pagar` 🔒
- **Función:** `test_payway_pagar()` (línea 10350)
- **Descripción:** Cobra el monto indicado con el installments elegido y devuelve la

#### `GET /verificar-pago` 🔓
- **Función:** `verificar_pago()` (línea 7476)
- **Descripción:** API JSON: consulta el estado real de un pago en MP. Usado por el auto-refresh.

#### `POST /webhook/clearsale` 🔓
- **Función:** `webhook_clearsale()` (línea 10594)
- **Tablas:** `ventas`

#### `POST /webhook/clearsale-test` 🔓
- **Función:** `webhook_clearsale_test()` (línea 10532)
- **Descripción:** Recibe el OrderStatus de ClearSale sandbox y lo deja en sistema_logs.

#### `POST /webhook/getnet` 🔓
- **Función:** `webhook_getnet()` (línea 8884)
- **Descripción:** Recibe notificaciones de GetNet cuando el pago es aprobado.
- **Tablas:** `cupones`, `cupones_uso`, `items_venta`, `ventas`

#### `POST /webhook/mp` 🔓
- **Función:** `webhook_mp()` (línea 8406)
- **Descripción:** Recibe notificaciones de MP.
- **Tablas:** `configuracion`, `cupones`, `cupones_uso`, `items_venta`, `pedidos_pendientes`, `ventas`

---

## 🔧 Helpers (sin ruta HTTP) — 268 funciones

### `app.py`

- `_acortar_family_name()` (L11460) — ML rechaza family_name > 60 chars. Esta función acorta de forma inteligente:
- `_aplica_logica_z()` (L15848) — Determina si aplica lógica Z (demora) para un SKU.
- `_armar_bultos_cotizador()` (L21937) — Dado una lista de SKUs, arma los bultos para cotizar en Zipnova. [tablas: componentes, productos_base, productos_compuestos]
- `_build_precio_compra_map()` (L20096) — Idéntico a _build_precio_costos_map pero usando _calcular_precio_compra (sin multiplicador). [tablas: configuracion]
- `_build_precio_costos_map()` (L19631) — Construye un mapa sku → precio_lista_costos para mostrar en tienda_precios. [tablas: configuracion, conjunto_configuracion]
- `_calcular_carga_viaje()` (L14704) — Calcula si los productos del viaje entran en las zonas del vehículo. [tablas: componentes, items_venta, productos_base, productos_compuestos, viajes]
- `_calcular_importe_pp()` (L14138) — Calcula importe con pronto pago. Ej: 5% → total/1.05, redondeado sin decimales.
- `_calcular_precio_compra()` (L19616) — Precio de compra (costo neto) = precio_cannon con todos los descuentos aplicados,
- `_calcular_precio_lista()` (L19597) — precio_lista = precio_cannon
- `_clasificar_mensajes()` (L18025) — Separa los mensajes en (con_comprador, con_mediacion).
- `_construir_payload_desde_hermana()` (L11504) — Dado el GET completo de la hermana mayor (publi de listado general activa
- `_costos_map()` (L9675) — {sku_ml: {contado, c3, c6, c12}} con el precio de lista de costos (productos_base.precio_base) [tablas: componentes, productos_base, productos_compuestos]
- `_crear_tabla_ml_reclamos()` (L17734) — Crea la tabla de cabecera de reclamos ML si no existe.
- `_crear_tablas_fletes()` (L14021)
- `_crear_tablas_pagos_cannon()` (L14068)
- `_crear_tablas_productos()` (L21237) — Tabla de fotos y columnas opcionales en productos_base. Solo corre una vez por proceso.
- `_cs_rechazan_sql()` (L73) — Devuelve ('%s,%s,...', [estados]) para un IN con los estados de ClearSale
- `_cuotas_reales_map()` (L9780) — {mla: 'texto cuotas'} con las cuotas reales de cada publi, en multiget de 20.
- `_ejemplos_relevantes()` (L18376) — Elige los k ejemplos MÁS RELEVANTES (no los últimos) para no encarecer el prompt.
- `_enviar_email_hot_event()` (L306) — Envía el email del HOT MERCADOMUEBLES a un destinatario.
- `_envio_label()` (L9402) — Convierte el bloque shipping de ML a (label, color_bg, color_fg) para mostrar en UI.
- `_es_almohada()` (L15843)
- `_es_compac()` (L15839)
- `_extraer_skus_base_de_items()` (L16142) — Dado una lista de items [{sku, cantidad}], devuelve el set de SKUs base [tablas: componentes, productos_base, productos_compuestos]
- `_faltantes_catalogo_guardar_cache()` (L11258) — Guarda resultados en configuracion para que la ruta sirva al instante. [tablas: configuracion]
- `_fmt_money_ar()` (L18039) — Formatea un número como $1.234.567 (estilo AR). Devuelve '—' si no es numérico.
- `_ga4_query()` (L17530) — Consulta la GA4 Data API y retorna rows.
- `_generar_pdf_lista()` (L20246) — Genera el PDF de lista (costos o precios) en A4 horizontal, una sola hoja.
- `_get_config_costos()` (L19592) — Retorna dict con todos los descuentos y multiplicador desde DB.
- `_get_fotos()` (L21273) — Devuelve lista de filenames ordenados para un SKU. [tablas: productos_fotos]
- `_get_ml_z_sin_stock_config()` (L1136) — Lee la config de stock/demora para publicaciones Z sin stock disponible. [tablas: configuracion]
- `_get_precio_costos_sku()` (L19403) — Retorna el precio calculado por costos para un SKU dado. [tablas: configuracion, conjunto_configuracion]
- `_humanizar_atraso()` (L18327) — Devuelve 'hace 2d 3h' / 'hace 5h 10m' / 'hace 12m'.
- `_ids_no_modificables()` (L11485) — Extrae los IDs de atributos que ML marca como 'not modifiable'/'ignored'
- `_importar_orden_automatica()` (L16220) — Importa automáticamente una orden de ML sin intervención del usuario. [tablas: componentes, configuracion, items_venta, productos_base, productos_compuestos, ventas]
- `_indexar_catalogo_mla()` (L10832) — Guarda en mla_catalogo el catálogo de las publis que se acaban de consultar.
- `_init_auto_import_table()` (L16166) [tablas: auto_import_log]
- `_job_auto_importar_ml_inner()` (L16690) [tablas: auto_import_log, configuracion, ventas]
- `_limpiar_html_mensaje()` (L17974) — Convierte el HTML que mandan los mensajes de ML (sobre todo el mediador) en
- `_ml_progress_get()` (L16958) — Lee el progreso desde la BD. [tablas: configuracion]
- `_ml_progress_save()` (L16945) — Guarda el progreso en la BD para que sea compartido entre workers. [tablas: configuracion]
- `_mlas_desde_pubs_json()` (L12016) — Extrae lista de MLAs desde el JSON de publicaciones que manda el template.
- `_mlas_pausadas_con_stock()` (L12032) — Devuelve los MLAs cuya publicación está en status 'paused' y tiene stock > 0
- `_normalizar_mensaje()` (L18001) — Devuelve un dict uniforme {rol, rol_label, es_seller, fecha, texto, adjuntos, es_mediacion}.
- `_num_form()` (L6797) — Convierte un valor del formulario a número de forma segura.
- `_origen_label()` (L17558) — Clasifica el origen de tráfico de una venta de tienda web a partir de
- `_pack_zona()` (L14596) — Algoritmo de carga para objetos planos (colchones, bases, sommiers).
- `_parse_ml_datetime()` (L17767) — Convierte fecha ISO de ML (2024-09-11T22:39:00.000-04:00) a hora Argentina
- `_participar_campania_una()` (L10260) — Une UNA publicación a una campaña de precio fijo (SMART / PRICE_MATCHING).
- `_participar_deal_una()` (L10402) — Une UNA publicación a una campaña DEAL (oferta con rango de descuento).
- `_participar_lightning_una()` (L10337) — Une UNA publicación a una campaña LIGHTNING (oferta relámpago).
- `_payway_api_listar()` (L18699) — GET /payments de Payway/Decidir (solo lectura). Devuelve dict o None.
- `_payway_upsert_intento()` (L18718) — Inserta/actualiza una operación de Payway en payway_intentos.
- `_poner_demora_ml()` (L15883) — Poner demora de manufacturing_time en una publi ML.
- `_pregunta_historial()` (L18305) — P/R previas del MISMO comprador sobre la MISMA publicación (JSON string o None).
- `_pregunta_item_ctx()` (L18264) — Contexto de la PUBLICACIÓN (todo desde ML, nada de la BD):
- `_preguntas_reglas()` (L18355) — Reglas del bot de preguntas (desde configuracion.preguntas_reglas, con defaults). [tablas: configuracion]
- `_preguntas_search()` (L18241) — Trae preguntas del seller desde ML.
- `_promo_aporte_de()` (L10112) — (aporte_propio_pct, aporte_meli_pct) de una promo cruda de la API.
- `_promo_campanias()` (L9718) — Lista de campañas del vendedor (para el dropdown).
- `_promo_coefs()` (L9660) — (coef_3_efectivo, coef_6, coef_12, getnet_on, mp12_on) según medios activos. [tablas: configuracion]
- `_promo_fecha_ar()` (L9735) — ISO UTC de ML → string en hora Argentina (UTC-3).
- `_promo_hist_registrar()` (L10152) — Guarda una fila en promos_ml_historial. Nunca levanta excepción: el registro
- `_promo_leer_aplicada()` (L10126) — Relee en ML la promo que quedó realmente aplicada a una publicación.
- `_promo_limite_aporte()` (L10100) — Tope de aporte propio (%) por encima del cual NO se aplica una promo. [tablas: configuracion]
- `_promo_row()` (L9748) — Normaliza una promo (de /items o de una campaña) a los campos del template.
- `_promo_verificar_y_registrar()` (L10205) — Post-aplicación: relee lo que ML dejó, lo compara con lo que se mostró, lo
- `_prontopago_pct()` (L14056) — % de pronto pago configurado en Costos (cannon_descuentos.prontopago).
- `_publis_de_catalogo()` (L10863) — Nuestras publicaciones en un producto de catálogo de ML.
- `_push_stock_ml_una()` (L15926) — Empuja stock a UNA publicación. Intenta el PUT normal (available_quantity);
- `_quitar_demora_ml()` (L15895) — Quitar demora de manufacturing_time en una publi ML.
- `_quitar_promo_una()` (L10549) — Saca UNA publicación de una promo. Pensado para el pool del lote.
- `_recargar_publicaciones()` (L12058) — Helper: devuelve lista de publicaciones.
- `_rechequear_orden_ml()` (L17249) — Re-consulta una orden de ML auto-importada y actualiza solo los campos que [tablas: items_venta, ventas]
- `_reclamo_affects_reputation()` (L17823)
- `_reclamo_detail()` (L17815)
- `_reclamo_get()` (L17807)
- `_reclamo_messages()` (L17831)
- `_reclamo_orden_info()` (L18047) — Trae datos de la venta asociada al reclamo: items, importe, comprador.
- `_reclamo_send_message()` (L17857)
- `_reclamo_status_history()` (L17844)
- `_reclamos_search()` (L17788)
- `_responder_pregunta_ml()` (L18562) — POST de la respuesta a ML. Devuelve (ok, response).
- `_rol_label()` (L17991)
- `_seller_puede_responder()` (L17958) — Devuelve (puede_responder, receiver_sugerido) según available_actions del seller.
- `_sku_ml_existe()` (L7567) — ¿Existe ese SKU tal cual como producto, base o compuesto? [tablas: productos_base, productos_compuestos]
- `_sugerir_respuesta()` (L18406) — Respuesta sugerida con Claude: reglas + envío (Flex/ME1 según Z) + conocimiento de
- `_sync_almohadas_ml()` (L15969) — Empuja a ML el stock de las almohadas afectadas (menos PLATINO), con margen
- `_sync_ml_por_venta()` (L16007) — Wrapper para eventos de VENTA (importar/cancelar/eliminar/editar):
- `_sync_preguntas()` (L18478) — Wrapper con lock entre workers: solo UN worker corre el sync+push por vez.
- `_sync_preguntas_inner()` (L18497) — Upsert de preguntas sin responder; marca como ANSWERED las que ya no figuran.
- `_sync_reclamo_cabecera()` (L17865) — Consulta la API de ML y hace upsert de la cabecera del reclamo en ml_reclamos.
- `_ultima_vigencia_lista()` (L19767) — Vigencia de la última lista de precios cargada (AAAA-MM-DD) o ''.
- `_zipnova_auth_adm()` (L21933)
- `activar_publicacion_ml()` (L4363) — Reactivar (activar) una publicación pausada en Mercado Libre.
- `actualizar_handling_time_ml()` (L8089) — Actualizar el tiempo de disponibilidad (handling_time) en ML
- `actualizar_publicaciones_ml()` (L16017) — Dado un set de SKUs base que cambiaron disponible, actualiza en ML [tablas: componentes, productos_base, productos_compuestos]
- `actualizar_publicaciones_ml_con_progreso()` (L16970) — Corre la actualización de ML guardando progreso en BD (compartido entre workers). [tablas: componentes, productos_base, productos_compuestos]
- `actualizar_stock_compac_dep_ml()` (L16852) — Actualiza el stock selling_address (DEP) en ML para todas las publicaciones
- `actualizar_stock_ml()` (L4285) — Actualizar stock de una publicación en Mercado Libre
- `admin_required()` (L142)
- `agencia_only()` (L161) — Solo agencia puede acceder — redirige a /agencia si intenta acceder a otra ruta.
- `calcular_stock_por_sku()` (L12833) — Calcula stock disponible para todos los SKUs (base + combos). [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `cargar_ml_token()` (L7467) — Cargar token ML desde la base de datos. Si está vencido, lo renueva. [tablas: configuracion]
- `clearsale_bloquea()` (L948) — (bloquea, motivo) para una venta. FAIL-OPEN a propósito: si algo de
- `clearsale_modo_actual()` (L937) — '0', 'sombra' o '1'. Se lee una sola vez por request y se pasa a
- `construir_in_clause()` (L236) — Recibe lista de valores y nombre de columna SQL.
- `debug_orden_ml_completa()` (L8840) — Ver TODOS los datos que trae ML de una orden
- `decimal_to_float()` (L6571) — Convertir Decimals a float para JSON serialization
- `descontar_stock_item()` (L4179) — Descuenta stock de un item considerando: [tablas: componentes, productos_base, productos_compuestos]
- `descontar_stock_simple()` (L4220) — Descuenta stock de un producto simple según ubicación y registra en movimientos_stock [tablas: productos_base]
- `detectar_alertas_stock_bajo()` (L1197) — Detecta productos con stock disponible <= 0. [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `devolver_stock_item()` (L4060) — Devuelve stock de un item (lo opuesto a descontar_stock_item) [tablas: componentes, productos_base, productos_compuestos]
- `devolver_stock_simple()` (L4102) — Devuelve stock de un producto simple según ubicación (SUMA en lugar de RESTAR) [tablas: productos_base]
- `enviar_hot_event_a_fallidos()` (L615) — Reintento del HOT MERCADOMUEBLES SOLO a los destinatarios que figuran en [tablas: configuracion]
- `enviar_hot_event_a_todos()` (L465) — Envía el email del HOT MERCADOMUEBLES a todos los suscriptores + email testigo. [tablas: configuracion, suscriptores]
- `enviar_whatsapp()` (L253) — Envía un mensaje de WhatsApp usando una plantilla aprobada por Meta.
- `execute_db()` (L206) — Ejecutar query INSERT/UPDATE/DELETE
- `extraer_billing_info_ml()` (L9100) — Extraer datos de facturación del formato de ML
- `get_db_connection()` (L187) — Crear conexión a la base de datos
- `guardar_ml_token()` (L7485) — Guardar token ML en la base de datos (persiste en Railway) [tablas: configuracion]
- `iniciar_scheduler()` (L19105)
- `inject_alertas_pendientes()` (L88) — Inyecta el contador de alertas en todos los templates
- `inject_clearsale()` (L58) — Clasificación de estados de ClearSale para los templates, así el color
- `job_auto_importar_ml()` (L16659) — Job que corre cada 60 segundos.
- `job_catalogo_mla()` (L19073) — Refresco diario del índice de catálogos, una sola vez por día. [tablas: configuracion]
- `job_completar_notas_mp()` (L17163) — Job que corre cada 10 minutos. [tablas: ventas]
- `job_faltantes_catalogo_ml()` (L11273) — Corre en background (scheduler o thread manual). [tablas: configuracion]
- `job_imagenes_catalogo()` (L18986) — Normaliza para el feed de Meta las fotos nuevas y las que cambiaron.
- `job_promos_rechequeo()` (L10655) — Rechequeo diario de las promos aplicadas: registra en el historial toda [tablas: configuracion]
- `job_rechequear_autoimportadas()` (L17436) — Job que corre cada 5 minutos. Re-consulta ML para corregir datos que [tablas: ventas]
- `job_sincronizar_payway()` (L18797) — Job (cada 5 min): refresca los intentos de pago Payway (liviano).
- `job_sincronizar_preguntas()` (L18569) — Job (cada ~3 min): refresca las preguntas sin responder.
- `job_sincronizar_reclamos()` (L17929) — Job de respaldo (cada 10 min) + botón Sincronizar.
- `job_verificar_cancelaciones_ml()` (L16777) — Job que corre cada 10 minutos. [tablas: ventas]
- `load_user()` (L136) [tablas: usuarios]
- `ml_request()` (L9358) — Helper para requests a ML con rate limiting global + retry exponencial.
- `normalizar_sku_ml()` (L7589) — Normaliza SKUs de ML que difieren del SKU en la BD.
- `obtener_datos_ml()` (L9271) — Consulta datos actuales de una publicación ML.
- `obtener_datos_ml_batch()` (L9497) — Consulta datos de múltiples publicaciones ML en chunks de 20 (límite de la API).
- `obtener_ordenes_ml()` (L7513) — Obtener órdenes de Mercado Libre
- `obtener_permalinks_ml()` (L9613) — Devuelve permalinks para los MLAs dados.
- `obtener_promos_ml()` (L9444) — Consulta /items/{mla_id}/prices para cada MLA en paralelo y devuelve SOLO los
- `obtener_shipping_completo()` (L7756) — Obtener detalles completos de shipping desde ML
- `obtener_shipping_details()` (L7543) — Obtener detalles del envío desde ML
- `obtener_stock_disponible()` (L1027) — Obtiene el stock disponible de un producto según su tipo y ubicación. [tablas: productos_base]
- `parsear_filtro_multi()` (L217) — Convierte un valor de filtro recibido por GET en una lista limpia de valores.
- `pausar_publicacion_ml()` (L4325) — Pausar una publicación en Mercado Libre
- `procesar_orden_ml()` (L7633) — Procesar orden de ML SIN obtener detalles de shipping
- `provincia_a_codigo()` (L5236) — Convierte nombre de provincia a código AFIP, sin importar tildes/mayúsculas
- `query_db()` (L191) — Ejecutar query SELECT y retornar resultados
- `query_one()` (L201) — Ejecutar query SELECT y retornar un solo resultado
- `quitar_handling_time_ml()` (L8146) — Quitar el tiempo de disponibilidad (handling_time) en ML
- `quitar_manufacturing_time_ml()` (L12395) — Elimina completamente el MANUFACTURING_TIME de una publicación ML.
- `refrescar_catalogo_mla()` (L19007) — Rearma mla_catalogo preguntándole a ML en qué producto de catálogo está
- `refresh_ml_token()` (L7421) — Renovar el access_token usando el refresh_token guardado en DB [tablas: configuracion]
- `sync_payway_intentos()` (L18770) — Trae operaciones de Payway y las upsertea en payway_intentos.
- `vendedor_required()` (L151) — Admin y vendedor pueden acceder. Solo viewer no puede.
- `verificar_sku_en_bd()` (L8070) — Verificar si un SKU existe en la base de datos [tablas: productos_base, productos_compuestos]
- `verificar_stock_disponible()` (L965) — Verifica si hay stock suficiente para todos los items de una venta. [tablas: componentes, productos_base, productos_compuestos]
- `zero_dash()` (L44) — Convierte 0 en '-' para el dashboard visual

### `tienda_bp.py`

- `_aplicar_extra_hot()` (L2632) — Calcula el descuento efectivo aplicando el extra del evento HOT:
- `_aviso_interno_aprobacion()` (L7864) — Mail al equipo cuando ClearSale aprueba: la venta que habia entrado
- `_aviso_interno_rechazo()` (L7936) — Mail al equipo. Hay dos cosas que el sistema NO puede hacer solo y
- `_capi_phone()` (L6108)
- `_capi_sha256()` (L6103)
- `_capturar_origen_server()` (L52) — Captura server-side del origen (fbclid/gclid/utm/referrer externo) apenas
- `_carrito_solo_almohadas()` (L3942) — True si en el carrito no hay nada que no sea una almohada.
- `_cod_provincia_cs()` (L6311) — Provincia -> código de 2 letras para CyberSource.
- `_crear_tabla_suscriptores()` (L8232) — Crea la tabla suscriptores si no existe.
- `_cs_avisar_veredicto()` (L7846) — Avisos del veredicto de ClearSale. Corre en un hilo aparte porque
- `_cs_log()` (L7668) — Imprime SIEMPRE, además de loguear. La app no configura logging, así
- `_descontar_stock()` (L9288) — Fallback público (compatibilidad). Abre su propia conexión.
- `_descontar_stock_fallback()` (L9303) — Descuenta stock buscando SKU por título (cuando no hay external_reference). [tablas: productos_base]
- `_descontar_stock_por_sku()` (L9276) — Descuenta stock usando los SKUs reales del carrito. [tablas: productos_base]
- `_email_estado_pago()` (L7614)
- `_enviar_email_bienvenida()` (L8267) — Envía el cupón de bienvenida al suscriptor.
- `_es_cp_caba()` (L3948) — CABA va del 1000 al 1499. Acepta el formato 'C1407AAB' además del numérico.
- `_factura_fields()` (L5303) — (doc_type, doc_number, taxpayer_type) para las columnas factura_* de ventas.
- `_fecha_nacimiento_valida()` (L3880) — Normaliza la fecha de nacimiento del titular, o '' si no es creíble.
- `_feed_construir()` (L9646) — Arma el feed replicando la misma lógica de publicación que la home. [tablas: conjunto_configuracion, ofertas_home, productos_base, productos_compuestos]
- `_feed_item()` (L9585) — Arma un <item> del feed, o None si el producto no es publicable.
- `_feed_nombre_archivo()` (L9390) — SKU -> nombre de archivo de la imagen. 'SEX140+2' -> 'SEX140_2'.
- `_feed_vencida()` (L9477) — True si hay que (re)generar: no existe, o la foto original es más nueva.
- `_filtro_ahorro_total()` (L96) — Cuánto se ahorra contra el precio de lista, ya con el cupón del evento
- `_filtro_con_cupon()` (L122) — Precio con el cupon del evento aplicado, ya formateado.
- `_filtro_lleva_cupon()` (L150) — True si al SKU le corre el cupón del evento. Para las plantillas, que
- `_filtro_precio_2x1()` (L158) — Precio por unidad llevando dos, formateado. Es el mensaje que reemplaza
- `_flag_activo()` (L2382) — Lee un flag on/off de configuracion. Default OFF. [tablas: configuracion]
- `_fraude_gate()` (L6198) — Devuelve (bloqueado, motivo). Reglas: [tablas: pedidos_pendientes]
- `_fraude_norm()` (L6090) — Normaliza para comparar: minúsculas, sin tildes, espacios colapsados.
- `_fraude_registrar_bloqueo()` (L6293) — Registra un bloqueo del gate en fraude_bloqueos (para verlo en /intentos-pago).
- `_get_nl_config()` (L8254) — Lee monto y mínimo del cupón newsletter desde la tabla configuracion. [tablas: configuracion]
- `_get_stock_real()` (L2673) — Stock real para cualquier SKU — maneja sommiers (busca colchon+base). [tablas: conjunto_configuracion, productos_base]
- `_getnet_get_token()` (L7020) — Obtiene access_token de GetNet (OAuth2 client_credentials) con cache.
- `_importe_total_venta()` (L5312) — Total numérico de una venta por numero_venta (para el evento purchase del dataLayer). 0 si no existe. [tablas: ventas]
- `_mail_interno()` (L7880) — Mail al equipo con el encabezado y los datos de la venta. Lo comparten
- `_premium_orden_medida()` (L3293) — '140x190' → 140, para ordenar las medidas de menor a mayor.
- `_shipping_unificado()` (L3970) — Lee el flag global 'shipping_unificado_zipnova' de configuracion. [tablas: configuracion]
- `_tipo_envio_sku()` (L3986) — Devuelve 'almohada', 'me2' o 'zipnova' según el SKU.
- `_track_args()` (L47) — Query params de tracking presentes en la request (para no perderlos en 301).
- `_validar_cuit()` (L5288) — Valida un CUIT/CUIL argentino: 11 dígitos + dígito verificador (módulo 11).
- `_wa_estado_pago()` (L7593)
- `_wa_normalizar()` (L7549) — A formato internacional sin '+', como lo pide la Cloud API.
- `_zipnova_auth()` (L4757)
- `aplica_demora()` (L2697) — Retorna True si este producto puede mostrar demora en vez de sin-stock.
- `aplicar_veredicto_clearsale()` (L7743) — Asienta un estado de ClearSale sobre una venta y actúa en consecuencia. [tablas: ventas]
- `armar_bultos_zipnova()` (L4761) — Dado el carrito, arma la lista de paquetes para Zipnova. [tablas: componentes, productos_base, productos_compuestos]
- `avisar_estado_pago()` (L7567) — Manda el aviso de estado por mail y WhatsApp. Cada canal va en su
- `calc_cuotas()` (L2299) — Devuelve dict con info de cuotas para mostrar en detalle del producto.
- `calc_cuotas_producto()` (L2402) — calc_cuotas para la página de producto: la de '3 cuotas' usa el MENOR
- `calcular_fecha_demora()` (L2706) — Retorna la fecha de disponibilidad como string DD/MM/YYYY.
- `calculate_package_dimensions()` (L4703) — Calcula dimensiones totales para ME2. Retorna string LxWxH,grams para MP.
- `cupon_aplica_sku()` (L3839) — True si el cupón del evento alcanza a este SKU. Falso en almohadas.
- `descuento_cupon()` (L3851) — Descuento del cupón en pesos, contando solo los productos elegibles.
- `enviar_capi_purchase()` (L6118) — Envía Purchase a la Meta CAPI. No bloquea ni lanza: corre en thread daemon.
- `enviar_email_confirmacion()` (L7988) — Envía email de confirmación al cliente cuando se aprueba el pago.
- `enviar_email_vendedor()` (L8123) — Notifica al vendedor cuando entra una venta nueva.
- `envio_gratis_caba()` (L3922) — Durante el evento, los envios a CABA van sin cargo para todo el
- `factor_cupon_sku()` (L3863) — Factor a aplicar al precio unitario de un item por efecto del cupón.
- `feed_fotos_origen()` (L9395) — Rutas absolutas de las fotos de un SKU, en orden, con la misma regla que [tablas: productos_fotos]
- `feed_normalizar_imagen()` (L9435) — Normaliza una foto a FEED_IMG_LADO² sobre blanco. Sin deformar ni recortar.
- `feed_preparar_imagenes()` (L9487) — Deja las imágenes de catálogo del SKU al día y devuelve sus URLs.
- `feed_regenerar_todas()` (L9551) — Normaliza las imágenes nuevas y las que cambiaron. Idempotente.
- `feed_skus_publicados()` (L9531) — SKU que la tienda publica hoy. Mismos criterios que la home y el feed. [tablas: productos_base, productos_compuestos]
- `flete_almohadas_caba()` (L3954) — Tarifa plana para carritos de solo almohadas con destino CABA. [tablas: configuracion]
- `format_price()` (L2197) — Formatea precio como $424.000
- `get_coef_12()` (L2247) — Coeficiente de recargo para 12 cuotas (MercadoPago). Default 1.6. [tablas: configuracion]
- `get_coef_3_payway()` (L2349) — Coeficiente de 3 cuotas de Payway. En los días de promo es 1.0 (sin interés real).
- `get_coef_6_payway()` (L2225) — Coeficiente de 6 cuotas de PAYWAY, separado del de GetNet. [tablas: configuracion]
- `get_coef_mp3()` (L2273) — Coeficiente de recargo para 3 cuotas MercadoPago. Default 1.18. [tablas: configuracion]
- `get_coeficientes_cuotas()` (L2205) — Lee coeficientes de cuotas desde configuracion. Defaults: 1.11 (3c) y 1.22 (6c). [tablas: configuracion]
- `get_db()` (L208)
- `get_demora_sin_stock()` (L2509) — Retorna los días de demora configurados para productos sin stock (0 si está desactivado). [tablas: configuracion]
- `get_dimensions()` (L4690) — Retorna dict con length, width, height (cm) y weight (kg). Solo para SKUs que van por ME2.
- `get_foto_url()` (L2502) — Retorna URL de la foto principal (primera disponible).
- `get_fotos_producto()` (L2445) — Devuelve las fotos de la tienda para un SKU. [tablas: productos_fotos]
- `get_hot_event()` (L2523) — Lee el flag del evento promocional desde la tabla configuracion. [tablas: configuracion]
- `get_mp_sdk()` (L220)
- `get_mp_sdk_test()` (L225) — SDK de Mercado Pago en modo PRUEBA (sandbox).
- `get_patas_sommier()` (L4678) — Retorna cantidad de patas según medida del sommier.
- `get_plaza()` (L2191)
- `get_shipping_info()` (L4717) — Clasifica el carrito:
- `get_stock_disponible_sku()` (L2713) — Stock disponible = (stock_actual + stock_full) - vendido en ventas pendientes. [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `getnet_activo()` (L2394)
- `hay_3cuotas_activo()` (L2377) — True si hay algún medio de 3 cuotas activo (Payway o MercadoPago 3).
- `inject_hot_event()` (L176) — Evento y promo 2x1, disponibles en todos los templates de la tienda.
- `inject_nl_popup_desc()` (L85) — Inyecta nl_popup_desc en todos los templates de la tienda.
- `inject_now()` (L79)
- `inject_promo_3sin()` (L191) — Promo bancaria de 3 cuotas sin interés (miércoles y sábado) para los templates.
- `job_clearsale_respaldo()` (L7677) — Red de seguridad por si un webhook se pierde: consulta a ClearSale el [tablas: ventas]
- `modo_promo_activa()` (L3725) — Resuelve un interruptor de promo de tres estados. [tablas: configuracion]
- `mp_12_cuotas_activo()` (L2261) — True si el medio 'MercadoPago 12 cuotas' está activo (flag en configuracion). [tablas: configuracion]
- `mp_3_cuotas_activo()` (L2287) — True si el medio 'MercadoPago 3 cuotas' está activo (flag en configuracion). [tablas: configuracion]
- `payway_6_activo()` (L2398)
- `payway_cuotas_activo()` (L2362) — True si el medio 'Payway 3 cuotas' está activo (default ON, siempre se mostró). [tablas: configuracion]
- `precio_2x1_por_unidad()` (L3908) — Precio por unidad llevando dos, cuando el 2x1 está activo.
- `precio_efectivo_item()` (L3797) — Precio unitario ya con el 2x1 repartido entre las unidades.
- `promo_2x1_activa()` (L3775) — 2x1 en almohadas. Tiene clave propia para poder correrla fuera de un
- `promo_3sin_activa()` (L2311) — True si hoy corre la promo bancaria de 3 cuotas SIN INTERÉS por Payway. [tablas: configuracion]
- `sku_colchon_a_conjunto()` (L2432) — CEX140 → SEX140, CDO80 → SDO80, etc.
- `sku_conjunto_a_colchon()` (L2438) — SEX140 → CEX140, SEXP100+1 → CEXP100 (limpia sufijo +N)
- `slugify()` (L199) — Convierte 'Colchón Cannon Tropical 80x190cm' → 'colchon-cannon-tropical-80x190cm'
- `subtotal_carrito()` (L3815) — Subtotal del carrito, YA con el 2x1 aplicado si está activo.
- `subtotal_elegible_cupon()` (L3844) — Parte del subtotal sobre la que corre el cupón (sin almohadas).
- `unidades_bonificadas()` (L3781) — Cuántas unidades van gratis por el 2x1. Agrupa por SKU: 2 Platino dan
- `zipnova_cotizar()` (L4958) — Llama a Zipnova API para cotizar. Retorna lista de opciones.
- `zipnova_crear_envio()` (L4984) — Crea el envío en Zipnova post-pago. Retorna dict con id y tracking o None.
