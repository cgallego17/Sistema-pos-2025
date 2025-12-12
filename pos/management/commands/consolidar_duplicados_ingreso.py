from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import IngresoMercancia, ItemIngresoMercancia
from collections import defaultdict


class Command(BaseCommand):
    help = 'Consolida productos duplicados en un ingreso de mercancía'

    def add_arguments(self, parser):
        parser.add_argument(
            'ingreso_id',
            type=int,
            help='ID del ingreso a consolidar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué se haría sin hacer cambios'
        )

    def handle(self, *args, **options):
        ingreso_id = options['ingreso_id']
        dry_run = options['dry_run']
        
        try:
            ingreso = IngresoMercancia.objects.get(id=ingreso_id)
        except IngresoMercancia.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Ingreso #{ingreso_id} no encontrado'))
            return
        
        self.stdout.write(f'Analizando ingreso #{ingreso_id}...')
        self.stdout.write(f'Proveedor: {ingreso.proveedor}')
        self.stdout.write('')
        
        # Agrupar items por producto
        items_por_producto = defaultdict(list)
        for item in ingreso.items.all():
            items_por_producto[item.producto.id].append(item)
        
        # Identificar duplicados
        duplicados = {pid: items for pid, items in items_por_producto.items() if len(items) > 1}
        
        if not duplicados:
            self.stdout.write(self.style.SUCCESS('No se encontraron productos duplicados'))
            return
        
        self.stdout.write(self.style.WARNING(f'Se encontraron {len(duplicados)} productos duplicados:'))
        self.stdout.write('')
        
        total_items_eliminados = 0
        total_cantidad_consolidada = 0
        
        with transaction.atomic():
            for producto_id, items in duplicados.items():
                producto = items[0].producto
                self.stdout.write(f'  Producto: {producto.nombre} (ID: {producto_id})')
                self.stdout.write(f'    Items duplicados: {len(items)}')
                
                # Calcular totales
                cantidad_total = sum(item.cantidad for item in items)
                precio_total = sum(item.precio_compra * item.cantidad for item in items)
                precio_promedio = precio_total // cantidad_total if cantidad_total > 0 else 0
                subtotal_total = cantidad_total * precio_promedio
                
                self.stdout.write(f'    Cantidad total: {cantidad_total}')
                self.stdout.write(f'    Precio promedio: ${precio_promedio:,}')
                self.stdout.write(f'    Subtotal: ${subtotal_total:,}')
                
                if not dry_run:
                    # Mantener el primer item y actualizar sus valores
                    item_principal = items[0]
                    item_principal.cantidad = cantidad_total
                    item_principal.precio_compra = precio_promedio
                    item_principal.subtotal = subtotal_total
                    item_principal.save()
                    
                    # Eliminar los demás items
                    items_a_eliminar = items[1:]
                    for item in items_a_eliminar:
                        self.stdout.write(f'      Eliminando item ID: {item.id}')
                        item.delete()
                    
                    total_items_eliminados += len(items_a_eliminar)
                    total_cantidad_consolidada += cantidad_total
                
                self.stdout.write('')
            
            if not dry_run:
                # Recalcular total del ingreso
                nuevo_total = sum(item.subtotal for item in ingreso.items.all())
                ingreso.total = nuevo_total
                ingreso.save()
                
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write(self.style.SUCCESS('CONSOLIDACIÓN COMPLETADA'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write(f'Items eliminados: {total_items_eliminados}')
                self.stdout.write(f'Nuevo total del ingreso: ${nuevo_total:,}')
            else:
                self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se realizaron cambios'))
                self.stdout.write('Ejecuta sin --dry-run para aplicar los cambios')
        
        self.stdout.write('')

