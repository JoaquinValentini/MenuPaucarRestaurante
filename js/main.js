/* main.js – Menú Lo de Paucar (Daina)
   - Procesa placeholders [data-products]
   - Carga manifest data/categories.json con soporte de subcategorías
   - Renderiza tarjetas usando <template id="product-card-template">
   - Robustez: no-cache, placeholder de imagen, precios en ARS
*/

const GRID_PATH = 'Componentes/productGrid.html';
const CARD_TEMPLATE_PATH = 'Componentes/productCard.html';
const CATEGORIES_MANIFEST = 'data/categories.json';
const PLACEHOLDER = 'Imagenes/placeholder.svg';

// Activa/desactiva logs de depuración
const DEBUG = true;

/* ---------- Utils ---------- */

function log(...args) { if (DEBUG) console.log(...args); }

async function fetchJSON(url) {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`HTTP ${res.status} – ${url}`);
  return res.json();
}

function formatARS(value) {
  // Si viene string con símbolo, intenta limpiarlo
  if (typeof value === 'string') {
    // quita todo excepto dígitos y separador decimal
    const num = Number(
      value.replace(/[^\d.,-]/g, '').replace(/\./g, '').replace(',', '.')
    );
    if (!Number.isNaN(num)) return `$ ${num.toLocaleString('es-AR')}`;
    return value; // si no pudo, muestra tal cual
  }
  if (typeof value === 'number') {
    return `$ ${Number(value).toLocaleString('es-AR')}`;
  }
  return '';
}

/* ---------- Plantilla de tarjeta ---------- */

