# 🗄️ DB_MAP — Mapa de la Base de Datos

Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**

Cada tabla muestra las funciones que la **leen** (R) o **modifican** (W).

---

## `ventas`
_Ventas (cabecera): número, cliente, total, estado, canal, método envío_

**✏️ Modifican (35):**
- `_importar_orden_automatica()` (app.py:L16220)
- `_rechequear_orden_ml()` (app.py:L17249)
- `aplicar_veredicto_clearsale()` (tienda_bp.py:L7743)
- `cancelar_venta()` (app.py:L2682)
- `cancelar_ventas_multiple()` (app.py:L3106)
- `editar_venta()` (app.py:L3772)
- `ejecutar_reseteo()` (app.py:L7331)
- `eliminar_venta()` (app.py:L2779)
- `facturar_multiple()` (app.py:L5632)
- `facturar_multiple_excel()` (app.py:L5438)
- `generar_factura_excel()` (app.py:L5297)
- `guardar_trid()` (app.py:L13948)
- `guardar_venta()` (app.py:L6813)
- `historicas_marcar_entregado_ml()` (app.py:L5053)
- `historicas_volver_activas()` (app.py:L4978)
- `historicas_volver_activas_multiple()` (app.py:L5105)
- `job_completar_notas_mp()` (app.py:L17163)
- `job_rechequear_autoimportadas()` (app.py:L17436)
- `job_verificar_cancelaciones_ml()` (app.py:L16777)
- `marcar_entregada()` (app.py:L2595)
- `marcar_entregadas_multiple()` (app.py:L2977)
- `pago_payway()` (tienda_bp.py:L6372)
- `pasar_a_proceso()` (app.py:L2504)
- `pasar_a_proceso_multiple()` (app.py:L2853)
- `proceso_cancelar_devolver()` (app.py:L3425)
- `proceso_cancelar_multiple()` (app.py:L3677)
- `proceso_marcar_entregada()` (app.py:L3370)
- `proceso_marcar_entregadas_multiple()` (app.py:L3581)
- `proceso_volver_activas()` (app.py:L3319)
- `proceso_volver_activas_multiple()` (app.py:L3501)
- `quitar_demora_venta()` (app.py:L2740)
- `rentabilidad_editar_costo()` (app.py:L20015)
- `rentabilidad_recalcular_costos()` (app.py:L19951)
- `webhook_getnet()` (tienda_bp.py:L8884)
- `webhook_mp()` (tienda_bp.py:L8406)

**👁️ Leen (35):**
- `_importe_total_venta()` (tienda_bp.py:L5312)
- `_job_auto_importar_ml_inner()` (app.py:L16690)
- `agencia_dashboard()` (app.py:L17583)
- `calcular_stock_por_sku()` (app.py:L12833)
- `dashboard_visual()` (app.py:L7133)
- `detectar_alertas_stock_bajo()` (app.py:L1197)
- `estadisticas()` (app.py:L13257)
- `etiqueta_ml()` (app.py:L1738)
- `etiquetas_ml_masivo()` (app.py:L1819)
- `exportar_reposicion()` (app.py:L13481)
- `exportar_ventas_activas_excel()` (app.py:L1419)
- `get_stock_disponible_sku()` (tienda_bp.py:L2713)
- `home()` (tienda_bp.py:L2745)
- `index()` (app.py:L801)
- `intentos_pago()` (app.py:L18808)
- `intentos_pago_blocklist_add()` (app.py:L18900)
- `job_clearsale_respaldo()` (tienda_bp.py:L7677)
- `ml_importar_ordenes()` (app.py:L8465)
- `nota_pedido_pdf()` (app.py:L15161)
- `nueva_venta()` (app.py:L6589)
- `orden_retiro_pdf()` (app.py:L1914)
- `pago_exito()` (tienda_bp.py:L7299)
- `pago_exito_getnet()` (tienda_bp.py:L7264)
- `papel_azul_pdf()` (app.py:L15379)
- `remito_conforme_pdf()` (app.py:L2233)
- `rentabilidad()` (app.py:L19782)
- `seguimiento()` (tienda_bp.py:L9882)
- `ventas_activas()` (app.py:L1495)
- `ventas_historicas()` (app.py:L4774)
- `ventas_proceso()` (app.py:L3206)
- `ver_stock()` (app.py:L4567)
- `viaje_detalle()` (app.py:L14854)
- `viaje_nuevo()` (app.py:L14824)
- `webhook_clearsale()` (tienda_bp.py:L10594)
- `whatsapp_enviar()` (app.py:L1656)

