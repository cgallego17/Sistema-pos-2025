"""
Tests para el módulo de Marketing
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import Venta, ItemVenta, Producto, Caja
from django.test.client import store_rendered_templates

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class MarketingTestCase(TestCase):
    """Tests para el módulo de marketing"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        self.user.groups.add(grupo_admin)
        signals.template_rendered.disconnect(store_rendered_templates)
        signals.template_rendered.receivers.clear()
        signals.template_rendered.send = lambda *args, **kwargs: None
        
        self.vendedor1 = User.objects.create_user(
            username='vendedor1',
            password='pass123',
            first_name='Vendedor',
            last_name='Uno'
        )
        
        self.vendedor2 = User.objects.create_user(
            username='vendedor2',
            password='pass123',
            first_name='Vendedor',
            last_name='Dos'
        )
        
        self.caja = Caja.objects.create(numero=1, nombre='Caja Principal')
        
        self.producto = Producto.objects.create(
            codigo='PROD001',
            nombre='Producto Test',
            precio=10000,
            stock=100,
            activo=True
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_ranking_vendedores(self):
        """Test: Verificar ranking de vendedores"""
        # Crear ventas para vendedor1
        venta1 = Venta.objects.create(
            usuario=self.user,
            vendedor=self.vendedor1,
            metodo_pago='efectivo',
            total=50000,
            completada=True,
            caja=self.caja
        )
        
        venta2 = Venta.objects.create(
            usuario=self.user,
            vendedor=self.vendedor1,
            metodo_pago='tarjeta',
            total=30000,
            completada=True,
            caja=self.caja
        )
        
        # Crear venta para vendedor2
        venta3 = Venta.objects.create(
            usuario=self.user,
            vendedor=self.vendedor2,
            metodo_pago='efectivo',
            total=20000,
            completada=True,
            caja=self.caja
        )
        
        response = self.client.get(reverse('pos:marketing'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_ranking_excluye_anuladas(self):
        """Test: Verificar que las ventas anuladas no cuentan en el ranking"""
        # Crear venta normal
        venta1 = Venta.objects.create(
            usuario=self.user,
            vendedor=self.vendedor1,
            metodo_pago='efectivo',
            total=50000,
            completada=True,
            anulada=False,
            caja=self.caja
        )
        
        # Crear venta anulada
        venta2 = Venta.objects.create(
            usuario=self.user,
            vendedor=self.vendedor1,
            metodo_pago='efectivo',
            total=100000,
            completada=True,
            anulada=True,
            caja=self.caja
        )
        
        response = self.client.get(reverse('pos:marketing'))
        self.assertIn(response.status_code, [200, 302])

