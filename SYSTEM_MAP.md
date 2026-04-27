# 📘 SYSTEM_MAP — Mapa del Sistema Cannon

Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**

---

## 🌐 Rutas HTTP — 164 endpoints

### `app.py`

#### `GET /` 🔒
- **Función:** `index()` (línea 262)
- **Descripción:** Dashboard principal
- **Templates:** `dashboard.html`
- **Tablas:** `ventas`

#### `GET /admin/logs` 🔒
- **Función:** `admin_logs()` (línea 12612)
- **Templates:** `admin_logs.html`

#### `GET /agencia` 🔒
- **Función:** `agencia_dashboard()` (línea 12439)
- **Templates:** `agencia.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /alertas` 🔒
- **Función:** `alertas_ml()` (línea 3148)
- **Descripción:** Ver alertas de stock pendientes con info de publicaciones ML (normales y con Z)
- **Templates:** `alertas.html`

#### `POST /alertas/<int:alerta_id>/configurar-demora-ml` 🔒
- **Función:** `configurar_demora_ml_desde_alerta()` (línea 6508)
- **Descripción:** Configurar días de demora en las publicaciones CON Z

#### `POST /alertas/<int:alerta_id>/procesar` 🔒
- **Función:** `marcar_alerta_procesada()` (línea 3190)
- **Descripción:** Marcar una alerta como procesada

#### `POST /alertas/<int:alerta_id>/sincronizar-ml` 🔒
- **Función:** `sincronizar_ml_desde_alerta()` (línea 3054)
- **Descripción:** Poner stock en 0 en las publicaciones NORMALES (sin Z)

#### `POST /alertas/marcar-todas-procesadas` 🔒
- **Función:** `marcar_todas_procesadas()` (línea 3206)
- **Descripción:** Marcar TODAS las alertas pendientes como procesadas

