
import re, json, sys, shutil
from pathlib import Path

# --- Configuración ---
SRC_DIR = Path("data")  # carpeta donde están tus "json" en formato plano
FIELDS = ["id", "title", "desc", "note", "img", "price"]

# Si tienes algunos .json que YA son válidos y no quieres tocarlos, ponlos aquí:
EXCLUDE_FILES = {
    # Ejemplos:
    # Path("data/categories.json"),
    # Path("data/entradas.json"),
}

# ¿Querés backup del original antes de convertir? (True/False)
MAKE_BACKUP = True

def is_probably_json(text: str) -> bool:
    """Heurística simple: si empieza con '{' o '[', asumimos JSON."""
    t = text.strip()
    return t.startswith("{") or t.startswith("[")

def parse_line(line: str) -> dict:
    """
    Convierte una línea tipo:
      id coca cola title Coca Cola desc 1.75L y 500ml note Sin alcohol img imagenes/coca cola.png price
    en un objeto {id, title, desc, note, img, price}
    """
    # Separa por etiquetas y agrupa valores entre etiquetas
    tokens = re.split(r'\b(id|title|desc|note|img|price)\b', line, flags=re.IGNORECASE)
    obj = {}
    current_key = None

    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        low = tok.lower()
        if low in FIELDS:
            current_key = low
            obj.setdefault(current_key, "")
        else:
            if current_key:
                # Concatenamos el valor (por si hay espacios)
                if obj[current_key]:
                    obj[current_key] += " " + tok
                else:
                    obj[current_key] = tok

    # Normalizaciones:
    # - id sin espacios + minúscula + guiones bajos
    if "id" in obj:
        obj["id"] = obj["id"].strip().lower().replace(" ", "_")

    # - price: si quedó vacío → 0; si es número en string, lo intentamos parsear
    if "price" in obj:
        val = obj["price"].strip()
        if val == "":
            obj["price"] = 0
        else:
            # Si es algo como "123", parsea; si es texto, lo deja como string
            try:
                obj["price"] = float(val) if "." in val or "," in val else int(val)
            except:
                obj["price"] = val

    # Aseguramos todas las claves con string por defecto
    for f in FIELDS:
        obj.setdefault(f, "")

    return obj

def convert_file(path: Path):
    # Excluir si está en la lista de exclusiones
    if path in EXCLUDE_FILES:
        print(f"[SKIP] {path} (excluido)")
        return

    raw = path.read_text(encoding="utf-8", errors="ignore")

    # Si ya parece JSON, lo dejamos intacto
    if is_probably_json(raw):
        try:
            json.loads(raw)  # valida
            print(f"[OK] {path} ya es JSON válido (no se modifica)")
            return
        except Exception as e:
            print(f"[INFO] {path} parece JSON pero no es válido ({e}). Se intentará convertir desde formato plano.")

    # Dividimos por líneas no vacías
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    items = []

    for ln in lines:
        obj = parse_line(ln)
        # si la línea no contiene al menos 'id' y 'title', la ignoramos
        if obj.get("id") or obj.get("title"):
            items.append(obj)

    if not items:
        print(f"[WARN] {path} no produjo items; no se modifica.")
        return

    # Backup antes de sobrescribir
    if MAKE_BACKUP:
        backup_path = path.with_suffix(".bak")
        shutil.copy2(path, backup_path)
        print(f"[BKP] Copia de seguridad creada: {backup_path.name}")

    # Escribir JSON válido
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[FIX] {path} → {len(items)} item(s) convertidos a JSON")

def main():
    if not SRC_DIR.exists():
        print(f"ERROR: No existe la carpeta {SRC_DIR}. Créala y pon tus archivos .json allí.")
        sys.exit(1)

    converted = 0
    for p in SRC_DIR.rglob("*.json"):
        try:
            convert_file(p)
            converted += 1
        except Exception as e:
            print(f"[ERR] {p}: {e}")

    print(f"\n✅ Conversión completa. Archivos procesados: {converted}")
    print("Ahora podés ejecutar: python scripts/build_i18n.py  para generar i18n/pt/data/...")

if __name__ == "__main__":
    main()