"""
Comando de gestión para resetear todos los stocks de productos a cero
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import Producto


class Command(BaseCommand):
    help = 'Resetea todos los stocks de productos a cero'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma el reseteo de todos los stocks a cero',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    '[ADVERTENCIA] Este comando reseteará TODOS los stocks de productos a cero.\n\n'
                    'Para confirmar, ejecuta: python manage.py resetear_stock_productos --confirmar'
                )
            )
            return

        with transaction.atomic():
            # Contar productos antes de actualizar
            total_productos = Producto.objects.count()
            
            self.stdout.write('Reseteando stocks de productos a cero...')
            
            # Actualizar todos los productos
            productos_actualizados = Producto.objects.update(stock=0)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Stocks reseteados a cero para {productos_actualizados} productos'
                )
            )
            
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'[COMPLETADO] Proceso completado. Total de productos actualizados: {productos_actualizados}'
                )
            )