async function ensureCardTemplate() {
  if (document.getElementById('product-card-template')) return;

  try {
    const res = await fetch(CARD_TEMPLATE_PATH, { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const html = await res.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    const tpl = tmp.querySelector('template');
    if (tpl) {
      document.body.appendChild(tpl);
      log('[TPL] Cargada desde', CARD_TEMPLATE_PATH);
      return;
    }
    throw new Error('No se encontró <template> en ' + CARD_TEMPLATE_PATH);
  } catch (err) {
    console.warn('No se pudo cargar plantilla, se usa fallback mínimo:', err);
    // Fallback: plantilla mínima compatible con los selectores usados
    const fallback = document.createElement('template');
    fallback.id = 'product-card-template';
    fallback.innerHTML = `
      <article class="product-card">
        <img class="product-img" alt="Producto" loading="lazy" />
        <div class="product-body">
          <h4 class="product-title"></h4>
          <p class="product-desc"></p>
          <p class="product-note"></p>
          <p class="product-price"></p>
        </div>
      </article>
    `;
    document.body.appendChild(fallback);
  }
}

/* ---------- Render de tarjetas ---------- */

function renderProductsIntoGrid(grid, products) {
  const tpl = document.getElementById('product-card-template');
  if (!tpl) return;

  products.forEach(prod => {
    const clone = tpl.content.cloneNode(true);

    const img = clone.querySelector('.product-img');
    const titleEl = clone.querySelector('.product-title');
    const descEl = clone.querySelector('.product-desc');
    const noteEl = clone.querySelector('.product-note');
    const priceEl = clone.querySelector('.product-price');

    // Imagen con placeholder y encoding de espacios
    const imgSrc = prod.img ? encodeURI(prod.img) : PLACEHOLDER;
    if (img) {
      img.src = imgSrc;
      img.alt = prod.title || 'Producto';
      img.addEventListener('error', () => { img.src = PLACEHOLDER; });
    }

    if (titleEl) titleEl.textContent = prod.title || '';
    if (descEl)  descEl.textContent  = prod.desc  || '';
    if (noteEl)  noteEl.textContent  = prod.note  || '';

    if (priceEl) {
      const hasPrice = prod.price !== undefined && prod.price !== null && prod.price !== '';
      priceEl.textContent = hasPrice ? formatARS(prod.price) : '';
    }

    grid.appendChild(clone);
  });
}

/* ---------- Construcción de secciones ---------- */

function createSectionWithSeparator(titleText) {
  // Estructura que respeta tu CSS (section-separator + separator-title)
  const section = document.createElement('section');
  section.className = 'category-section';

  const sep = document.createElement('div');
  sep.className = 'section-separator';

  const h = document.createElement('h2');
  h.className = 'separator-title';
  h.textContent = titleText || '';

  sep.appendChild(h);
  section.appendChild(sep);

  const grid = document.createElement('div');
  grid.className = 'product-grid';
  section.appendChild(grid);

  return { section, grid };
}

function renderError(container) {
  container.innerHTML = `
😞
<h3>Lamentamos las molestias</h3>
<p>La página está temporalmente caída.</p>
<p>🔄 Reintentar &nbsp; ✉️ Contactar</p>
<p class="muted">Error técnico: No se pudo cargar el menú.</p>
`;
}

/* ---------- Carga desde el manifest (categorías + subcategorías) ---------- */

async function loadFromManifest(container, renderedFiles) {
  log('>>> Cargando manifest:', CATEGORIES_MANIFEST);

  let manifest;
  try {
    manifest = await fetchJSON(CATEGORIES_MANIFEST);
  } catch (err) {
    console.warn('No se pudo leer el manifest', err);
    renderError(container);
    // Fallback legacy grid
    try {
      const r = await fetch(GRID_PATH, { cache: 'no-cache' });
      if (r.ok) container.innerHTML = await r.text();
    } catch (e) {
      console.error('Fallback failed', e);
    }
    return;
  }

  const categories = manifest.categories || manifest || []; // por si accidentalmente guardaste un array
  log('>>> categories:', categories.map(c => ({
    title: c.title,
    file: c.file,
    subcount: Array.isArray(c.subcategories) ? c.subcategories.length : 0
  })));

  for (const cat of categories) {
    // Si ya se renderizó ese JSON por placeholder, evitar duplicado
    if (cat.file && renderedFiles.has(cat.file)) {
      log('[SKIP CAT ya renderizada por placeholder]', cat.file);
      continue;
    }

    // 1) Categoría simple (un solo file)
    if (cat.file) {
      const { section, grid } = createSectionWithSeparator(cat.title || 'Categoría');
      try {
        const items = await fetchJSON(cat.file);
        renderProductsIntoGrid(grid, items);
      } catch (err) {
        console.warn('No se pudo cargar productos de', cat.file, err);
        const warn = document.createElement('div');
        warn.className = 'notice';
        warn.textContent = 'No hay productos disponibles para esta categoría.';
        section.appendChild(warn);
      }
      container.appendChild(section);
      continue;
    }

    // 2) Categoría con subcategorías (caso "Platos")
    if (Array.isArray(cat.subcategories) && cat.subcategories.length) {
      // Sección padre con separador de categoría
      const parent = document.createElement('section');
      const hCat = document.createElement('h2');

      for (const sub of cat.subcategories) {
        // Evita duplicado si la subcat ya se pintó por placeholder
        if (sub.file && renderedFiles.has(sub.file)) {
          log('[SKIP SUB ya renderizada por placeholder]', sub.file);
          continue;
        }

        // Título h3 por subcategoría
        const hSub = document.createElement('h3');
        hSub.textContent = sub.title || 'Subcategoría';
        parent.appendChild(hSub);

        // Grid por subcategoría
        const subGrid = document.createElement('div');
        subGrid.className = 'product-grid';
        parent.appendChild(subGrid);

        try {
          const items = await fetchJSON(sub.file);
          renderProductsIntoGrid(subGrid, items);
        } catch (err) {
          console.warn(`No se pudo cargar ${sub.file}`, err);
          const warn = document.createElement('div');
          warn.className = 'notice';
          warn.textContent = `No hay productos disponibles para "${sub.title}".`;
          parent.appendChild(warn);
        }
      }

      container.appendChild(parent);
      continue;
    }

    // 3) Categoría sin datos
    const empty = document.createElement('section');
    empty.className = 'category-section';
    const sep2 = document.createElement('div');
    sep2.className = 'section-separator';
    const h2 = document.createElement('h2');
    h2.className = 'separator-title';
    h2.textContent = cat.title || 'Categoría';
    sep2.appendChild(h2);
    empty.appendChild(sep2);
    const muted = document.createElement('div');
    muted.className = 'notice';
    muted.textContent = 'Sin contenido.';
    empty.appendChild(muted);
    container.appendChild(muted);
  }
}

/* ---------- Render principal ---------- */

async function renderAll() {
  // 0) Contenedor donde pintaremos (si no existe, se crea)
  let container = document.getElementById('grid-container');
  const mainEl = document.querySelector('main') || document.body;
  if (!container) {
    container = document.createElement('section');
    container.id = 'grid-container';
    container.setAttribute('aria-label', 'Lista de productos');
    mainEl.appendChild(container);
  }

  await ensureCardTemplate();

  // 1) Procesar placeholders explícitos (respetar orden del HTML)
  const placeholders = Array.from(document.querySelectorAll('[data-products]'));
  const renderedFiles = new Set();

  for (const el of placeholders) {
    const file = el.getAttribute('data-products');
    const title = el.getAttribute('data-title') || null;
    if (!file) continue;

    // Limpia el placeholder y agrega su separador si corresponde
    el.innerHTML = '';
    if (title) {
      const sep = document.createElement('div');
      sep.className = 'section-separator';
      const h = document.createElement('h2');
      h.className = 'separator-title';
      h.textContent = title;
      sep.appendChild(h);
      el.appendChild(sep);
    }

    // Crea su grid local
    const grid = document.createElement('div');
    grid.className = 'product-grid';
    el.appendChild(grid);

    // Carga y render
    try {
      log('[PLACEHOLDER]', { title, file });
      const r = await fetch(file, { cache: 'no-cache' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const products = await r.json();
      renderProductsIntoGrid(grid, products);
      renderedFiles.add(file);
    } catch (err) {
      console.warn('No se pudo cargar', file, err);
      const warn = document.createElement('div');
      warn.className = 'notice';
      warn.textContent = 'No hay productos disponibles para esta sección.';
      el.appendChild(warn);
    }
  }

  // 2) Además, cargar el manifest para el resto (incluye "Platos" con subcategorías)
  await loadFromManifest(container, renderedFiles);
}

document.addEventListener('DOMContentLoaded', renderAll);
