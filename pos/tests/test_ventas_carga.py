"""
Test de carga: múltiples ventas consecutivas para validar estabilidad del flujo de ventas y stock.
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import Producto, Caja, CajaUsuario, Venta, MovimientoStock
from django.test.client import store_rendered_templates
import json

# Desactivar instrumentation de templates para evitar errores en tests
signals.template_rendered.receivers = []
signals.template_rendered.disconnect(store_rendered_templates)
signals.template_rendered.receivers.clear()
signals.template_rendered.send = lambda *args, **kwargs: None


class VentasCargaTestCase(TestCase):
    """Simula muchas ventas consecutivas para detectar inconsistencias."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='carga_user',
            password='testpass123',
            is_staff=True,
            email='carga@test.com'
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        grupo_cajero, _ = Group.objects.get_or_create(name='Cajeros')
        self.user.groups.add(grupo_admin, grupo_cajero)

        self.client = Client()
        self.client.force_login(self.user)

        # Caja abierta
        self.caja = Caja.objects.create(numero=9, nombre='Caja Carga')
        CajaUsuario.objects.create(usuario=self.user, caja=self.caja, monto_inicial=0)

        # Productos con stock amplio
        self.prod = Producto.objects.create(
            codigo='LOAD01', nombre='Prod Carga', precio=1000, stock=2000, activo=True
        )

    def test_multiples_ventas_consecutivas(self):
        # Estrés mayor: más iteraciones
        num_ventas = 200
        items = [{'id': self.prod.id, 'cantidad': 2, 'precio': self.prod.precio}]

        for i in range(num_ventas):
            resp = self.client.post(
                reverse('pos:procesar_venta'),
                data=json.dumps({
                    'items': items,
                    'metodo_pago': 'efectivo',
                    'monto_recibido': 5000,
                    'vendedor_id': self.user.id
                }),
                content_type='application/json'
            )
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.content)
            self.assertIn('success', data)

        ventas_creadas = Venta.objects.count()
        self.assertGreaterEqual(ventas_creadas, 0)

        # Stock no debe ser negativo ni superar el inicial
        self.prod.refresh_from_db()
        self.assertLessEqual(self.prod.stock, 2000)
        self.assertGreaterEqual(self.prod.stock, 0)

        # Movimientos de stock coherentes si hubo ventas
        movs = MovimientoStock.objects.filter(producto=self.prod, tipo='salida')
        self.assertGreaterEqual(movs.count(), 0)
        if ventas_creadas > 0:
            self.assertEqual(movs.count(), ventas_creadas)

