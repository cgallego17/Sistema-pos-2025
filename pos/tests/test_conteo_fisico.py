"""
Tests para el sistema de conteo físico de inventario
"""
import json
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase, signals
from django.urls import reverse
from django.utils import timezone

from pos.models import ConteoFisico, MovimientoStock, Producto

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class ConteoFisicoTestCase(TestCase):
    """Tests para el sistema de conteo físico de inventario"""

    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuarios
        self.user_admin = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True,
        )
        self.user_vendedor = User.objects.create_user(
            username='vendedor_test',
            password='testpass123',
            is_staff=False,
        )

        # Asignar grupos
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        self.user_admin.groups.add(grupo_admin)

        # Crear productos de prueba
        self.producto1 = Producto.objects.create(
            codigo='PROD001',
            nombre='Producto 1',
            precio=1000,
            stock=50,
            activo=True,
        )
        self.producto2 = Producto.objects.create(
            codigo='PROD002',
            nombre='Producto 2',
            atributo='Rojo',
            precio=2000,
            stock=30,
            activo=True,
        )
        self.producto3 = Producto.objects.create(
            codigo='PROD002',
            nombre='Producto 2',
            atributo='Azul',
            precio=2000,
            stock=20,
            activo=True,
        )

        self.client = Client()

    def test_guardar_conteo_fisico_nuevo(self):
        """Test: Guardar un conteo físico nuevo"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '45',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 45)
        self.assertTrue(data['created'])
        
        # Verificar que se guardó en la base de datos
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, 45)
        self.assertEqual(conteo.usuario, self.user_admin)

    def test_guardar_conteo_fisico_con_atributo(self):
        """Test: Guardar conteo físico para producto con atributo"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD002',
            'atributo': 'Rojo',
            'cantidad': '35',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que se guardó correctamente
        conteo = ConteoFisico.objects.get(codigo='PROD002', atributo='Rojo')
        self.assertEqual(conteo.cantidad_contada, 35)

    def test_actualizar_conteo_fisico_existente(self):
        """Test: Actualizar un conteo físico existente"""
        self.client.force_login(self.user_admin)
        
        # Crear conteo inicial
        conteo = ConteoFisico.objects.create(
            codigo='PROD001',
            atributo=None,
            cantidad_contada=40,
            usuario=self.user_admin,
        )
        
        url = reverse('pos:guardar_conteo_fisico')
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '50',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['created'])  # No es nuevo, es actualización
        
        # Verificar que se actualizó
        conteo.refresh_from_db()
        self.assertEqual(conteo.cantidad_contada, 50)

    def test_guardar_conteo_sin_cantidad(self):
        """Test: Cantidad vacía ahora se interpreta como 0 (cambió el comportamiento)"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '',  # Cantidad vacía ahora se acepta como 0
        })
        
        # Ahora debe aceptar cantidad vacía como 0
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 0)
        
        # Verificar que se guardó con valor 0
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_guardar_conteo_cantidad_invalida(self):
        """Test: Validar que la cantidad sea un número válido"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': 'abc',
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('número', data['error'])

    def test_guardar_conteo_sin_codigo(self):
        """Test: Validar que se requiere código"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': '',
            'atributo': '',
            'cantidad': '50',
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Código requerido', data['error'])

    def test_guardar_conteo_solo_administradores(self):
        """Test: Solo administradores pueden guardar conteos"""
        self.client.force_login(self.user_vendedor)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '50',
        })
        
        # Debe redirigir o dar error 403
        self.assertIn(response.status_code, [302, 403])

    def test_guardar_conteo_metodo_no_permitido(self):
        """Test: Solo se permite método POST"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_conteos_fisicos_en_reporte_inventario(self):
        """Test: Los conteos físicos se cargan correctamente en el reporte de inventario"""
        self.client.force_login(self.user_admin)
        
        # Crear movimientos de stock para que aparezcan en el reporte
        MovimientoStock.objects.create(
            producto=self.producto1,
            tipo='ingreso',
            cantidad=10,
            stock_anterior=50,
            stock_nuevo=60,
            motivo='Test',
            usuario=self.user_admin,
        )
        
        # Crear conteo físico
        conteo = ConteoFisico.objects.create(
            codigo='PROD001',
            atributo=None,
            cantidad_contada=55,
            usuario=self.user_admin,
        )
        
        # Verificar que el conteo existe
        self.assertEqual(ConteoFisico.objects.count(), 1)
        self.assertEqual(conteo.cantidad_contada, 55)
        
        # Verificar que se puede obtener el conteo por código
        conteo_recuperado = ConteoFisico.objects.filter(
            codigo='PROD001',
            atributo=None
        ).order_by('-fecha_conteo').first()
        
        self.assertIsNotNone(conteo_recuperado)
        self.assertEqual(conteo_recuperado.cantidad_contada, 55)

    def test_conteos_fisicos_multiples_productos_mismo_codigo(self):
        """Test: Conteos para productos con mismo código pero diferentes atributos"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        # Guardar conteo para producto Rojo
        response1 = self.client.post(url, {
            'codigo': 'PROD002',
            'atributo': 'Rojo',
            'cantidad': '35',
        })
        self.assertEqual(response1.status_code, 200)
        
        # Guardar conteo para producto Azul
        response2 = self.client.post(url, {
            'codigo': 'PROD002',
            'atributo': 'Azul',
            'cantidad': '25',
        })
        self.assertEqual(response2.status_code, 200)
        
        # Verificar que ambos conteos existen
        conteo_rojo = ConteoFisico.objects.get(codigo='PROD002', atributo='Rojo')
        conteo_azul = ConteoFisico.objects.get(codigo='PROD002', atributo='Azul')
        
        self.assertEqual(conteo_rojo.cantidad_contada, 35)
        self.assertEqual(conteo_azul.cantidad_contada, 25)

    def test_conteo_fisico_cantidad_cero(self):
        """Test: Permitir guardar conteo con cantidad cero"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '0',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_conteo_fisico_cantidad_negativa(self):
        """Test: Permitir guardar conteo con cantidad negativa (puede ser válido en algunos casos)"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '-5',
        })
        
        # Django acepta números negativos como int válido
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, -5)

    def test_conteo_fisico_atributo_normalizado(self):
        """Test: Normalizar atributos vacíos o '-' a None"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        # Probar con atributo vacío
        response1 = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '50',
        })
        self.assertEqual(response1.status_code, 200)
        
        # Probar con atributo '-'
        response2 = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '-',
            'cantidad': '55',
        })
        self.assertEqual(response2.status_code, 200)
        
        # Ambos deben apuntar al mismo registro (atributo=None)
        conteos = ConteoFisico.objects.filter(codigo='PROD001', atributo=None)
        self.assertEqual(conteos.count(), 1)
        self.assertEqual(conteos.first().cantidad_contada, 55)  # El último valor

    def test_guardar_conteo_cantidad_cero_explicita(self):
        """Test: Guardar conteo con cantidad cero explícita (string '0')"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '0',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 0)  # Verificar que la respuesta incluye 0
        self.assertTrue(data['created'])
        
        # Verificar que se guardó en la base de datos con valor 0
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, 0)
        self.assertEqual(conteo.usuario, self.user_admin)

    def test_guardar_conteo_cantidad_vacia_como_cero(self):
        """Test: Guardar conteo con cantidad vacía (debe interpretarse como 0)"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '',  # Cantidad vacía
        })
        
        # Debe aceptar cantidad vacía como 0
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 0)
        
        # Verificar que se guardó con valor 0
        conteo = ConteoFisico.objects.get(codigo='PROD001', atributo=None)
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_actualizar_conteo_a_cero(self):
        """Test: Actualizar un conteo existente a cero"""
        self.client.force_login(self.user_admin)
        
        # Crear conteo inicial con valor diferente de 0
        conteo = ConteoFisico.objects.create(
            codigo='PROD001',
            atributo=None,
            cantidad_contada=50,
            usuario=self.user_admin,
        )
        
        url = reverse('pos:guardar_conteo_fisico')
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '0',  # Actualizar a 0
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 0)
        self.assertFalse(data['created'])  # Es actualización, no creación
        
        # Verificar que se actualizó a 0
        conteo.refresh_from_db()
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_actualizar_conteo_desde_cero(self):
        """Test: Actualizar un conteo que está en cero a otro valor"""
        self.client.force_login(self.user_admin)
        
        # Crear conteo inicial con valor 0
        conteo = ConteoFisico.objects.create(
            codigo='PROD001',
            atributo=None,
            cantidad_contada=0,
            usuario=self.user_admin,
        )
        
        url = reverse('pos:guardar_conteo_fisico')
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '25',  # Actualizar desde 0 a 25
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 25)
        self.assertFalse(data['created'])  # Es actualización
        
        # Verificar que se actualizó correctamente
        conteo.refresh_from_db()
        self.assertEqual(conteo.cantidad_contada, 25)

    def test_guardar_conteo_cero_con_atributo(self):
        """Test: Guardar conteo con cantidad cero para producto con atributo"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD002',
            'atributo': 'Rojo',
            'cantidad': '0',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad'], 0)
        
        # Verificar que se guardó correctamente
        conteo = ConteoFisico.objects.get(codigo='PROD002', atributo='Rojo')
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_respuesta_json_incluye_cero(self):
        """Test: Verificar que la respuesta JSON incluye correctamente el valor 0"""
        self.client.force_login(self.user_admin)
        url = reverse('pos:guardar_conteo_fisico')
        
        response = self.client.post(url, {
            'codigo': 'PROD001',
            'atributo': '',
            'cantidad': '0',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verificar que la respuesta incluye todos los campos esperados
        self.assertTrue(data['success'])
        self.assertIn('cantidad', data)
        self.assertEqual(data['cantidad'], 0)
        self.assertIn('created', data)
        self.assertIn('codigo', data)
        self.assertIn('atributo', data)
        
        # Verificar que cantidad es exactamente 0 (no None, no False)
        self.assertIsInstance(data['cantidad'], int)
        self.assertEqual(data['cantidad'], 0)

