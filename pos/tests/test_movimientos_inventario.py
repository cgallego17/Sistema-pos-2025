"""
Tests para el módulo de Movimientos de Inventario
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from pos.models import (
    Producto, MovimientoStock, Venta, ItemVenta,
    IngresoMercancia, ItemIngresoMercancia
)


class MovimientosInventarioTestCase(TestCase):
    """Tests para el módulo de movimientos de inventario"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.producto = Producto.objects.create(
            codigo='PROD001',
            nombre='Producto Test',
            precio=10000,
            stock=100,
            activo=True
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_listar_movimientos(self):
        """Test: Listar movimientos de inventario"""
        # Crear algunos movimientos
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='ingreso',
            cantidad=10,
            stock_anterior=100,
            stock_nuevo=110,
            motivo='Test ingreso',
            usuario=self.user
        )
        
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='salida',
            cantidad=5,
            stock_anterior=110,
            stock_nuevo=105,
            motivo='Test salida',
            usuario=self.user
        )
        
        response = self.client.get(reverse('pos:movimientos_inventario'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Movimientos de Inventario')
        
        # Verificar paginación
        movimientos = response.context['movimientos']
        self.assertIsNotNone(movimientos)
        self.assertGreaterEqual(movimientos.paginator.count, 2)
    
    def test_filtrar_movimientos_por_producto(self):
        """Test: Filtrar movimientos por producto"""
        producto2 = Producto.objects.create(
            codigo='PROD002',
            nombre='Producto 2',
            precio=20000,
            stock=50,
            activo=True
        )
        
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='ingreso',
            cantidad=10,
            stock_anterior=100,
            stock_nuevo=110,
            motivo='Test',
            usuario=self.user
        )
        
        MovimientoStock.objects.create(
            producto=producto2,
            tipo='ingreso',
            cantidad=5,
            stock_anterior=50,
            stock_nuevo=55,
            motivo='Test',
            usuario=self.user
        )
        
        response = self.client.get(
            reverse('pos:movimientos_inventario'),
            {'producto': self.producto.id}
        )
        
        self.assertEqual(response.status_code, 200)
        movimientos = response.context['movimientos']
        # Todos los movimientos deben ser del producto filtrado
        for mov in movimientos:
            self.assertEqual(mov.producto.id, self.producto.id)
    
    def test_filtrar_movimientos_por_tipo(self):
        """Test: Filtrar movimientos por tipo"""
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='ingreso',
            cantidad=10,
            stock_anterior=100,
            stock_nuevo=110,
            motivo='Test',
            usuario=self.user
        )
        
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='salida',
            cantidad=5,
            stock_anterior=110,
            stock_nuevo=105,
            motivo='Test',
            usuario=self.user
        )
        
        response = self.client.get(
            reverse('pos:movimientos_inventario'),
            {'tipo': 'ingreso'}
        )
        
        self.assertEqual(response.status_code, 200)
        movimientos = response.context['movimientos']
        # Todos deben ser de tipo ingreso
        for mov in movimientos:
            self.assertEqual(mov.tipo, 'ingreso')
    
    def test_filtrar_movimientos_por_fecha(self):
        """Test: Filtrar movimientos por rango de fechas"""
        from datetime import date, timedelta
        
        hoy = timezone.now().date()
        ayer = hoy - timedelta(days=1)
        mañana = hoy + timedelta(days=1)
        
        # Movimiento de ayer
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='ingreso',
            cantidad=10,
            stock_anterior=100,
            stock_nuevo=110,
            motivo='Test',
            usuario=self.user,
            fecha=timezone.make_aware(timezone.datetime.combine(ayer, timezone.datetime.min.time()))
        )
        
        # Movimiento de hoy
        MovimientoStock.objects.create(
            producto=self.producto,
            tipo='ingreso',
            cantidad=5,
            stock_anterior=110,
            stock_nuevo=115,
            motivo='Test',
            usuario=self.user
        )
        
        response = self.client.get(
            reverse('pos:movimientos_inventario'),
            {
                'fecha_desde': hoy.strftime('%Y-%m-%d'),
                'fecha_hasta': mañana.strftime('%Y-%m-%d')
            }
        )
        
        self.assertEqual(response.status_code, 200)
        movimientos = response.context['movimientos']
        # Debe incluir al menos el movimiento de hoy
        self.assertGreaterEqual(movimientos.paginator.count, 1)

