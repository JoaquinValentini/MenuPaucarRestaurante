import os, json, secrets, hashlib, hmac, time, threading, mimetypes, re, io
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, unquote
from http.cookies import SimpleCookie

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / '.private'
PRIVATE.mkdir(exist_ok=True)
ACCOUNT = PRIVATE / 'account.json'
PORT = int(os.getenv('PORT', '8000'))
ORIGIN = os.getenv('PUBLIC_ORIGIN', f'http://localhost:{PORT}').rstrip('/')
HOST = os.getenv('BIND_HOST', '127.0.0.1')
SECURE = ORIGIN.startswith('https://')
if HOST not in ('localhost','127.0.0.1') and not SECURE:
    raise SystemExit('Para acceso remoto configure PUBLIC_ORIGIN con HTTPS y un proxy TLS.')
TOKEN = secrets.token_urlsafe(32) if not ACCOUNT.exists() else ''
if TOKEN: (PRIVATE / 'setup-url.txt').write_text(f'{ORIGIN}/admin/#setup={TOKEN}', encoding='utf-8')
SESSIONS = {}
ATTEMPTS = {}
LOCK = threading.RLock()
def atomic(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp,path)
def digest(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384,r=8,p=1).hex()
def categories():
    data=json.loads((ROOT/'data/categories.json').read_text(encoding='utf-8-sig'))
    return [s for c in data['categories'] for s in c.get('subcategories',[c])]
