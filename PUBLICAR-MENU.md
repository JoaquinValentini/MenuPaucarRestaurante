# Guardar y publicar desde el panel local

INICIAR.cmd abre http://localhost:8000/admin/. Al guardar una categoría, el servidor guarda sus datos, crea un commit con ese archivo y sus fotos, y ejecuta push a origin/main. El acceso a GitHub usa las credenciales Git de la computadora; no se pide ni se guarda un token en la página.

La computadora necesita Git, conexión a Internet y acceso de escritura al repositorio. Si GitHub no acepta el envío, el panel conserva los cambios locales y explica que no se confirmó la publicación. Corregí el acceso desde VS Code y volvé a guardar. Si ya se había creado el commit, el reintento lo envía sin duplicarlo.

El panel no incorpora archivos de código ni credenciales al commit. Si hay commits de código pendientes o cambios nuevos en GitHub, pide sincronizar desde VS Code antes de publicar. No hace push forzado ni resuelve conflictos automáticamente.

Un envío exitoso no significa que el despliegue terminó: GitHub Pages todavía debe completar su publicación. Revisá Actions en GitHub si el sitio no cambia. Este mecanismo supone que Pages publica desde main o que su workflow se activa con los cambios enviados a main.

Este panel se usa en localhost. GitHub Pages aloja el menú público; no ejecuta el servidor ni el acceso del administrador.
