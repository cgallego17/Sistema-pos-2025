# -*- coding: utf-8 -*-
"""
Comando para limpiar cajas duplicadas y dejar solo una caja única
"""
from django.core.management.base import BaseCommand
from pos.models import Caja, CajaUsuario
from django.db.models import Sum
from django.utils import timezone
from pos.models import GastoCaja, Venta


class Command(BaseCommand):
    help = 'Limpia cajas duplicadas y deja solo una caja única en el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la limpieza sin preguntar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.ERROR('ADVERTENCIA: OPERACION IRREVERSIBLE'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        # Obtener Caja Principal
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR('[ERROR] No existe la Caja Principal'))
            return
        
        # Contar cajas existentes
        total_cajas = CajaUsuario.objects.filter(caja=caja_principal).count()
        cajas_abiertas = CajaUsuario.objects.filter(
            caja=caja_principal,
            fecha_cierre__isnull=True
        ).count()
        cajas_cerradas = CajaUsuario.objects.filter(
            caja=caja_principal,
            fecha_cierre__isnull=False
        ).count()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('ESTADO ACTUAL:'))
        self.stdout.write(f'  Total de cajas: {total_cajas}')
        self.stdout.write(f'  Cajas abiertas: {cajas_abiertas}')
        self.stdout.write(f'  Cajas cerradas: {cajas_cerradas}')
        
        if total_cajas == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No hay cajas para limpiar'))
            return
        
        if total_cajas == 1:
            self.stdout.write(self.style.SUCCESS('[OK] Ya existe solo una caja. No se necesita limpiar.'))
            return
        
        # Confirmación
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('Esta operacion NO se puede deshacer.'))
            self.stdout.write('')
            self.stdout.write('Se eliminaran todas las cajas excepto una.')
            self.stdout.write('Se conservara la caja mas reciente (por fecha de apertura).')
            self.stdout.write('')
            respuesta = input('¿Deseas continuar? (escribe "si" para confirmar): ')
            if respuesta.lower() != 'si':
                self.stdout.write(self.style.WARNING('Operacion cancelada'))
                return
        
        # Obtener la caja más reciente (la que se conservará)
        caja_conservar = CajaUsuario.objects.filter(
            caja=caja_principal
        ).order_by('-fecha_apertura').first()
        
        if not caja_conservar:
            self.stdout.write(self.style.ERROR('[ERROR] No se encontro ninguna caja para conservar'))
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('INICIANDO LIMPIEZA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Caja a conservar: ID={caja_conservar.id}')
        self.stdout.write(f'  Fecha apertura: {caja_conservar.fecha_apertura}')
        self.stdout.write(f'  Fecha cierre: {caja_conservar.fecha_cierre or "Abierta"}')
        self.stdout.write(f'  Monto inicial: ${caja_conservar.monto_inicial:,}')
        
        # Obtener todas las cajas excepto la que se conservará
        cajas_a_eliminar = CajaUsuario.objects.filter(
            caja=caja_principal
        ).exclude(id=caja_conservar.id)
        
        cantidad_eliminar = cajas_a_eliminar.count()
        
        if cantidad_eliminar == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No hay cajas duplicadas para eliminar'))
            return
        
        self.stdout.write('')
        self.stdout.write(f'Eliminando {cantidad_eliminar} caja(s) duplicada(s)...')
        
        # IMPORTANTE: Antes de eliminar, verificar si hay gastos o ventas asociadas
        # Si las hay, no podemos eliminar esas cajas sin perder datos
        cajas_con_datos = []
        for caja in cajas_a_eliminar:
            gastos_count = GastoCaja.objects.filter(caja_usuario=caja).count()
            ventas_count = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=caja.fecha_apertura,
                fecha__lte=caja.fecha_cierre if caja.fecha_cierre else timezone.now()
            ).count()
            
            if gastos_count > 0 or ventas_count > 0:
                cajas_con_datos.append({
                    'caja': caja,
                    'gastos': gastos_count,
                    'ventas': ventas_count
                })
        
        if cajas_con_datos:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('ADVERTENCIA: Se encontraron cajas con datos asociados:'))
            for item in cajas_con_datos:
                self.stdout.write(f'  Caja ID={item["caja"].id}: {item["gastos"]} gastos, {item["ventas"]} ventas')
            self.stdout.write('')
            self.stdout.write('Estas cajas NO se eliminaran para conservar los datos historicos.')
            self.stdout.write('Solo se eliminaran las cajas sin datos asociados.')
            
            # Eliminar solo las cajas sin datos
            cajas_sin_datos = cajas_a_eliminar.exclude(
                id__in=[item['caja'].id for item in cajas_con_datos]
            )
            eliminadas = cajas_sin_datos.count()
            if eliminadas > 0:
                cajas_sin_datos.delete()
                self.stdout.write(self.style.SUCCESS(f'[OK] {eliminadas} caja(s) sin datos eliminada(s)'))
        else:
            # Eliminar todas las cajas duplicadas
            eliminadas = cajas_a_eliminar.delete()[0]
            self.stdout.write(self.style.SUCCESS(f'[OK] {eliminadas} caja(s) eliminada(s)'))
        
        # Verificar resultado final
        total_final = CajaUsuario.objects.filter(caja=caja_principal).count()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('LIMPIEZA COMPLETADA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total de cajas restantes: {total_final}')
        
        if total_final == 1:
            self.stdout.write(self.style.SUCCESS('[OK] Ahora existe solo una caja en el sistema'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Quedan {total_final} cajas (algunas tienen datos historicos asociados)'))