## `items_venta`
_Detalle de productos vendidos en cada venta_

**✏️ Modifican (9):**
- `_importar_orden_automatica()` (app.py:L16220)
- `_rechequear_orden_ml()` (app.py:L17249)
- `editar_venta()` (app.py:L3772)
- `ejecutar_reseteo()` (app.py:L7331)
- `eliminar_venta()` (app.py:L2779)
- `guardar_venta()` (app.py:L6813)
- `pago_payway()` (tienda_bp.py:L6372)
- `webhook_getnet()` (tienda_bp.py:L8884)
- `webhook_mp()` (tienda_bp.py:L8406)

**👁️ Leen (43):**
- `_calcular_carga_viaje()` (app.py:L14704)
- `agencia_dashboard()` (app.py:L17583)
- `calcular_stock_por_sku()` (app.py:L12833)
- `cancelar_venta()` (app.py:L2682)
- `cancelar_ventas_multiple()` (app.py:L3106)
- `dashboard_visual()` (app.py:L7133)
- `detectar_alertas_stock_bajo()` (app.py:L1197)
- `estadisticas()` (app.py:L13257)
- `etiqueta_ml()` (app.py:L1738)
- `etiquetas_ml_masivo()` (app.py:L1819)
- `exportar_reposicion()` (app.py:L13481)
- `exportar_ventas_activas_excel()` (app.py:L1419)
- `facturar_multiple()` (app.py:L5632)
- `facturar_multiple_excel()` (app.py:L5438)
- `generar_factura_excel()` (app.py:L5297)
- `get_stock_disponible_sku()` (tienda_bp.py:L2713)
- `historicas_volver_activas()` (app.py:L4978)
- `historicas_volver_activas_multiple()` (app.py:L5105)
- `home()` (tienda_bp.py:L2745)
- `index()` (app.py:L801)
- `marcar_entregada()` (app.py:L2595)
- `marcar_entregadas_multiple()` (app.py:L2977)
- `nota_pedido_pdf()` (app.py:L15161)
- `nueva_venta()` (app.py:L6589)
- `orden_retiro_pdf()` (app.py:L1914)
- `pago_exito()` (tienda_bp.py:L7299)
- `papel_azul_pdf()` (app.py:L15379)
- `pasar_a_proceso()` (app.py:L2504)
- `pasar_a_proceso_multiple()` (app.py:L2853)
- `proceso_cancelar_devolver()` (app.py:L3425)
- `proceso_cancelar_multiple()` (app.py:L3677)
- `proceso_volver_activas()` (app.py:L3319)
- `proceso_volver_activas_multiple()` (app.py:L3501)
- `remito_conforme_pdf()` (app.py:L2233)
- `rentabilidad()` (app.py:L19782)
- `rentabilidad_recalcular_costos()` (app.py:L19951)
- `seguimiento()` (tienda_bp.py:L9882)
- `ventas_activas()` (app.py:L1495)
- `ventas_historicas()` (app.py:L4774)
- `ventas_proceso()` (app.py:L3206)
- `ver_stock()` (app.py:L4567)
- `viaje_detalle()` (app.py:L14854)
- `viaje_nuevo()` (app.py:L14824)

