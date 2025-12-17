"""
Crear cajas por día para ventas que no tienen caja adecuada.
Uso: python manage.py crear_cajas_por_dia
"""
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pos.models import Caja, CajaUsuario, Venta, GastoCaja


class Command(BaseCommand):
    help = "Crea CajaUsuario por día para ventas sin caja adecuada (12/12 y 13/12/2025)"

    def handle(self, *args, **options):
        User = get_user_model()
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR("No se encontró Caja Principal"))
            return

        fechas = [
            datetime(2025, 12, 13).date(),
            datetime(2025, 12, 14).date(),
        ]

        for fecha in fechas:
            ventas = Venta.objects.filter(completada=True, fecha__date=fecha)
            if not ventas.exists():
                self.stdout.write(f"Sin ventas en {fecha}")
                continue

            apertura = min(v.fecha for v in ventas)
            cierre = apertura.replace(hour=23, minute=59, second=59, microsecond=0)
            usuario = ventas.first().usuario or User.objects.filter(
                is_superuser=True
            ).first()

            caja = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                fecha_apertura=apertura,
                fecha_cierre=cierre,
                monto_inicial=0,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Creada CajaUsuario {caja.id} para {fecha} (apertura {apertura})"
                )
            )

            # Asignar gastos de ese día a la nueva caja
            gastos = GastoCaja.objects.filter(fecha__date=fecha)
            for g in gastos:
                g.caja_usuario = caja
                g.save(update_fields=["caja_usuario"])
            if gastos.exists():
                self.stdout.write(
                    f"  Gastos asignados: {[g.id for g in gastos]} ({gastos.count()})"
                )

        self.stdout.write(self.style.SUCCESS("Proceso completado"))






