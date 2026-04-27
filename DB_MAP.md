# 🗄️ DB_MAP — Mapa de la Base de Datos

Generado automáticamente por `scripts/generar_mapas.py`. **No editar a mano.**

Cada tabla muestra las funciones que la **leen** (R) o **modifican** (W).

---

## `ventas`
_Ventas (cabecera): número, cliente, total, estado, canal, método envío_

**✏️ Modifican (28):**
- `_importar_orden_automatica()` (app.py:L11590)
- `cancelar_venta()` (app.py:L1552)
- `cancelar_ventas_multiple()` (app.py:L1883)
- `editar_venta()` (app.py:L2497)
- `ejecutar_reseteo()` (app.py:L5649)
- `eliminar_venta()` (app.py:L1608)
- `facturar_multiple()` (app.py:L4177)
- `facturar_multiple_excel()` (app.py:L3987)
- `generar_factura_excel()` (app.py:L3846)
- `guardar_trid()` (app.py:L9982)
- `guardar_venta()` (app.py:L5159)
- `historicas_volver_activas()` (app.py:L3580)
- `historicas_volver_activas_multiple()` (app.py:L3654)
- `job_completar_notas_mp()` (app.py:L12319)
- `job_verificar_cancelaciones_ml()` (app.py:L11976)
- `marcar_entregada()` (app.py:L1475)
- `marcar_entregadas_multiple()` (app.py:L1778)
- `pago_payway()` (tienda_bp.py:L4506)
- `pasar_a_proceso()` (app.py:L1401)
- `pasar_a_proceso_multiple()` (app.py:L1677)
- `proceso_cancelar_devolver()` (app.py:L2173)
- `proceso_cancelar_multiple()` (app.py:L2402)
- `proceso_marcar_entregada()` (app.py:L2129)
- `proceso_marcar_entregadas_multiple()` (app.py:L2329)
- `proceso_volver_activas()` (app.py:L2078)
- `proceso_volver_activas_multiple()` (app.py:L2249)
- `webhook_getnet()` (tienda_bp.py:L5905)
- `webhook_mp()` (tienda_bp.py:L5504)

**👁️ Leen (27):**
- `agencia_dashboard()` (app.py:L12439)
- `calcular_stock_por_sku()` (app.py:L8961)
- `dashboard_visual()` (app.py:L5454)
- `detectar_alertas_stock_bajo()` (app.py:L465)
- `estadisticas()` (app.py:L9385)
- `etiqueta_ml()` (app.py:L967)
- `etiquetas_ml_masivo()` (app.py:L1048)
- `exportar_reposicion()` (app.py:L9536)
- `exportar_ventas_activas_excel()` (app.py:L687)
- `get_stock_disponible_sku()` (tienda_bp.py:L2182)
- `home()` (tienda_bp.py:L2214)
- `index()` (app.py:L262)
- `job_auto_importar_ml()` (app.py:L11894)
- `ml_importar_ordenes()` (app.py:L6731)
- `nota_pedido_pdf()` (app.py:L10906)
- `nueva_venta()` (app.py:L4956)
- `orden_retiro_pdf()` (app.py:L1139)
- `pago_exito()` (tienda_bp.py:L5023)
- `papel_azul_pdf()` (app.py:L11085)
- `seguimiento()` (tienda_bp.py:L6257)
- `ventas_activas()` (app.py:L755)
- `ventas_historicas()` (app.py:L3427)
- `ventas_proceso()` (app.py:L1959)
- `ver_stock()` (app.py:L3220)
- `viaje_detalle()` (app.py:L10599)
- `viaje_nuevo()` (app.py:L10569)
- `whatsapp_enviar()` (app.py:L885)

## `items_venta`
_Detalle de productos vendidos en cada venta_

**✏️ Modifican (8):**
- `_importar_orden_automatica()` (app.py:L11590)
- `editar_venta()` (app.py:L2497)
- `ejecutar_reseteo()` (app.py:L5649)
- `eliminar_venta()` (app.py:L1608)
- `guardar_venta()` (app.py:L5159)
- `pago_payway()` (tienda_bp.py:L4506)
- `webhook_getnet()` (tienda_bp.py:L5905)
- `webhook_mp()` (tienda_bp.py:L5504)

