"""
URL configuration for pos app.
"""
from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('login/pin/', views.login_pin_view, name='login_pin'),
    path('logout/', views.logout_view, name='logout'),
    
    # Registradora
    path('seleccionar-registradora/', views.seleccionar_registradora_view, name='seleccionar_registradora'),
    path('cerrar-registradora/', views.cerrar_registradora_view, name='cerrar_registradora'),
    
    # Punto de Venta (página principal)
    path('', views.vender_view, name='vender'),
    path('vender/', views.vender_view, name='vender_alt'),
    path('dashboard/', views.home_view, name='home'),
    path('vender/procesar/', views.procesar_venta, name='procesar_venta'),
    
    # Productos
    path('productos/', views.productos_view, name='productos'),
    path('productos/nuevo/', views.crear_producto_view, name='crear_producto'),
    path('productos/<int:producto_id>/editar/', views.editar_producto_view, name='editar_producto'),
    
    # Ventas
    path('ventas/', views.lista_ventas_view, name='lista_ventas'),
    path('ventas/<int:venta_id>/', views.detalle_venta_view, name='detalle_venta'),
    path('ventas/<int:venta_id>/editar/', views.editar_venta_view, name='editar_venta'),
    path('ventas/<int:venta_id>/anular/', views.anular_venta_view, name='anular_venta'),
    path('ventas/<int:venta_id>/imprimir/', views.imprimir_ticket_view, name='imprimir_ticket'),
    path('ventas/<int:venta_id>/enviar-email/', views.enviar_ticket_email_view, name='enviar_ticket_email'),
    
    # Caja
    path('caja/', views.caja_view, name='caja'),
    path('caja/abrir/', views.abrir_caja_view, name='abrir_caja'),
    path('caja/cerrar/', views.cerrar_caja_view, name='cerrar_caja'),
    path('caja/registrar-gasto/', views.registrar_gasto_view, name='registrar_gasto'),
    path('caja/registrar-ingreso/', views.registrar_ingreso_view, name='registrar_ingreso'),
    
    # Reportes
    path('reportes/', views.reportes_view, name='reportes'),
    
    # Inventario (Ingreso/Salida Mercancía unificado)
    path('inventario/', views.inventario_view, name='inventario'),
    path('movimientos-inventario/', views.movimientos_inventario_view, name='movimientos_inventario'),
    path('ingreso-mercancia/', views.ingreso_mercancia_view, name='ingreso_mercancia'),
    path('ingreso-mercancia/nuevo/', views.crear_ingreso_view, name='crear_ingreso'),
    path('ingreso-mercancia/<int:ingreso_id>/', views.detalle_ingreso_view, name='detalle_ingreso'),
    path('salida-mercancia/', views.salida_mercancia_view, name='salida_mercancia'),
    path('salida-mercancia/nuevo/', views.crear_salida_view, name='crear_salida'),
    path('salida-mercancia/<int:salida_id>/', views.detalle_salida_view, name='detalle_salida'),
    
    # Marketing
    path('marketing/', views.marketing_view, name='marketing'),
    
    # Clientes
    path('formulario-clientes/', views.formulario_clientes_view, name='formulario_clientes'),
    path('clientes-potenciales/', views.clientes_potenciales_view, name='clientes_potenciales'),
    path('clientes-potenciales/<int:cliente_id>/', views.gestionar_cliente_view, name='gestionar_cliente'),
    
    # Usuarios
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('usuarios/nuevo/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/<int:usuario_id>/editar/', views.editar_usuario_view, name='editar_usuario'),
    
    # Sistema de Carrito
    path('buscar/', views.buscar_productos_view, name='buscar_productos'),
    path('agregar/', views.agregar_al_carrito_view, name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_cantidad_carrito_view, name='actualizar_cantidad'),
    path('carrito/precio/<int:producto_id>/', views.actualizar_precio_carrito_view, name='actualizar_precio'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_item_carrito_view, name='eliminar_item'),
    path('limpiar/', views.limpiar_carrito_view, name='limpiar_carrito'),
    path('procesar/', views.procesar_venta_completa_view, name='procesar_venta_completa'),
    
    # API
    path('api/usuarios/', views.api_usuarios_view, name='api_usuarios'),
]