#### `GET /api/productos` 🔒
- **Función:** `api_productos()` (línea 4384)
- **Descripción:** API para el buscador de productos en templates
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /auditoria-ml` 🔒
- **Función:** `auditoria_ml()` (línea 9071)
- **Descripción:** Renderiza la página de auditoría. Los datos se cargan vía AJAX por sección.
- **Templates:** `auditoria_ml.html`

#### `POST /auditoria-ml/activar` 🔒
- **Función:** `auditoria_activar_publicaciones()` (línea 9211)
- **Descripción:** Activar (despausar) publicaciones seleccionadas. Devuelve JSON.

#### `POST /auditoria-ml/bajar-cero` 🔒
- **Función:** `auditoria_bajar_cero()` (línea 9315)
- **Descripción:** Bajar stock a 0 en publicaciones seleccionadas. Para sección stock_en_ml.

#### `POST /auditoria-ml/cargar-stock` 🔒
- **Función:** `auditoria_cargar_stock()` (línea 9247)
- **Descripción:** Cargar stock en publicaciones seleccionadas. Devuelve JSON.

#### `POST /auditoria-ml/poner-demora` 🔒
- **Función:** `auditoria_poner_demora()` (línea 9345)
- **Descripción:** Poner X días de demora en publicaciones Z seleccionadas. Para sección stock_en_ml.

#### `POST /auditoria-ml/reducir-demora` 🔒
- **Función:** `auditoria_reducir_demora()` (línea 9285)
- **Descripción:** Quitar demora completamente en publicaciones seleccionadas. Devuelve JSON.

#### `GET /auditoria-ml/run/<tipo>` 🔒
- **Función:** `auditoria_ml_run()` (línea 9084)
- **Descripción:** Ejecuta un tipo específico de auditoría y devuelve JSON con los resultados.

#### `GET /bajar-stock` 🔒
- **Función:** `bajar_stock()` (línea 4585)
- **Descripción:** Formulario para dar de baja stock
- **Templates:** `bajar_stock.html`
- **Tablas:** `productos_base`

#### `POST /bajar-stock-cero-masivo` 🔒
- **Función:** `bajar_stock_cero_masivo()` (línea 8419)
- **Descripción:** Poner stock en 0 en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /bajar-stock-mla-cero` 🔒
- **Función:** `bajar_stock_mla_cero()` (línea 8386)
- **Descripción:** Poner stock en 0 en una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /bajar-stock/guardar` 🔒
- **Función:** `bajar_stock_guardar()` (línea 4610)
- **Descripción:** Guardar bajas de stock - acepta form o JSON
- **Tablas:** `productos_base`

#### `POST /buscar-sku-ml` 🔒
- **Función:** `buscar_sku_ml()` (línea 7812)
- **Templates:** `cargar_stock_ml.html`, `cargar_stock_ml.html`, `cargar_stock_ml.html`, `cargar_stock_ml.html`
- **Tablas:** `configuracion`

#### `POST /cambiar-precio-masivo` 🔒
- **Función:** `cambiar_precio_masivo()` (línea 8179)
- **Descripción:** Cambiar el precio de todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /cambiar-precio-mla` 🔒
- **Función:** `cambiar_precio_mla()` (línea 8127)
- **Descripción:** Cambiar el precio de una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /cambiar-precios-individuales` 🔒
- **Función:** `cambiar_precios_individuales()` (línea 8238)
- **Descripción:** Actualizar precios individuales de múltiples MLAs de una vez
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-demora-masivo` 🔒
- **Función:** `cargar_demora_masivo()` (línea 8499)
- **Descripción:** Poner X días de MANUFACTURING_TIME en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-demora-mla` 🔒
- **Función:** `cargar_demora_mla()` (línea 8459)
- **Descripción:** Poner X días de MANUFACTURING_TIME en una publicación
- **Templates:** `cargar_stock_ml.html`

#### `GET, POST /cargar-stock` 🔒
- **Función:** `cargar_stock()` (línea 4416)
- **Descripción:** Formulario para cargar/agregar stock de productos
- **Templates:** `cargar_stock.html`
- **Tablas:** `productos_base`

#### `POST /cargar-stock-masivo` 🔒
- **Función:** `cargar_stock_masivo()` (línea 8845)
- **Descripción:** Cargar el mismo stock en todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `GET /cargar-stock-ml` 🔒
- **Función:** `cargar_stock_ml()` (línea 7602)
- **Descripción:** Mostrar página para cargar stock en ML
- **Templates:** `cargar_stock_ml.html`
- **Tablas:** `configuracion`

#### `POST /cargar-stock-mla` 🔒
- **Función:** `cargar_stock_mla()` (línea 8758)
- **Descripción:** Cargar stock en una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `POST /cargar-stock/guardar` 🔒
- **Función:** `guardar_stock()` (línea 4510)
- **Descripción:** Agregar stock (SUMA al stock actual) y registrar movimientos
- **Tablas:** `productos_base`

#### `GET /configuracion/porcentajes-ml` 🔒
- **Función:** `get_porcentajes_ml()` (línea 433)
- **Descripción:** Retorna los porcentajes de ML guardados en DB
- **Tablas:** `configuracion`

#### `POST /configuracion/porcentajes-ml` 🔒
- **Función:** `guardar_porcentajes_ml()` (línea 445)
- **Descripción:** Guarda los porcentajes de ML en DB
- **Tablas:** `configuracion`

#### `GET /configuracion/resetear` 🔒
- **Función:** `resetear_sistema()` (línea 5642)
- **Descripción:** Página para resetear el sistema (requiere contraseña)
- **Templates:** `resetear_sistema.html`

#### `POST /configuracion/resetear/ejecutar` 🔒
- **Función:** `ejecutar_reseteo()` (línea 5649)
- **Descripción:** Ejecutar reseteo completo del sistema
- **Tablas:** `items_venta`, `productos_base`, `ventas`

#### `GET /costos` 🔓
- **Función:** `costos_index()` (línea 12890)
- **Descripción:** Calculadora de precios — vista principal.
- **Templates:** `costos.html`
- **Tablas:** `configuracion`

#### `POST /costos/aplicar` 🔓
- **Función:** `costos_aplicar()` (línea 13414)
- **Descripción:** Aplica precios calculados a productos_base.
- **Tablas:** `productos_base`

#### `GET /costos/calcular` 🔓
- **Función:** `costos_calcular()` (línea 13141)
- **Descripción:** Tabla de precios calculados con opción de aplicar a productos_base.
- **Templates:** `costos_calcular.html`
- **Tablas:** `configuracion`, `conjunto_configuracion`, `productos_base`

#### `GET, POST /costos/descuentos` 🔓
- **Función:** `costos_descuentos()` (línea 12933)
- **Descripción:** Configurar descuentos por modelo, prontopago y multiplicador.
- **Templates:** `costos_descuentos.html`

#### `GET, POST /costos/envio` 🔓
- **Función:** `costos_envio()` (línea 13045)
- **Descripción:** Gestionar costos de envío colecta/flex por SKU.
- **Templates:** `costos_envio.html`
- **Tablas:** `productos_base`

#### `GET /costos/envio/barrido-ml` 🔓
- **Función:** `costos_envio_barrido_ml()` (línea 13082)
- **Descripción:** Consulta costos de colecta ML para los SKUs de barrido y compara con lo guardado.

#### `GET, POST /costos/importar` 🔓
- **Función:** `costos_importar()` (línea 12960)
- **Descripción:** Subir Excel de lista de precios Cannon.
- **Templates:** `costos_importar.html`

#### `GET, POST /costos/productos` 🔓
- **Función:** `costos_productos()` (línea 13007)
- **Descripción:** Ver/editar SKU de productos Cannon y descuentos adicionales.
- **Templates:** `costos_productos.html`

#### `GET /cotizador-envio` 🔒
- **Función:** `cotizador_envio()` (línea 14058)
- **Descripción:** Página del cotizador de envíos Zipnova.
- **Templates:** `cotizador_envio.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /cotizador-envio/cotizar` 🔒
- **Función:** `cotizador_cotizar()` (línea 14084)
- **Descripción:** AJAX: cotiza envío Zipnova para los SKUs indicados.

#### `GET /cotizador-envio/localidades` 🔒
- **Función:** `cotizador_localidades()` (línea 14074)
- **Descripción:** Devuelve localidades para un CP dado.

#### `GET /dashboard-visual` 🔒
- **Función:** `dashboard_visual()` (línea 5454)
- **Descripción:** Dashboard visual - Stock Físico y Ventas Activas con lógica de bases grandes
- **Templates:** `dashboard_visual.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /debug-mla` 🔒
- **Función:** `debug_mla()` (línea 9907)

#### `GET /debug-token-temp` 🔒
- **Función:** `debug_token_temp()` (línea 8056)

#### `GET /debug/ml/<orden_id>` 🔒
- **Función:** `debug_ml_orden()` (línea 7450)
- **Descripción:** Ver qué datos trae ML de una orden

#### `GET /estadisticas` 🔒
- **Función:** `estadisticas()` (línea 9385)
- **Templates:** `estadisticas.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /estadisticas/exportar-reposicion` 🔒
- **Función:** `exportar_reposicion()` (línea 9536)
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /faltantes-catalogo-ml` 🔒
- **Función:** `faltantes_catalogo_ml()` (línea 7943)
- **Templates:** `faltantes_catalogo_ml.html`, `faltantes_catalogo_ml.html`
- **Tablas:** `configuracion`

#### `GET /fletes` 🔒
- **Función:** `fletes()` (línea 10255)
- **Templates:** `fletes.html`