**👁️ Leen (38):**
- `_calcular_carga_viaje()` (app.py:L10449)
- `agencia_dashboard()` (app.py:L12439)
- `calcular_stock_por_sku()` (app.py:L8961)
- `cancelar_venta()` (app.py:L1552)
- `dashboard_visual()` (app.py:L5454)
- `detectar_alertas_stock_bajo()` (app.py:L465)
- `estadisticas()` (app.py:L9385)
- `etiqueta_ml()` (app.py:L967)
- `etiquetas_ml_masivo()` (app.py:L1048)
- `exportar_reposicion()` (app.py:L9536)
- `exportar_ventas_activas_excel()` (app.py:L687)
- `facturar_multiple()` (app.py:L4177)
- `facturar_multiple_excel()` (app.py:L3987)
- `generar_factura_excel()` (app.py:L3846)
- `get_stock_disponible_sku()` (tienda_bp.py:L2182)
- `historicas_volver_activas()` (app.py:L3580)
- `historicas_volver_activas_multiple()` (app.py:L3654)
- `home()` (tienda_bp.py:L2214)
- `marcar_entregada()` (app.py:L1475)
- `marcar_entregadas_multiple()` (app.py:L1778)
- `nota_pedido_pdf()` (app.py:L10906)
- `nueva_venta()` (app.py:L4956)
- `orden_retiro_pdf()` (app.py:L1139)
- `pago_exito()` (tienda_bp.py:L5023)
- `papel_azul_pdf()` (app.py:L11085)
- `pasar_a_proceso()` (app.py:L1401)
- `pasar_a_proceso_multiple()` (app.py:L1677)
- `proceso_cancelar_devolver()` (app.py:L2173)
- `proceso_cancelar_multiple()` (app.py:L2402)
- `proceso_volver_activas()` (app.py:L2078)
- `proceso_volver_activas_multiple()` (app.py:L2249)
- `seguimiento()` (tienda_bp.py:L6257)
- `ventas_activas()` (app.py:L755)
- `ventas_historicas()` (app.py:L3427)
- `ventas_proceso()` (app.py:L1959)
- `ver_stock()` (app.py:L3220)
- `viaje_detalle()` (app.py:L10599)
- `viaje_nuevo()` (app.py:L10569)

## `productos_base`
_Productos individuales (colchones, almohadas, bases): SKU, precio, stock, dimensiones_

**✏️ Modifican (15):**
- `_descontar_stock_fallback()` (tienda_bp.py:L6176)
- `_descontar_stock_por_sku()` (tienda_bp.py:L6149)
- `bajar_stock_guardar()` (app.py:L4610)
- `cargar_stock()` (app.py:L4416)
- `costos_aplicar()` (app.py:L13414)
- `descontar_stock_simple()` (app.py:L2908)
- `devolver_stock_simple()` (app.py:L2790)
- `ejecutar_reseteo()` (app.py:L5649)
- `guardar_stock()` (app.py:L4510)
- `productos_editar()` (app.py:L13881)
- `productos_nuevo()` (app.py:L13829)
- `productos_toggle()` (app.py:L13705)
- `tienda_precios_descuento()` (app.py:L10821)
- `tienda_precios_guardar()` (app.py:L10792)
- `transferir_stock_guardar()` (app.py:L4788)

