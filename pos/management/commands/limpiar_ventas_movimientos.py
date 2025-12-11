# -*- coding: utf-8 -*-
"""
Comando para limpiar TODOS los datos de ventas y movimientos de la caja
ADVERTENCIA: Esta operación es IRREVERSIBLE
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import (
    Venta, ItemVenta, GastoCaja, CajaUsuario, Caja
)
from django.db.models import Count


class Command(BaseCommand):
    help = 'Elimina TODOS los datos de ventas y movimientos de la caja (IRREVERSIBLE)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación sin preguntar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.ERROR('ADVERTENCIA: OPERACION IRREVERSIBLE'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Este comando eliminará PERMANENTEMENTE:'))
        self.stdout.write('  - Todas las ventas (Venta)')
        self.stdout.write('  - Todos los items de venta (ItemVenta)')
        self.stdout.write('  - Todos los movimientos de caja (GastoCaja)')
        self.stdout.write('  - Todas las cajas de usuario (CajaUsuario)')
        self.stdout.write('')
        
        # Contar registros antes de eliminar
        total_ventas = Venta.objects.count()
        total_items = ItemVenta.objects.count()
        total_gastos = GastoCaja.objects.count()
        total_cajas = CajaUsuario.objects.count()
        
        self.stdout.write(self.style.SUCCESS('Registros a eliminar:'))
        self.stdout.write(f'  - Ventas: {total_ventas:,}')
        self.stdout.write(f'  - Items de venta: {total_items:,}')
        self.stdout.write(f'  - Movimientos de caja: {total_gastos:,}')
        self.stdout.write(f'  - Cajas de usuario: {total_cajas:,}')
        self.stdout.write('')
        
        if total_ventas == 0 and total_items == 0 and total_gastos == 0 and total_cajas == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No hay datos para eliminar. La base de datos ya esta limpia.'))
            return
        
        # Confirmación
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('Esta operacion NO se puede deshacer.'))
            confirmacion = input('¿Estás SEGURO de que quieres continuar? Escribe "SI" para confirmar: ')
            
            if confirmacion.upper() != 'SI':
                self.stdout.write(self.style.SUCCESS('Operación cancelada.'))
                return
        
        # Proceder con la eliminación
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Iniciando eliminación...'))
        
        try:
            with transaction.atomic():
                # Eliminar items de venta primero (por las foreign keys)
                self.stdout.write('  - Eliminando items de venta...')
                items_eliminados = ItemVenta.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    [OK] {items_eliminados[0]:,} items eliminados'))
                
                # Eliminar ventas
                self.stdout.write('  - Eliminando ventas...')
                ventas_eliminadas = Venta.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    [OK] {ventas_eliminadas[0]:,} ventas eliminadas'))
                
                # Eliminar movimientos de caja
                self.stdout.write('  - Eliminando movimientos de caja...')
                gastos_eliminados = GastoCaja.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    [OK] {gastos_eliminados[0]:,} movimientos eliminados'))
                
                # Eliminar cajas de usuario
                self.stdout.write('  - Eliminando cajas de usuario...')
                cajas_eliminadas = CajaUsuario.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    [OK] {cajas_eliminadas[0]:,} cajas eliminadas'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('LIMPIEZA COMPLETADA EXITOSAMENTE'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Resumen:'))
            self.stdout.write(f'  - Items de venta eliminados: {items_eliminados[0]:,}')
            self.stdout.write(f'  - Ventas eliminadas: {ventas_eliminadas[0]:,}')
            self.stdout.write(f'  - Movimientos eliminados: {gastos_eliminados[0]:,}')
            self.stdout.write(f'  - Cajas eliminadas: {cajas_eliminadas[0]:,}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Nota: Las cajas principales (Caja) y otros datos NO se eliminaron.'))
            self.stdout.write(self.style.WARNING('Solo se eliminaron ventas, items, movimientos y cajas de usuario.'))
            
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('ERROR AL ELIMINAR DATOS'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('La transacción fue revertida. No se eliminó ningún dato.'))
            raise

