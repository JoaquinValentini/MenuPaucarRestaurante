
# scripts/build_i18n_en.py
import json, os, sys
from pathlib import Path

# --- Config ---
SRC_DIR = Path("data")           # origen (español)
OUT_DIR = Path("i18n/en/data")   # destino (inglés)
CACHE_FILE = Path("cache/translations_es_en.json")
TRANSLATE_ALL_VALUES_FILES = {"ui.json"}

# Ajustá según tus esquemas:
FIELDS_TO_TRANSLATE = {"title", "desc", "note"}  # agregá aquí las nuevas claves si hace falta

# --- Carga traductor offline Argos ---
try:
    import argostranslate.package, argostranslate.translate
except ImportError:
    print("ERROR: Falta argostranslate. Ejecuta: pip install argostranslate", file=sys.stderr)
    sys.exit(1)

installed_languages = argostranslate.translate.get_installed_languages()
es = next((l for l in installed_languages if l.code.startswith("es")), None)
en = next((l for l in installed_languages if l.code.startswith("en")), None)
if not es or not en:
    print("ERROR: Falta paquete ES->EN. Ejecuta:\n python -m argostranslate.install --from-lang es --to-lang en", file=sys.stderr)
    sys.exit(1)

translator = es.get_translation(en)

# --- Cache de traducciones ---
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
    translated = translator.translate(t)
    cache[t] = translated
    return translated


def translate_value(key: str, value, *, translate_all: bool = False):
    if isinstance(value, str):
        # Si el archivo está en la lista, traducimos cualquier string
        if translate_all or key in FIELDS_TO_TRANSLATE:
            DO_NOT_TRANSLATE = {
                "Coca-Cola", "Sprite", "Levité", "Lo de Paucar",
                "anticucho", "ají amarillo", "choripán", "papa a la huancaína",
            }
            if value.strip() in DO_NOT_TRANSLATE:
                return value
            return tr(value)
    return value

def walk_and_translate(node, *, translate_all: bool = False):
    if isinstance(node, dict):
        return {k: walk_and_translate(translate_value(k, v, translate_all=translate_all),
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

    # Si el nombre del archivo está en la lista, traducimos todo
    translate_all = rel.name in TRANSLATE_ALL_VALUES_FILES  # <--- NUEVO
    translated = walk_and_translate(data, translate_all=translate_all)
    out_path.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {rel} -> {out_path}")

def main():
    for path in SRC_DIR.rglob("*.json"):
        process_file(path)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nListo. Archivos traducidos en:", OUT_DIR)

if __name__ == "__main__":
    main()