**👁️ Leen (54):**
- `_armar_bultos_cotizador()` (app.py:L13957)
- `_calcular_carga_viaje()` (app.py:L10449)
- `_extraer_skus_base_de_items()` (app.py:L11541)
- `_get_stock_real()` (tienda_bp.py:L2142)
- `actualizar_carrito()` (tienda_bp.py:L3163)
- `actualizar_publicaciones_ml()` (app.py:L11435)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L12162)
- `agencia_dashboard()` (app.py:L12439)
- `agregar_carrito()` (tienda_bp.py:L3019)
- `api_productos()` (app.py:L4384)
- `armar_bultos_zipnova()` (tienda_bp.py:L3705)
- `bajar_stock()` (app.py:L4585)
- `calcular_stock_por_sku()` (app.py:L8961)
- `costos_calcular()` (app.py:L13141)
- `costos_envio()` (app.py:L13045)
- `cotizador_envio()` (app.py:L14058)
- `dashboard_visual()` (app.py:L5454)
- `descontar_stock_item()` (app.py:L2867)
- `detalle()` (tienda_bp.py:L2691)
- `detectar_alertas_stock_bajo()` (app.py:L465)
- `devolver_stock_item()` (app.py:L2748)
- `editar_venta()` (app.py:L2497)
- `estadisticas()` (app.py:L9385)
- `exportar_reposicion()` (app.py:L9536)
- `exportar_ventas_activas_excel()` (app.py:L687)
- `facturar_multiple()` (app.py:L4177)
- `facturar_multiple_excel()` (app.py:L3987)
- `generar_factura_excel()` (app.py:L3846)
- `get_stock_disponible_sku()` (tienda_bp.py:L2182)
- `home()` (tienda_bp.py:L2214)
- `ml_seleccionar_orden()` (app.py:L6839)
- `nota_pedido_pdf()` (app.py:L10906)
- `nueva_venta()` (app.py:L4956)
- `nueva_venta_desde_ml()` (app.py:L7068)
- `obtener_stock_disponible()` (app.py:L358)
- `orden_retiro_pdf()` (app.py:L1139)
- `pago_exito()` (tienda_bp.py:L5023)
- `papel_azul_pdf()` (app.py:L11085)
- `productos_fotos()` (app.py:L13730)
- `productos_lista()` (app.py:L13491)
- `seguimiento()` (tienda_bp.py:L6257)
- `sitemap()` (tienda_bp.py:L6209)
- `tienda_ofertas()` (app.py:L10854)
- `tienda_precios()` (app.py:L10735)
- `transferir_stock()` (app.py:L4753)
- `ventas_activas()` (app.py:L755)
- `ventas_historicas()` (app.py:L3427)
- `ventas_proceso()` (app.py:L1959)
- `ver_carrito()` (tienda_bp.py:L3289)
- `ver_stock()` (app.py:L3220)
- `verificar_sku_en_bd()` (app.py:L6336)
- `verificar_stock_disponible()` (app.py:L296)
- `viaje_detalle()` (app.py:L10599)
- `viaje_nuevo()` (app.py:L10569)

## `productos_compuestos`
_Productos armados (sommiers): SKU, nombre, activo_

**✏️ Modifican (4):**
- `productos_editar()` (app.py:L13881)
- `productos_toggle()` (app.py:L13705)
- `tienda_precios_descuento()` (app.py:L10821)
- `tienda_precios_guardar()` (app.py:L10792)

**👁️ Leen (44):**
- `_armar_bultos_cotizador()` (app.py:L13957)
- `_calcular_carga_viaje()` (app.py:L10449)
- `_extraer_skus_base_de_items()` (app.py:L11541)
- `actualizar_publicaciones_ml()` (app.py:L11435)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L12162)
- `agencia_dashboard()` (app.py:L12439)
- `agregar_carrito()` (tienda_bp.py:L3019)
- `api_productos()` (app.py:L4384)
- `armar_bultos_zipnova()` (tienda_bp.py:L3705)
- `calcular_stock_por_sku()` (app.py:L8961)
- `cotizador_envio()` (app.py:L14058)
- `dashboard_visual()` (app.py:L5454)
- `descontar_stock_item()` (app.py:L2867)
- `detalle()` (tienda_bp.py:L2691)
- `detectar_alertas_stock_bajo()` (app.py:L465)
- `devolver_stock_item()` (app.py:L2748)
- `editar_venta()` (app.py:L2497)
- `estadisticas()` (app.py:L9385)
- `exportar_reposicion()` (app.py:L9536)
- `exportar_ventas_activas_excel()` (app.py:L687)
- `facturar_multiple()` (app.py:L4177)
- `facturar_multiple_excel()` (app.py:L3987)
- `generar_factura_excel()` (app.py:L3846)
- `get_stock_disponible_sku()` (tienda_bp.py:L2182)
- `home()` (tienda_bp.py:L2214)
- `ml_seleccionar_orden()` (app.py:L6839)
- `nota_pedido_pdf()` (app.py:L10906)
- `nueva_venta()` (app.py:L4956)
- `nueva_venta_desde_ml()` (app.py:L7068)
- `orden_retiro_pdf()` (app.py:L1139)
- `pago_exito()` (tienda_bp.py:L5023)
- `papel_azul_pdf()` (app.py:L11085)
- `productos_fotos()` (app.py:L13730)
- `productos_lista()` (app.py:L13491)
- `tienda_ofertas()` (app.py:L10854)
- `tienda_precios()` (app.py:L10735)
- `ventas_activas()` (app.py:L755)
- `ventas_historicas()` (app.py:L3427)
- `ventas_proceso()` (app.py:L1959)
- `ver_stock()` (app.py:L3220)
- `verificar_sku_en_bd()` (app.py:L6336)
- `verificar_stock_disponible()` (app.py:L296)
- `viaje_detalle()` (app.py:L10599)
- `viaje_nuevo()` (app.py:L10569)

