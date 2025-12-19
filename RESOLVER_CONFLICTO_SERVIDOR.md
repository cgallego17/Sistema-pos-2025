# Resolver Conflicto de Merge en el Servidor

## Pasos para resolver el conflicto

### 1. Ver el conflicto
```bash
cd /ruta/al/proyecto  # Ajusta la ruta según tu configuración
git status
```

### 2. Ver el archivo con conflictos
```bash
grep -n "<<<<<<< HEAD" pos/views.py
grep -n "=======" pos/views.py
grep -n ">>>>>>>" pos/views.py
```

### 3. Opción A: Usar la versión del servidor (si tienes cambios locales importantes)
```bash
# Ver qué cambios hay en el servidor
git diff HEAD pos/views.py

# Si quieres mantener los cambios del servidor y descartar los remotos
git checkout --ours pos/views.py
git add pos/views.py
git commit -m "Resolver conflicto: mantener versión del servidor"
```

### 4. Opción B: Usar la versión remota (recomendado si los cambios remotos son los correctos)
```bash
# Usar la versión remota (la que acabamos de corregir)
git checkout --theirs pos/views.py
git add pos/views.py
git commit -m "Resolver conflicto: usar versión remota con correcciones"
```

### 5. Opción C: Resolver manualmente (si necesitas combinar ambos)
```bash
# Abrir el archivo y buscar los marcadores de conflicto
nano pos/views.py
# o
vim pos/views.py
```

Busca líneas que contengan:
- `<<<<<<< HEAD` (inicio del conflicto, versión local)
- `=======` (separador)
- `>>>>>>> origin/main` (fin del conflicto, versión remota)

### 6. Después de resolver, continuar con el merge
```bash
git add pos/views.py
git commit -m "Resolver conflicto de merge en pos/views.py"
```

### 7. Continuar con la actualización
```bash
update  # o el comando que uses para actualizar
```

## Solución Rápida (Recomendada)

Si quieres usar la versión remota (que tiene las correcciones para el guardado de conteos con valor 0):

```bash
cd /ruta/al/proyecto
git checkout --theirs pos/views.py
git add pos/views.py
git commit -m "Resolver conflicto: usar versión remota con correcciones de conteo físico"
update
```



