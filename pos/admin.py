from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Producto, Caja, CajaUsuario, Venta, ItemVenta,
    MovimientoStock, PerfilUsuario, CajaGastos,
    CajaGastosUsuario, GastoCaja, ClientePotencial,
    IngresoMercancia, ItemIngresoMercancia,
    SalidaMercancia, ItemSalidaMercancia, CampanaMarketing,
    RegistradoraActiva
)

# Desregistrar el User admin por defecto y registrar uno personalizado
# Esto ayuda a evitar el error 'super' object has no attribute 'dicts'
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para User que evita el error de 'dicts'"""
    pass


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'precio', 'stock', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['codigo', 'codigo_barras', 'nombre']
    list_editable = ['precio', 'stock', 'activo']
    readonly_fields = ['fecha_creacion']


class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha', 'total', 'metodo_pago', 'completada', 'anulada', 'usuario', 'caja']
    list_filter = ['completada', 'anulada', 'metodo_pago', 'fecha']
    search_fields = ['id', 'usuario__username', 'email_cliente']
    readonly_fields = ['fecha', 'total']
    inlines = [ItemVentaInline]


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nombre', 'activa']
    list_filter = ['activa']
    search_fields = ['nombre']


@admin.register(CajaUsuario)
class CajaUsuarioAdmin(admin.ModelAdmin):
    list_display = ['caja', 'usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 'monto_final']
    list_filter = ['caja', 'fecha_apertura', 'fecha_cierre']
    search_fields = ['usuario__username']


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'fecha', 'usuario']
    list_filter = ['tipo', 'fecha']
    search_fields = ['producto__nombre', 'producto__codigo']
    readonly_fields = ['fecha']


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'pin_establecido', 'fecha_creacion_pin']
    search_fields = ['usuario__username']


@admin.register(CajaGastos)
class CajaGastosAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'fecha_creacion']


@admin.register(CajaGastosUsuario)
class CajaGastosUsuarioAdmin(admin.ModelAdmin):
    list_display = ['caja_gastos', 'usuario', 'fecha_apertura', 'fecha_cierre', 'monto_inicial', 'monto_final']
    list_filter = ['fecha_apertura', 'fecha_cierre']
    search_fields = ['usuario__username']


@admin.register(GastoCaja)
class GastoCajaAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'monto', 'descripcion', 'fecha', 'usuario']
    list_filter = ['tipo', 'fecha']
    search_fields = ['descripcion', 'usuario__username']


@admin.register(ClientePotencial)
class ClientePotencialAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'telefono', 'tipo_interes', 'estado', 'fecha_registro']
    list_filter = ['estado', 'tipo_interes', 'fecha_registro']
    search_fields = ['nombre', 'email', 'empresa']
    readonly_fields = ['fecha_registro']


class ItemIngresoInline(admin.TabularInline):
    model = ItemIngresoMercancia
    extra = 1
    fields = ('producto', 'cantidad', 'precio_compra', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(IngresoMercancia)
class IngresoMercanciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha', 'proveedor', 'total', 'completado', 'usuario']
    list_filter = ['completado', 'fecha']
    search_fields = ['proveedor', 'numero_factura']
    readonly_fields = ['fecha', 'total']
    inlines = [ItemIngresoInline]
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer campos readonly según el estado del objeto"""
        readonly = list(self.readonly_fields)
        if obj and obj.completado:
            readonly.extend(['proveedor', 'numero_factura', 'observaciones', 'usuario'])
        return readonly


class ItemSalidaInline(admin.TabularInline):
    model = ItemSalidaMercancia
    extra = 1
    fields = ('producto', 'cantidad')


@admin.register(SalidaMercancia)
class SalidaMercanciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha', 'tipo', 'destino', 'completado', 'usuario']
    list_filter = ['tipo', 'completado', 'fecha']
    search_fields = ['destino', 'motivo']
    readonly_fields = ['fecha']
    inlines = [ItemSalidaInline]
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer campos readonly según el estado del objeto"""
        readonly = list(self.readonly_fields)
        if obj and obj.completado:
            readonly.extend(['tipo', 'destino', 'motivo', 'usuario'])
        return readonly


@admin.register(CampanaMarketing)
class CampanaMarketingAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'estado', 'fecha_inicio', 'fecha_fin', 'presupuesto']
    list_filter = ['estado', 'tipo', 'fecha_inicio']
    search_fields = ['nombre', 'descripcion']
    filter_horizontal = ['productos']


@admin.register(RegistradoraActiva)
class RegistradoraActivaAdmin(admin.ModelAdmin):
    list_display = ['registradora_id', 'usuario', 'fecha_apertura']
    list_filter = ['registradora_id', 'fecha_apertura']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name']
    readonly_fields = ['fecha_apertura']