## `productos_base`
_Productos individuales (colchones, almohadas, bases): SKU, precio, stock, dimensiones_

**✏️ Modifican (15):**
- `_descontar_stock_fallback()` (tienda_bp.py:L9303)
- `_descontar_stock_por_sku()` (tienda_bp.py:L9276)
- `bajar_stock_guardar()` (app.py:L6243)
- `cargar_stock()` (app.py:L5871)
- `costos_aplicar()` (app.py:L21207)
- `descontar_stock_simple()` (app.py:L4220)
- `devolver_stock_simple()` (app.py:L4102)
- `ejecutar_reseteo()` (app.py:L7331)
- `guardar_stock()` (app.py:L6143)
- `productos_editar()` (app.py:L21861)
- `productos_nuevo()` (app.py:L21809)
- `productos_toggle()` (app.py:L21685)
- `tienda_precios_descuento()` (app.py:L15076)
- `tienda_precios_guardar()` (app.py:L15047)
- `transferir_stock_guardar()` (app.py:L6421)

**👁️ Leen (68):**
- `_armar_bultos_cotizador()` (app.py:L21937)
- `_calcular_carga_viaje()` (app.py:L14704)
- `_costos_map()` (app.py:L9675)
- `_extraer_skus_base_de_items()` (app.py:L16142)
- `_feed_construir()` (tienda_bp.py:L9646)
- `_get_stock_real()` (tienda_bp.py:L2673)
- `_importar_orden_automatica()` (app.py:L16220)
- `_sku_ml_existe()` (app.py:L7567)
- `actualizar_carrito()` (tienda_bp.py:L4155)
- `actualizar_publicaciones_ml()` (app.py:L16017)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L16970)
- `agencia_dashboard()` (app.py:L17583)
- `agregar_carrito()` (tienda_bp.py:L4003)
- `api_productos()` (app.py:L5839)
- `armar_bultos_zipnova()` (tienda_bp.py:L4761)
- `bajar_stock()` (app.py:L6218)
- `calcular_stock_por_sku()` (app.py:L12833)
- `costos_calcular()` (app.py:L20822)
- `costos_envio()` (app.py:L20724)
- `cotizador_envio()` (app.py:L22038)
- `dashboard_visual()` (app.py:L7133)
- `descontar_stock_item()` (app.py:L4179)
- `detalle()` (tienda_bp.py:L3400)
- `detectar_alertas_stock_bajo()` (app.py:L1197)
- `devolver_stock_item()` (app.py:L4060)
- `editar_venta()` (app.py:L3772)
- `escanear_remito()` (app.py:L5966)
- `estadisticas()` (app.py:L13257)
- `exportar_reposicion()` (app.py:L13481)
- `exportar_ventas_activas_excel()` (app.py:L1419)
- `facturar_multiple()` (app.py:L5632)
- `facturar_multiple_excel()` (app.py:L5438)
- `feed_skus_publicados()` (tienda_bp.py:L9531)
- `generar_factura_excel()` (app.py:L5297)
- `get_stock_disponible_sku()` (tienda_bp.py:L2713)
- `home()` (tienda_bp.py:L2745)
- `index()` (app.py:L801)
- `ml_seleccionar_orden()` (app.py:L8566)
- `nota_pedido_pdf()` (app.py:L15161)
- `nueva_venta()` (app.py:L6589)
- `nueva_venta_desde_ml()` (app.py:L8798)
- `obtener_stock_disponible()` (app.py:L1027)
- `orden_retiro_pdf()` (app.py:L1914)
- `pago_exito()` (tienda_bp.py:L7299)
- `papel_azul_pdf()` (app.py:L15379)
- `premium()` (tienda_bp.py:L3302)
- `productos_fotos()` (app.py:L21710)
- `productos_lista()` (app.py:L21284)
- `registrar_mapeo_remito()` (app.py:L6118)
- `remito_conforme_pdf()` (app.py:L2233)
- `rentabilidad()` (app.py:L19782)
- `rentabilidad_recalcular_costos()` (app.py:L19951)
- `seguimiento()` (tienda_bp.py:L9882)
- `sitemap()` (tienda_bp.py:L9834)
- `test_getnet()` (tienda_bp.py:L10045)
- `test_mp()` (tienda_bp.py:L10145)
- `tienda_ofertas()` (app.py:L15109)
- `tienda_precios()` (app.py:L14990)
- `transferir_stock()` (app.py:L6386)
- `ventas_activas()` (app.py:L1495)
- `ventas_historicas()` (app.py:L4774)
- `ventas_proceso()` (app.py:L3206)
- `ver_carrito()` (tienda_bp.py:L4292)
- `ver_stock()` (app.py:L4567)
- `verificar_sku_en_bd()` (app.py:L8070)
- `verificar_stock_disponible()` (app.py:L965)
- `viaje_detalle()` (app.py:L14854)
- `viaje_nuevo()` (app.py:L14824)

