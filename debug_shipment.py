import requests, json, sys
sys.path.insert(0, '/home/cannon/app')
from app import cargar_ml_token

ORDER_ID = '2000015509390936'  # Cambiá este ID

token   = cargar_ml_token()
headers = {'Authorization': f'Bearer {token}'}

orden = requests.get(f'https://api.mercadolibre.com/orders/{ORDER_ID}', headers=headers).json()
shipping_id = orden.get('shipping', {}).get('id')
print(f'shipping_id: {shipping_id}')

if shipping_id:
    shipment = requests.get(f'https://api.mercadolibre.com/shipments/{shipping_id}', headers=headers).json()
    print(json.dumps(shipment, indent=2))
else:
    print('Sin shipping en esta orden')
    print(json.dumps(orden, indent=2))
