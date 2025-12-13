# -*- coding: utf-8 -*-
"""
Comando para revisar todas las cajas del sistema y verificar sus cálculos
"""
from django.core.management.base import BaseCommand
from pos.models import Caja, CajaUsuario, Venta, GastoCaja
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Revisa todas las cajas del sistema y verifica sus cálculos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('REVISIÓN COMPLETA DE TODAS LAS CAJAS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        # Obtener Caja Principal
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR('No existe la Caja Principal'))
            return
        
        # Obtener TODAS las cajas del sistema
        todas_cajas = CajaUsuario.objects.filter(
            caja=caja_principal
        ).order_by('-fecha_apertura')
        
        total_cajas = todas_cajas.count()
        
        if total_cajas == 0:
            self.stdout.write(self.style.ERROR('No existen cajas en el sistema'))
            return
        
        self.stdout.write(f'Total de cajas encontradas: {total_cajas}')
        self.stdout.write('')
        
        # Separar cajas abiertas y cerradas
        cajas_abiertas = todas_cajas.filter(fecha_cierre__isnull=True)
        cajas_cerradas = todas_cajas.filter(fecha_cierre__isnull=False)
        
        self.stdout.write(f'  - Cajas abiertas: {cajas_abiertas.count()}')
        self.stdout.write(f'  - Cajas cerradas: {cajas_cerradas.count()}')
        self.stdout.write('')
        
        # Revisar cada caja
        for idx, caja_item in enumerate(todas_cajas, 1):
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS(f'CAJA #{idx} - ID: {caja_item.id}'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            
            # Información básica
            estado = 'ABIERTA' if not caja_item.fecha_cierre else 'CERRADA'
            # Función para formatear números con espacios
            def formatear_numero(num):
                return f"{num:,}".replace(",", " ")
            
            self.stdout.write(f'Estado: {estado}')
            self.stdout.write(f'Fecha apertura: {caja_item.fecha_apertura}')
            if caja_item.fecha_cierre:
                self.stdout.write(f'Fecha cierre: {caja_item.fecha_cierre}')
            self.stdout.write(f'Usuario: {caja_item.usuario.username if caja_item.usuario else "N/A"}')
            if caja_item.monto_inicial:
                self.stdout.write(f'Monto inicial: ${formatear_numero(int(caja_item.monto_inicial))}')
            else:
                self.stdout.write('Monto inicial: $0')
            if caja_item.monto_final:
                self.stdout.write(f'Monto final: ${formatear_numero(int(caja_item.monto_final))}')
            self.stdout.write('')
            
            # Determinar período - usar desde la fecha de apertura de la caja
            if caja_item.fecha_cierre:
                # Caja cerrada: usar período completo de la caja
                inicio_periodo = caja_item.fecha_apertura
                fin_periodo = caja_item.fecha_cierre
                ventas_todas = Venta.objects.filter(
                    caja=caja_principal,
                    fecha__gte=inicio_periodo,
                    fecha__lte=fin_periodo,
                    completada=True
                )
            else:
                # Caja abierta: usar desde la fecha de apertura de la caja hasta ahora
                ventas_todas = Venta.objects.filter(
                    caja=caja_principal,
                    fecha__gte=caja_item.fecha_apertura,
                    completada=True
                )
            
            # Separar ventas válidas y anuladas
            ventas_validas = ventas_todas.filter(anulada=False)
            ventas_anuladas = ventas_todas.filter(anulada=True)
            
            total_ventas_validas = ventas_validas.aggregate(total=Sum('total'))['total'] or 0
            total_ventas_anuladas = ventas_anuladas.aggregate(total=Sum('total'))['total'] or 0
            cantidad_ventas_validas = ventas_validas.count()
            cantidad_ventas_anuladas = ventas_anuladas.count()
            
            # Gastos e ingresos
            gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_item)
            gastos = gastos_todos.filter(tipo='gasto')
            ingresos = gastos_todos.filter(tipo='ingreso')
            
            total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or 0
            total_ingresos = ingresos.aggregate(total=Sum('monto'))['total'] or 0
            cantidad_gastos = gastos.count()
            cantidad_ingresos = ingresos.count()
            
            # Convertir a enteros
            monto_inicial = int(caja_item.monto_inicial) if caja_item.monto_inicial else 0
            total_ventas_validas = int(total_ventas_validas)
            total_ventas_anuladas = int(total_ventas_anuladas)
            total_gastos = int(total_gastos)
            total_ingresos = int(total_ingresos)
            
            # Verificar gastos de devolución
            gastos_devolucion = gastos.filter(descripcion__icontains='Devolución por anulación')
            total_gastos_devolucion = gastos_devolucion.aggregate(total=Sum('monto'))['total'] or 0
            total_gastos_devolucion = int(total_gastos_devolucion)
            
            # Calcular saldo según la lógica del sistema
            if total_gastos_devolucion > 0:
                # Si hay gastos de devolución, las ventas anuladas ingresaron dinero
                saldo_calculado = monto_inicial + total_ventas_validas + total_ventas_anuladas + total_ingresos - total_gastos
            else:
                # Si NO hay gastos de devolución, las ventas anuladas no afectan el dinero físico
                saldo_calculado = monto_inicial + total_ventas_validas + total_ingresos - total_gastos
            
            # Función para formatear números con espacios
            def formatear_numero(num):
                return f"{num:,}".replace(",", " ")
            
            # Mostrar resumen
            self.stdout.write(self.style.SUCCESS('-' * 80))
            self.stdout.write('RESUMEN DE MOVIMIENTOS')
            self.stdout.write(self.style.SUCCESS('-' * 80))
            self.stdout.write(f'Ventas válidas: ${formatear_numero(total_ventas_validas)} ({cantidad_ventas_validas} ventas)')
            self.stdout.write(f'Ventas anuladas: ${formatear_numero(total_ventas_anuladas)} ({cantidad_ventas_anuladas} ventas)')
            self.stdout.write(f'Ingresos: ${formatear_numero(total_ingresos)} ({cantidad_ingresos} registros)')
            self.stdout.write(f'Gastos: ${formatear_numero(total_gastos)} ({cantidad_gastos} registros)')
            if total_gastos_devolucion > 0:
                self.stdout.write(f'  - Devoluciones: ${formatear_numero(total_gastos_devolucion)}')
            self.stdout.write('')
            
            # Mostrar cálculo
            self.stdout.write(self.style.SUCCESS('-' * 80))
            self.stdout.write('CÁLCULO DEL SALDO')
            self.stdout.write(self.style.SUCCESS('-' * 80))
            if total_gastos_devolucion > 0:
                self.stdout.write(f'Fórmula: Monto Inicial + Ventas Válidas + Ventas Anuladas + Ingresos - Gastos')
                self.stdout.write(f'  ${formatear_numero(monto_inicial)} + ${formatear_numero(total_ventas_validas)} + ${formatear_numero(total_ventas_anuladas)} + ${formatear_numero(total_ingresos)} - ${formatear_numero(total_gastos)}')
            else:
                self.stdout.write(f'Fórmula: Monto Inicial + Ventas Válidas + Ingresos - Gastos')
                self.stdout.write(f'  ${formatear_numero(monto_inicial)} + ${formatear_numero(total_ventas_validas)} + ${formatear_numero(total_ingresos)} - ${formatear_numero(total_gastos)}')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Saldo calculado: ${formatear_numero(saldo_calculado)}'))
            
            # Comparar con monto final si existe
            if caja_item.monto_final:
                monto_final = int(caja_item.monto_final)
                diferencia = saldo_calculado - monto_final
                self.stdout.write(f'Monto final registrado: ${formatear_numero(monto_final)}')
                
                if diferencia == 0:
                    self.stdout.write(self.style.SUCCESS('✓ El saldo cuadra perfectamente'))
                elif abs(diferencia) < 1000:
                    self.stdout.write(self.style.WARNING(f'⚠ Diferencia menor: ${formatear_numero(diferencia)}'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Diferencia significativa: ${formatear_numero(diferencia)}'))
            else:
                if estado == 'CERRADA':
                    self.stdout.write(self.style.WARNING('⚠ Caja cerrada sin monto final registrado'))
                else:
                    self.stdout.write('Caja abierta (sin monto final)')
            
            self.stdout.write('')
            
            # Mostrar ventas por método de pago
            ventas_efectivo = ventas_validas.filter(metodo_pago='efectivo').aggregate(total=Sum('total'))['total'] or 0
            ventas_tarjeta = ventas_validas.filter(metodo_pago='tarjeta').aggregate(total=Sum('total'))['total'] or 0
            ventas_transferencia = ventas_validas.filter(metodo_pago='transferencia').aggregate(total=Sum('total'))['total'] or 0
            
            if total_ventas_validas > 0:
                self.stdout.write('Ventas por método de pago:')
                self.stdout.write(f'  - Efectivo: ${formatear_numero(int(ventas_efectivo))}')
                self.stdout.write(f'  - Tarjeta: ${formatear_numero(int(ventas_tarjeta))}')
                self.stdout.write(f'  - Transferencia: ${formatear_numero(int(ventas_transferencia))}')
                self.stdout.write('')
        
        # Resumen final
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('RESUMEN GENERAL'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'Total de cajas revisadas: {total_cajas}')
        self.stdout.write(f'  - Abiertas: {cajas_abiertas.count()}')
        self.stdout.write(f'  - Cerradas: {cajas_cerradas.count()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Revisión completada'))

