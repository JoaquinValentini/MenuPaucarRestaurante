from pathlib import Path
import json, sys

BASE_DIR = Path(__file__).resolve().parent.parent

SRC_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "i18n" / "pt" / "data"
CACHE_FILE = BASE_DIR / "cache" / "translations_es_pt.json"

FIELDS_TO_TRANSLATE = {"title", "desc", "note"}
TRANSLATE_ALL_VALUES_FILES = {"ui.json"}

# --- Carga traductor offline Argos ---
try:
    import argostranslate.package, argostranslate.translate
except ImportError:
    print("ERROR: Falta argostranslate. Ejecuta: pip install argostranslate", file=sys.stderr)
    sys.exit(1)

# Prepara traductor ES->PT
installed_languages = argostranslate.translate.get_installed_languages()
es = next((l for l in installed_languages if l.code.startswith("es")), None)
pt = next((l for l in installed_languages if l.code.startswith("pt")), None)
if not es or not pt:
    print("ERROR: Falta paquete ES->PT. Ejecuta:\n  python -m argostranslate.install --from-lang es --to-lang pt", file=sys.stderr)
    sys.exit(1)
translator = es.get_translation(pt)

# --- Cache de traducciones (para no repetir) ---
cache = {}
if CACHE_FILE.exists():
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}

def tr(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return t
    if t in cache:
        return cache[t]
    # Traduce y guarda en cache
    translated = translator.translate(t)
    cache[t] = translated
    return translated

def translate_value(key: str, value, *, translate_all: bool = False):
    if isinstance(value, str):
        # Si el archivo está en la lista, traducimos cualquier string; si no, solo los campos definidos
        if translate_all or key in FIELDS_TO_TRANSLATE:
            DO_NOT_TRANSLATE = {
                "Coca-Cola", "Sprite", "Levité", "Lo de Paucar",
                # Platos/terminología que preferís mantener en español:
                "anticucho", "ají amarillo", "choripán", "papa a la huancaína",
            }
            if value.strip() in DO_NOT_TRANSLATE:
                return value
            return tr(value)
    return value

def walk_and_translate(node, *, translate_all: bool = False):
    if isinstance(node, dict):
        return {k: walk_and_translate(
                    translate_value(k, v, translate_all=translate_all),
                    translate_all=translate_all)
                for k, v in node.items()}
    if isinstance(node, list):
        return [walk_and_translate(item, translate_all=translate_all) for item in node]
    return node

def process_file(src_path: Path):
    rel = src_path.relative_to(SRC_DIR)
    out_path = OUT_DIR / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(src_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] {src_path} no es JSON válido ({e}). Se copia sin cambios.")
        out_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
        return

    # NUEVO: si el archivo es ui.json, traducimos TODOS los strings
    translate_all = rel.name in TRANSLATE_ALL_VALUES_FILES  # <--- NUEVO

    translated = walk_and_translate(data, translate_all=translate_all)
    out_path.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {rel} -> {out_path}")

def main():
    # Recorre todos los .json en data/
    for path in SRC_DIR.rglob("*.json"):
        process_file(path)
    # Guarda cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nListo. Archivos traducidos en:", OUT_DIR)

if __name__ == "__main__":
    main()
