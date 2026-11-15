-- 021: permisos por rol, editables desde /configuracion/permisos (ver permisos.py).
-- Solo guarda lo que se cambia desde la página: los niveles por defecto viven en
-- permisos.MODULOS, así que la tabla nace vacía y el sistema funciona igual.
-- admin no se guarda: siempre tiene todo.
CREATE TABLE IF NOT EXISTS permisos_rol (
    rol             VARCHAR(20)  NOT NULL,
    modulo          VARCHAR(40)  NOT NULL,
    nivel           ENUM('ninguno','ver','editar') NOT NULL,
    actualizado_por VARCHAR(50)  NULL,
    actualizado     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rol, modulo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
