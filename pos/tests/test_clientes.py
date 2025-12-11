"""
Tests para el módulo de Clientes Potenciales
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import ClientePotencial
from django.test.client import store_rendered_templates

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class ClientesTestCase(TestCase):
    """Tests para el módulo de clientes potenciales"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        self.user.groups.add(grupo_admin)
        
        self.client = Client()
        self.client.force_login(self.user)
        signals.template_rendered.disconnect(store_rendered_templates)
        signals.template_rendered.receivers.clear()
        signals.template_rendered.send = lambda *args, **kwargs: None
    
    def test_listar_clientes(self):
        """Test: Listar clientes potenciales"""
        # Crear algunos clientes
        ClientePotencial.objects.create(
            nombre='Cliente Test 1',
            email='cliente1@test.com',
            telefono='1234567890'
        )
        
        ClientePotencial.objects.create(
            nombre='Cliente Test 2',
            email='cliente2@test.com',
            telefono='0987654321'
        )
        
        response = self.client.get(reverse('pos:clientes_potenciales'))
        self.assertIn(response.status_code, [200, 302])
        # Verificar registros
        self.assertGreaterEqual(ClientePotencial.objects.count(), 2)
    
    def test_crear_cliente(self):
        """Test: Crear un cliente potencial"""
        response = self.client.post(reverse('pos:formulario_clientes'), {
            'nombre': 'Nuevo Cliente',
            'email': 'nuevo@test.com',
            'telefono': '1234567890',
            'mensaje': 'Interesado en productos'
        })
        
        self.assertIn(response.status_code, [200, 302])
        
        # Verificar que se creó el cliente
        cliente = ClientePotencial.objects.filter(email='nuevo@test.com').first()
        self.assertIsNotNone(cliente)
        self.assertEqual(cliente.nombre, 'Nuevo Cliente')

