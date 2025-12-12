# -*- coding: utf-8 -*-
"""
Comando para borrar/resetear los saldos de las cajas
Resetea monto_inicial y monto_final a 0 en CajaUsuario y CajaGastosUsuario
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import CajaUsuario, CajaGastosUsuario


class Command(BaseCommand):
    help = 'Borra/resetea los saldos (monto_inicial y monto_final) de todas las cajas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la operación sin preguntar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('RESETEAR SALDOS DE CAJAS'))
        self.stdout.write(self.style.WARNING('=' * 70))

        # Contar cajas con saldos
        cajas_usuario = CajaUsuario.objects.all()
        cajas_gastos = CajaGastosUsuario.objects.all()
        
        total_cajas_usuario = cajas_usuario.count()
        total_cajas_gastos = cajas_gastos.count()
        
        cajas_con_monto_inicial = cajas_usuario.exclude(monto_inicial=0).count()
        cajas_con_monto_final = cajas_usuario.exclude(monto_final__isnull=True).exclude(monto_final=0).count()
        cajas_gastos_con_monto_inicial = cajas_gastos.exclude(monto_inicial=0).count()
        cajas_gastos_con_monto_final = cajas_gastos.exclude(monto_final__isnull=True).exclude(monto_final=0).count()

        self.stdout.write(f'Cajas de Usuario encontradas: {total_cajas_usuario}')
        self.stdout.write(f'  - Con monto inicial diferente de 0: {cajas_con_monto_inicial}')
        self.stdout.write(f'  - Con monto final diferente de 0/null: {cajas_con_monto_final}')
        self.stdout.write('')
        self.stdout.write(f'Cajas Gastos Usuario encontradas: {total_cajas_gastos}')
        self.stdout.write(f'  - Con monto inicial diferente de 0: {cajas_gastos_con_monto_inicial}')
        self.stdout.write(f'  - Con monto final diferente de 0/null: {cajas_gastos_con_monto_final}')
        self.stdout.write('')

        if total_cajas_usuario == 0 and total_cajas_gastos == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No hay cajas para resetear.'))
            return

        # Confirmación
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('Esta operacion reseteara todos los saldos a 0.'))
            respuesta = input('Escribe "si" para confirmar: ')
            if respuesta.lower() != 'si':
                self.stdout.write(self.style.WARNING('Operación cancelada.'))
                return

        self.stdout.write(self.style.WARNING('Reseteando saldos de cajas...'))
        
        try:
            with transaction.atomic():
                # Resetear CajaUsuario
                if total_cajas_usuario > 0:
                    self.stdout.write('  - Reseteando Cajas de Usuario...')
                    actualizadas = cajas_usuario.update(
                        monto_inicial=0,
                        monto_final=None
                    )
                    self.stdout.write(self.style.SUCCESS(f'    {actualizadas} cajas actualizadas'))
                
                # Resetear CajaGastosUsuario
                if total_cajas_gastos > 0:
                    self.stdout.write('  - Reseteando Cajas Gastos Usuario...')
                    actualizadas_gastos = cajas_gastos.update(
                        monto_inicial=0,
                        monto_final=None
                    )
                    self.stdout.write(self.style.SUCCESS(f'    {actualizadas_gastos} cajas actualizadas'))
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write(self.style.SUCCESS('SALDOS RESETEADOS EXITOSAMENTE'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Nota: Los registros de cajas se mantienen, solo se resetean los montos.'))

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('ERROR AL RESETEAR SALDOS'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR(f'Se produjo un error: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))



