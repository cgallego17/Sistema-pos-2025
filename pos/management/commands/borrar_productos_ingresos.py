# -*- coding: utf-8 -*-
"""
Comando para borrar todos los productos e ingresos de mercancía
ADVERTENCIA: Esta operación es IRREVERSIBLE
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import (
    Producto,
    IngresoMercancia,
    ItemIngresoMercancia,
    MovimientoStock
)


class Command(BaseCommand):
    help = 'Borra todos los productos e ingresos de mercancía'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación sin preguntar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('ADVERTENCIA: ESTA OPERACIÓN ES IRREVERSIBLE'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Contar registros
        total_productos = Producto.objects.count()
        total_ingresos = IngresoMercancia.objects.count()
        total_items_ingreso = ItemIngresoMercancia.objects.count()
        total_movimientos = MovimientoStock.objects.count()
        
        self.stdout.write(f'Productos a eliminar: {total_productos:,}')
        self.stdout.write(f'Ingresos de mercancía a eliminar: {total_ingresos:,}')
        self.stdout.write(f'Items de ingreso a eliminar: {total_items_ingreso:,}')
        self.stdout.write(f'Movimientos de stock a eliminar: {total_movimientos:,}')
        self.stdout.write('')
        
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('Para confirmar, ejecuta el comando con --confirm'))
            self.stdout.write('Ejemplo: python manage.py borrar_productos_ingresos --confirm')
            return
        
        self.stdout.write(self.style.WARNING('Iniciando eliminación...'))
        self.stdout.write('')
        
        try:
            with transaction.atomic():
                # 1. Eliminar items de ingresos primero (dependencia de IngresoMercancia)
                self.stdout.write('  - Eliminando items de ingresos de mercancía...')
                items_eliminados = ItemIngresoMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {items_eliminados[0]:,} items eliminados'))
                
                # 2. Eliminar ingresos de mercancía (esto también eliminará los movimientos por señal)
                self.stdout.write('  - Eliminando ingresos de mercancía...')
                ingresos_eliminados = IngresoMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {ingresos_eliminados[0]:,} ingresos eliminados'))
                
                # 3. Eliminar movimientos de stock restantes (por si acaso)
                self.stdout.write('  - Eliminando movimientos de stock...')
                movimientos_eliminados = MovimientoStock.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {movimientos_eliminados[0]:,} movimientos eliminados'))
                
                # 4. Eliminar productos
                self.stdout.write('  - Eliminando productos...')
                productos_eliminados = Producto.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {productos_eliminados[0]:,} productos eliminados'))
                
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('ERROR AL ELIMINAR'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ELIMINACIÓN COMPLETADA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total de productos eliminados: {productos_eliminados[0]:,}')
        self.stdout.write(f'Total de ingresos eliminados: {ingresos_eliminados[0]:,}')
        self.stdout.write(f'Total de items de ingreso eliminados: {items_eliminados[0]:,}')
        self.stdout.write(f'Total de movimientos eliminados: {movimientos_eliminados[0]:,}')
        self.stdout.write('')

