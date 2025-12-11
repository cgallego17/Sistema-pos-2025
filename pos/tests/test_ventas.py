"""
Tests para el módulo de Ventas
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from pos.models import (
    Producto, Venta, ItemVenta, MovimientoStock, Caja, CajaUsuario
)
import json


class VentasTestCase(TestCase):
    """Tests para el módulo de ventas"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com'
        )
        
        # Crear caja
        self.caja = Caja.objects.create(numero=1, nombre='Caja Principal')
        
        # Crear productos
        self.producto1 = Producto.objects.create(
            codigo='PROD001',
            nombre='Producto Test 1',
            precio=10000,
            stock=100,
            activo=True
        )
        
        self.producto2 = Producto.objects.create(
            codigo='PROD002',
            nombre='Producto Test 2',
            precio=20000,
            stock=50,
            activo=True
        )
        
        # Crear cliente de prueba
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_crear_venta_efectivo(self):
        """Test: Crear una venta en efectivo"""
        # Datos de la venta
        items = [
            {'id': self.producto1.id, 'cantidad': 2, 'precio': 10000},
            {'id': self.producto2.id, 'cantidad': 1, 'precio': 20000}
        ]
        
        # Crear venta
        response = self.client.post(reverse('pos:procesar_venta'), {
            'items': json.dumps(items),
            'metodo_pago': 'efectivo',
            'monto_recibido': 50000,
            'vendedor_id': self.user.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que la venta se creó
        venta = Venta.objects.last()
        self.assertIsNotNone(venta)
        self.assertEqual(venta.metodo_pago, 'efectivo')
        self.assertEqual(venta.total, 40000)  # 2*10000 + 1*20000
        
        # Verificar que el stock se actualizó
        self.producto1.refresh_from_db()
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto1.stock, 98)  # 100 - 2
        self.assertEqual(self.producto2.stock, 49)  # 50 - 1
        
        # Verificar movimientos de stock
        movimientos = MovimientoStock.objects.filter(producto=self.producto1)
        self.assertEqual(movimientos.count(), 1)
        self.assertEqual(movimientos.first().tipo, 'salida')
        self.assertEqual(movimientos.first().cantidad, 2)
    
    def test_crear_venta_tarjeta(self):
        """Test: Crear una venta con tarjeta"""
        items = [{'id': self.producto1.id, 'cantidad': 1, 'precio': 10000}]
        
        response = self.client.post(reverse('pos:procesar_venta'), {
            'items': json.dumps(items),
            'metodo_pago': 'tarjeta',
            'vendedor_id': self.user.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        venta = Venta.objects.last()
        self.assertEqual(venta.metodo_pago, 'tarjeta')
        self.assertIsNone(venta.monto_recibido)
    
    def test_venta_sin_stock_suficiente(self):
        """Test: Intentar vender más de lo que hay en stock"""
        items = [{'id': self.producto1.id, 'cantidad': 200, 'precio': 10000}]
        
        response = self.client.post(reverse('pos:procesar_venta'), {
            'items': json.dumps(items),
            'metodo_pago': 'efectivo',
            'monto_recibido': 2000000,
            'vendedor_id': self.user.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Stock insuficiente', data['error'])
        
        # Verificar que no se creó la venta
        venta_count = Venta.objects.count()
        self.assertEqual(venta_count, 0)
    
    def test_anular_venta(self):
        """Test: Anular una venta y devolver stock"""
        # Crear venta primero
        venta = Venta.objects.create(
            usuario=self.user,
            vendedor=self.user,
            metodo_pago='efectivo',
            monto_recibido=10000,
            total=10000,
            completada=True
        )
        
        ItemVenta.objects.create(
            venta=venta,
            producto=self.producto1,
            cantidad=1,
            precio_unitario=10000,
            subtotal=10000
        )
        
        # Reducir stock manualmente (simulando la venta)
        self.producto1.stock -= 1
        self.producto1.save()
        
        stock_antes = self.producto1.stock
        
        # Anular venta
        response = self.client.post(reverse('pos:anular_venta', args=[venta.id]), {
            'motivo': 'Test de anulación',
            'accion_dinero': 'devolver'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que la venta está anulada
        venta.refresh_from_db()
        self.assertTrue(venta.anulada)
        
        # Verificar que el stock se devolvió
        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, stock_antes + 1)
        
        # Verificar movimiento de stock de anulación
        movimientos = MovimientoStock.objects.filter(
            producto=self.producto1,
            tipo='ingreso',
            motivo__contains='Anulación'
        )
        self.assertEqual(movimientos.count(), 1)
    
    def test_lista_ventas(self):
        """Test: Listar ventas"""
        # Crear algunas ventas
        for i in range(5):
            Venta.objects.create(
                usuario=self.user,
                vendedor=self.user,
                metodo_pago='efectivo',
                total=10000 * (i + 1),
                completada=True
            )
        
        response = self.client.get(reverse('pos:lista_ventas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ventas')
        
        # Verificar paginación
        ventas = response.context['ventas']
        self.assertIsNotNone(ventas)

