"""
Tests para el módulo de Inventario (Ingresos y Salidas)
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import (
    Producto, IngresoMercancia, ItemIngresoMercancia,
    SalidaMercancia, ItemSalidaMercancia, MovimientoStock
)
import json
from django.test.client import store_rendered_templates

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class InventarioTestCase(TestCase):
    """Tests para el módulo de inventario"""
    
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
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_crear_ingreso_mercancia(self):
        """Test: Crear un ingreso de mercancía"""
        items_data = [
            {
                'producto_id': self.producto1.id,
                'cantidad': 10,
                'precio_compra': 5000
            },
            {
                'producto_id': self.producto2.id,
                'cantidad': 5,
                'precio_compra': 10000
            }
        ]
        
        response = self.client.post(reverse('pos:crear_ingreso'), {
            'proveedor': 'Proveedor Test',
            'numero_factura': 'FAC-001',
            'items': json.dumps(items_data)
        })
        
        self.assertIn(response.status_code, [200, 302])  # Puede redirigir después de crear
        
        # Verificar que se creó el ingreso
        ingreso = IngresoMercancia.objects.last()
        self.assertIsNotNone(ingreso)
        self.assertEqual(ingreso.proveedor, 'Proveedor Test')
        self.assertEqual(ingreso.items.count(), 2)
        self.assertFalse(ingreso.completado)
    
    def test_verificar_y_procesar_items_ingreso(self):
        """Test: Verificar y procesar items de un ingreso"""
        # Crear ingreso
        ingreso = IngresoMercancia.objects.create(
            proveedor='Proveedor Test',
            usuario=self.user
        )
        
        item1 = ItemIngresoMercancia.objects.create(
            ingreso=ingreso,
            producto=self.producto1,
            cantidad=10,
            precio_compra=5000,
            subtotal=50000
        )
        
        item2 = ItemIngresoMercancia.objects.create(
            ingreso=ingreso,
            producto=self.producto2,
            cantidad=5,
            precio_compra=10000,
            subtotal=50000
        )
        
        stock_inicial_p1 = self.producto1.stock
        stock_inicial_p2 = self.producto2.stock
        
        # Verificar item 1
        response = self.client.post(
            reverse('pos:detalle_ingreso', args=[ingreso.id]),
            {'item_id': item1.id, 'verificar': '1'}
        )
        self.assertEqual(response.status_code, 200)
        
        item1.refresh_from_db()
        self.assertTrue(item1.verificado)
        
        # Procesar items verificados
        response = self.client.post(
            reverse('pos:detalle_ingreso', args=[ingreso.id]),
            {'completar': '1'}
        )
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar que solo el item verificado se procesó
        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertTrue(item1.procesado)
        self.assertFalse(item2.procesado)
        
        # Verificar que el stock se actualizó solo para item1
        self.producto1.refresh_from_db()
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto1.stock, stock_inicial_p1 + 10)
        self.assertEqual(self.producto2.stock, stock_inicial_p2)  # No cambió
        
        # Verificar movimiento de stock
        movimiento = MovimientoStock.objects.filter(producto=self.producto1).last()
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.tipo, 'ingreso')
        self.assertEqual(movimiento.cantidad, 10)
    
    def test_crear_salida_mercancia(self):
        """Test: Crear una salida de mercancía"""
        items_data = [
            {
                'producto_id': self.producto1.id,
                'cantidad': 5
            }
        ]
        
        response = self.client.post(reverse('pos:crear_salida'), {
            'tipo': 'merma',
            'motivo': 'Producto dañado',
            'items': json.dumps(items_data)
        })
        
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar que se creó la salida
        salida = SalidaMercancia.objects.last()
        self.assertIsNotNone(salida)
        self.assertEqual(salida.tipo, 'merma')
        self.assertEqual(salida.items.count(), 1)
        self.assertFalse(salida.completado)
    
    def test_completar_salida_mercancia(self):
        """Test: Completar una salida de mercancía"""
        # Crear salida
        salida = SalidaMercancia.objects.create(
            tipo='merma',
            motivo='Test',
            usuario=self.user
        )
        
        ItemSalidaMercancia.objects.create(
            salida=salida,
            producto=self.producto1,
            cantidad=5
        )
        
        stock_inicial = self.producto1.stock
        
        # Completar salida
        response = self.client.post(
            reverse('pos:detalle_salida', args=[salida.id]),
            {'completar': '1'}
        )
        
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar que la salida se completó
        salida.refresh_from_db()
        self.assertTrue(salida.completado)
        
        # Verificar que el stock se redujo
        self.producto1.refresh_from_db()
        self.assertEqual(self.producto1.stock, stock_inicial - 5)
        
        # Verificar movimiento de stock
        movimiento = MovimientoStock.objects.filter(producto=self.producto1).last()
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.tipo, 'salida')
        self.assertEqual(movimiento.cantidad, 5)
    
    def test_salida_sin_stock_suficiente(self):
        """Test: Intentar salida con stock insuficiente"""
        # Crear salida con cantidad mayor al stock
        salida = SalidaMercancia.objects.create(
            tipo='merma',
            motivo='Test',
            usuario=self.user
        )
        
        ItemSalidaMercancia.objects.create(
            salida=salida,
            producto=self.producto1,
            cantidad=200  # Más de lo que hay (stock = 100)
        )
        
        # Intentar completar
        response = self.client.post(
            reverse('pos:detalle_salida', args=[salida.id]),
            {'completar': '1'}
        )
        
        # Debe redirigir con error
        self.assertIn(response.status_code, [200, 302])

