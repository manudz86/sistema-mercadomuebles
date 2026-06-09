-- 007_payway_intentos.sql
-- Log de auditoría de intentos de pago Payway (acreditados, autorizados, rechazados, anulados).
-- Se alimenta SOLO por lectura desde la API de Payway (GET /payments) vía sync_payway_intentos().
-- No toca el flujo de cobro. payment_id es el id de la operación en Payway (único).

CREATE TABLE IF NOT EXISTS payway_intentos (
    payment_id          BIGINT       NOT NULL,
    site_transaction_id VARCHAR(40)  DEFAULT NULL,   -- "PW-<ref>"
    ref                 VARCHAR(40)  DEFAULT NULL,    -- <ref> sin "PW-" (join a pedidos_pendientes)
    fecha               DATETIME     DEFAULT NULL,
    amount              DECIMAL(14,2) DEFAULT NULL,   -- en pesos (amount/100)
    installments        INT          DEFAULT NULL,
    status              VARCHAR(20)  DEFAULT NULL,    -- crudo: approved/rejected/annulled/...
    status_es           VARCHAR(20)  DEFAULT NULL,    -- mapeado: Acreditada/Rechazada/...
    motivo              VARCHAR(120) DEFAULT NULL,    -- status_details.error.reason.description
    motivo_id           INT          DEFAULT NULL,
    card_brand          VARCHAR(30)  DEFAULT NULL,
    bin                 VARCHAR(10)  DEFAULT NULL,
    last4               VARCHAR(4)   DEFAULT NULL,
    tid                 VARCHAR(40)  DEFAULT NULL,
    payment_method_id   INT          DEFAULT NULL,
    raw_json            JSON         DEFAULT NULL,
    fecha_sync          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (payment_id),
    KEY idx_fecha (fecha),
    KEY idx_status (status),
    KEY idx_ref (ref)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
