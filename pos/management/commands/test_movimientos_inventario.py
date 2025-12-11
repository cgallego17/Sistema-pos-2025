"""
Script de prueba para verificar el flujo completo de movimientos de inventario
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from pos.models import (
    Producto, MovimientoStock, Venta, ItemVenta,
    IngresoMercancia, ItemIngresoMercancia,
    SalidaMercancia, ItemSalidaMercancia
)
from django.db import transaction


class Command(BaseCommand):
    help = 'Prueba completa del flujo de movimientos de inventario'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('PRUEBA DE FLUJO DE MOVIMIENTOS DE INVENTARIO'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Obtener o crear usuario de prueba
        usuario, _ = User.objects.get_or_create(
            username='test_movimientos',
            defaults={'email': 'test@test.com', 'first_name': 'Test', 'last_name': 'Usuario'}
        )
        
        # Obtener un producto de prueba
        producto = Producto.objects.filter(activo=True).first()
        if not producto:
            self.stdout.write(self.style.ERROR('No hay productos activos en el sistema'))
            return
        
        self.stdout.write(f'Producto de prueba: {producto.nombre} (Codigo: {producto.codigo})')
        self.stdout.write(f'Stock inicial (actual en BD): {producto.stock}')
        self.stdout.write('')
        
        # El stock inicial para el cálculo debe ser 0, ya que los movimientos registran
        # el stock desde el inicio. Si hay movimientos antiguos, el stock inicial real
        # sería el stock_anterior del primer movimiento.
        movimientos_ordenados = MovimientoStock.objects.filter(producto=producto).order_by('fecha')
        if movimientos_ordenados.exists():
            primer_mov = movimientos_ordenados.first()
            stock_inicial_calculado = primer_mov.stock_anterior
            self.stdout.write(f'Stock inicial segun primer movimiento: {stock_inicial_calculado}')
            self.stdout.write('')
            stock_inicial = stock_inicial_calculado
        else:
            stock_inicial = producto.stock
        
        # ============================================
        # PRUEBA 1: Verificar movimientos existentes
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 1: Verificando movimientos existentes'))
        movimientos_existentes = MovimientoStock.objects.filter(producto=producto).count()
        self.stdout.write(f'  Movimientos existentes para este producto: {movimientos_existentes}')
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 2: Verificar consistencia de stock_anterior y stock_nuevo
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 2: Verificando consistencia de movimientos'))
        movimientos = list(MovimientoStock.objects.filter(producto=producto).order_by('fecha'))
        
        errores_consistencia = []
        stock_calculado = stock_inicial
        
        # Calcular stock desde el inicio sumando/restando movimientos
        for mov in movimientos:
            # Verificar que stock_anterior + cantidad (si ingreso) o - cantidad (si salida) = stock_nuevo
            if mov.tipo == 'ingreso':
                stock_esperado = mov.stock_anterior + mov.cantidad
            elif mov.tipo == 'salida':
                stock_esperado = mov.stock_anterior - mov.cantidad
            else:  # ajuste
                stock_esperado = mov.stock_nuevo
            
            if stock_esperado != mov.stock_nuevo:
                errores_consistencia.append({
                    'movimiento': mov,
                    'stock_anterior': mov.stock_anterior,
                    'stock_nuevo': mov.stock_nuevo,
                    'stock_esperado': stock_esperado,
                    'tipo': mov.tipo,
                    'cantidad': mov.cantidad,
                    'error_tipo': 'calculo'
                })
            
            # Actualizar stock calculado desde el inicio
            if mov.tipo == 'ingreso':
                stock_calculado += mov.cantidad
            elif mov.tipo == 'salida':
                stock_calculado -= mov.cantidad
            
            # Verificar que el stock_anterior del siguiente movimiento sea igual al stock_nuevo del anterior
            # Solo si están en secuencia temporal cercana (mismo día o siguiente)
            if movimientos.index(mov) < len(movimientos) - 1:
                siguiente_idx = movimientos.index(mov) + 1
                siguiente_mov = movimientos[siguiente_idx]
                
                # Solo verificar consecutividad si los movimientos están en el mismo día o días consecutivos
                diferencia_dias = abs((siguiente_mov.fecha.date() - mov.fecha.date()).days)
                if diferencia_dias <= 1:  # Mismo día o día siguiente
                    if mov.stock_nuevo != siguiente_mov.stock_anterior:
                        errores_consistencia.append({
                            'tipo': 'consecutividad',
                            'movimiento_actual': mov,
                            'movimiento_siguiente': siguiente_mov,
                            'stock_nuevo_actual': mov.stock_nuevo,
                            'stock_anterior_siguiente': siguiente_mov.stock_anterior,
                            'error_tipo': 'consecutividad',
                            'diferencia_dias': diferencia_dias
                        })
        
        if errores_consistencia:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Se encontraron {len(errores_consistencia)} errores de consistencia:'))
            for error in errores_consistencia[:5]:  # Mostrar solo los primeros 5
                if error.get('error_tipo') == 'consecutividad':
                    mov_actual = error['movimiento_actual']
                    mov_sig = error['movimiento_siguiente']
                    fecha_actual = mov_actual.fecha.strftime('%d/%m/%Y %H:%M')
                    fecha_sig = mov_sig.fecha.strftime('%d/%m/%Y %H:%M')
                    self.stdout.write(
                        self.style.ERROR(
                            f"    - Movimiento #{mov_actual.id} ({fecha_actual}, stock_nuevo={error['stock_nuevo_actual']}) "
                            f"no coincide con stock_anterior del siguiente #{mov_sig.id} ({fecha_sig}, stock_anterior={error['stock_anterior_siguiente']})"
                        )
                    )
                else:
                    mov = error['movimiento']
                    fecha_str = mov.fecha.strftime('%d/%m/%Y %H:%M')
                    self.stdout.write(
                        self.style.ERROR(
                            f"    - Movimiento #{mov.id} ({fecha_str}, {error['tipo']}): "
                            f"stock_anterior={error['stock_anterior']}, stock_nuevo={error['stock_nuevo']}, "
                            f"stock_esperado={error['stock_esperado']}"
                        )
                    )
            if len(errores_consistencia) > 5:
                self.stdout.write(self.style.ERROR(f"    ... y {len(errores_consistencia) - 5} errores mas"))
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Todos los movimientos son consistentes'))
        
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 3: Verificar que el stock actual coincida con los movimientos
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 3: Verificando stock actual vs movimientos'))
        producto.refresh_from_db()
        stock_actual = producto.stock
        
        if stock_calculado != stock_actual:
            self.stdout.write(
                self.style.ERROR(
                    f'  [ERROR] Stock calculado ({stock_calculado}) no coincide con stock actual ({stock_actual})'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  [OK] Stock calculado ({stock_calculado}) coincide con stock actual ({stock_actual})'
                )
            )
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 4: Verificar que todos los movimientos tengan usuario
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 4: Verificando usuarios en movimientos'))
        movimientos_sin_usuario = MovimientoStock.objects.filter(producto=producto, usuario__isnull=True).count()
        if movimientos_sin_usuario > 0:
            self.stdout.write(
                self.style.ERROR(f'  [ERROR] {movimientos_sin_usuario} movimientos sin usuario')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Todos los movimientos tienen usuario'))
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 5: Verificar que todos los movimientos tengan motivo
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 5: Verificando motivos en movimientos'))
        movimientos_sin_motivo = MovimientoStock.objects.filter(
            producto=producto
        ).filter(
            Q(motivo__isnull=True) | Q(motivo='')
        ).count()
        if movimientos_sin_motivo > 0:
            self.stdout.write(
                self.style.WARNING(f'  [ADVERTENCIA] {movimientos_sin_motivo} movimientos sin motivo')
            )
        else:
            self.stdout.write(self.style.SUCCESS('  [OK] Todos los movimientos tienen motivo'))
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 6: Resumen de movimientos por tipo
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 6: Resumen de movimientos por tipo'))
        from django.db.models import Count, Sum
        
        resumen = MovimientoStock.objects.filter(producto=producto).values('tipo').annotate(
            total=Count('id'),
            cantidad_total=Sum('cantidad')
        ).order_by('tipo')
        
        for item in resumen:
            tipo_display = dict(MovimientoStock.TIPOS).get(item['tipo'], item['tipo'])
            self.stdout.write(
                f"  {tipo_display}: {item['total']} movimientos, cantidad total: {item['cantidad_total']}"
            )
        self.stdout.write('')
        
        # ============================================
        # PRUEBA 7: Verificar movimientos recientes (últimos 10)
        # ============================================
        self.stdout.write(self.style.WARNING('PRUEBA 7: Últimos 10 movimientos'))
        ultimos_movimientos = MovimientoStock.objects.filter(
            producto=producto
        ).order_by('-fecha')[:10]
        
        for mov in ultimos_movimientos:
            tipo_display = dict(MovimientoStock.TIPOS).get(mov.tipo, mov.tipo)
            fecha_str = mov.fecha.strftime('%d/%m/%Y %H:%M')
            usuario_str = mov.usuario.username if mov.usuario else 'N/A'
            motivo_str = mov.motivo[:50] if mov.motivo else 'Sin motivo'
            self.stdout.write(
                f"  [{fecha_str}] {tipo_display}: {mov.cantidad} unidades "
                f"(Stock: {mov.stock_anterior} -> {mov.stock_nuevo}) "
                f"- {motivo_str} - Usuario: {usuario_str}"
            )
        self.stdout.write('')
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN DE PRUEBAS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Producto: {producto.nombre} ({producto.codigo})')
        self.stdout.write(f'Stock inicial: {stock_inicial}')
        self.stdout.write(f'Stock actual: {stock_actual}')
        self.stdout.write(f'Stock calculado desde movimientos: {stock_calculado}')
        self.stdout.write(f'Total de movimientos: {movimientos_existentes}')
        self.stdout.write(f'Errores de consistencia: {len(errores_consistencia)}')
        self.stdout.write('')
        
        if len(errores_consistencia) == 0 and stock_calculado == stock_actual:
            self.stdout.write(self.style.SUCCESS('[RESULTADO] OK - Flujo de movimientos es CONGRUENTE'))
        else:
            self.stdout.write(self.style.ERROR('[RESULTADO] ERROR - Flujo de movimientos tiene INCONSISTENCIAS'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('NOTA: Las inconsistencias pueden deberse a:'))
            self.stdout.write('  - Reseteo manual de stock sin crear movimiento de ajuste')
            self.stdout.write('  - Movimientos antiguos que no reflejan el estado actual del stock')
            self.stdout.write('  - Errores en la creacion de movimientos')
        
        self.stdout.write('')

