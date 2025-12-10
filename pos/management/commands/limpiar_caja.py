"""
Comando para limpiar todas las ventas, gastos e ingresos de la caja
"""
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date

from pos.models import (
    Venta, ItemVenta, GastoCaja, CajaUsuario
)


class Command(BaseCommand):
    help = 'Limpia todas las ventas, gastos e ingresos de la caja'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma que quieres eliminar todos los datos',
        )
        parser.add_argument(
            '--solo-hoy',
            action='store_true',
            help='Elimina solo los movimientos del día de hoy',
        )

    def handle(self, *args, **options):
        hoy = date.today()
        
        if not options['confirmar']:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('ADVERTENCIA: Este comando eliminará datos'))
            self.stdout.write(self.style.WARNING('=' * 70))
            
            if options['solo_hoy']:
                self.stdout.write(f'\nSe eliminarán TODOS los movimientos del día de hoy ({hoy.strftime("%d/%m/%Y")})')
            else:
                self.stdout.write('\nSe eliminarán TODOS los movimientos de la caja:')
                self.stdout.write('  - Todas las ventas')
                self.stdout.write('  - Todos los gastos')
                self.stdout.write('  - Todos los ingresos')
            
            self.stdout.write('\n' + self.style.ERROR('Esta acción NO se puede deshacer'))
            self.stdout.write('\nPara confirmar, ejecuta el comando con --confirmar')
            if options['solo_hoy']:
                self.stdout.write('\nEjemplo: python manage.py limpiar_caja --solo-hoy --confirmar')
            else:
                self.stdout.write('\nEjemplo: python manage.py limpiar_caja --confirmar')
            return
        
        self.stdout.write('=' * 70)
        self.stdout.write('LIMPIEZA DE CAJA')
        self.stdout.write('=' * 70)
        
        if options['solo_hoy']:
            self.stdout.write(f'\nEliminando movimientos del día: {hoy.strftime("%d/%m/%Y")}')
            
            # Filtrar por fecha del día actual
            inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Contar antes de eliminar
            ventas_count = Venta.objects.filter(
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).count()
            
            gastos_count = GastoCaja.objects.filter(
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).count()
            
            # Eliminar items de venta primero (foreign key)
            ItemVenta.objects.filter(
                venta__fecha__gte=inicio_dia,
                venta__fecha__lte=fin_dia
            ).delete()
            
            # Eliminar ventas
            ventas_eliminadas = Venta.objects.filter(
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).delete()[0]
            
            # Eliminar gastos e ingresos
            gastos_eliminados = GastoCaja.objects.filter(
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia
            ).delete()[0]
            
            self.stdout.write(f'\n[OK] Eliminadas {ventas_eliminadas} ventas del día')
            self.stdout.write(f'[OK] Eliminados {gastos_eliminados} gastos/ingresos del día')
            
        else:
            self.stdout.write('\nEliminando TODOS los movimientos de la caja...')
            
            # Contar antes de eliminar
            ventas_count = Venta.objects.count()
            gastos_count = GastoCaja.objects.count()
            
            # Eliminar items de venta primero (foreign key)
            items_eliminados = ItemVenta.objects.all().delete()[0]
            self.stdout.write(f'[OK] Eliminados {items_eliminados} items de venta')
            
            # Eliminar ventas
            ventas_eliminadas = Venta.objects.all().delete()[0]
            self.stdout.write(f'[OK] Eliminadas {ventas_eliminadas} ventas')
            
            # Eliminar gastos e ingresos
            gastos_eliminados = GastoCaja.objects.all().delete()[0]
            self.stdout.write(f'[OK] Eliminados {gastos_eliminados} gastos/ingresos')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('LIMPIEZA COMPLETADA'))
        self.stdout.write('=' * 70)
        
        # Mostrar estado actual
        ventas_restantes = Venta.objects.count()
        gastos_restantes = GastoCaja.objects.count()
        
        self.stdout.write(f'\nEstado actual:')
        self.stdout.write(f'  Ventas restantes: {ventas_restantes}')
        self.stdout.write(f'  Gastos/Ingresos restantes: {gastos_restantes}')

