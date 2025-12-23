const GRID_PATH = 'Componentes/productGrid.html';
const CARD_TEMPLATE_PATH = 'Componentes/productCard.html';
const CATEGORIES_MANIFEST = 'data/categories.json';
const PLACEHOLDER = 'imagenes/placeholder.svg';

async function ensureCardTemplate(){
  if(document.getElementById('product-card-template')) return;
  try{
    const res = await fetch(CARD_TEMPLATE_PATH);
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const html = await res.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    const tpl = tmp.querySelector('template');
    if(tpl) document.body.appendChild(tpl);
  }catch(err){
    console.warn('No se pudo cargar plantilla:', CARD_TEMPLATE_PATH, err);
  }
}

function renderError(container){
  container.innerHTML = `
    <div style="
      text-align: center;
      padding: 60px 20px;
      background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
      border-radius: 15px;
      margin: 40px 0;
    ">
      <div style="font-size: 72px; margin-bottom: 20px;">😞</div>
      <h2 style="color: #2d3748; margin-bottom: 15px;">Lamentamos las molestias</h2>
      <p style="color: #4a5568; font-size: 18px; line-height: 1.6; max-width: 500px; margin: 0 auto 30px;">
        La página está temporalmente caída.<br>
        Nuestro equipo técnico está trabajando para solucionarlo lo antes posible.
      </p>
      <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
        <button onclick="location.reload()" style="
          background: #4299e1;
          color: white;
          padding: 12px 30px;
          border-radius: 25px;
          border: none;
          font-weight: bold;
          cursor: pointer;
          font-size: 16px;
        ">
          🔄 Reintentar
        </button>
        <button onclick="window.location.href='mailto:contacto@daina.com'" style="
          background: #38a169;
          color: white;
          padding: 12px 30px;
          border-radius: 25px;
          border: none;
          font-weight: bold;
          cursor: pointer;
          font-size: 16px;
        ">
          📧 Contactar
        </button>
      </div>
      <p style="color: #a0aec0; margin-top: 30px; font-size: 14px;">
        Error técnico: No se pudo cargar el menú
      </p>
    </div>
  `;
}
function renderProductsIntoGrid(grid, products){
  const tpl = document.getElementById('product-card-template');
  if(!tpl) return;
  products.forEach(prod => {
    const clone = tpl.content.cloneNode(true);

    const img = clone.querySelector('.product-img');
    img.src = encodeURI(prod.img || PLACEHOLDER);
    img.alt = prod.title || 'Producto';
    img.loading = 'lazy';
    img.addEventListener('error', ()=>{ img.src = PLACEHOLDER; });

    const titleEl = clone.querySelector('.product-title'); if(titleEl) titleEl.textContent = prod.title || '';
    const descEl = clone.querySelector('.product-desc'); if(descEl) descEl.textContent = prod.desc || '';
    const noteEl = clone.querySelector('.product-note'); if(noteEl) noteEl.textContent = prod.note || '';
    const priceEl = clone.querySelector('.product-price'); if(priceEl) priceEl.textContent = prod.price || '';

    grid.appendChild(clone);
  });
}
async function renderAll(){
  // Crear `#grid-container` automáticamente si falta en el HTML
  let container = document.getElementById('grid-container');
  const mainEl = document.querySelector('main') || document.body;
  if(!container){
    container = document.createElement('section');
    container.id = 'grid-container';
    container.setAttribute('aria-label', 'Lista de productos');
    mainEl.appendChild(container);
  }

  await ensureCardTemplate();

  // 1) Procesar placeholders explícitos: cualquier elemento con `data-products`
  const placeholders = Array.from(document.querySelectorAll('[data-products]'));
  const renderedFiles = new Set();
  for(const el of placeholders){
    const file = el.getAttribute('data-products');
    const title = el.getAttribute('data-title') || null;
    if(!file) continue;
    el.innerHTML = '';
    if(title){ const h = document.createElement('h2'); h.textContent = title; el.appendChild(h); }
    const grid = document.createElement('div'); grid.className = 'product-grid'; el.appendChild(grid);

    try{
      const r = await fetch(file);
      if(!r.ok) throw new Error('HTTP ' + r.status);
      const products = await r.json();
      renderProductsIntoGrid(grid, products);
      renderedFiles.add(file);
    }catch(err){
      console.warn('No se pudo cargar', file, err);
      const warn = document.createElement('div'); warn.className = 'notice'; warn.textContent = 'No hay productos disponibles para esta sección.'; el.appendChild(warn);
    }
  }

  // Si hay placeholders explícitos en la página, respetamos el orden y NO cargamos el manifiesto
  // (así podés controlar exactamente qué se muestra y dónde). Si no hay placeholders, entonces
  // continuamos y cargamos el manifiesto normalmente.
  if(placeholders.length > 0) return;

  // 2) Cargar manifiesto y renderizar las categorías restantes en #grid-container
  try{
    const res = await fetch(CATEGORIES_MANIFEST);
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const categories = await res.json();

    // Limpia el contenedor por defecto sólo si está vacío
    if(container.innerHTML.trim() === '') container.innerHTML = '';

    for(const cat of categories){
      if(renderedFiles.has(cat.file)) continue; // ya renderizada manualmente
      const { section, grid } = (function(){
        const s = document.createElement('section'); s.className = 'category';
        if(cat.title){ const h = document.createElement('h2'); h.id = `cat-${cat.title}`; h.textContent = cat.title; s.appendChild(h); }
        const g = document.createElement('div'); g.className = 'product-grid'; s.appendChild(g);
        return { section: s, grid: g };
      })();

      try{
        const r = await fetch(cat.file);
        if(!r.ok) throw new Error('HTTP ' + r.status);
        const products = await r.json();
        renderProductsIntoGrid(grid, products);
      }catch(err){
        console.warn('No se pudo cargar productos de', cat.file, err);
        const warn = document.createElement('div'); warn.className = 'notice'; warn.textContent = 'No hay productos disponibles para esta categoría.'; section.appendChild(warn);
      }

      container.appendChild(section);
    }
  }catch(err){
    console.warn('No se pudo cargar manifest', CATEGORIES_MANIFEST, err);
    renderError(container);

    // Intentar el viejo grid como último recurso
    try{
      const r = await fetch(GRID_PATH);
      if(r.ok){ const html = await r.text(); container.innerHTML = html; }
    }catch(e){
      console.error('Fallback failed', e);
    }
  }
}

// Inicializa la interacción de las pestañas nav: asegura que solo la pestaña clickeada tenga `active`
function initNavTabs(){
  const tabs = Array.from(document.querySelectorAll('.nav-tab'));
  if(!tabs.length) return;

  tabs.forEach(tab => {
    // marcar estado inicial accesible
    tab.setAttribute('aria-pressed', tab.classList.contains('active') ? 'true' : 'false');

    tab.addEventListener('click', (e) => {
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-pressed', 'false');
      });
      const clicked = e.currentTarget;
      clicked.classList.add('active');
      clicked.setAttribute('aria-pressed', 'true');
    });
  });
}

document.addEventListener('DOMContentLoaded', () => { renderAll(); initNavTabs(); });