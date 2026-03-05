-- ============================================
-- TABLA DE HISTORIAL DE MOVIMIENTOS DE STOCK
-- ============================================

CREATE TABLE IF NOT EXISTS movimientos_stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    nombre_producto VARCHAR(255),
    tipo_movimiento ENUM('carga', 'baja', 'venta', 'ajuste') NOT NULL,
    cantidad INT NOT NULL,
    stock_anterior INT NOT NULL,
    stock_nuevo INT NOT NULL,
    motivo TEXT,
    usuario VARCHAR(100) DEFAULT 'Sistema',
    fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_sku (sku),
    INDEX idx_tipo (tipo_movimiento),
    INDEX idx_fecha (fecha_movimiento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- VERIFICAR QUE SE CREÓ CORRECTAMENTE
-- ============================================

DESCRIBE movimientos_stock;

-- ============================================
-- EJEMPLO DE DATOS (OPCIONAL - PARA PROBAR)
-- ============================================

-- INSERT INTO movimientos_stock (sku, nombre_producto, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, motivo)
-- VALUES 
-- ('CEX140', 'Colchón Exclusive 140x190', 'carga', 5, 2, 7, 'Reposición mensual'),
-- ('BASE_CHOC80200', 'Base Chocolate 80x200', 'baja', 2, 6, 4, 'Productos defectuosos'),
-- ('PLATINO', 'Almohada Platino', 'carga', 50, 50, 100, 'Nueva compra');

-- ============================================
-- QUERIES ÚTILES PARA CONSULTAR HISTORIAL
-- ============================================

-- Ver últimos 10 movimientos
SELECT * FROM movimientos_stock ORDER BY fecha_movimiento DESC LIMIT 10;

-- Ver movimientos de un producto específico
SELECT * FROM movimientos_stock WHERE sku = 'CEX140' ORDER BY fecha_movimiento DESC;

-- Ver solo cargas de stock
SELECT * FROM movimientos_stock WHERE tipo_movimiento = 'carga' ORDER BY fecha_movimiento DESC;

-- Ver movimientos de hoy
SELECT * FROM movimientos_stock WHERE DATE(fecha_movimiento) = CURDATE() ORDER BY fecha_movimiento DESC;

-- Resumen por tipo de movimiento
SELECT 
    tipo_movimiento,
    COUNT(*) as total_movimientos,
    SUM(cantidad) as total_unidades
FROM movimientos_stock
GROUP BY tipo_movimiento;
