"""Publish only menu content using the computer's existing Git credentials."""
import os
import subprocess
from pathlib import Path

def publish(root, category_file, products):
    committed = False
    commit_id = None
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'}
    def git(*args, timeout=15):
        transport = ['-c', 'http.sslBackend=openssl'] if os.name == 'nt' else []
        result = subprocess.run(['git', *transport, *args], cwd=root, env=env, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=timeout)
        if result.returncode:
            if 'permission denied' in result.stderr.lower() and ('.git/' in result.stderr or '.git\\' in result.stderr):
                raise RuntimeError('No se pudo escribir en la carpeta interna de Git. Cerrá este servidor y ejecutá INICIAR.cmd desde el Explorador de Windows con tu usuario habitual.')
            raise RuntimeError('Git no pudo completar la operación. Revisá la conexión y el acceso a GitHub desde VS Code y volvé a guardar.')
        return result.stdout.strip()
    def menu_path(path):
        return (path.startswith('data/') and path.endswith('.json')) or path.startswith('imagenes/')
    try:
        if git('branch', '--show-current') != 'main':
            raise RuntimeError('La publicación requiere la rama main. Cambiala desde VS Code antes de reintentar.')
        paths=[category_file]
        for product in products:
            image=product.get('img','')
            if image and (root/image).is_file() and image not in paths:
                paths.append(image)
        # Do not include unrelated staged files or credentials in the commit.
        changed=git('status','--porcelain','--',*paths)
        if changed:
            git('add','--',*paths)
            git('commit','--only','-m',
                'Actualizar carta: '+Path(category_file).stem,'--',*paths)
        commit_id=git('rev-parse','--short','HEAD')
        committed=True
        # Create the local commit even when the connection to GitHub is unavailable.
        git('fetch', 'origin', 'main', timeout=25)
        ahead, behind = map(int, git('rev-list', '--left-right', '--count', 'HEAD...origin/main').split())
        if behind:
            raise RuntimeError('Hay cambios nuevos en GitHub. Sincronizá el proyecto desde VS Code y volvé a guardar; no se sobrescribió nada.')
        if ahead:
            outgoing=git('log','--format=','--name-only','origin/main..HEAD').splitlines()
            if any(not menu_path(p) for p in outgoing if p):
                raise RuntimeError('Hay commits de código pendientes. Publicalos desde VS Code antes de usar la publicación del menú.')
        git('push','origin','HEAD:main',timeout=30)
        return {'published':True,'committed':True,'commit':commit_id,
                'message':'Cambios enviados a GitHub. La página pública se actualizará cuando termine el despliegue de GitHub Pages.'}
    except subprocess.TimeoutExpired:
        return {'published':False,'committed':committed,'commit':commit_id,'message':('Commit '+commit_id+' guardado. ' if committed else 'Guardado localmente, sin commit confirmado. ')+'GitHub tardó demasiado en responder. Volvé a guardar para reintentar la publicación.'}
    except (RuntimeError,OSError) as error:
        return {'published':False,'committed':committed,'commit':commit_id,'message':('Commit '+commit_id+' guardado; envío pendiente. ' if committed else 'Guardado localmente, pero no se pudo crear el commit. ')+str(error)}