## `productos_compuestos`
_Productos armados (sommiers): SKU, nombre, activo_

**✏️ Modifican (4):**
- `productos_editar()` (app.py:L21861)
- `productos_toggle()` (app.py:L21685)
- `tienda_precios_descuento()` (app.py:L15076)
- `tienda_precios_guardar()` (app.py:L15047)

**👁️ Leen (54):**
- `_armar_bultos_cotizador()` (app.py:L21937)
- `_calcular_carga_viaje()` (app.py:L14704)
- `_costos_map()` (app.py:L9675)
- `_extraer_skus_base_de_items()` (app.py:L16142)
- `_feed_construir()` (tienda_bp.py:L9646)
- `_importar_orden_automatica()` (app.py:L16220)
- `_sku_ml_existe()` (app.py:L7567)
- `actualizar_publicaciones_ml()` (app.py:L16017)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L16970)
- `agencia_dashboard()` (app.py:L17583)
- `agregar_carrito()` (tienda_bp.py:L4003)
- `api_productos()` (app.py:L5839)
- `armar_bultos_zipnova()` (tienda_bp.py:L4761)
- `calcular_stock_por_sku()` (app.py:L12833)
- `cotizador_envio()` (app.py:L22038)
- `dashboard_visual()` (app.py:L7133)
- `descontar_stock_item()` (app.py:L4179)
- `detalle()` (tienda_bp.py:L3400)
- `detectar_alertas_stock_bajo()` (app.py:L1197)
- `devolver_stock_item()` (app.py:L4060)
- `editar_venta()` (app.py:L3772)
- `estadisticas()` (app.py:L13257)
- `exportar_reposicion()` (app.py:L13481)
- `exportar_ventas_activas_excel()` (app.py:L1419)
- `facturar_multiple()` (app.py:L5632)
- `facturar_multiple_excel()` (app.py:L5438)
- `feed_skus_publicados()` (tienda_bp.py:L9531)
- `generar_factura_excel()` (app.py:L5297)
- `get_stock_disponible_sku()` (tienda_bp.py:L2713)
- `home()` (tienda_bp.py:L2745)
- `index()` (app.py:L801)
- `ml_seleccionar_orden()` (app.py:L8566)
- `nota_pedido_pdf()` (app.py:L15161)
- `nueva_venta()` (app.py:L6589)
- `nueva_venta_desde_ml()` (app.py:L8798)
- `orden_retiro_pdf()` (app.py:L1914)
- `pago_exito()` (tienda_bp.py:L7299)
- `papel_azul_pdf()` (app.py:L15379)
- `premium()` (tienda_bp.py:L3302)
- `productos_fotos()` (app.py:L21710)
- `productos_lista()` (app.py:L21284)
- `remito_conforme_pdf()` (app.py:L2233)
- `rentabilidad()` (app.py:L19782)
- `rentabilidad_recalcular_costos()` (app.py:L19951)
- `tienda_ofertas()` (app.py:L15109)
- `tienda_precios()` (app.py:L14990)
- `ventas_activas()` (app.py:L1495)
- `ventas_historicas()` (app.py:L4774)
- `ventas_proceso()` (app.py:L3206)
- `ver_stock()` (app.py:L4567)
- `verificar_sku_en_bd()` (app.py:L8070)
- `verificar_stock_disponible()` (app.py:L965)
- `viaje_detalle()` (app.py:L14854)
- `viaje_nuevo()` (app.py:L14824)

