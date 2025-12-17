# Comandos para Resolver el Problema de Git

## Opción 1: Guardar cambios locales (recomendado)

```bash
cd /var/www/sistema-pos
git stash push -m "Cambios locales antes de deploy"
git pull origin main
```

## Opción 2: Descartar cambios locales (si no los necesitas)

```bash
cd /var/www/sistema-pos
git reset --hard HEAD
git pull origin main
```

## Opción 3: Hacer commit de los cambios locales (si quieres guardarlos)

```bash
cd /var/www/sistema-pos
git add .
git commit -m "Cambios locales antes de pull"
git pull origin main
```

## Ver qué cambios tienes localmente

```bash
cd /var/www/sistema-pos
git status
```

## Recuperar cambios guardados en stash (después del pull)

```bash
git stash list
git stash pop
```


