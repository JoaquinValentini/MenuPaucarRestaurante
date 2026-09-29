const $=id=>document.getElementById(id);
let csrf='',catalog=[],current=null,dirty=false;
let setupToken=new URLSearchParams(location.hash.slice(1)).get('setup') || sessionStorage.getItem('paucar.setup');
let needsSetup=false;
if(setupToken){sessionStorage.setItem('paucar.setup',setupToken);history.replaceState(null,'','/admin/');}
const message=text=>{$('message').textContent=text;};
async function api(path,data,raw=false){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),path==='save'?120000:(raw?45000:12000));
 try{
  const r=await fetch('/api/'+path,{signal:controller.signal,...(data===undefined?{}:{method:'POST',headers:{'Content-Type':raw?'application/octet-stream':'application/json','X-CSRF-Token':csrf},body:raw?data:JSON.stringify(data)})});
  if(!(r.headers.get('content-type')||'').includes('application/json'))throw Error('El servidor abierto no corresponde al panel. Cerrá el servidor anterior y ejecutá INICIAR.cmd.');
  const v=await r.json();if(!r.ok){if(r.status===401&&path!=='login')showAuth();throw Error(v.error||'No se pudo completar la operación.');}return v;
 }catch(e){if(e.name==='AbortError')throw Error('El servidor tardó demasiado en responder. Volvé a intentar; si estabas creando la cuenta, primero recargá para comprobar si se guardó.');if(e instanceof TypeError)throw Error('No se pudo conectar al servidor. Ejecutá INICIAR.cmd y volvé a intentar.');throw e;}finally{clearTimeout(timer);}
}
function showAuth(){$('auth').hidden=false;$('editor').hidden=true;$('logout').hidden=true;}
async function load(){
 const s=await api('session');
 if(s.autoPublishVersion!==2)throw Error('Está ejecutándose un servidor anterior que no publica automáticamente. Cerralo y abrí INICIAR.cmd de MenuPaucarRestaurante.');
 csrf=s.csrf||'';needsSetup=s.needsSetup;
 if(!needsSetup){setupToken=null;sessionStorage.removeItem('paucar.setup');}
 $('authTitle').textContent=needsSetup?'Crear la única cuenta':'Bienvenido';
 $('authHelp').textContent=needsSetup?(setupToken?'Elegí un usuario de 3 a 40 letras, números, puntos o guiones y una contraseña de al menos 12 caracteres.':'Para configurar la cuenta, abrí INICIAR.cmd en esta computadora.'):'Ingresá con la cuenta del restaurante.';
 $('loginButton').textContent=needsSetup?'Crear cuenta':'Ingresar';$('loginButton').disabled=needsSetup&&!setupToken;
 $('confirmationLabel').hidden=!needsSetup;$('confirmation').required=needsSetup;$('password').minLength=needsSetup?12:1;$('password').autocomplete=needsSetup?'new-password':'current-password';
 if(!s.authenticated){showAuth();return;}
 const d=await api('catalog');catalog=d.categories;$('category').replaceChildren(...catalog.map(c=>new Option(c.title,c.key)));current=catalog[0];$('auth').hidden=true;$('editor').hidden=false;$('logout').hidden=false;render();
}
$('loginForm').onsubmit=async e=>{
 e.preventDefault();$('loginButton').disabled=true;$('loginButton').textContent=needsSetup?'Creando cuenta…':'Ingresando…';message('Conectando con el servidor…');
 try{
  if(needsSetup&&$('password').value!==$('confirmation').value)throw Error('Las contraseñas no coinciden.');
  await api(needsSetup?'setup':'login',{username:$('username').value.trim(),password:$('password').value,token:setupToken});
  $('password').value='';$('confirmation').value='';message('Sesión iniciada.');await load();
 }catch(e){message(e.message);}finally{$('loginButton').disabled=needsSetup&&!setupToken;$('loginButton').textContent=needsSetup?'Crear cuenta':'Ingresar';}
};
function field(label,value,update,type='text'){const l=document.createElement('label');l.textContent=label;const input=document.createElement(type==='textarea'?'textarea':'input');if(type!=='textarea')input.type=type;input.value=value??'';if(type==='number'){input.min=0;input.step='0.01';}input.oninput=()=>{update(type==='number'?(input.value===''?'':Number(input.value)):input.value);dirty=true;};l.append(input);return l;}
function render(){$('count').textContent=current.products.length+' productos · '+current.title;$('products').replaceChildren();for(const p of current.products){const card=document.createElement('article');card.className='product';const img=document.createElement('img');img.src='/'+(p.img||'imagenes/placeholder.svg');img.alt=p.title;img.onerror=()=>{img.onerror=null;img.src='/imagenes/placeholder.svg';};card.append(img);const body=document.createElement('div');body.className='product-content';const grid=document.createElement('div');grid.className='fields';grid.append(field('Nombre',p.title,v=>p.title=v),field('Precio en pesos',p.price,v=>p.price=v,'number'));for(const[k,label]of[['desc','Descripción'],['note','Aclaración']]){const f=field(label,p[k],v=>p[k]=v,k==='desc'?'textarea':'text');f.className='wide';grid.append(f);}body.append(grid);const upload=document.createElement('label');upload.className='upload';upload.textContent='Cambiar foto (JPG, PNG o WebP · máximo 8 MB)';const file=document.createElement('input');file.type='file';file.accept='image/jpeg,image/png,image/webp';file.onchange=async()=>{if(!file.files[0])return;file.disabled=true;$('save').disabled=true;try{const d=await api('upload',file.files[0],true);p.img=d.path;img.src='/'+p.img;dirty=true;message('Foto cargada. Guardá los cambios para mostrarla en el menú.');}catch(e){message(e.message);}finally{file.disabled=false;$('save').disabled=false;}};upload.append(file);body.append(upload);const visibility=document.createElement('label');visibility.className='visible';const box=document.createElement('input');box.type='checkbox';box.checked=p.available!==false;box.onchange=()=>{p.available=box.checked;dirty=true;};visibility.append(box,document.createTextNode('Mostrar en el menú'));body.append(visibility);const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Traducciones (opcional)';details.append(summary);for(const[lang,name]of[['en','Inglés'],['pt','Portugués']]){p[lang]??={};for(const[key,label]of[['title','nombre'],['desc','descripción'],['note','aclaración']])details.append(field(name+' · '+label,p[lang][key],v=>p[lang][key]=v));}body.append(details);card.append(body);$('products').append(card);}}
$('category').onchange=()=>{if(dirty&&!confirm('Hay cambios sin guardar. ¿Querés descartarlos?')){$('category').value=current.key;return;}dirty=false;api('catalog').then(d=>{catalog=d.categories;current=catalog.find(c=>c.key===$('category').value);render();}).catch(e=>message(e.message));};
$('add').onclick=()=>{current.products.push({id:crypto.randomUUID(),title:'Nuevo producto',desc:'',note:'',price:'',img:'',available:true});dirty=true;render();$('products').lastElementChild.scrollIntoView({behavior:'smooth'});};
$('save').onclick=async()=>{$('save').disabled=true;$('save').textContent='Guardando y publicando…';message('Guardando los cambios y enviándolos a GitHub…');try{const result=await api('save',{category:current.key,products:current.products});dirty=false;message(result.message||'El servidor guardó los archivos, pero no confirmó el commit. Reiniciá el servidor con INICIAR.cmd.'); }catch(e){message(e.message);}finally{$('save').disabled=false;$('save').textContent='Guardar y publicar';}};
$('logout').onclick=async()=>{if(dirty&&!confirm('¿Cerrar sesión y descartar cambios sin guardar?'))return;try{await api('logout',{});dirty=false;location.href='/admin/';}catch(e){message(e.message);}};
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
load().catch(e=>{message(e.message);$('retry').hidden=false;});
$('retry').onclick=async()=>{$('retry').disabled=true;try{await load();message('');$('retry').hidden=true;}catch(e){message(e.message);}finally{$('retry').disabled=false;}};