## `componentes`
_Relación productos_compuestos ↔ productos_base con cantidades_

**👁️ Leen (20):**
- `_armar_bultos_cotizador()` (app.py:L21937)
- `_calcular_carga_viaje()` (app.py:L14704)
- `_costos_map()` (app.py:L9675)
- `_extraer_skus_base_de_items()` (app.py:L16142)
- `_importar_orden_automatica()` (app.py:L16220)
- `actualizar_publicaciones_ml()` (app.py:L16017)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L16970)
- `armar_bultos_zipnova()` (tienda_bp.py:L4761)
- `calcular_stock_por_sku()` (app.py:L12833)
- `dashboard_visual()` (app.py:L7133)
- `descontar_stock_item()` (app.py:L4179)
- `detectar_alertas_stock_bajo()` (app.py:L1197)
- `devolver_stock_item()` (app.py:L4060)
- `exportar_reposicion()` (app.py:L13481)
- `get_stock_disponible_sku()` (tienda_bp.py:L2713)
- `nueva_venta()` (app.py:L6589)
- `rentabilidad()` (app.py:L19782)
- `rentabilidad_recalcular_costos()` (app.py:L19951)
- `ver_stock()` (app.py:L4567)
- `verificar_stock_disponible()` (app.py:L965)

## `conjunto_configuracion`
_Config de sommiers: colchón + base default + cantidad bases_

**👁️ Leen (15):**
- `_build_precio_costos_map()` (app.py:L19631)
- `_feed_construir()` (tienda_bp.py:L9646)
- `_get_precio_costos_sku()` (app.py:L19403)
- `_get_stock_real()` (tienda_bp.py:L2673)
- `actualizar_carrito()` (tienda_bp.py:L4155)
- `agregar_carrito()` (tienda_bp.py:L4003)
- `costos_calcular()` (app.py:L20822)
- `detalle()` (tienda_bp.py:L3400)
- `home()` (tienda_bp.py:L2745)
- `papel_azul_pdf()` (app.py:L15379)
- `premium()` (tienda_bp.py:L3302)
- `productos_lista()` (app.py:L21284)
- `sitemap()` (tienda_bp.py:L9834)
- `tienda_precios()` (app.py:L14990)
- `ver_carrito()` (tienda_bp.py:L4292)

## `productos_fotos`
_Fotos de productos: SKU, filename, orden_

**✏️ Modifican (2):**
- `productos_fotos_eliminar()` (app.py:L21773)
- `productos_fotos_reordenar()` (app.py:L21795)

**👁️ Leen (5):**
- `_get_fotos()` (app.py:L21273)
- `feed_fotos_origen()` (tienda_bp.py:L9395)
- `get_fotos_producto()` (tienda_bp.py:L2445)
- `productos_fotos_subir()` (app.py:L21727)
- `productos_lista()` (app.py:L21284)

## `usuarios`
_Login del sistema: username, password_hash, rol, activo_

**👁️ Leen (2):**
- `load_user()` (app.py:L136)
- `login()` (app.py:L774)

## `configuracion`
_Configuración general del sistema (key/value): demora_sin_stock, ml_token, etc._

