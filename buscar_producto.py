import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

from pos.models import Producto, MovimientoStock
from django.db.models import Sum, Q

# Buscar productos con OPALINA en el nombre
productos = Producto.objects.filter(nombre__icontains='OPALINA')
print(f'\nProductos encontrados: {productos.count()}\n')

for p in productos:
    print(f'ID: {p.id}')
    print(f'  Código: {p.codigo}')
    print(f'  Nombre: {p.nombre}')
    print(f'  Atributo: {p.atributo or "(vacio)"}')
    print(f'  Stock: {p.stock}')
    
    # Movimientos de este producto
    movimientos = MovimientoStock.objects.filter(producto=p)
    ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('cantidad'))['total'] or 0
    salidas = movimientos.filter(tipo='salida').aggregate(total=Sum('cantidad'))['total'] or 0
    ajustes = movimientos.filter(tipo='ajuste').aggregate(total=Sum('cantidad'))['total'] or 0
    
    print(f'  Movimientos: Ingresos={ingresos}, Salidas={salidas}, Ajustes={ajustes}, Neto={ingresos - salidas + ajustes}')
    print()

