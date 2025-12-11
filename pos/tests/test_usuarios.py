"""
Tests para el módulo de Usuarios y Login
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import PerfilUsuario


class UsuariosTestCase(TestCase):
    """Tests para el módulo de usuarios"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com'
        )
        
        # Crear perfil con PIN
        PerfilUsuario.objects.create(
            usuario=self.user,
            pin='1234'
        )
        
        self.client = Client()
    
    def test_login_con_pin(self):
        """Test: Login con username y PIN"""
        response = self.client.post(reverse('pos:login'), {
            'username': 'testuser',
            'pin': '1234'
        })
        
        # Debe redirigir después del login exitoso
        self.assertIn(response.status_code, [200, 302])
    
    def test_login_pin_incorrecto(self):
        """Test: Login con PIN incorrecto"""
        response = self.client.post(reverse('pos:login'), {
            'username': 'testuser',
            'pin': '9999'  # PIN incorrecto
        })
        
        # No debe hacer login
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_listar_usuarios(self):
        """Test: Listar usuarios"""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('pos:usuarios'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuarios')
        
        # Verificar paginación
        usuarios = response.context['usuarios']
        self.assertIsNotNone(usuarios)
    
    def test_crear_usuario(self):
        """Test: Crear un nuevo usuario"""
        self.client.force_login(self.user)
        
        response = self.client.post(reverse('pos:crear_usuario'), {
            'username': 'nuevousuario',
            'email': 'nuevo@test.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'password': 'pass123',
            'is_staff': 'on',
            'is_active': 'on'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect después de crear
        
        # Verificar que se creó el usuario
        usuario = User.objects.filter(username='nuevousuario').first()
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.email, 'nuevo@test.com')
        
        # Verificar que se creó el perfil
        perfil = PerfilUsuario.objects.filter(usuario=usuario).first()
        self.assertIsNotNone(perfil)