**✏️ Modifican (20):**
- `_faltantes_catalogo_guardar_cache()` (app.py:L11258)
- `_ml_progress_save()` (app.py:L16945)
- `auto_import_toggle()` (app.py:L16835)
- `costos_descuentos()` (app.py:L20547)
- `email_hot_masivo()` (app.py:L15716)
- `enviar_hot_event_a_fallidos()` (app.py:L615)
- `enviar_hot_event_a_todos()` (app.py:L465)
- `guardar_ml_token()` (app.py:L7485)
- `guardar_ml_z_sin_stock()` (app.py:L1168)
- `guardar_porcentajes_ml()` (app.py:L1114)
- `job_catalogo_mla()` (app.py:L19073)
- `preguntas_reglas()` (app.py:L18668)
- `productos_cuotas_coeficientes()` (app.py:L21526)
- `productos_demora_guardar()` (app.py:L21485)
- `productos_evento_guardar()` (app.py:L21595)
- `productos_flete_almohadas()` (app.py:L21570)
- `productos_medio_toggle()` (app.py:L21665)
- `productos_newsletter_cupon()` (app.py:L21503)
- `refresh_ml_token()` (app.py:L7421)
- `rentabilidad_config()` (app.py:L20032)

**👁️ Leen (39):**
- `_build_precio_compra_map()` (app.py:L20096)
- `_build_precio_costos_map()` (app.py:L19631)
- `_flag_activo()` (tienda_bp.py:L2382)
- `_get_ml_z_sin_stock_config()` (app.py:L1136)
- `_get_nl_config()` (tienda_bp.py:L8254)
- `_get_precio_costos_sku()` (app.py:L19403)
- `_importar_orden_automatica()` (app.py:L16220)
- `_job_auto_importar_ml_inner()` (app.py:L16690)
- `_ml_progress_get()` (app.py:L16958)
- `_preguntas_reglas()` (app.py:L18355)
- `_promo_coefs()` (app.py:L9660)
- `_promo_limite_aporte()` (app.py:L10100)
- `_shipping_unificado()` (tienda_bp.py:L3970)
- `buscar_sku_ml()` (app.py:L10908)
- `cargar_ml_token()` (app.py:L7467)
- `cargar_stock_ml()` (app.py:L9332)
- `checkout()` (tienda_bp.py:L5327)
- `costos_calcular()` (app.py:L20822)
- `costos_index()` (app.py:L20051)
- `faltantes_catalogo_ml()` (app.py:L11411)
- `flete_almohadas_caba()` (tienda_bp.py:L3954)
- `get_coef_12()` (tienda_bp.py:L2247)
- `get_coef_6_payway()` (tienda_bp.py:L2225)
- `get_coef_mp3()` (tienda_bp.py:L2273)
- `get_coeficientes_cuotas()` (tienda_bp.py:L2205)
- `get_demora_sin_stock()` (tienda_bp.py:L2509)
- `get_hot_event()` (tienda_bp.py:L2523)
- `get_porcentajes_ml()` (app.py:L1102)
- `job_faltantes_catalogo_ml()` (app.py:L11273)
- `job_promos_rechequeo()` (app.py:L10655)
- `modo_promo_activa()` (tienda_bp.py:L3725)
- `mp_12_cuotas_activo()` (tienda_bp.py:L2261)
- `mp_3_cuotas_activo()` (tienda_bp.py:L2287)
- `payway_cuotas_activo()` (tienda_bp.py:L2362)
- `productos_lista()` (app.py:L21284)
- `promo_3sin_activa()` (tienda_bp.py:L2311)
- `rentabilidad()` (app.py:L19782)
- `ventas_activas()` (app.py:L1495)
- `webhook_mp()` (tienda_bp.py:L8406)

## `cupones`
_Cupones de descuento: código, tipo, valor, mínimo, vencimiento_

