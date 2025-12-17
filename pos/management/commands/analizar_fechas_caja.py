"""
Script para analizar fechas de ventas y cajas
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from pos.models import Venta, CajaUsuario, GastoCaja
from django.utils import timezone


class Command(BaseCommand):
    help = 'Analiza fechas de ventas y cajas'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('ANALISIS DE FECHAS')
        self.stdout.write('=' * 80)
        
        # Ventas por fecha
        self.stdout.write('\nVENTAS POR FECHA:')
        ventas_por_fecha = Venta.objects.filter(completada=True).extra(
            select={'fecha_dia': 'DATE(fecha)'}
        ).values('fecha_dia').annotate(count=Count('id')).order_by('fecha_dia')
        
        for v in ventas_por_fecha:
            self.stdout.write(f'  {v["fecha_dia"]}: {v["count"]} ventas')
        
        # CajasUsuario
        self.stdout.write('\nCAJAS USUARIO:')
        cajas = CajaUsuario.objects.all().order_by('fecha_apertura')
        for c in cajas:
            estado = 'Abierta' if c.fecha_cierre is None else f'Cerrada: {c.fecha_cierre}'
            self.stdout.write(f'  ID: {c.id}, Apertura: {c.fecha_apertura}, {estado}')
        
        # Gastos por fecha
        self.stdout.write('\nGASTOS POR FECHA:')
        gastos_por_fecha = GastoCaja.objects.extra(
            select={'fecha_dia': 'DATE(fecha)'}
        ).values('fecha_dia').annotate(count=Count('id')).order_by('fecha_dia')
        
        for g in gastos_por_fecha:
            self.stdout.write(f'  {g["fecha_dia"]}: {g["count"]} gastos')
        
        # Gastos fuera de periodo
        self.stdout.write('\nGASTOS FUERA DE PERIODO:')
        for gasto in GastoCaja.objects.filter(caja_usuario__isnull=False).select_related('caja_usuario'):
            caja = gasto.caja_usuario
            if caja.fecha_cierre:
                fuera = gasto.fecha < caja.fecha_apertura or gasto.fecha > caja.fecha_cierre
            else:
                fuera = gasto.fecha < caja.fecha_apertura
            
            if fuera:
                self.stdout.write(f'  Gasto ID {gasto.id}: Fecha {gasto.fecha}, Caja {caja.id} (Apertura: {caja.fecha_apertura})')
        
        self.stdout.write('\n' + '=' * 80 + '\n')