#### `POST /fletes/guardar` 🔒
- **Función:** `fletes_guardar()` (línea 10300)

#### `GET /historial-stock` 🔒
- **Función:** `historial_stock()` (línea 4677)
- **Descripción:** Ver historial de movimientos de stock
- **Templates:** `historial_stock.html`

#### `GET, POST /login` 🔓
- **Función:** `login()` (línea 235)
- **Templates:** `login.html`
- **Tablas:** `usuarios`

#### `GET /logout` 🔒
- **Función:** `logout()` (línea 254)

#### `GET /ml/callback` 🔒
- **Función:** `ml_callback()` (línea 9930)
- **Descripción:** Recibe el code de ML y lo canjea automáticamente por el token

#### `GET /nueva-venta` 🔒
- **Función:** `nueva_venta()` (línea 4956)
- **Descripción:** Formulario para registrar venta con stock disponible y ubicaciones
- **Templates:** `nueva_venta.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /nueva-venta/guardar` 🔒
- **Función:** `guardar_venta()` (línea 5159)
- **Descripción:** Guardar venta SIN descontar stock (solo registra la venta)
- **Tablas:** `items_venta`, `ventas`

#### `GET /pagos-cannon` 🔒
- **Función:** `pagos_cannon()` (línea 10114)
- **Templates:** `pagos_cannon.html`

#### `POST /pagos-cannon/guardar` 🔒
- **Función:** `pagos_cannon_guardar()` (línea 10174)

#### `GET /productos` 🔓
- **Función:** `productos_lista()` (línea 13491)
- **Templates:** `productos_lista.html`
- **Tablas:** `configuracion`, `conjunto_configuracion`, `productos_base`, `productos_compuestos`, `productos_fotos`

#### `GET /productos/<sku>/fotos` 🔓
- **Función:** `productos_fotos()` (línea 13730)
- **Templates:** `productos_fotos.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /productos/<sku>/fotos/eliminar` 🔓
- **Función:** `productos_fotos_eliminar()` (línea 13793)
- **Tablas:** `productos_fotos`

#### `POST /productos/<sku>/fotos/reordenar` 🔓
- **Función:** `productos_fotos_reordenar()` (línea 13815)
- **Tablas:** `productos_fotos`

#### `POST /productos/<sku>/fotos/subir` 🔓
- **Función:** `productos_fotos_subir()` (línea 13747)
- **Tablas:** `productos_fotos`

#### `POST /productos/cuotas-coeficientes` 🔓
- **Función:** `productos_cuotas_coeficientes()` (línea 13681)
- **Tablas:** `configuracion`

#### `POST /productos/demora` 🔓
- **Función:** `productos_demora_guardar()` (línea 13640)
- **Tablas:** `configuracion`

#### `GET, POST /productos/editar/<sku>` 🔓
- **Función:** `productos_editar()` (línea 13881)
- **Templates:** `productos_form.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /productos/newsletter-cupon` 🔓
- **Función:** `productos_newsletter_cupon()` (línea 13658)
- **Tablas:** `configuracion`

#### `GET, POST /productos/nuevo` 🔓
- **Función:** `productos_nuevo()` (línea 13829)
- **Templates:** `productos_form.html`, `productos_form.html`, `productos_form.html`
- **Tablas:** `productos_base`

#### `POST /productos/toggle/<sku>` 🔓
- **Función:** `productos_toggle()` (línea 13705)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /publicar-catalogo-cuota` 🔒
- **Función:** `publicar_catalogo_cuota()` (línea 8063)

#### `POST /quitar-demora-masivo` 🔒
- **Función:** `quitar_demora_masivo()` (línea 8680)
- **Descripción:** Eliminar MANUFACTURING_TIME de todas las publicaciones de un SKU
- **Templates:** `cargar_stock_ml.html`

#### `POST /quitar-demora-mla` 🔒
- **Función:** `quitar_demora_mla()` (línea 8611)
- **Descripción:** Eliminar MANUFACTURING_TIME de una publicación específica
- **Templates:** `cargar_stock_ml.html`

#### `GET /stock` 🔒
- **Función:** `ver_stock()` (línea 3220)
- **Descripción:** Ver stock disponible con filtros - PRODUCTOS BASE + COMBOS
- **Templates:** `stock.html`
- **Tablas:** `componentes`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /test/manufacturing-time` 🔒
- **Función:** `test_manufacturing_time()` (línea 9714)
- **Descripción:** Página de prueba para ver y modificar el MANUFACTURING_TIME
- **Templates:** `test_manufacturing_time.html`

#### `POST /test/manufacturing-time/poner` 🔒
- **Función:** `poner_manufacturing_time()` (línea 9842)
- **Descripción:** Pone o restaura el MANUFACTURING_TIME a un valor específico.

#### `POST /test/manufacturing-time/quitar` 🔒
- **Función:** `quitar_manufacturing_time()` (línea 9773)
- **Descripción:** Elimina el MANUFACTURING_TIME de una publicación enviando null.

#### `POST /test/manufacturing-time/ver` 🔒
- **Función:** `ver_manufacturing_time()` (línea 9724)
- **Descripción:** Consulta el estado actual de una publicación:

#### `GET /tienda-admin/cupones` 🔒
- **Función:** `tienda_cupones()` (línea 11272)
- **Templates:** `tienda_cupones.html`
- **Tablas:** `cupones`, `cupones_uso`, `suscriptores`

#### `POST /tienda-admin/cupones/guardar` 🔒
- **Función:** `tienda_cupones_guardar()` (línea 11324)
- **Tablas:** `cupones`

