-- Preguntas ML — Fase 1b (sugerencias con Claude + reglas + aprendizaje)
-- Campos de contexto agregados a ml_preguntas (ver tambien 005):
ALTER TABLE ml_preguntas
  ADD COLUMN IF NOT EXISTS tipo_publi VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS cuotas     VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS historial  TEXT NULL;
-- Tabla de aprendizaje (few-shot de respuestas confirmadas):
CREATE TABLE IF NOT EXISTS preguntas_ejemplos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pregunta TEXT, respuesta TEXT, sku VARCHAR(50),
  fecha DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX idx_fecha (fecha)
);
-- Reglas editables: configuracion.preguntas_reglas (JSON: saludo, cierre, tono, prohibido[], envio_me1, envio_flex)
