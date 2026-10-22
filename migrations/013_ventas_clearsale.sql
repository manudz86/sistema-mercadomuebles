-- 013 — Columnas de ClearSale en ventas
--
-- ClearSale analiza la venta DESPUES de que Payway aprueba, asi que la venta
-- nace en un estado intermedio ("pago en proceso") y recien se confirma
-- cuando llega el veredicto por webhook.
--
-- No se toca el ENUM de ventas.estado: hay mucho codigo que depende de sus
-- valores. La capa de ClearSale es aditiva y vive en columnas propias.
--
-- clearsale_estado guarda el codigo de 3 letras tal cual lo manda ClearSale
-- (NVO, AMA, APA, APM, RPA, RPM, SUS, FRD, CAN, ERR, RPP, APG). NULL = la
-- venta no paso por ClearSale (MercadoPago, ventas de ML, o Payway con el
-- flag clearsale_enabled apagado).
--
-- Aplicado en produccion el 22/10/2026. Backup previo:
--   backups/dump_pre-clearsale-cols_20261022_183519.sql

ALTER TABLE ventas
    ADD COLUMN clearsale_estado      VARCHAR(3)  DEFAULT NULL AFTER estado_pago,
    ADD COLUMN clearsale_order_id    VARCHAR(60) DEFAULT NULL AFTER clearsale_estado,
    ADD COLUMN clearsale_score       VARCHAR(20) DEFAULT NULL AFTER clearsale_order_id,
    ADD COLUMN clearsale_actualizado DATETIME    DEFAULT NULL AFTER clearsale_score,
    ADD INDEX idx_clearsale_estado (clearsale_estado);

-- Interruptor general. En 0 el checkout se comporta exactamente como antes:
-- no se envia nada a ClearSale y las ventas de Payway siguen naciendo pagadas.
INSERT IGNORE INTO configuracion (clave, valor) VALUES ('clearsale_enabled', '0');
