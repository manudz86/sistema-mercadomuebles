-- ============================================================
-- AGREGAR PRODUCTOS MDF Y PANEL - SIN MANEJO DE STOCK
-- Ejecutar en MySQL sobre la base inventario_cannon
-- ============================================================

INSERT INTO productos_base (sku, nombre, tipo, stock_actual) VALUES
('MD3100',    'MDF 3mm 260x183cm',              'servicio', 0),
('MD55100',   'MDF 5,5mm 260x183cm',            'servicio', 0),
('MD9100',    'MDF 9mm 275x183cm',              'servicio', 0),
('MD12100',   'MDF 12mm 275x183cm',             'servicio', 0),
('MD15100',   'MDF 15mm 275x183cm',             'servicio', 0),
('MD18100',   'MDF 18mm 275x183cm',             'servicio', 0),
('MD25100',   'MDF 25mm 275x183cm',             'servicio', 0),
('PAN90BL',   'Panel Ranurado Blanco 260x90cm', 'servicio', 0),
('PAN120OT',  'Panel Ranurado Color 120x90cm',  'servicio', 0);

-- ============================================================
-- VERIFICAR QUE SE INSERTARON CORRECTAMENTE:
-- ============================================================
SELECT sku, nombre, tipo, stock_actual 
FROM productos_base 
WHERE sku IN ('MD3100','MD55100','MD9100','MD12100','MD15100','MD18100','MD25100','PAN90BL','PAN120OT');
