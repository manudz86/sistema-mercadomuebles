# ============================================================================
# DEBUG: VER TODOS LOS DATOS QUE TRAE ML DE UNA ORDEN
# Ejecutar en tu terminal o agregar como ruta temporal en Flask
# ============================================================================

import requests
import json
from pprint import pprint

def debug_orden_ml_completa(orden_id, access_token):
    """
    Ver TODOS los datos que trae ML de una orden
    Incluyendo billing_info, buyer, shipping, payments, etc.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    
    print("\n" + "="*80)
    print(f"🔍 DEBUG COMPLETO - ORDEN ML: {orden_id}")
    print("="*80 + "\n")
    
    # ============================================
    # 1. ORDEN COMPLETA
    # ============================================
    print("📦 1. INFORMACIÓN COMPLETA DE LA ORDEN:")
    print("-" * 80)
    
    try:
        response = requests.get(
            f'https://api.mercadolibre.com/orders/{orden_id}',
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
        
        orden = response.json()
        
        # Guardar JSON completo en archivo
        with open(f'debug_orden_{orden_id}.json', 'w', encoding='utf-8') as f:
            json.dump(orden, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON completo guardado en: debug_orden_{orden_id}.json")
        print()
        
        # Mostrar estructura principal
        print("📋 ESTRUCTURA PRINCIPAL:")
        for key in orden.keys():
            valor = orden[key]
            tipo = type(valor).__name__
            
            if isinstance(valor, (list, dict)):
                if isinstance(valor, list):
                    longitud = f"[{len(valor)} items]"
                else:
                    longitud = f"{{{len(valor)} keys}}"
                print(f"   • {key}: {tipo} {longitud}")
            else:
                print(f"   • {key}: {tipo} = {valor}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error al obtener orden: {str(e)}")
        return
    
    # ============================================
    # 2. DATOS DEL COMPRADOR (BUYER)
    # ============================================
    print("\n👤 2. DATOS DEL COMPRADOR (buyer):")
    print("-" * 80)
    
    buyer = orden.get('buyer', {})
    
    if buyer:
        print("📋 Campos disponibles en 'buyer':")
        pprint(buyer, width=120)
    else:
        print("⚠️ No hay datos de buyer")
    
    print()
    
    # ============================================
    # 3. BILLING INFO (FACTURACIÓN)
    # ============================================
    print("\n🧾 3. INFORMACIÓN DE FACTURACIÓN (billing_info):")
    print("-" * 80)
    
    try:
        billing_response = requests.get(
            f'https://api.mercadolibre.com/orders/{orden_id}/billing_info',
            headers=headers
        )
        
        if billing_response.status_code == 200:
            billing = billing_response.json()
            
            print("✅ BILLING INFO DISPONIBLE:")
            print()
            
            # Guardar JSON de billing
            with open(f'debug_billing_{orden_id}.json', 'w', encoding='utf-8') as f:
                json.dump(billing, f, indent=2, ensure_ascii=False)
            
            print(f"✅ JSON guardado en: debug_billing_{orden_id}.json")
            print()
            
            print("📋 DATOS DE FACTURACIÓN:")
            pprint(billing, width=120)
            
        elif billing_response.status_code == 404:
            print("⚠️ NO HAY BILLING INFO (404 - Not Found)")
            print()
            print("Esto es normal si:")
            print("   • No sos Responsable Inscripto")
            print("   • La venta no requiere factura")
            print("   • El comprador es Consumidor Final sin CUIT")
        
        else:
            print(f"⚠️ Error {billing_response.status_code}: {billing_response.text}")
    
    except Exception as e:
        print(f"❌ Error al obtener billing_info: {str(e)}")
    
    print()
    
    # ============================================
    # 4. SHIPPING (ENVÍO)
    # ============================================
    print("\n🚚 4. DATOS DE ENVÍO (shipping):")
    print("-" * 80)
    
    shipping = orden.get('shipping', {})
    
    if shipping:
        print("📋 Campos disponibles en 'shipping':")
        pprint(shipping, width=120)
        
        # Si hay shipping_id, obtener detalles completos
        shipping_id = shipping.get('id')
        if shipping_id:
            print()
            print(f"📦 Obteniendo detalles completos del envío {shipping_id}...")
            
            try:
                ship_response = requests.get(
                    f'https://api.mercadolibre.com/shipments/{shipping_id}',
                    headers=headers
                )
                
                if ship_response.status_code == 200:
                    shipment = ship_response.json()
                    
                    with open(f'debug_shipment_{orden_id}.json', 'w', encoding='utf-8') as f:
                        json.dump(shipment, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Shipment guardado en: debug_shipment_{orden_id}.json")
                    print()
                    
                    print("📍 DIRECCIÓN DE ENVÍO:")
                    receiver = shipment.get('receiver_address', {})
                    pprint(receiver, width=120)
                
            except Exception as e:
                print(f"⚠️ Error al obtener shipment: {str(e)}")
    else:
        print("⚠️ No hay datos de shipping")
    
    print()
    
    # ============================================
    # 5. PAYMENTS (PAGOS)
    # ============================================
    print("\n💳 5. INFORMACIÓN DE PAGOS (payments):")
    print("-" * 80)
    
    payments = orden.get('payments', [])
    
    if payments:
        for i, pago in enumerate(payments, 1):
            print(f"\n💰 Pago #{i}:")
            pprint(pago, width=120)
    else:
        print("⚠️ No hay datos de pagos")
    
    print()
    
    # ============================================
    # 6. ORDER ITEMS (PRODUCTOS)
    # ============================================
    print("\n📦 6. PRODUCTOS DE LA ORDEN (order_items):")
    print("-" * 80)
    
    items = orden.get('order_items', [])
    
    if items:
        for i, item in enumerate(items, 1):
            print(f"\n🛒 Item #{i}:")
            pprint(item, width=120)
    else:
        print("⚠️ No hay items")
    
    print()
    
    # ============================================
    # 7. RESUMEN
    # ============================================
    print("\n" + "="*80)
    print("📊 RESUMEN - DATOS ÚTILES PARA FACTURACIÓN:")
    print("="*80 + "\n")
    
    print("✅ DATOS DISPONIBLES:")
    print()
    
    # Buyer
    print("👤 COMPRADOR (buyer):")
    print(f"   • ID: {buyer.get('id', 'N/A')}")
    print(f"   • Nickname: {buyer.get('nickname', 'N/A')}")
    print(f"   • Email: {buyer.get('email', 'N/A')}")
    print(f"   • First name: {buyer.get('first_name', 'N/A')}")
    print(f"   • Last name: {buyer.get('last_name', 'N/A')}")
    print(f"   • Phone: {buyer.get('phone', {}).get('number', 'N/A')}")
    print()
    
    # Billing (si existe)
    try:
        if billing_response.status_code == 200:
            billing = billing_response.json()
            print("🧾 FACTURACIÓN (billing_info):")
            print(f"   • Doc type: {billing.get('doc_type', 'N/A')}")
            print(f"   • Doc number: {billing.get('doc_number', 'N/A')}")
            
            # Buscar más datos
            if 'additional_info' in billing:
                print(f"   • Additional info: {billing.get('additional_info')}")
            
            print()
        else:
            print("🧾 FACTURACIÓN: No disponible (consumidor final)")
            print()
    except:
        pass
    
    # Totales
    print("💰 TOTALES:")
    print(f"   • Total amount: ${orden.get('total_amount', 0)}")
    print(f"   • Paid amount: ${orden.get('paid_amount', 0)}")
    
    if payments:
        fee = payments[0].get('marketplace_fee', 0)
        print(f"   • Marketplace fee: ${fee}")
        print(f"   • Neto vendedor: ${orden.get('total_amount', 0) - fee}")
    
    print()
    
    # Dirección
    if shipping and 'receiver_address' in shipment:
        addr = shipment.get('receiver_address', {})
        print("📍 DIRECCIÓN:")
        print(f"   • Address line: {addr.get('address_line', 'N/A')}")
        print(f"   • City: {addr.get('city', {}).get('name', 'N/A')}")
        print(f"   • State: {addr.get('state', {}).get('name', 'N/A')}")
        print(f"   • Zip code: {addr.get('zip_code', 'N/A')}")
        print()
    
    print("="*80)
    print("✅ DEBUG COMPLETO - Revisá los archivos JSON generados")
    print("="*80 + "\n")


# ============================================================================
# RUTA TEMPORAL PARA USAR EN FLASK
# ============================================================================

@app.route('/debug/ml/<orden_id>')
def debug_orden_ml_ruta(orden_id):
    """
    Ruta temporal para debuggear una orden de ML
    Acceder: http://localhost:5000/debug/ml/2000015193517850
    """
    access_token = cargar_ml_token()
    
    if not access_token:
        return "❌ No hay token de ML configurado", 400
    
    debug_orden_ml_completa(orden_id, access_token)
    
    return f"""
    <html>
    <head><title>Debug ML Orden {orden_id}</title></head>
    <body style="font-family: monospace; padding: 20px; background: #1e1e1e; color: #fff;">
        <h2>✅ Debug completado</h2>
        <p>La información se imprimió en la consola de Flask.</p>
        <p>También se generaron archivos JSON:</p>
        <ul>
            <li><code>debug_orden_{orden_id}.json</code></li>
            <li><code>debug_billing_{orden_id}.json</code> (si existe)</li>
            <li><code>debug_shipment_{orden_id}.json</code> (si existe)</li>
        </ul>
        <br>
        <a href="/ventas/activas" style="color: #4fc3f7;">← Volver a Ventas Activas</a>
    </body>
    </html>
    """


# ============================================================================
# USO DIRECTO (SCRIPT STANDALONE)
# ============================================================================

if __name__ == "__main__":
    """
    Para ejecutar directamente:
    1. Copiar este archivo como: debug_ml.py
    2. Ejecutar: python debug_ml.py
    """
    
    # Configurar tu token
    ACCESS_TOKEN = "TU_ACCESS_TOKEN_AQUI"
    
    # ID de una orden real tuya (de las que viste en las imágenes)
    ORDEN_ID = "2000015193517850"  # Cambiar por una de tus órdenes reales
    
    debug_orden_ml_completa(ORDEN_ID, ACCESS_TOKEN)
