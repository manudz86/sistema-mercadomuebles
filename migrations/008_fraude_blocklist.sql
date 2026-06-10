-- 008_fraude_blocklist.sql
-- Blocklist antifraude para los checkouts de la tienda (Payway y GetNet).
-- La consultan los gates de pago_payway() y pago_getnet_crear() en tienda_bp.py
-- (fail-open: cualquier error en el chequeo deja pasar el pago).
-- Se gestiona desde /intentos-pago (solapa Blocklist).
--
-- tipo: direccion | dni | email | telefono | nombre | tarjeta
--   - direccion / nombre: match por substring sobre el valor normalizado
--     (minusculas, sin tildes) del pedido.
--   - dni / email / telefono: match exacto normalizado.
--   - tarjeta: ultimos 4 o bin+ultimos4.

CREATE TABLE IF NOT EXISTS fraude_blocklist (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    tipo       VARCHAR(20)  NOT NULL,
    valor      VARCHAR(255) NOT NULL,
    motivo     VARCHAR(255) DEFAULT NULL,
    activo     TINYINT(1)   NOT NULL DEFAULT 1,
    fecha_alta TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_tipo_valor (tipo, valor),
    KEY idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
