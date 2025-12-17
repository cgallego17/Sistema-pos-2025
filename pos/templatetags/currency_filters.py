from django import template

register = template.Library()


@register.filter(name='currency')
def currency(value):
    """
    Formatea un número como moneda con 2 decimales y separadores de miles.
    Ejemplo: 37318.181818181 -> "37,318.18"
    """
    try:
        num = float(value)
        # Formatear con 2 decimales y separadores de miles
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return "0.00"