CATEGORIES = {Path(c['file']).stem:c for c in categories()}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,data, cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.headers_common()
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def headers_common(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if SECURE: self.send_header('Strict-Transport-Security','max-age=31536000')
    def session(self):
        try:
            c=SimpleCookie(self.headers.get('Cookie','')); token=c['session'].value
            with LOCK:
                s=SESSIONS.get(token)
                if s and s['expires']>time.time(): return token,s
                SESSIONS.pop(token,None)
        except (KeyError,ValueError): pass
        return None,None
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/session':
            _,s=self.session()
            return self.reply(200,{'authenticated':bool(s),'csrf':s['csrf'] if s else None,'needsSetup':not ACCOUNT.exists()})
        if path=='/api/catalog':
            if not self.session()[1]: return self.reply(401,{'error':'Iniciá sesión.'})
            return self.reply(200,{'categories':[{'key':k,'title':c['title'],'products':json.loads((ROOT/c['file']).read_text(encoding='utf-8-sig'))['products']} for k,c in CATEGORIES.items()]})
        path=unquote(path)
        if path in ('/admin','/admin/'): path='/admin/index.html'
        if path=='/': path='/index.html'
        parts=Path(path.lstrip('/')).parts
        allowed=bool(parts) and (parts[0] in ('css','js','Componentes','imagenes','data','i18n') or path in ('/index.html','/admin/index.html','/admin/app.js','/admin/style.css'))
        f=(ROOT/path.lstrip('/')).resolve()
        if not allowed or any(p.startswith('.') for p in parts) or not f.is_relative_to(ROOT) or not f.is_file(): return self.reply(404,{'error':'No encontrado.'})
        raw=f.read_bytes(); self.send_response(200); self.headers_common()
        self.send_header('Content-Type',mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        if self.headers.get('Origin')!=ORIGIN: return self.reply(403,{'error':'Origen no autorizado.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>8*1024*1024: return self.reply(413,{'error':'Archivo o solicitud demasiado grande (máximo 8 MB).'})
            raw=self.rfile.read(size)
            path=urlsplit(self.path).path
            if path=='/api/upload':
                _,s=self.session()
                if not s: return self.reply(401,{'error':'Iniciá sesión.'})
                if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.reply(403,{'error':'Sesión inválida.'})
                from PIL import Image, ImageOps
                Image.MAX_IMAGE_PIXELS=25000000
                with Image.open(io.BytesIO(raw)) as im:
                    if im.format not in ('JPEG','PNG','WEBP'): raise ValueError('Usá JPG, PNG o WebP.')
                    im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((1600,1600))
                    name='imagenes/'+secrets.token_hex(16)+'.jpg'; im.save(ROOT/name,'JPEG',quality=86)
                return self.reply(200,{'path':name})
            body=json.loads(raw)
            if path in ('/api/setup','/api/login'):
                with LOCK:
                    now=time.time(); failures=[t for t in ATTEMPTS.get('account',[]) if now-t<900]
                    ATTEMPTS['account']=failures
                    if len(failures)>=10: return self.reply(429,{'error':'Demasiados intentos. Esperá 15 minutos.'})
                    user=body.get('username',''); password=body.get('password','')
                    if not isinstance(user,str) or not isinstance(password,str) or len(password)>256: raise ValueError('Datos inválidos.')
                    if path=='/api/setup':
                        if ACCOUNT.exists() or not TOKEN or not hmac.compare_digest(body.get('token',''),TOKEN): return self.reply(403,{'error':'Configuración no autorizada.'})
                        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}',user) or len(password)<12: raise ValueError('Usuario: 3 a 40 letras, números, punto o guion. Contraseña: mínimo 12 caracteres.')
                        salt=secrets.token_hex(16); atomic(ACCOUNT,{'username':user,'salt':salt,'hash':digest(password,salt)})
                        (PRIVATE/'setup-url.txt').unlink(missing_ok=True)
                    else:
                        if not ACCOUNT.exists(): return self.reply(403,{'error':'Falta configurar la cuenta.'})
                        a=json.loads(ACCOUNT.read_text()); valid=hmac.compare_digest(digest(password,a['salt']),a['hash'])
                        if not (hmac.compare_digest(user,a['username']) and valid):
                            failures.append(now); return self.reply(401,{'error':'Usuario o contraseña incorrectos.'})
                    ATTEMPTS.clear()
                    for key in list(SESSIONS):
                        if SESSIONS[key]['expires']<now: del SESSIONS[key]
                    token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
                    SESSIONS[token]={'csrf':csrf,'expires':now+28800}
                return self.reply(200,{'ok':True,'csrf':csrf},f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if SECURE else ''))
            token,s=self.session()
            if not s: return self.reply(401,{'error':'Iniciá sesión.'})
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.reply(403,{'error':'Sesión inválida.'})
            if path=='/api/logout':
                with LOCK: SESSIONS.pop(token,None)
                return self.reply(200,{'ok':True},'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if SECURE else ''))
            if path=='/api/save':
                key=body.get('category'); items=body.get('products')
                if key not in CATEGORIES or not isinstance(items,list) or len(items)>500: raise ValueError('Categoría inválida.')
                ids=set()
                for p in items:
                    if not isinstance(p,dict) or not isinstance(p.get('title'),str) or not p['title'].strip(): raise ValueError('Cada producto necesita nombre.')
                    if not isinstance(p.get('id'),str) or not p['id'] or p['id'] in ids: raise ValueError('Identificador duplicado o vacío.')
                    ids.add(p['id'])
                    if p.get('price') not in ('',None) and (isinstance(p['price'],bool) or not isinstance(p['price'],(int,float)) or not 0<=p['price']<=100000000): raise ValueError('Precio inválido.')
                    img=p.get('img','')
                    if img and (not isinstance(img,str) or not img.startswith('imagenes/') or not (ROOT/img).resolve().is_relative_to(ROOT/'imagenes')): raise ValueError('Imagen inválida.')
                    if len(json.dumps(p))>15000: raise ValueError('Texto demasiado largo.')
                with LOCK:
                    f=ROOT/CATEGORIES[key]['file']; backup=PRIVATE/'backups'; backup.mkdir(exist_ok=True)
                    (backup/(key+'-'+str(time.time_ns())+'.json')).write_bytes(f.read_bytes())
                    atomic(f,{'products':items})
                return self.reply(200,{'ok':True})
            return self.reply(404,{'error':'No encontrado.'})
        except (ValueError,TypeError,KeyError): return self.reply(400,{'error':'Revisá los datos: nombre, precio, imagen y contraseña.'})
        except Exception: return self.reply(500,{'error':'No se pudo completar la operación. Los cambios no fueron confirmados.'})

if __name__=='__main__':
    print('Panel disponible en '+ORIGIN+'/admin/',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
