"""
Test integral: caja + ingresos + ventas + salidas + movimientos.
Se recorre el flujo principal para detectar fallos generales.
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import (
    Producto, Caja, CajaUsuario, Venta, MovimientoStock,
    IngresoMercancia, ItemIngresoMercancia,
    SalidaMercancia, ItemSalidaMercancia
)
from django.db import models
from django.test.client import store_rendered_templates
import json

# Desactivar instrumentation de templates para evitar errores en tests
signals.template_rendered.receivers = []
signals.template_rendered.disconnect(store_rendered_templates)
signals.template_rendered.receivers.clear()
signals.template_rendered.send = lambda *args, **kwargs: None


class FlujoIntegralTestCase(TestCase):
    """Flujo integral: apertura caja, ingreso stock, venta, salida, cierre."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='integral_user',
            password='testpass123',
            is_staff=True,
            email='integral@test.com'
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        grupo_cajero, _ = Group.objects.get_or_create(name='Cajeros')
        grupo_inv, _ = Group.objects.get_or_create(name='Inventario')
        self.user.groups.add(grupo_admin, grupo_cajero, grupo_inv)

        self.client = Client()
        self.client.force_login(self.user)

        # Caja base (usar la principal #1 para que procesar_venta funcione)
        self.caja = Caja.objects.create(numero=1, nombre='Caja Integral')

        # Producto base
        self.prod = Producto.objects.create(
            codigo='INT01', nombre='Prod Integral', precio=2000, stock=10, activo=True
        )

    def test_flujo_integral(self):
        # Abrir caja
        resp_abrir = self.client.post(reverse('pos:abrir_caja'), {'monto_inicial': 10000})
        self.assertIn(resp_abrir.status_code, [200, 302])
        caja_usuario = CajaUsuario.objects.filter(usuario=self.user).last()
        self.assertIsNotNone(caja_usuario)

        # Ingreso de mercancía vía vista
        ingreso_items = [{
            'producto_id': self.prod.id,
            'cantidad': 20,
            'precio_compra': 1000
        }]
        resp_ingreso = self.client.post(reverse('pos:crear_ingreso'), {
            'proveedor': 'Proveedor Test',
            'numero_factura': 'FAC-INT-01',
            'items': json.dumps(ingreso_items)
        })
        self.assertIn(resp_ingreso.status_code, [200, 302])

        ingreso = IngresoMercancia.objects.last()
        self.assertIsNotNone(ingreso)

        # Marcar items como verificados para permitir el procesamiento
        ingreso.items.update(verificado=True)

        # Verificar y completar ingreso (procesar stock)
        resp_det_ingreso = self.client.post(
            reverse('pos:detalle_ingreso', args=[ingreso.id]),
            {'completar': '1'}
        )
        self.assertIn(resp_det_ingreso.status_code, [200, 302])

        # Venta en efectivo
        items_venta = [{'id': self.prod.id, 'cantidad': 2, 'precio': self.prod.precio}]
        resp_venta = self.client.post(
            reverse('pos:procesar_venta'),
            data=json.dumps({
                'items': items_venta,
                'metodo_pago': 'efectivo',
                'monto_recibido': 10000,
                'vendedor_id': self.user.id
            }),
            content_type='application/json'
        )
        self.assertEqual(resp_venta.status_code, 200)
        data_venta = json.loads(resp_venta.content)
        self.assertIn('success', data_venta)

        # Salida de mercancía
        salida = SalidaMercancia.objects.create(
            tipo='merma',
            motivo='Test salida',
            usuario=self.user
        )
        ItemSalidaMercancia.objects.create(
            salida=salida,
            producto=self.prod,
            cantidad=1
        )
        resp_salida = self.client.post(
            reverse('pos:detalle_salida', args=[salida.id]),
            {'completar': '1'}
        )
        self.assertIn(resp_salida.status_code, [200, 302])

        # Registrar gasto de caja
        resp_gasto = self.client.post(reverse('pos:registrar_gasto'), {
            'descripcion': 'Gasto test',
            'monto': 500,
            'tipo': 'gasto'
        })
        self.assertIn(resp_gasto.status_code, [200, 302])

        # Registrar ingreso de caja
        resp_ing_caja = self.client.post(reverse('pos:registrar_ingreso'), {
            'descripcion': 'Ingreso test',
            'monto': 700,
            'tipo': 'ingreso'
        })
        self.assertIn(resp_ing_caja.status_code, [200, 302])

        # Calcular saldo esperado antes de retirar
        monto_inicial = 10000
        total_venta = 2 * self.prod.precio  # 4000
        total_ingresos = 700
        total_gastos = 500
        retiro = 2000
        saldo_post_retiro = monto_inicial + total_venta + total_ingresos - total_gastos - retiro

        # Cerrar caja
        resp_cerrar = self.client.post(reverse('pos:cerrar_caja'), {
            'dinero_retirar': retiro,
            'monto_final': saldo_post_retiro
        })
        self.assertIn(resp_cerrar.status_code, [200, 302])

        # Validaciones básicas de estado
        self.prod.refresh_from_db()
        # Stock esperado con los pasos: ingreso(+20), venta(-2), salida(-1) => 27
        self.assertEqual(self.prod.stock, 27)
        # Venta registrada
        self.assertEqual(Venta.objects.count(), 1)
        # Movimientos: ingreso, venta (si aplica), salida
        self.assertGreaterEqual(MovimientoStock.objects.filter(producto=self.prod).count(), 2)
        # Caja cerrada y monto_final correcto
        caja_usuario.refresh_from_db()
        self.assertIsNotNone(caja_usuario.fecha_cierre)
        self.assertEqual(caja_usuario.monto_final, saldo_post_retiro)
        # Gastos/ingresos en caja: gasto (500) + retiro (2000) = 2 gastos; 1 ingreso
        from pos.models import GastoCaja
        self.assertEqual(GastoCaja.objects.filter(caja_usuario=caja_usuario, tipo='gasto').count(), 2)
        self.assertEqual(GastoCaja.objects.filter(caja_usuario=caja_usuario, tipo='ingreso').count(), 1)

        # Conciliación de montos en caja
        total_gastos = GastoCaja.objects.filter(caja_usuario=caja_usuario, tipo='gasto').aggregate(total=models.Sum('monto'))['total'] or 0
        total_ingresos = GastoCaja.objects.filter(caja_usuario=caja_usuario, tipo='ingreso').aggregate(total=models.Sum('monto'))['total'] or 0
        self.assertEqual(total_gastos, 2500)  # 500 gasto + 2000 retiro
        self.assertEqual(total_ingresos, 700)
        self.assertEqual(saldo_post_retiro, 10000 + 4000 + 700 - total_gastos)

        # Conciliación de stock vs movimientos
        mov_ing = MovimientoStock.objects.filter(producto=self.prod, tipo='ingreso').aggregate(total=models.Sum('cantidad'))['total'] or 0
        mov_sal = MovimientoStock.objects.filter(producto=self.prod, tipo='salida').aggregate(total=models.Sum('cantidad'))['total'] or 0
        stock_calc = 10 + mov_ing - mov_sal
        self.assertEqual(stock_calc, self.prod.stock)

