# 🔄 FLUJO COMPLETO DE VENTAS - DIAGRAMA

## 📊 ESTADOS Y TRANSICIONES:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VENTAS ACTIVAS                              │
│                      (estado: pendiente)                            │
│                                                                     │
│  • Stock: NO descontado                                            │
│  • Acción disponible: Pasar a Proceso / Cancelar / Marcar Entregada│
└─────────────────────────────────────────────────────────────────────┘
            ↓                           ↓                        ↓
    [Pasar a Proceso]              [Cancelar]          [Marcar Entregada]
    (descuenta stock)          (NO toca stock)         (descuenta stock)
            ↓                           ↓                        ↓
┌──────────────────────┐    ┌──────────────────────┐            ↓
│  PROCESO DE ENVÍO    │    │ VENTAS HISTÓRICAS    │            ↓
│ (estado: en_proceso) │    │ (estado: cancelada)  │            ↓
│                      │    │                      │            ↓
│ • Stock: Descontado  │    │ • Stock: Intacto     │            ↓
│ • Acciones:          │    │ • Acciones:          │            ↓
│   - Volver Activas   │    │   - Volver Activas ← NUEVO       ↓
│   - Marcar Entregada │    └──────────────────────┘            ↓
│   - Cancelar         │              ↓                         ↓
└──────────────────────┘              ↓                         ↓
            ↓                         ↓                         ↓
    [Marcar Entregada]                ↓                         ↓
            ↓                         ↓                         ↓
┌──────────────────────────────────────────────────────────────────┐
│                    VENTAS HISTÓRICAS                             │
│                   (estado: entregada)                            │
│                                                                  │
│  • Stock: Descontado                                            │
│  • Acciones: Volver Activas ← NUEVO (devuelve stock)           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔄 NUEVAS TRANSICIONES (AGREGADAS):

### 1. CANCELADA → ACTIVA
```
VENTAS HISTÓRICAS (cancelada)
         ↓
   [Volver Activas]
         ↓
   Stock: SIN CAMBIOS (porque nunca se descontó)
   Estado: pendiente
         ↓
   VENTAS ACTIVAS
```

### 2. ENTREGADA → ACTIVA
```
VENTAS HISTÓRICAS (entregada)
         ↓
   [Volver Activas]
         ↓
   Stock: DEVUELTO (+X unidades)
   Estado: pendiente
         ↓
   VENTAS ACTIVAS
```

---

## 📋 TABLA DE TRANSICIONES:

| Desde          | A             | Botón               | Stock               |
|----------------|---------------|---------------------|---------------------|
| Activas        | Proceso       | Pasar a Proceso     | ⬇️ Descuenta       |
| Activas        | Cancelada     | Cancelar            | — Sin cambio       |
| Activas        | Entregada     | Marcar Entregada    | ⬇️ Descuenta       |
| Proceso        | Activas       | Volver Activas      | ⬆️ Devuelve        |
| Proceso        | Entregada     | Marcar Entregada    | — Ya descontado    |
| Proceso        | Cancelada     | Cancelar            | ⬆️ Devuelve        |
| **Cancelada**  | **Activas**   | **Volver Activas**  | **— Sin cambio** ← NUEVO |
| **Entregada**  | **Activas**   | **Volver Activas**  | **⬆️ Devuelve**  ← NUEVO |

---

## 🎯 CASOS DE USO:

### Escenario 1: Error al cancelar
```
1. Vendiste 1 colchón (VENTA-100)
2. Cliente llamó para cancelar
3. Marcaste como "Cancelada" por error
   → Stock actual: 10 (no cambió porque cancelar no descuenta)
4. Cliente confirma que SÍ quiere el colchón
5. Click "Volver a Activas" en Ventas Históricas
   → Stock actual: 10 (sigue igual)
6. Venta vuelve a Activas, lista para procesar
```

### Escenario 2: Error al entregar
```
1. Vendiste 2 bases (VENTA-200)
2. Pasaste a Proceso → Stock: 10 - 2 = 8
3. Marcaste como "Entregada" muy rápido
   → Stock actual: 8
4. Te das cuenta que NO se entregó todavía
5. Click "Volver a Activas" en Ventas Históricas
   → Stock actual: 8 + 2 = 10 (devuelve las 2 bases)
6. Venta vuelve a Activas con stock restaurado
```

### Escenario 3: Cliente devuelve producto
```
1. Entregaste 1 almohada (VENTA-300)
2. Stock después de entrega: 5 - 1 = 4
3. Cliente devuelve el producto al día siguiente
4. Click "Volver a Activas" en Ventas Históricas
   → Stock actual: 4 + 1 = 5 (devuelve la almohada)
5. Ahora podés:
   - Volver a procesarla si el cliente quiere otro producto
   - O cancelarla definitivamente
```

---

## ⚠️ IMPORTANTE:

### Botón "Volver Activas" aparece en:
- ✅ Ventas Históricas (entregadas)
- ✅ Ventas Históricas (canceladas)
- ❌ NO en Ventas Activas (ya están activas)
- ❌ NO en Proceso de Envío (usar "Volver Activas" de proceso)

### Confirmación diferente:
```javascript
// Si está ENTREGADA:
"¿Volver esta venta a Ventas Activas?
Se devolverá el stock descontado."

// Si está CANCELADA:
"¿Volver esta venta a Ventas Activas?
No se modificará el stock."
```

---

## 🔍 VERIFICACIÓN POST-INSTALACIÓN:

### Test completo:
1. Crear venta VENTA-TEST con 1 producto
2. Anotar stock actual del producto
3. Pasar a Proceso → verificar stock bajó
4. Marcar Entregada → verificar sigue bajo
5. Ir a Históricas → debe aparecer
6. Click "Volver Activas" → confirmar
7. Verificar stock SUBIÓ de nuevo
8. Ir a Activas → venta debe estar ahí
9. Repetir proceso: Proceso → Cancelar
10. Volver Activas → stock debe mantenerse

**Si todo funciona → ✅ Instalación correcta**

---

**¡Flujo completo!** 🔄
