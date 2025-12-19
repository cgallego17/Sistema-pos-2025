# Resolver Conflicto de Merge en el Servidor

## Opción 1: Usar versión remota (RECOMENDADO)
Esta opción usa la versión remota que incluye todas las correcciones recientes:

```bash
cd /var/www/miapp
git checkout --theirs pos/views.py
git add pos/views.py
git commit -m "Resolver conflicto: usar versión remota de pos/views.py"
```

## Opción 2: Ver el conflicto primero
Si quieres revisar el conflicto antes de resolverlo:

```bash
cd /var/www/miapp
git diff pos/views.py
```

Luego puedes elegir:
- `git checkout --theirs pos/views.py` (versión remota)
- `git checkout --ours pos/views.py` (versión local)
- O editar manualmente el archivo

## Después de resolver

1. Verificar que el conflicto esté resuelto:
```bash
git status
```

2. Si todo está bien, hacer commit:
```bash
git commit -m "Resolver conflicto: usar versión remota de pos/views.py"
```

3. Sincronizar con el remoto:
```bash
git pull --rebase
# O si prefieres merge:
git pull
```

## Nota importante
La versión remota incluye todas las correcciones para guardar conteos físicos con valor 0, por lo que es la versión recomendada.
