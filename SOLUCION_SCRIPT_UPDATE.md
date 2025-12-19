# Solución para el problema de "nano" en el script update

## Problema
El script de actualización tiene un comando `nano` que está causando que el script se quede abierto esperando entrada interactiva.

## Solución

### Paso 1: Localizar el script
```bash
# Buscar el script update
which update
# o
alias | grep update
# o buscar en archivos comunes
ls -la ~/update
ls -la /usr/local/bin/update
ls -la /root/update
```

### Paso 2: Ver el contenido del script
```bash
cat ~/update
# o
cat /usr/local/bin/update
# o donde esté ubicado
```

### Paso 3: Corregir el script

El problema probablemente es algo como esto:
```bash
# ❌ INCORRECTO - Abre nano y se queda esperando
nano archivo.txt
```

**Solución:** Eliminar o comentar la línea de `nano`, o usar un comando no interactivo.

### Ejemplo de script corregido:

```bash
#!/bin/bash
# Script de actualización del sistema POS

echo "----------------------"
echo "🔄  ACTUALIZANDO APLICACIÓN"
echo "----------------------"

# Obtener cambios del repositorio
echo "📥 Obteniendo cambios del repositorio..."
cd /var/www/sistema-pos  # o la ruta donde esté tu proyecto

# Configurar git para merge
git config pull.rebase false

# Hacer pull
git pull origin main

# Si hay conflictos, manejarlos automáticamente o mostrar mensaje
if [ $? -ne 0 ]; then
    echo "⚠️  Hay conflictos. Revisar manualmente."
    exit 1
fi

# Aplicar migraciones
echo "📦 Aplicando migraciones..."
python3 manage.py migrate --noinput

# Recopilar archivos estáticos (si aplica)
# python3 manage.py collectstatic --noinput

# Reiniciar servicios (ajustar según tu configuración)
echo "🔄 Reiniciando servicios..."
# systemctl restart gunicorn  # o el servicio que uses
# systemctl restart nginx      # si aplica

echo "✅ Actualización completada"
```

### Paso 4: Hacer el script ejecutable
```bash
chmod +x ~/update
# o
chmod +x /usr/local/bin/update
```

### Paso 5: Si el script está en .bashrc o .bash_profile

Si el "update" es un alias o función en tu `.bashrc` o `.bash_profile`:

```bash
# Editar el archivo
nano ~/.bashrc
# o
nano ~/.bash_profile

# Buscar la función o alias "update" y eliminar cualquier línea con "nano"
```

### Alternativa: Usar un script separado

Si prefieres, puedes crear un nuevo script limpio:

```bash
# Crear nuevo script
cat > ~/update_pos.sh << 'EOF'
#!/bin/bash
echo "----------------------"
echo "🔄  ACTUALIZANDO APLICACIÓN"
echo "----------------------"
cd /var/www/sistema-pos
git config pull.rebase false
git pull origin main
python3 manage.py migrate --noinput
echo "✅ Actualización completada"
EOF

chmod +x ~/update_pos.sh

# Crear alias
echo 'alias update="~/update_pos.sh"' >> ~/.bashrc
source ~/.bashrc
```

## Verificación

Después de corregir, prueba el script:
```bash
update
```

Debería ejecutarse sin quedarse esperando entrada.