#### `GET /tienda-admin/ofertas` 🔒
- **Función:** `tienda_ofertas()` (línea 10854)
- **Templates:** `tienda_ofertas.html`
- **Tablas:** `ofertas_home`, `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/ofertas/guardar` 🔒
- **Función:** `tienda_ofertas_guardar()` (línea 10874)
- **Tablas:** `ofertas_home`

#### `GET /tienda-admin/precios` 🔓
- **Función:** `tienda_precios()` (línea 10735)
- **Templates:** `tienda_precios.html`
- **Tablas:** `conjunto_configuracion`, `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/precios/descuento` 🔓
- **Función:** `tienda_precios_descuento()` (línea 10821)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/precios/guardar` 🔓
- **Función:** `tienda_precios_guardar()` (línea 10792)
- **Tablas:** `productos_base`, `productos_compuestos`

#### `POST /tienda-admin/suscriptores/eliminar` 🔒
- **Función:** `tienda_suscriptores_eliminar()` (línea 11356)
- **Tablas:** `suscriptores`

#### `GET /transferir-stock` 🔒
- **Función:** `transferir_stock()` (línea 4753)
- **Descripción:** Formulario para transferir stock de Depósito a Full (Compac y Almohadas)
- **Templates:** `transferir_stock.html`
- **Tablas:** `productos_base`

#### `POST /transferir-stock/guardar` 🔒
- **Función:** `transferir_stock_guardar()` (línea 4788)
- **Descripción:** Procesar transferencia de stock de Depósito a Full (Compac y Almohadas)
- **Tablas:** `productos_base`

#### `GET /ventas/<int:venta_id>/nota-pedido` 🔒
- **Función:** `nota_pedido_pdf()` (línea 10906)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/<int:venta_id>/papel-azul` 🔒
- **Función:** `papel_azul_pdf()` (línea 11085)
- **Descripción:** Genera el papel azul de despacho para ventas Flex o Flete Propio.
- **Tablas:** `conjunto_configuracion`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/activas` 🔒
- **Función:** `ventas_activas()` (línea 755)
- **Descripción:** Lista de ventas activas con filtros de búsqueda
- **Templates:** `ventas_activas.html`
- **Tablas:** `configuracion`, `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/cancelar` 🔒
- **Función:** `cancelar_venta()` (línea 1552)
- **Descripción:** Cancelar venta (NO descuenta stock)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/eliminar` 🔒
- **Función:** `eliminar_venta()` (línea 1608)
- **Descripción:** Eliminar venta completamente de la base de datos
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/entregada` 🔒
- **Función:** `marcar_entregada()` (línea 1475)
- **Descripción:** Marcar venta como entregada (descuenta stock si no se descontó, con verificación)
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/activas/<int:venta_id>/etiqueta-ml` 🔒
- **Función:** `etiqueta_ml()` (línea 967)
- **Descripción:** Descarga etiqueta de envío ML (PDF o ZPL) para una venta.
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/activas/<int:venta_id>/orden-retiro` 🔒
- **Función:** `orden_retiro_pdf()` (línea 1139)
- **Descripción:** Generar PDF de orden de retiro (2 copias: cliente + archivo)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/proceso` 🔒
- **Función:** `pasar_a_proceso()` (línea 1401)
- **Descripción:** Pasar venta a proceso de envío (descuenta stock con verificación)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/<int:venta_id>/whatsapp-enviar` 🔒
- **Función:** `whatsapp_enviar()` (línea 885)
- **Descripción:** Envía mensaje de WhatsApp al cliente de una venta activa.
- **Tablas:** `ventas`

#### `POST /ventas/activas/cancelar-multiple` 🔒
- **Función:** `cancelar_ventas_multiple()` (línea 1883)
- **Descripción:** Cancelar múltiples ventas
- **Tablas:** `ventas`

#### `GET /ventas/activas/exportar-excel` 🔒
- **Función:** `exportar_ventas_activas_excel()` (línea 687)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/activas/marcar-entregadas-multiple` 🔒
- **Función:** `marcar_entregadas_multiple()` (línea 1778)
- **Descripción:** Marcar múltiples ventas como entregadas
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/activas/pasar-proceso-multiple` 🔒
- **Función:** `pasar_a_proceso_multiple()` (línea 1677)
- **Descripción:** Pasar múltiples ventas a proceso de envío
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/auto-import-toggle` 🔒
- **Función:** `auto_import_toggle()` (línea 12034)
- **Tablas:** `configuracion`

#### `GET, POST /ventas/editar/<int:venta_id>` 🔒
- **Función:** `editar_venta()` (línea 2497)
- **Descripción:** Editar una venta activa
- **Templates:** `editar_venta.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/etiquetas-ml-masivo` 🔒
- **Función:** `etiquetas_ml_masivo()` (línea 1048)
- **Descripción:** Descarga etiquetas ML para múltiples ventas en un solo ZPL/PDF.
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/guardar-trid` 🔒
- **Función:** `guardar_trid()` (línea 9982)
- **Descripción:** Guardar o actualizar el TRID (código de tracking Correo Argentino) en notas
- **Tablas:** `ventas`

#### `GET /ventas/historicas` 🔒
- **Función:** `ventas_historicas()` (línea 3427)
- **Descripción:** Lista de ventas históricas (entregadas y canceladas) con filtros
- **Templates:** `ventas_historicas.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/historicas/<int:venta_id>/generar-factura-excel` 🔒
- **Función:** `generar_factura_excel()` (línea 3846)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/historicas/<int:venta_id>/volver_activas` 🔒
- **Función:** `historicas_volver_activas()` (línea 3580)
- **Descripción:** Volver venta histórica (entregada o cancelada) a ventas activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/historicas/facturar-multiple` 🔒
- **Función:** `facturar_multiple()` (línea 4177)
- **Descripción:** Generar UN SOLO archivo .txt con TODAS las ventas seleccionadas
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /ventas/historicas/facturar-multiple-excel` 🔒
- **Función:** `facturar_multiple_excel()` (línea 3987)
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/historicas/volver-activas-multiple` 🔒
- **Función:** `historicas_volver_activas_multiple()` (línea 3654)
- **Descripción:** Volver múltiples ventas históricas a ventas activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /ventas/ml-progress` 🔒
- **Función:** `ml_progress()` (línea 12291)

