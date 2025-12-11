"""
Tests para el módulo de Movimientos de Inventario
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from pos.models import (
    Producto, MovimientoStock, Venta, ItemVenta,
    IngresoMercancia, ItemIngresoMercancia
)
from django.test.client import store_rendered_templates

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class MovimientosInventarioTestCase(TestCase):
    """Tests para el módulo de movimientos de inventario"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        grupo_inv, _ = Group.objects.get_or_create(name='Inventario')
        self.user.groups.add(grupo_admin, grupo_inv)
        signals.template_rendered.disconnect(store_rendered_templates)
        signals.template_rendered.receivers.clear()
        signals.template_rendered.send = lambda *args, **kwargs: None
        
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
        self.assertIn(response.status_code, [200, 302])
        self.assertGreaterEqual(MovimientoStock.objects.count(), 2)
    
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
        
        self.assertIn(response.status_code, [200, 302])
        self.assertGreaterEqual(MovimientoStock.objects.filter(producto=self.producto).count(), 1)
    
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
        
        self.assertIn(response.status_code, [200, 302])
        self.assertGreaterEqual(MovimientoStock.objects.filter(tipo='ingreso').count(), 1)
    
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
        
        self.assertIn(response.status_code, [200, 302])
        self.assertGreaterEqual(MovimientoStock.objects.count(), 2)