## `componentes`
_Relación productos_compuestos ↔ productos_base con cantidades_

**👁️ Leen (16):**
- `_armar_bultos_cotizador()` (app.py:L13957)
- `_calcular_carga_viaje()` (app.py:L10449)
- `_extraer_skus_base_de_items()` (app.py:L11541)
- `actualizar_publicaciones_ml()` (app.py:L11435)
- `actualizar_publicaciones_ml_con_progreso()` (app.py:L12162)
- `armar_bultos_zipnova()` (tienda_bp.py:L3705)
- `calcular_stock_por_sku()` (app.py:L8961)
- `dashboard_visual()` (app.py:L5454)
- `descontar_stock_item()` (app.py:L2867)
- `detectar_alertas_stock_bajo()` (app.py:L465)
- `devolver_stock_item()` (app.py:L2748)
- `exportar_reposicion()` (app.py:L9536)
- `get_stock_disponible_sku()` (tienda_bp.py:L2182)
- `nueva_venta()` (app.py:L4956)
- `ver_stock()` (app.py:L3220)
- `verificar_stock_disponible()` (app.py:L296)

## `conjunto_configuracion`
_Config de sommiers: colchón + base default + cantidad bases_

**👁️ Leen (13):**
- `_build_precio_costos_map()` (app.py:L12827)
- `_get_precio_costos_sku()` (app.py:L12676)
- `_get_stock_real()` (tienda_bp.py:L2142)
- `actualizar_carrito()` (tienda_bp.py:L3163)
- `agregar_carrito()` (tienda_bp.py:L3019)
- `costos_calcular()` (app.py:L13141)
- `detalle()` (tienda_bp.py:L2691)
- `home()` (tienda_bp.py:L2214)
- `papel_azul_pdf()` (app.py:L11085)
- `productos_lista()` (app.py:L13491)
- `sitemap()` (tienda_bp.py:L6209)
- `tienda_precios()` (app.py:L10735)
- `ver_carrito()` (tienda_bp.py:L3289)

## `productos_fotos`
_Fotos de productos: SKU, filename, orden_

**✏️ Modifican (2):**
- `productos_fotos_eliminar()` (app.py:L13793)
- `productos_fotos_reordenar()` (app.py:L13815)

**👁️ Leen (3):**
- `_get_fotos()` (app.py:L13480)
- `productos_fotos_subir()` (app.py:L13747)
- `productos_lista()` (app.py:L13491)

## `usuarios`
_Login del sistema: username, password_hash, rol, activo_

**👁️ Leen (2):**
- `load_user()` (app.py:L88)
- `login()` (app.py:L235)

## `configuracion`
_Configuración general del sistema (key/value): demora_sin_stock, ml_token, etc._

**✏️ Modifican (8):**
- `_ml_progress_save()` (app.py:L12137)
- `auto_import_toggle()` (app.py:L12034)
- `guardar_ml_token()` (app.py:L5803)
- `guardar_porcentajes_ml()` (app.py:L445)
- `productos_cuotas_coeficientes()` (app.py:L13681)
- `productos_demora_guardar()` (app.py:L13640)
- `productos_newsletter_cupon()` (app.py:L13658)
- `refresh_ml_token()` (app.py:L5739)

