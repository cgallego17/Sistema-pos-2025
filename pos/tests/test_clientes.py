"""
Tests para el módulo de Clientes Potenciales
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from pos.models import ClientePotencial


class ClientesTestCase(TestCase):
    """Tests para el módulo de clientes potenciales"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_listar_clientes(self):
        """Test: Listar clientes potenciales"""
        # Crear algunos clientes
        ClientePotencial.objects.create(
            nombre='Cliente Test 1',
            email='cliente1@test.com',
            telefono='1234567890',
            usuario=self.user
        )
        
        ClientePotencial.objects.create(
            nombre='Cliente Test 2',
            email='cliente2@test.com',
            telefono='0987654321',
            usuario=self.user
        )
        
        response = self.client.get(reverse('pos:clientes_potenciales'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clientes Potenciales')
        
        # Verificar paginación
        clientes = response.context['clientes']
        self.assertIsNotNone(clientes)
        self.assertGreaterEqual(clientes.paginator.count, 2)
    
    def test_crear_cliente(self):
        """Test: Crear un cliente potencial"""
        response = self.client.post(reverse('pos:formulario_clientes'), {
            'nombre': 'Nuevo Cliente',
            'email': 'nuevo@test.com',
            'telefono': '1234567890',
            'mensaje': 'Interesado en productos'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el cliente
        cliente = ClientePotencial.objects.filter(email='nuevo@test.com').first()
        self.assertIsNotNone(cliente)
        self.assertEqual(cliente.nombre, 'Nuevo Cliente')

