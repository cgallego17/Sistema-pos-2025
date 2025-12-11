"""
Comando de gestión para borrar todos los registros de caja, ventas e inventario
Elimina: CajaUsuario, GastoCaja, CajaGastosUsuario, Venta, ItemVenta,
         IngresoMercancia, ItemIngresoMercancia, SalidaMercancia, ItemSalidaMercancia, MovimientoStock
Mantiene: Caja (principal), CajaGastos (principal), Producto
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import (
    CajaUsuario, GastoCaja, CajaGastosUsuario, Venta, ItemVenta,
    IngresoMercancia, ItemIngresoMercancia, SalidaMercancia, ItemSalidaMercancia, MovimientoStock
)


class Command(BaseCommand):
    help = 'Borra todos los registros de caja, ventas e inventario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma la eliminación de todos los registros de caja',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    '[ADVERTENCIA] Este comando eliminará TODOS los registros de caja, ventas e inventario:\n'
                    '   - CajaUsuario (aperturas/cierres de caja)\n'
                    '   - GastoCaja (gastos e ingresos)\n'
                    '   - CajaGastosUsuario (cajas de gastos por usuario)\n'
                    '   - Venta (todas las ventas)\n'
                    '   - ItemVenta (items de las ventas)\n'
                    '   - IngresoMercancia (ingresos de mercancía)\n'
                    '   - ItemIngresoMercancia (items de ingresos)\n'
                    '   - SalidaMercancia (salidas de mercancía)\n'
                    '   - ItemSalidaMercancia (items de salidas)\n'
                    '   - MovimientoStock (movimientos de stock)\n\n'
                    'Para confirmar, ejecuta: python manage.py borrar_registros_caja --confirmar'
                )
            )
            return

        with transaction.atomic():
            self.stdout.write('Eliminando registros de caja, ventas e inventario...')

            # Eliminar en orden (respetando dependencias)
            # 1. Items de inventario (dependen de sus respectivos modelos)
            deleted_items_salida = ItemSalidaMercancia.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_items_salida[0]} registros de ItemSalidaMercancia'
                )
            )

            deleted_items_ingreso = ItemIngresoMercancia.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_items_ingreso[0]} registros de ItemIngresoMercancia'
                )
            )

            # 2. Salidas e Ingresos de mercancía
            deleted_salidas = SalidaMercancia.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_salidas[0]} registros de SalidaMercancia'
                )
            )

            deleted_ingresos = IngresoMercancia.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_ingresos[0]} registros de IngresoMercancia'
                )
            )

            # 3. Movimientos de stock
            deleted_movimientos = MovimientoStock.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_movimientos[0]} registros de MovimientoStock'
                )
            )

            # 4. Items de ventas
            deleted_items_venta = ItemVenta.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_items_venta[0]} registros de ItemVenta'
                )
            )

            # 5. Ventas
            deleted_ventas = Venta.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_ventas[0]} registros de Venta'
                )
            )

            # 6. GastoCaja (puede referenciar CajaUsuario)
            deleted_gastos = GastoCaja.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_gastos[0]} registros de GastoCaja'
                )
            )

            # 7. CajaGastosUsuario
            deleted_caja_gastos = CajaGastosUsuario.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_caja_gastos[0]} registros de CajaGastosUsuario'
                )
            )

            # 8. Finalmente CajaUsuario
            deleted_caja_usuario = CajaUsuario.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Eliminados {deleted_caja_usuario[0]} registros de CajaUsuario'
                )
            )

            total_eliminados = (
                deleted_items_salida[0] +
                deleted_items_ingreso[0] +
                deleted_salidas[0] +
                deleted_ingresos[0] +
                deleted_movimientos[0] +
                deleted_items_venta[0] +
                deleted_ventas[0] +
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
                self.style.WARNING(
                    '[NOTA] Se mantienen intactos: Caja, CajaGastos y Producto (solo se eliminan los movimientos de stock).'
                )
            )