**✏️ Modifican (5):**
- `pago_payway()` (tienda_bp.py:L6372)
- `suscribirse()` (tienda_bp.py:L8339)
- `tienda_cupones_guardar()` (app.py:L15618)
- `webhook_getnet()` (tienda_bp.py:L8884)
- `webhook_mp()` (tienda_bp.py:L8406)

**👁️ Leen (4):**
- `test_mp_preparar()` (tienda_bp.py:L10171)
- `tienda_cupones()` (app.py:L15566)
- `tienda_suscriptores_exportar()` (app.py:L15661)
- `validar_cupon()` (tienda_bp.py:L4372)

## `cupones_uso`
_Registro de uso de cupones por email_

**✏️ Modifican (3):**
- `pago_payway()` (tienda_bp.py:L6372)
- `webhook_getnet()` (tienda_bp.py:L8884)
- `webhook_mp()` (tienda_bp.py:L8406)

**👁️ Leen (2):**
- `tienda_cupones()` (app.py:L15566)
- `validar_cupon()` (tienda_bp.py:L4372)

## `suscriptores`
_Suscriptores newsletter: email, cupón asignado_

**✏️ Modifican (2):**
- `suscribirse()` (tienda_bp.py:L8339)
- `tienda_suscriptores_eliminar()` (app.py:L15650)

**👁️ Leen (4):**
- `email_hot_masivo()` (app.py:L15716)
- `enviar_hot_event_a_todos()` (app.py:L465)
- `tienda_cupones()` (app.py:L15566)
- `tienda_suscriptores_exportar()` (app.py:L15661)

## `ofertas_home`
_Ofertas destacadas en home tienda: SKU, descuento, orden_

**✏️ Modifican (1):**
- `tienda_ofertas_guardar()` (app.py:L15129)

**👁️ Leen (4):**
- `_feed_construir()` (tienda_bp.py:L9646)
- `detalle()` (tienda_bp.py:L3400)
- `home()` (tienda_bp.py:L2745)
- `tienda_ofertas()` (app.py:L15109)

## `pedidos_pendientes`
_Pedidos en checkout antes del webhook MP_

**✏️ Modifican (3):**
- `checkout()` (tienda_bp.py:L5327)
- `pago_payway()` (tienda_bp.py:L6372)
- `webhook_mp()` (tienda_bp.py:L8406)

**👁️ Leen (7):**
- `_fraude_gate()` (tienda_bp.py:L6198)
- `intentos_pago()` (app.py:L18808)
- `intentos_pago_blocklist_add()` (app.py:L18900)
- `pago_ejecutar()` (tienda_bp.py:L5821)
- `pago_ejecutar_12()` (tienda_bp.py:L5923)
- `pago_ejecutar_3_mp()` (tienda_bp.py:L6004)
- `pago_getnet_crear()` (tienda_bp.py:L7058)

## `fletes`
_Cobros y pagos a fleteros_

_Sin uso detectado en el código._

## `viajes`
_Hojas de ruta de envíos_

**✏️ Modifican (1):**
- `viajes_guardar()` (app.py:L14914)

**👁️ Leen (3):**
- `_calcular_carga_viaje()` (app.py:L14704)
- `viaje_detalle()` (app.py:L14854)
- `viajes_lista()` (app.py:L14808)

## `auto_import_log`
_Log del job de auto-import ML_

**✏️ Modifican (4):**
- `_init_auto_import_table()` (app.py:L16166)
- `_job_auto_importar_ml_inner()` (app.py:L16690)
- `ml_importar_ordenes()` (app.py:L8465)
- `ventas_nuevas_reset()` (app.py:L17142)

**👁️ Leen (2):**
- `ventas_no_mapeadas_count()` (app.py:L17153)
- `ventas_nuevas_count()` (app.py:L17131)

## `ml_publicaciones`
_Publicaciones de MercadoLibre con su SKU local_

_Sin uso detectado en el código._

## `costos`
_Costos de productos para cálculo de rentabilidad_

_Sin uso detectado en el código._