#### `GET, POST /ventas/ml/configurar_token` 🔒
- **Función:** `ml_configurar_token()` (línea 6607)
- **Descripción:** Página para configurar/actualizar el token de ML
- **Templates:** `ml_configurar_token.html`

#### `GET /ventas/ml/importar` 🔒
- **Función:** `ml_importar_ordenes()` (línea 6731)
- **Descripción:** Traer órdenes de ML - FILTRO ARREGLADO
- **Templates:** `ml_importar_ordenes.html`
- **Tablas:** `ventas`

#### `POST /ventas/ml/mapear` 🔒
- **Función:** `ml_guardar_mapeo()` (línea 6968)
- **Descripción:** Guardar mapeo - Obtiene shipping completo y billing info

#### `GET /ventas/ml/seleccionar/<orden_id>` 🔒
- **Función:** `ml_seleccionar_orden()` (línea 6839)
- **Descripción:** Seleccionar orden - Con normalización automática de SKU (quita Z)
- **Templates:** `ml_mapear_productos.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /ventas/nueva/ml` 🔒
- **Función:** `nueva_venta_desde_ml()` (línea 7068)
- **Descripción:** Crear nueva venta con datos precargados desde ML
- **Templates:** `nueva_venta_ml.html`
- **Tablas:** `productos_base`, `productos_compuestos`

#### `GET /ventas/nuevas-count` 🔒
- **Función:** `ventas_nuevas_count()` (línea 12299)
- **Tablas:** `auto_import_log`

#### `POST /ventas/nuevas-reset` 🔒
- **Función:** `ventas_nuevas_reset()` (línea 12310)
- **Tablas:** `auto_import_log`

#### `GET /ventas/proceso` 🔒
- **Función:** `ventas_proceso()` (línea 1959)
- **Descripción:** Lista de ventas en proceso de envío con filtros
- **Templates:** `proceso_envio.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /ventas/proceso/<int:venta_id>/cancelar` 🔒
- **Función:** `proceso_cancelar_devolver()` (línea 2173)
- **Descripción:** Cancelar venta en proceso y DEVOLVER stock descontado (con motivo opcional)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/<int:venta_id>/entregada` 🔒
- **Función:** `proceso_marcar_entregada()` (línea 2129)
- **Descripción:** Marcar venta en proceso como entregada (stock ya descontado)
- **Tablas:** `ventas`

#### `POST /ventas/proceso/<int:venta_id>/volver_activas` 🔒
- **Función:** `proceso_volver_activas()` (línea 2078)
- **Descripción:** Volver venta de proceso a activas (devuelve stock)
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/cancelar-multiple` 🔒
- **Función:** `proceso_cancelar_multiple()` (línea 2402)
- **Descripción:** Cancelar múltiples ventas en proceso y DEVOLVER stock
- **Tablas:** `items_venta`, `ventas`

#### `POST /ventas/proceso/marcar-entregadas-multiple` 🔒
- **Función:** `proceso_marcar_entregadas_multiple()` (línea 2329)
- **Descripción:** Marcar múltiples ventas en proceso como entregadas
- **Tablas:** `ventas`

#### `POST /ventas/proceso/volver-activas-multiple` 🔒
- **Función:** `proceso_volver_activas_multiple()` (línea 2249)
- **Descripción:** Volver múltiples ventas en proceso a activas
- **Tablas:** `items_venta`, `ventas`

#### `GET /viajes` 🔒
- **Función:** `viajes_lista()` (línea 10553)
- **Templates:** `viajes.html`
- **Tablas:** `viajes`

#### `GET /viajes/<int:viaje_id>` 🔒
- **Función:** `viaje_detalle()` (línea 10599)
- **Templates:** `viaje_detalle.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`, `viajes`

#### `POST /viajes/guardar` 🔒
- **Función:** `viajes_guardar()` (línea 10659)
- **Tablas:** `viajes`

