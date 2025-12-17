"""
Lista ventas y gastos inconsistentes para diagnóstico rápido.
Uso: python manage.py listar_inconsistentes
"""
from collections import Counter
from django.core.management.base import BaseCommand
from pos.models import Venta, CajaUsuario, GastoCaja


class Command(BaseCommand):
    help = "Lista ventas con fechas inconsistentes y gastos fuera de periodo"

    def handle(self, *args, **options):
        bad = []
        for v in Venta.objects.filter(completada=True):
            cu = (
                CajaUsuario.objects.filter(
                    caja=v.caja, fecha_apertura__lte=v.fecha
                )
                .order_by("-fecha_apertura")
                .first()
            )
            if not cu or (cu.fecha_cierre and v.fecha > cu.fecha_cierre):
                bad.append(v)

        cnt = Counter([v.fecha.date() for v in bad])
        self.stdout.write(f"Ventas inconsistentes: {len(bad)}")
        for fecha, num in cnt.most_common():
            self.stdout.write(f"  {fecha}: {num} ventas")

        gastos_fuera = []
        for g in GastoCaja.objects.filter(caja_usuario__isnull=False).select_related(
            "caja_usuario"
        ):
            cu = g.caja_usuario
            fuera = (
                g.fecha < cu.fecha_apertura
                or (cu.fecha_cierre and g.fecha > cu.fecha_cierre)
            )
            if fuera:
                gastos_fuera.append(g)
        if gastos_fuera:
            self.stdout.write(f"Gastos fuera de periodo: {len(gastos_fuera)}")
        else:
            self.stdout.write("Gastos fuera de periodo: 0")






