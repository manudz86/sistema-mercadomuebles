-- Preguntas ML — Fase 1a (MVP)
-- Tabla espejo de las preguntas de Mercado Libre (sin responder / respondidas).
CREATE TABLE IF NOT EXISTS ml_preguntas (
  question_id        BIGINT PRIMARY KEY,
  item_id            VARCHAR(20),
  item_titulo        VARCHAR(255),
  sku                VARCHAR(50),
  precio             DECIMAL(12,2) NULL,
  stock              INT NULL,
  texto              TEXT,
  comprador_id       VARCHAR(30),
  fecha_pregunta     DATETIME NULL,
  status             VARCHAR(20) DEFAULT 'UNANSWERED',
  respuesta_sugerida TEXT NULL,   -- Fase 1b (LLM)
  respuesta_final    TEXT NULL,
  respondida_at      DATETIME NULL,
  synced_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_status (status),
  INDEX idx_item (item_id)
);
