# Panel con cuenta única

Ejecutá INICIAR.cmd. El primer inicio abre un enlace privado para elegir el usuario y la contraseña (12 caracteres como mínimo). No existe contraseña predeterminada. Una vez creada la cuenta, el alta queda cerrada. El personal comparte esa única cuenta.

Los cambios en productos y fotos se guardan en archivos reales del proyecto y sobreviven al reinicio. El menú conserva la dirección / y el panel /admin/. Para ocultar un producto, desactivá Mostrar en el menú. Las traducciones comparten foto, precio y disponibilidad. Las fotos se convierten a JPEG y se redimensionan hasta 1600 píxeles.

La contraseña se almacena con scrypt y una sal aleatoria en .private/account.json. Las sesiones son temporales, vencen a las 8 horas y se invalidan al cerrar sesión o reiniciar el servidor. Hay límite de intentos de contraseña, validación del origen y protección CSRF. Cada guardado crea una copia anterior en .private/backups. Respaldá .private, data e imagenes de forma privada; no publiques ni agregues .private a Git.

## Servidor en Internet

Esta aplicación necesita un servidor con Python y almacenamiento persistente. No funciona publicando solo HTML en GitHub Pages. Instalá requirements.txt en un entorno Python. Ejecutá server.py como servicio supervisado detrás de un proxy HTTPS (por ejemplo Caddy o nginx), con PUBLIC_ORIGIN=https://tu-dominio y BIND_HOST=127.0.0.1. El proxy debe ser la única entrada pública y pasar las solicitudes a localhost:8000. El servidor activa cookies Secure y HSTS cuando PUBLIC_ORIGIN usa HTTPS. No uses python -m http.server ni decap-server para alojar este proyecto: no proporcionan este control de acceso. El puerto interno no debe exponerse directamente.

La implementación funciona como proceso único; requiere configurar el servicio, dominio, TLS, copias de respaldo y monitorización antes de abrirla al equipo en Internet. No se ha realizado una auditoría independiente de seguridad. Los datos del menú son públicos; no uses sus archivos para información sensible. Los archivos antiguos de Decap ya no se sirven ni se utilizan.

Para recuperar el acceso, un administrador del servidor puede detenerlo, guardar una copia privada de account.json y retirar ese archivo. Al reiniciar se genera un nuevo enlace de configuración local. Esto no lo puede hacer un visitante de la web. El enlace inicial está en .private/setup-url.txt y desaparece al crear la cuenta.
