# 🎯 RESTAURACIÓN DEL BACKUP - GUÍA PASO A PASO

## ✅ PASOS PARA RECUPERAR TODO (10 MINUTOS):

---

### PASO 1: Restaurar el backup (3 minutos)

**En MySQL Workbench:**

1. Ir a: **File → Run SQL Script...**
2. Seleccionar: **backup.sql** (el archivo que subiste)
3. Click en **Run**
4. Esperar que termine (puede tardar 1-2 minutos)
5. Verificar que diga "Operation completed successfully"

**¿Qué recupera esto?**
- ✅ 8 tablas completas
- ✅ ~64 ventas con todos sus datos
- ✅ Todos tus productos base
- ✅ Combos/sommiers configurados
- ✅ Componentes de combos
- ✅ Alertas de stock
- ✅ Mapeo de SKU-MLA

---

### PASO 2: Agregar campos nuevos (2 minutos)

**En MySQL Workbench:**

1. Abrir el archivo: **RESTAURAR_BACKUP_Y_ACTUALIZAR.sql**
2. Ejecutar completo (Ctrl+Shift+Enter)
3. Verificar que no haya errores

**¿Qué agrega esto?**
- ✅ `dni_cliente` (VARCHAR 20)
- ✅ `provincia_cliente` (VARCHAR 100, default 'Capital Federal')
- ✅ 8 campos de facturación (`factura_*`)
- ✅ Control de factura generada

---

### PASO 3: Verificar que todo funciona (2 minutos)

**Ejecutar en MySQL Workbench:**

```sql
USE inventario_cannon;

-- Ver estructura de ventas (debe mostrar 42 campos)
DESCRIBE ventas;

-- Contar ventas recuperadas
SELECT COUNT(*) as total_ventas FROM ventas;

-- Ver algunos productos
SELECT sku, nombre, tipo, stock_actual 
FROM productos_base 
LIMIT 10;
```

**Resultados esperados:**
- ✅ Tabla `ventas` con **42 campos** (32 originales + 10 nuevos)
- ✅ Aproximadamente **64 ventas**
- ✅ Productos visibles

---

### PASO 4: Probar el sistema (3 minutos)

```bash
# Iniciar Flask
python app.py
```

**Ir a:**
- http://localhost:5000/ → Ver dashboard
- http://localhost:5000/ventas/activas → Ver las 64 ventas
- http://localhost:5000/ver-stock → Ver productos

**Probar:**
1. Crear nueva venta → Verificar campos DNI y Provincia
2. Marcar venta como entregada
3. Ir a Históricas → Facturar → Verificar Excel

---

## 📊 LO QUE RECUPERASTE:

### ✅ DATOS PRESERVADOS:
- **64 ventas** con todos sus detalles
- **Productos base** con stock actual
- **Combos/sommiers** configurados
- **Alertas de stock** históricas
- **Mapeo SKU-MLA** (publicaciones ML)

### ✅ CAMPOS NUEVOS AGREGADOS:
- DNI del cliente (manual)
- Provincia del cliente (manual)
- 8 campos de billing de ML (automáticos)
- Control de factura generada

### ❌ LO QUE NO TENÉS (normal):
- Ventas posteriores al backup (17 de febrero)
- Cambios de stock posteriores al backup

---

## 🔍 VERIFICACIONES IMPORTANTES:

### 1. Verificar tabla ventas:
```sql
DESCRIBE ventas;
```
**Debe mostrar 42 campos**, incluyendo:
- dni_cliente
- provincia_cliente
- factura_business_name
- factura_doc_number
- etc.

### 2. Verificar ventas:
```sql
SELECT numero_venta, nombre_cliente, importe_total, estado_entrega 
FROM ventas 
ORDER BY id DESC 
LIMIT 10;
```

### 3. Verificar productos:
```sql
SELECT sku, nombre, stock_actual 
FROM productos_base 
WHERE stock_actual > 0;
```

---

## ⚠️ SI ALGO FALLA:

### Error: "Table 'ventas' already exists"
→ El backup se importó bien, solo ejecutá el PASO 2

### Error: "Duplicate column name 'dni_cliente'"
→ Ya se agregaron los campos, está todo listo

### Flask no arranca
→ Verificar credenciales de BD en app.py

---

## 📝 CHECKLIST FINAL:

- [ ] Backup importado correctamente
- [ ] Script de actualización ejecutado
- [ ] Tabla ventas tiene 42 campos
- [ ] Flask arranca sin errores
- [ ] Ver ventas activas funciona
- [ ] Crear nueva venta funciona
- [ ] Campos DNI y Provincia aparecen en formulario
- [ ] Facturar Excel funciona

---

## 🎉 RESULTADO FINAL:

**Base de datos 100% funcional con:**
- ✅ Todos tus datos históricos (hasta el 17/02)
- ✅ Estructura completa actualizada
- ✅ Campos nuevos agregados
- ✅ Sistema listo para usar

---

¿Empezamos con el PASO 1? 🚀
