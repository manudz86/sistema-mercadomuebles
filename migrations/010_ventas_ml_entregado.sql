-- 010: marca cuándo se reportó la entrega a ML (POST seller_notifications) para
-- ventas ME1/Flete Propio, y así colorear el botón en Ventas Históricas.
ALTER TABLE ventas ADD COLUMN ml_entregado_at DATETIME NULL DEFAULT NULL;
