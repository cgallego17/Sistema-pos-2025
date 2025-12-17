from django.core.management.base import BaseCommand
from pos.models import MovimientoStock, Producto
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce


class Command(BaseCommand):
    help = 'Diagnostica los movimientos de un producto específico para verificar el reporte'

    def add_arguments(self, parser):
        parser.add_argument('--codigo', type=str, default=None, help='Código del producto a diagnosticar')
        parser.add_argument('--nombre', type=str, default=None, help='Nombre del producto (búsqueda parcial)')
        parser.add_argument('--atributo', type=str, default=None, help='Atributo del producto (opcional)')

    def handle(self, *args, **options):
        codigo = options.get('codigo')
        nombre = options.get('nombre')
        atributo = options.get('atributo')
        
        if not codigo and not nombre:
            self.stdout.write(self.style.ERROR('Debes proporcionar --codigo o --nombre'))
            return
        
        # Buscar productos
        productos = Producto.objects.all()
        if codigo:
            productos = productos.filter(codigo=codigo)
            self.stdout.write(self.style.SUCCESS(f'\n=== DIAGNÓSTICO DE PRODUCTO: Código={codigo} ===\n'))
        elif nombre:
            productos = productos.filter(nombre__icontains=nombre)
            self.stdout.write(self.style.SUCCESS(f'\n=== DIAGNÓSTICO DE PRODUCTO: Nombre contiene "{nombre}" ===\n'))
        
        if atributo:
            productos = productos.filter(atributo=atributo)
        else:
            # Si no se especifica atributo, buscar los que tienen atributo vacío o null
            productos = productos.filter(Q(atributo__isnull=True) | Q(atributo=''))
        
        self.stdout.write(f'Productos encontrados: {productos.count()}\n')
        
        for producto in productos:
            self.stdout.write(f'\n--- Producto ID: {producto.id} ---')
            self.stdout.write(f'  Código: {producto.codigo}')
            self.stdout.write(f'  Nombre: {producto.nombre}')
            self.stdout.write(f'  Atributo: {producto.atributo or "(vacío)"}')
            self.stdout.write(f'  Stock Actual: {producto.stock}')
            
            # Obtener todos los movimientos de este producto
            movimientos = MovimientoStock.objects.filter(producto=producto).order_by('fecha')
            
            self.stdout.write(f'\n  Total de movimientos: {movimientos.count()}')
            
            # Agrupar por tipo
            ingresos = movimientos.filter(tipo='ingreso')
            salidas = movimientos.filter(tipo='salida')
            ajustes = movimientos.filter(tipo='ajuste')
            
            total_ingresos = ingresos.aggregate(total=Sum('cantidad'))['total'] or 0
            total_salidas = salidas.aggregate(total=Sum('cantidad'))['total'] or 0
            total_ajustes = ajustes.aggregate(total=Sum('cantidad'))['total'] or 0
            
            self.stdout.write(f'\n  RESUMEN POR TIPO:')
            self.stdout.write(f'    Ingresos: {total_ingresos} (en {ingresos.count()} movimientos)')
            self.stdout.write(f'    Salidas: {total_salidas} (en {salidas.count()} movimientos)')
            self.stdout.write(f'    Ajustes: {total_ajustes} (en {ajustes.count()} movimientos)')
            self.stdout.write(f'    Neto: {total_ingresos - total_salidas + total_ajustes}')
            
            # Mostrar detalle de movimientos
            self.stdout.write(f'\n  DETALLE DE MOVIMIENTOS:')
            for mov in movimientos[:20]:  # Mostrar primeros 20
                self.stdout.write(f'    {mov.fecha.strftime("%Y-%m-%d %H:%M")} | {mov.tipo:10} | Cantidad: {mov.cantidad:5} | Stock: {mov.stock_anterior} -> {mov.stock_nuevo} | Motivo: {mov.motivo[:50] if mov.motivo else "N/A"}')
            
            if movimientos.count() > 20:
                self.stdout.write(f'    ... y {movimientos.count() - 20} movimientos más')
        
        # Ahora verificar cómo el reporte agrupa estos productos
        self.stdout.write(f'\n\n=== CÓMO EL REPORTE AGRUPA ESTOS PRODUCTOS ===\n')
        
        # Simular el agrupamiento del reporte
        from django.db.models import Min
        movimientos_qs = MovimientoStock.objects.filter(producto__codigo=codigo)
        if atributo:
            movimientos_qs = movimientos_qs.filter(producto__atributo=atributo)
        else:
            movimientos_qs = movimientos_qs.filter(
                Q(producto__atributo__isnull=True) | Q(producto__atributo='')
            )
        
        resumen_agrupado = movimientos_qs.values(
            'producto__codigo',
            'producto__atributo'
        ).annotate(
            producto__nombre=Min('producto__nombre'),
            total_entradas=Sum('cantidad', filter=Q(tipo='ingreso')),
            total_salidas=Sum('cantidad', filter=Q(tipo='salida')),
            total_ajustes=Sum('cantidad', filter=Q(tipo='ajuste'))
        )
        
        for item in resumen_agrupado:
            self.stdout.write(f'\n--- Agrupación por código+atributo ---')
            self.stdout.write(f'  Código: {item["producto__codigo"]}')
            self.stdout.write(f'  Atributo: {item["producto__atributo"] or "(vacío)"}')
            self.stdout.write(f'  Nombre: {item["producto__nombre"]}')
            self.stdout.write(f'  Total Entradas: {item["total_entradas"] or 0}')
            self.stdout.write(f'  Total Salidas: {item["total_salidas"] or 0}')
            self.stdout.write(f'  Total Ajustes: {item["total_ajustes"] or 0}')
            self.stdout.write(f'  Neto: {(item["total_entradas"] or 0) - (item["total_salidas"] or 0) + (item["total_ajustes"] or 0)}')
            
            # Calcular stock actual sumando todos los productos con ese código+atributo
            productos_mismo_codigo = Producto.objects.filter(
                codigo=item['producto__codigo'],
                activo=True
            )
            if item['producto__atributo']:
                productos_mismo_codigo = productos_mismo_codigo.filter(atributo=item['producto__atributo'])
            else:
                productos_mismo_codigo = productos_mismo_codigo.filter(
                    Q(atributo__isnull=True) | Q(atributo='')
                )
            
            stock_total = sum(p.stock for p in productos_mismo_codigo)
            self.stdout.write(f'  Stock Actual (suma de productos): {stock_total}')
            self.stdout.write(f'  Productos con este código+atributo: {productos_mismo_codigo.count()}')
            for p in productos_mismo_codigo:
                self.stdout.write(f'    - ID {p.id}: {p.nombre} (Stock: {p.stock})')

