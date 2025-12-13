# Análisis del Sistema de Caja y Cálculo de Totales

## 📊 Resumen del Sistema de Caja

El sistema utiliza una **caja única global** compartida por todos los usuarios. La caja se abre y cierra diariamente.

## 🔢 Cálculo de Totales

### 1. **Total de Ventas** (`total_ventas`)
```python
# Solo ventas válidas (no anuladas)
ventas_caja = ventas_caja_todas.filter(anulada=False)
total_ventas = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
```
- **Incluye:** Solo ventas completadas y no anuladas
- **Excluye:** Ventas anuladas

### 2. **Total de Gastos** (`total_gastos`)
```python
gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_mostrar)
total_gastos = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
```
- **Incluye:** Todos los gastos registrados en la caja
- **Tipos:** Gastos normales, retiros, devoluciones por anulación

### 3. **Total de Ingresos** (`total_ingresos`)
```python
total_ingresos = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
```
- **Incluye:** Todos los ingresos registrados en la caja

### 4. **Saldo en Caja** (`saldo_caja`)
```python
# Verificar si hay gastos de devolución
gastos_devolucion_total = gastos_todos.filter(
    descripcion__icontains='Devolución por anulación'
).aggregate(total=Sum('monto'))['total'] or 0

if gastos_devolucion_total > 0:
    # Si hay devoluciones, las ventas anuladas SÍ ingresaron dinero
    saldo_caja = monto_inicial + total_ventas + total_anuladas + total_ingresos - total_gastos
else:
    # Si NO hay devoluciones, las ventas anuladas NO afectan el dinero físico
    saldo_caja = monto_inicial + total_ventas + total_ingresos - total_gastos
```

**Lógica:**
- Si hay gastos de devolución → Las ventas anuladas ingresaron dinero que luego se devolvió
- Si NO hay gastos de devolución → Las ventas anuladas nunca ingresaron dinero físico

### 5. **Dinero Físico en Caja** (`dinero_fisico_caja`)
```python
# Solo efectivo (no tarjeta ni transferencia)
ventas_efectivo = ventas_caja.filter(metodo_pago='efectivo').aggregate(total=Sum('total'))['total'] or 0
ventas_anuladas_efectivo = ventas_anuladas_caja.filter(metodo_pago='efectivo').aggregate(total=Sum('total'))['total'] or 0

# Verificar gastos de devolución en efectivo
gastos_devolucion_efectivo_total = ... # Filtrado por ventas en efectivo

if gastos_devolucion_efectivo_total > 0:
    dinero_fisico_caja = monto_inicial + ventas_efectivo + ventas_anuladas_efectivo + total_ingresos - total_gastos
else:
    dinero_fisico_caja = monto_inicial + ventas_efectivo + total_ingresos - total_gastos
```

**Diferencia con Saldo en Caja:**
- **Saldo en Caja:** Incluye todos los métodos de pago (efectivo + tarjeta + transferencia)
- **Dinero Físico:** Solo efectivo (lo que realmente hay en la caja física)

## 📈 Movimientos de Caja

### Tipos de Movimientos:

1. **Apertura** (`tipo: 'apertura'`)
   - Monto: `monto_inicial`
   - Efecto: Suma al saldo

2. **Venta** (`tipo: 'venta'`)
   - Monto: `venta.total`
   - Efecto: Suma al saldo
   - Incluye: Ventas válidas y anuladas (las anuladas se muestran con "(Anulada)")

3. **Devolución** (`tipo: 'devolucion'`)
   - Monto: `-venta.total` (negativo)
   - Efecto: Resta del saldo
   - Solo si: La venta está anulada Y NO existe un GastoCaja de devolución (para evitar duplicación)

4. **Gasto** (`tipo: 'gasto'`)
   - Monto: `gasto.monto`
   - Efecto: Resta del saldo

5. **Ingreso** (`tipo: 'ingreso'`)
   - Monto: `ingreso.monto`
   - Efecto: Suma al saldo

6. **Retiro** (`tipo: 'retiro'`)
   - Monto: `gasto.monto` (cuando la descripción contiene "Retiro de dinero al cerrar caja")
   - Efecto: Resta del saldo

### Cálculo de Saldo por Movimiento:

```python
saldo_actual = 0  # Iniciar en 0 antes de la apertura

for movimiento in movimientos_unificados:
    saldo_antes = saldo_actual
    monto = int(movimiento['monto'])
    
    if movimiento['tipo'] == 'apertura':
        saldo_despues = saldo_antes + monto
    elif movimiento['tipo'] == 'venta' or movimiento['tipo'] == 'ingreso':
        saldo_despues = saldo_antes + monto
    elif movimiento['tipo'] == 'devolucion':
        saldo_despues = saldo_antes + monto  # monto ya es negativo
    elif movimiento['tipo'] == 'retiro' or movimiento['tipo'] == 'gasto':
        saldo_despues = saldo_antes - monto
    else:
        saldo_despues = saldo_antes
    
    movimiento['saldo_antes'] = saldo_antes
    movimiento['saldo_despues'] = saldo_despues
    saldo_actual = saldo_despues
```

## 🔍 Puntos Importantes

### Ventas Anuladas:
- **Si hay GastoCaja de devolución:** La venta anulada ingresó dinero que luego se devolvió
- **Si NO hay GastoCaja de devolución:** La venta anulada nunca ingresó dinero físico

### Filtrado de Ventas:
- **Caja abierta:** Ventas del día actual (`inicio_dia` a `fin_dia`)
- **Caja cerrada:** Ventas desde `fecha_apertura` hasta `fecha_cierre`

### Gastos e Ingresos:
- Se incluyen **TODOS** los gastos/ingresos de la caja (no solo del día)
- Esto incluye retiros registrados al cerrar la caja

## 📋 Verificación de Consistencia

Para verificar que los cálculos son correctos:

1. **Saldo Final = Saldo Calculado:**
   ```
   saldo_caja == último movimiento['saldo_despues']
   ```

2. **Dinero Físico = Solo Efectivo:**
   ```
   dinero_fisico_caja == monto_inicial + ventas_efectivo + ingresos - gastos
   ```

3. **Total Ventas = Suma de Ventas Válidas:**
   ```
   total_ventas == sum(venta.total for venta in ventas_caja if not venta.anulada)
   ```

## 🛠️ Comandos Útiles para Verificar

```bash
# Verificar totales de una caja
python manage.py trazar_saldo_caja

# Diagnosticar problemas de caja
python manage.py diagnosticar_caja
```

