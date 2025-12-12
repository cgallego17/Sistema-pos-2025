# -*- coding: utf-8 -*-
"""
Comando para borrar solo registros de ventas y movimientos de caja
Elimina: Venta, ItemVenta, CajaUsuario, GastoCaja, CajaGastosUsuario
NO elimina: Inventario, Productos, Movimientos de Stock relacionados con inventario
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import (
    CajaUsuario, GastoCaja, CajaGastosUsuario, Venta, ItemVenta, MovimientoStock
)


class Command(BaseCommand):
    help = 'Borra todos los registros de ventas y movimientos de caja (sin tocar inventario)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma la eliminación de todos los registros de ventas y caja',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    '[ADVERTENCIA] Este comando eliminará TODOS los registros de ventas y caja:\n'
                    '   - Venta (todas las ventas)\n'
                    '   - ItemVenta (items de las ventas)\n'
                    '   - CajaUsuario (aperturas/cierres de caja)\n'
                    '   - GastoCaja (gastos e ingresos de caja)\n'
                    '   - CajaGastosUsuario (cajas de gastos por usuario)\n'
                    '   - MovimientoStock (solo movimientos relacionados con ventas)\n\n'
                    'NO se eliminarán:\n'
                    '   - Productos\n'
                    '   - Ingresos/Salidas de mercancía\n'
                    '   - Movimientos de stock relacionados con inventario\n\n'
                    'Para confirmar, ejecuta: python manage.py borrar_ventas_caja --confirmar'
                )
            )
            return

        with transaction.atomic():
            self.stdout.write('Eliminando registros de ventas y caja...')
            self.stdout.write('')

            # 1. Items de ventas
            deleted_items_venta = ItemVenta.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_items_venta[0]} registros de ItemVenta'
                )
            )

            # 2. Ventas
            deleted_ventas = Venta.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_ventas[0]} registros de Venta'
                )
            )

            # 3. Movimientos de stock relacionados con ventas
            deleted_movimientos_ventas = MovimientoStock.objects.filter(
                motivo__icontains='Venta'
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_movimientos_ventas[0]} movimientos de stock relacionados con ventas'
                )
            )

            # 4. GastoCaja (puede referenciar CajaUsuario)
            deleted_gastos = GastoCaja.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_gastos[0]} registros de GastoCaja'
                )
            )

            # 5. CajaGastosUsuario
            deleted_caja_gastos = CajaGastosUsuario.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_caja_gastos[0]} registros de CajaGastosUsuario'
                )
            )

            # 6. Finalmente CajaUsuario
            deleted_caja_usuario = CajaUsuario.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_caja_usuario[0]} registros de CajaUsuario'
                )
            )

            total_eliminados = (
                deleted_items_venta[0] +
                deleted_ventas[0] +
                deleted_movimientos_ventas[0] +
                deleted_gastos[0] +
                deleted_caja_gastos[0] +
                deleted_caja_usuario[0]
            )

            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'[COMPLETADO] Proceso completado. Total de registros eliminados: {total_eliminados}'
                )
            )
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    '[NOTA] Se mantienen intactos: Productos, Ingresos/Salidas de mercancía y movimientos de stock de inventario.'
                )
            )

