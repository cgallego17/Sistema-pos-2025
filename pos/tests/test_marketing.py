"""
Tests para el módulo de Marketing
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from pos.models import Venta, ItemVenta, Producto, Caja


class MarketingTestCase(TestCase):
    """Tests para el módulo de marketing"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
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
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se muestran los vendedores
        self.assertContains(response, 'Vendedor Uno')
        self.assertContains(response, 'Vendedor Dos')
    
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
        self.assertEqual(response.status_code, 200)
        
        # El ranking debe mostrar solo la venta no anulada
        vendedores = response.context.get('vendedores', [])
        for vendedor_data in vendedores:
            if vendedor_data['vendedor'] == self.vendedor1:
                # Debe tener solo 50000, no 150000
                self.assertEqual(vendedor_data['total_ventas'], 50000)

