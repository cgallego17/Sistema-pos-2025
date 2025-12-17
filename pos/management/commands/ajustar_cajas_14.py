"""
Ajusta todas las CajaUsuario del 14/12/2025 para cubrir todo el día (00:00 a 23:59:59.999999)
y reasigna los gastos de ese día a esas cajas.

Uso: python manage.py ajustar_cajas_14
"""
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from pos.models import CajaUsuario, GastoCaja


class Command(BaseCommand):
    help = "Ajusta cajas del 14/12/2025 y reasigna gastos de ese día"

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        target_date = datetime(2025, 12, 14, tzinfo=tz).date()
        apertura = datetime(2025, 12, 14, 0, 0, 0, tzinfo=tz)
        cierre = datetime(2025, 12, 14, 23, 59, 59, 999999, tzinfo=tz)

        cu_ids = list(
            CajaUsuario.objects.filter(fecha_apertura__date=target_date).values_list(
                "id", flat=True
            )
        )
        self.stdout.write(f"Cajas encontradas para {target_date}: {cu_ids}")

        for cid in cu_ids:
            cu = CajaUsuario.objects.get(id=cid)
            cu.fecha_apertura = apertura
            cu.fecha_cierre = cierre
            cu.save(update_fields=["fecha_apertura", "fecha_cierre"])

        # Reasignar gastos de ese día a cada caja (si hay varias, todos a la primera)
        if cu_ids:
            destino_id = cu_ids[0]
            gastos = GastoCaja.objects.filter(fecha__date=target_date)
            for g in gastos:
                if g.caja_usuario_id != destino_id:
                    g.caja_usuario_id = destino_id
                    g.save(update_fields=["caja_usuario"])
            self.stdout.write(
                f"Gastos del {target_date} reasignados a CajaUsuario {destino_id}"
            )

        self.stdout.write(self.style.SUCCESS("Ajuste completado"))






