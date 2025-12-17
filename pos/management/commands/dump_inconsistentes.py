"""
Muestra detalles de ventas inconsistentes (sin CajaUsuario válida).
Uso: python manage.py dump_inconsistentes
"""
from django.core.management.base import BaseCommand
from pos.models import Venta, CajaUsuario


class Command(BaseCommand):
    help = "Muestra las primeras ventas inconsistentes para diagnosticar"

    def handle(self, *args, **options):
        bad = []
        for v in Venta.objects.filter(completada=True).order_by("fecha"):
            cu = (
                CajaUsuario.objects.filter(caja=v.caja, fecha_apertura__lte=v.fecha)
                .order_by("-fecha_apertura")
                .first()
            )
            if not cu or (cu.fecha_cierre and v.fecha > cu.fecha_cierre):
                bad.append((v.id, v.fecha, v.caja_id, cu.id if cu else None, cu.fecha_apertura if cu else None, cu.fecha_cierre if cu else None))

        self.stdout.write(f"Total inconsistentes: {len(bad)}")
        for row in bad[:20]:
            vid, fecha, caja_id, cu_id, apertura, cierre = row
            self.stdout.write(f"Venta {vid} fecha {fecha} caja {caja_id} -> CU {cu_id} (apertura {apertura}, cierre {cierre})")






