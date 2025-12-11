"""
Tests para el módulo de Caja
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from pos.models import (
    Caja, CajaUsuario, GastoCaja, Venta, Producto, ItemVenta
)
import json
from decimal import Decimal


class CajaTestCase(TestCase):
    """Tests para el módulo de caja"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
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
    
    def test_abrir_caja(self):
        """Test: Abrir una caja"""
        response = self.client.post(reverse('pos:abrir_caja'), {
            'monto_inicial': 50000
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que se creó la caja
        caja_usuario = CajaUsuario.objects.filter(usuario=self.user).first()
        self.assertIsNotNone(caja_usuario)
        self.assertEqual(caja_usuario.monto_inicial, 50000)
        self.assertIsNone(caja_usuario.monto_final)
    
    def test_cerrar_caja(self):
        """Test: Cerrar una caja"""
        # Abrir caja primero
        caja_usuario = CajaUsuario.objects.create(
            usuario=self.user,
            monto_inicial=50000,
            fecha_apertura=timezone.now()
        )
        
        # Crear una venta para tener dinero en caja
        venta = Venta.objects.create(
            usuario=self.user,
            vendedor=self.user,
            metodo_pago='efectivo',
            monto_recibido=20000,
            total=20000,
            completada=True,
            caja=self.caja
        )
        
        # Cerrar caja
        response = self.client.post(reverse('pos:cerrar_caja'), {
            'dinero_retirar': 10000
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que la caja se cerró
        caja_usuario.refresh_from_db()
        self.assertIsNotNone(caja_usuario.monto_final)
        self.assertEqual(caja_usuario.dinero_retirar, 10000)
    
    def test_cerrar_caja_sin_dinero_suficiente(self):
        """Test: Intentar cerrar caja retirando más de lo disponible"""
        # Abrir caja con monto inicial
        CajaUsuario.objects.create(
            usuario=self.user,
            monto_inicial=50000,
            fecha_apertura=timezone.now()
        )
        
        # Intentar retirar más de lo disponible
        response = self.client.post(reverse('pos:cerrar_caja'), {
            'dinero_retirar': 100000  # Más de lo que hay
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('No se puede retirar más dinero', data['error'])
    
    def test_registrar_gasto(self):
        """Test: Registrar un gasto en la caja"""
        # Abrir caja
        caja_usuario = CajaUsuario.objects.create(
            usuario=self.user,
            monto_inicial=50000,
            fecha_apertura=timezone.now()
        )
        
        # Registrar gasto
        response = self.client.post(reverse('pos:registrar_gasto'), {
            'descripcion': 'Gasto de prueba',
            'monto': 10000,
            'tipo': 'gasto'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que se creó el gasto
        gasto = GastoCaja.objects.last()
        self.assertIsNotNone(gasto)
        self.assertEqual(gasto.monto, 10000)
        self.assertEqual(gasto.tipo, 'gasto')
        self.assertEqual(gasto.caja_usuario, caja_usuario)
    
    def test_registrar_ingreso(self):
        """Test: Registrar un ingreso en la caja"""
        # Abrir caja
        caja_usuario = CajaUsuario.objects.create(
            usuario=self.user,
            monto_inicial=50000,
            fecha_apertura=timezone.now()
        )
        
        # Registrar ingreso
        response = self.client.post(reverse('pos:registrar_ingreso'), {
            'descripcion': 'Ingreso de prueba',
            'monto': 15000,
            'tipo': 'ingreso'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que se creó el ingreso
        ingreso = GastoCaja.objects.last()
        self.assertIsNotNone(ingreso)
        self.assertEqual(ingreso.monto, 15000)
        self.assertEqual(ingreso.tipo, 'ingreso')
    
    def test_venta_afecta_caja(self):
        """Test: Verificar que una venta afecta el saldo de la caja"""
        # Abrir caja
        caja_usuario = CajaUsuario.objects.create(
            usuario=self.user,
            monto_inicial=50000,
            fecha_apertura=timezone.now()
        )
        
        # Crear venta en efectivo
        venta = Venta.objects.create(
            usuario=self.user,
            vendedor=self.user,
            metodo_pago='efectivo',
            monto_recibido=20000,
            total=20000,
            completada=True,
            caja=self.caja
        )
        
        # Verificar que la venta se registró
        self.assertIsNotNone(venta)
        self.assertEqual(venta.metodo_pago, 'efectivo')
        self.assertEqual(venta.total, 20000)

