"""Prueba (solo lectura) las expresiones Jinja del link 'ver publicación' y del botón
'Cotizar envío' de templates/preguntas.html con datos de ejemplo."""
from jinja2 import Environment

env = Environment()
tpl = env.from_string(
    "{% set _iid = (p.item_id or '')|upper %}"
    "https://articulo.mercadolibre.com.ar/{{ _iid[:3] ~ '-' ~ _iid[3:] if _iid[:3] == 'MLA' else _iid }}-_JM"
    " | sku={{ p.cotizar_sku or p.sku }} cant={{ p.cotizar_cant or 1 }}"
    " valor={{ p.precio|float|round|int if p.precio is not none else '' }}"
)
casos = [
    {'item_id': 'MLA3118054068', 'sku': 'SPR9023', 'precio': 560665.0},
    {'item_id': 'MLA1709629735', 'sku': 'CLASICAX2', 'cotizar_sku': 'CLASICA', 'cotizar_cant': 2, 'precio': 89999.5},
    {'item_id': 'MLA2247513680', 'sku': 'SREP160Z', 'cotizar_sku': 'SREP160', 'cotizar_cant': 1, 'precio': None},
]
for p in casos:
    print(tpl.render(p=p))
