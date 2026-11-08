-- Avisos de seguimiento ME1 a Mercado Libre (Flete Propio) — POST /v2/shipments/{id}/seller_notifications
-- ml_despachado_at:  se avisó "En camino" (shipped) — al imprimir el papel azul en Ventas Activas
-- ml_en_reparto_at:  se avisó "Salió a distribución" (shipped/out_for_delivery) — al pasar a Proceso de Envío
-- ml_entregado_at (ya existía): se avisó "Entregado" (delivered)
-- ml_aviso_error:    último error devuelto por ML (NULL si el último aviso salió bien)

ALTER TABLE ventas
    ADD COLUMN ml_despachado_at DATETIME NULL,
    ADD COLUMN ml_en_reparto_at DATETIME NULL,
    ADD COLUMN ml_aviso_error VARCHAR(255) NULL;