#### `GET /viajes/nuevo` 🔒
- **Función:** `viaje_nuevo()` (línea 10569)
- **Templates:** `viaje_form.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

### `tienda_bp.py`

#### `GET /` 🔓
- **Función:** `home()` (línea 2214)
- **Templates:** `tienda/home.html`
- **Tablas:** `conjunto_configuracion`, `items_venta`, `ofertas_home`, `productos_base`, `productos_compuestos`, `ventas`

#### `GET /carrito` 🔓
- **Función:** `ver_carrito()` (línea 3289)
- **Templates:** `tienda/carrito.html`
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /carrito/actualizar` 🔓
- **Función:** `actualizar_carrito()` (línea 3163)
- **Descripción:** Cambia la cantidad de un item (solo almohadas). delta = +1 o -1.
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /carrito/agregar` 🔓
- **Función:** `agregar_carrito()` (línea 3019)
- **Tablas:** `conjunto_configuracion`, `productos_base`, `productos_compuestos`

#### `POST /carrito/eliminar` 🔓
- **Función:** `eliminar_carrito()` (línea 3425)

#### `POST /carrito/quitar-cupon` 🔓
- **Función:** `quitar_cupon()` (línea 3418)

#### `POST /carrito/vaciar` 🔓
- **Función:** `vaciar_carrito()` (línea 3281)

#### `POST /carrito/validar-cupon` 🔓
- **Función:** `validar_cupon()` (línea 3354)
- **Tablas:** `cupones`, `cupones_uso`

#### `POST /checkout` 🔓
- **Función:** `checkout()` (línea 4115)
- **Templates:** `tienda/checkout_bricks.html`
- **Tablas:** `configuracion`, `pedidos_pendientes`

#### `POST /cotizar-envio` 🔓
- **Función:** `cotizar_envio()` (línea 3940)
- **Descripción:** AJAX: cotiza envío Zipnova para el carrito actual.

#### `GET /datos-envio` 🔓
- **Función:** `datos_envio()` (línea 4059)
- **Descripción:** Pantalla de datos del cliente antes de ir a MP.
- **Templates:** `tienda/datos_envio.html`

#### `GET /devoluciones` 🔓
- **Función:** `devoluciones()` (línea 6385)
- **Templates:** `tienda/devoluciones.html`

#### `GET /localidades` 🔓
- **Función:** `localidades()` (línea 3927)
- **Descripción:** Devuelve lista de localidades para un CP dado, usando dict estático.

#### `POST /pago/ejecutar` 🔓
- **Función:** `pago_ejecutar()` (línea 4401)
- **Descripción:** Endpoint para Checkout Bricks (Opción A).

#### `GET /pago/error` 🔓
- **Función:** `pago_error()` (línea 5120)
- **Templates:** `tienda/pago_error.html`

#### `GET /pago/exito` 🔓
- **Función:** `pago_exito()` (línea 5023)
- **Templates:** `tienda/pago_exito.html`, `tienda/pago_exito_getnet.html`
- **Tablas:** `items_venta`, `productos_base`, `productos_compuestos`, `ventas`

#### `POST /pago/getnet/crear` 🔓
- **Función:** `pago_getnet_crear()` (línea 4916)
- **Descripción:** PROVISORIO: crea un payment-intent en GetNet (digital-checkout) y devuelve
- **Tablas:** `pedidos_pendientes`

#### `POST /pago/getnet/webhook` 🔓
- **Función:** `getnet_webhook()` (línea 5015)
- **Descripción:** PROVISORIO: solo loggea el payload, no registra venta.

#### `POST /pago/payway` 🔓
- **Función:** `pago_payway()` (línea 4506)
- **Descripción:** Recibe token de Payway JS SDK + cuotas elegidas.
- **Tablas:** `cupones`, `cupones_uso`, `items_venta`, `pedidos_pendientes`, `ventas`

#### `POST /pago/payway/token` 🔓
- **Función:** `payway_token()` (línea 4478)
- **Descripción:** Proxy de tokenizacion para Payway.

#### `GET /pago/pendiente` 🔓
- **Función:** `pago_pendiente()` (línea 5085)
- **Descripción:** Con tarjeta de crédito, MP redirige acá con status=in_process.
- **Templates:** `tienda/pago_pendiente.html`

#### `GET /privacidad` 🔓
- **Función:** `privacidad()` (línea 6380)
- **Templates:** `tienda/privacidad.html`

#### `GET /producto/<sku_url>` 🔓
- **Función:** `detalle()` (línea 2691)
- **Templates:** `tienda/detalle.html`, `tienda/detalle.html`
- **Tablas:** `conjunto_configuracion`, `ofertas_home`, `productos_base`, `productos_compuestos`

#### `GET /seguimiento` 🔓
- **Función:** `seguimiento()` (línea 6257)
- **Descripción:** El cliente ingresa su número de venta (MP-XXXXXXX) o payment_id.
- **Templates:** `tienda/seguimiento.html`
- **Tablas:** `items_venta`, `productos_base`, `ventas`

#### `GET /sitemap.xml` 🔓
- **Función:** `sitemap()` (línea 6209)
- **Tablas:** `conjunto_configuracion`, `productos_base`

#### `POST /suscribirse` 🔓
- **Función:** `suscribirse()` (línea 5454)
- **Descripción:** Registra el email, genera un cupón único y envía el mail de bienvenida.
- **Tablas:** `cupones`, `suscriptores`

#### `GET /verificar-pago` 🔓
- **Función:** `verificar_pago()` (línea 5101)
- **Descripción:** API JSON: consulta el estado real de un pago en MP. Usado por el auto-refresh.

#### `POST /webhook/getnet` 🔓
- **Función:** `webhook_getnet()` (línea 5905)
- **Descripción:** Recibe notificaciones de GetNet cuando el pago es aprobado.
- **Tablas:** `cupones`, `cupones_uso`, `items_venta`, `pedidos_pendientes`, `ventas`

#### `POST /webhook/mp` 🔓
- **Función:** `webhook_mp()` (línea 5504)
- **Descripción:** Recibe notificaciones de MP.
- **Tablas:** `cupones`, `cupones_uso`, `items_venta`, `pedidos_pendientes`, `ventas`

---

## 🔧 Helpers (sin ruta HTTP) — 109 funciones

### `app.py`

- `_aplica_logica_z()` (L11383) — Determina si aplica lógica Z (demora) para un SKU.
- `_armar_bultos_cotizador()` (L13957) — Dado una lista de SKUs, arma los bultos para cotizar en Zipnova. [tablas: componentes, productos_base, productos_compuestos]
- `_build_precio_costos_map()` (L12827) — Construye un mapa sku → precio_lista_costos para mostrar en tienda_precios. [tablas: conjunto_configuracion]
- `_calcular_carga_viaje()` (L10449) — Calcula si los productos del viaje entran en las zonas del vehículo. [tablas: componentes, items_venta, productos_base, productos_compuestos, viajes]
- `_calcular_importe_pp()` (L10105) — Calcula importe con pronto pago. Ej: 5% → total/1.05, redondeado sin decimales.
- `_calcular_precio_lista()` (L12808) — precio_lista = precio_cannon
- `_crear_tablas_fletes()` (L10035)
- `_crear_tablas_pagos_cannon()` (L10061)
- `_crear_tablas_productos()` (L13444) — Tabla de fotos y columnas opcionales en productos_base. Solo corre una vez por proceso.
- `_es_almohada()` (L11378)
- `_es_compac()` (L11374)
- `_extraer_skus_base_de_items()` (L11541) — Dado una lista de items [{sku, cantidad}], devuelve el set de SKUs base [tablas: componentes, productos_base, productos_compuestos]
- `_ga4_query()` (L12409) — Consulta la GA4 Data API y retorna rows.
- `_get_config_costos()` (L12803) — Retorna dict con todos los descuentos y multiplicador desde DB.
- `_get_fotos()` (L13480) — Devuelve lista de filenames ordenados para un SKU. [tablas: productos_fotos]
- `_get_precio_costos_sku()` (L12676) — Retorna el precio calculado por costos para un SKU dado. [tablas: configuracion, conjunto_configuracion]
- `_importar_orden_automatica()` (L11590) — Importa automáticamente una orden de ML sin intervención del usuario. [tablas: items_venta, ventas]
- `_init_auto_import_table()` (L11565) [tablas: auto_import_log]
- `_ml_progress_get()` (L12150) — Lee el progreso desde la BD. [tablas: configuracion]
- `_ml_progress_save()` (L12137) — Guarda el progreso en la BD para que sea compartido entre workers. [tablas: configuracion]
- `_pack_zona()` (L10341) — Algoritmo de carga para objetos planos (colchones, bases, sommiers).
- `_poner_demora_ml()` (L11417) — Poner demora de manufacturing_time en una publi ML.
- `_quitar_demora_ml()` (L11429) — Quitar demora de manufacturing_time en una publi ML.
- `_recargar_publicaciones()` (L8310) — Helper: devuelve lista de publicaciones.
- `_zipnova_auth_adm()` (L13953)
- `actualizar_handling_time_ml()` (L6355) — Actualizar el tiempo de disponibilidad (handling_time) en ML
- `actualizar_publicaciones_ml()` (L11435) — Dado un set de SKUs base que cambiaron disponible, actualiza en ML [tablas: componentes, productos_base, productos_compuestos]
- `actualizar_publicaciones_ml_con_progreso()` (L12162) — Corre la actualización de ML guardando progreso en BD (compartido entre workers). [tablas: componentes, productos_base, productos_compuestos]
- `actualizar_stock_compac_dep_ml()` (L12051) — Actualiza el stock selling_address (DEP) en ML para todas las publicaciones
- `actualizar_stock_ml()` (L2973) — Actualizar stock de una publicación en Mercado Libre
- `admin_required()` (L94)
- `agencia_only()` (L113) — Solo agencia puede acceder — redirige a /agencia si intenta acceder a otra ruta.
- `calcular_stock_por_sku()` (L8961) — Calcula stock disponible para todos los SKUs (base + combos). [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `cargar_ml_token()` (L5785) — Cargar token ML desde la base de datos. Si está vencido, lo renueva. [tablas: configuracion]
- `debug_orden_ml_completa()` (L7110) — Ver TODOS los datos que trae ML de una orden
- `decimal_to_float()` (L4938) — Convertir Decimals a float para JSON serialization
- `descontar_stock_item()` (L2867) — Descuenta stock de un item considerando: [tablas: componentes, productos_base, productos_compuestos]
- `descontar_stock_simple()` (L2908) — Descuenta stock de un producto simple según ubicación y registra en movimientos_stock [tablas: productos_base]
- `detectar_alertas_stock_bajo()` (L465) — Detecta productos con stock disponible <= 0. [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `devolver_stock_item()` (L2748) — Devuelve stock de un item (lo opuesto a descontar_stock_item) [tablas: componentes, productos_base, productos_compuestos]
- `devolver_stock_simple()` (L2790) — Devuelve stock de un producto simple según ubicación (SUMA en lugar de RESTAR) [tablas: productos_base]
- `enviar_whatsapp()` (L173) — Envía un mensaje de WhatsApp usando una plantilla aprobada por Meta.
- `execute_db()` (L158) — Ejecutar query INSERT/UPDATE/DELETE
- `extraer_billing_info_ml()` (L7370) — Extraer datos de facturación del formato de ML
- `get_db_connection()` (L139) — Crear conexión a la base de datos
- `guardar_ml_token()` (L5803) — Guardar token ML en la base de datos (persiste en Railway) [tablas: configuracion]
- `iniciar_scheduler()` (L12549)
- `inject_alertas_pendientes()` (L58) — Inyecta el contador de alertas en todos los templates
- `job_auto_importar_ml()` (L11894) — Job que corre cada 60 segundos. [tablas: auto_import_log, configuracion, ventas]
- `job_completar_notas_mp()` (L12319) — Job que corre cada 10 minutos. [tablas: ventas]
- `job_verificar_cancelaciones_ml()` (L11976) — Job que corre cada 10 minutos. [tablas: ventas]
- `load_user()` (L88) [tablas: usuarios]
- `ml_request()` (L7624) — Helper para requests a ML con rate limiting global + retry exponencial.
- `normalizar_sku_ml()` (L5882) — Normaliza SKUs de ML que difieren del SKU en la BD.
- `obtener_datos_ml()` (L7541) — Consulta datos actuales de una publicación ML.
- `obtener_datos_ml_batch()` (L7666) — Consulta datos de múltiples publicaciones ML en chunks de 20 (límite de la API).
- `obtener_ordenes_ml()` (L5831) — Obtener órdenes de Mercado Libre
- `obtener_permalinks_ml()` (L7764) — Devuelve permalinks para los MLAs dados.
- `obtener_shipping_completo()` (L6036) — Obtener detalles completos de shipping desde ML
- `obtener_shipping_details()` (L5861) — Obtener detalles del envío desde ML
- `obtener_stock_disponible()` (L358) — Obtiene el stock disponible de un producto según su tipo y ubicación. [tablas: productos_base]
- `pausar_publicacion_ml()` (L3013) — Pausar una publicación en Mercado Libre
- `procesar_orden_ml()` (L5913) — Procesar orden de ML SIN obtener detalles de shipping
- `provincia_a_codigo()` (L3785) — Convierte nombre de provincia a código AFIP, sin importar tildes/mayúsculas
- `query_db()` (L143) — Ejecutar query SELECT y retornar resultados
- `query_one()` (L153) — Ejecutar query SELECT y retornar un solo resultado
- `quitar_handling_time_ml()` (L6412) — Quitar el tiempo de disponibilidad (handling_time) en ML
- `quitar_manufacturing_time_ml()` (L8551) — Elimina completamente el MANUFACTURING_TIME de una publicación ML.
- `refresh_ml_token()` (L5739) — Renovar el access_token usando el refresh_token guardado en DB [tablas: configuracion]
- `vendedor_required()` (L103) — Admin y vendedor pueden acceder. Solo viewer no puede.
- `verificar_sku_en_bd()` (L6336) — Verificar si un SKU existe en la base de datos [tablas: productos_base, productos_compuestos]
- `verificar_stock_disponible()` (L296) — Verifica si hay stock suficiente para todos los items de una venta. [tablas: componentes, productos_base, productos_compuestos]
- `zero_dash()` (L44) — Convierte 0 en '-' para el dashboard visual

### `tienda_bp.py`

- `_crear_tabla_suscriptores()` (L5347) — Crea la tabla suscriptores si no existe.
- `_descontar_stock()` (L6161) — Fallback público (compatibilidad). Abre su propia conexión.
- `_descontar_stock_fallback()` (L6176) — Descuenta stock buscando SKU por título (cuando no hay external_reference). [tablas: productos_base]
- `_descontar_stock_por_sku()` (L6149) — Descuenta stock usando los SKUs reales del carrito. [tablas: productos_base]
- `_enviar_email_bienvenida()` (L5382) — Envía el cupón de bienvenida al suscriptor.
- `_get_nl_config()` (L5369) — Lee monto y mínimo del cupón newsletter desde la tabla configuracion. [tablas: configuracion]
- `_get_stock_real()` (L2142) — Stock real para cualquier SKU — maneja sommiers (busca colchon+base). [tablas: conjunto_configuracion, productos_base]
- `_getnet_get_token()` (L4885) — Obtiene access_token de GetNet (OAuth2 client_credentials) con cache.
- `_tipo_envio_sku()` (L3005) — Devuelve 'almohada', 'me2' o 'zipnova' según el SKU.
- `_zipnova_auth()` (L3701)
- `aplica_demora()` (L2166) — Retorna True si este producto puede mostrar demora en vez de sin-stock.
- `armar_bultos_zipnova()` (L3705) — Dado el carrito, arma la lista de paquetes para Zipnova. [tablas: componentes, productos_base, productos_compuestos]
- `calc_cuotas()` (L2068) — Devuelve dict con info de cuotas para mostrar en detalle del producto.
- `calcular_fecha_demora()` (L2175) — Retorna la fecha de disponibilidad como string DD/MM/YYYY.
- `calculate_package_dimensions()` (L3651) — Calcula dimensiones totales para ME2. Retorna string LxWxH,grams para MP.
- `enviar_email_confirmacion()` (L5127) — Envía email de confirmación al cliente cuando se aprueba el pago.
- `enviar_email_vendedor()` (L5262) — Notifica al vendedor cuando entra una venta nueva.
- `format_price()` (L2040) — Formatea precio como $424.000
- `get_coeficientes_cuotas()` (L2048) — Lee coeficientes de cuotas desde configuracion. Defaults: 1.11 (3c) y 1.22 (6c). [tablas: configuracion]
- `get_db()` (L65)
- `get_demora_sin_stock()` (L2130) — Retorna los días de demora configurados para productos sin stock (0 si está desactivado). [tablas: configuracion]
- `get_dimensions()` (L3638) — Retorna dict con length, width, height (cm) y weight (kg). Solo para SKUs que van por ME2.
- `get_foto_url()` (L2123) — Retorna URL de la foto principal (primera disponible).
- `get_fotos_producto()` (L2091) — Busca fotos en /static/img/productos/<SKU>/
- `get_mp_sdk()` (L77)
- `get_patas_sommier()` (L3626) — Retorna cantidad de patas según medida del sommier.
- `get_plaza()` (L2034)
- `get_shipping_info()` (L3665) — Clasifica el carrito:
- `get_stock_disponible_sku()` (L2182) — Stock disponible = (stock_actual + stock_full) - vendido en ventas pendientes. [tablas: componentes, items_venta, productos_base, productos_compuestos, ventas]
- `inject_nl_popup_desc()` (L46) — Inyecta nl_popup_desc en todos los templates de la tienda.
- `inject_now()` (L40)
- `sku_colchon_a_conjunto()` (L2078) — CEX140 → SEX140, CDO80 → SDO80, etc.
- `sku_conjunto_a_colchon()` (L2084) — SEX140 → CEX140, SEXP100+1 → CEXP100 (limpia sufijo +N)
- `slugify()` (L56) — Convierte 'Colchón Cannon Tropical 80x190cm' → 'colchon-cannon-tropical-80x190cm'
- `zipnova_cotizar()` (L3850) — Llama a Zipnova API para cotizar. Retorna lista de opciones.
- `zipnova_crear_envio()` (L3876) — Crea el envío en Zipnova post-pago. Retorna dict con id y tracking o None.