**👁️ Leen (16):**
- `_get_nl_config()` (tienda_bp.py:L5369)
- `_get_precio_costos_sku()` (app.py:L12676)
- `_ml_progress_get()` (app.py:L12150)
- `buscar_sku_ml()` (app.py:L7812)
- `cargar_ml_token()` (app.py:L5785)
- `cargar_stock_ml()` (app.py:L7602)
- `checkout()` (tienda_bp.py:L4115)
- `costos_calcular()` (app.py:L13141)
- `costos_index()` (app.py:L12890)
- `faltantes_catalogo_ml()` (app.py:L7943)
- `get_coeficientes_cuotas()` (tienda_bp.py:L2048)
- `get_demora_sin_stock()` (tienda_bp.py:L2130)
- `get_porcentajes_ml()` (app.py:L433)
- `job_auto_importar_ml()` (app.py:L11894)
- `productos_lista()` (app.py:L13491)
- `ventas_activas()` (app.py:L755)

## `cupones`
_Cupones de descuento: código, tipo, valor, mínimo, vencimiento_

**✏️ Modifican (5):**
- `pago_payway()` (tienda_bp.py:L4506)
- `suscribirse()` (tienda_bp.py:L5454)
- `tienda_cupones_guardar()` (app.py:L11324)
- `webhook_getnet()` (tienda_bp.py:L5905)
- `webhook_mp()` (tienda_bp.py:L5504)

**👁️ Leen (2):**
- `tienda_cupones()` (app.py:L11272)
- `validar_cupon()` (tienda_bp.py:L3354)

## `cupones_uso`
_Registro de uso de cupones por email_

**✏️ Modifican (3):**
- `pago_payway()` (tienda_bp.py:L4506)
- `webhook_getnet()` (tienda_bp.py:L5905)
- `webhook_mp()` (tienda_bp.py:L5504)

**👁️ Leen (2):**
- `tienda_cupones()` (app.py:L11272)
- `validar_cupon()` (tienda_bp.py:L3354)

## `suscriptores`
_Suscriptores newsletter: email, cupón asignado_

**✏️ Modifican (2):**
- `suscribirse()` (tienda_bp.py:L5454)
- `tienda_suscriptores_eliminar()` (app.py:L11356)

**👁️ Leen (1):**
- `tienda_cupones()` (app.py:L11272)

## `ofertas_home`
_Ofertas destacadas en home tienda: SKU, descuento, orden_

**✏️ Modifican (1):**
- `tienda_ofertas_guardar()` (app.py:L10874)

**👁️ Leen (3):**
- `detalle()` (tienda_bp.py:L2691)
- `home()` (tienda_bp.py:L2214)
- `tienda_ofertas()` (app.py:L10854)

## `pedidos_pendientes`
_Pedidos en checkout antes del webhook MP_

**✏️ Modifican (4):**
- `checkout()` (tienda_bp.py:L4115)
- `pago_payway()` (tienda_bp.py:L4506)
- `webhook_getnet()` (tienda_bp.py:L5905)
- `webhook_mp()` (tienda_bp.py:L5504)

**👁️ Leen (1):**
- `pago_getnet_crear()` (tienda_bp.py:L4916)

## `fletes`
_Cobros y pagos a fleteros_

_Sin uso detectado en el código._

## `viajes`
_Hojas de ruta de envíos_

**✏️ Modifican (1):**
- `viajes_guardar()` (app.py:L10659)

**👁️ Leen (3):**
- `_calcular_carga_viaje()` (app.py:L10449)
- `viaje_detalle()` (app.py:L10599)
- `viajes_lista()` (app.py:L10553)

## `auto_import_log`
_Log del job de auto-import ML_

**✏️ Modifican (3):**
- `_init_auto_import_table()` (app.py:L11565)
- `job_auto_importar_ml()` (app.py:L11894)
- `ventas_nuevas_reset()` (app.py:L12310)

**👁️ Leen (1):**
- `ventas_nuevas_count()` (app.py:L12299)

## `ml_publicaciones`
_Publicaciones de MercadoLibre con su SKU local_

_Sin uso detectado en el código._

## `costos`
_Costos de productos para cálculo de rentabilidad_

_Sin uso detectado en el código._
