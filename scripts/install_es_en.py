
# scripts/install_es_en.py
import sys

def log(msg):
    print(msg, flush=True)

print("== INICIO install_es_en.py ==")
try:
    import argostranslate.package as pkg
    import argostranslate.translate as tr
    log(" Import OK: argostranslate.package y .translate")
except Exception as e:
    print(" ERROR importando Argos Translate:", e)
    sys.exit(1)

try:
    log(" Actualizando índice de paquetes...")
    pkg.update_package_index()
    log(" Índice actualizado.")
except Exception as e:
    print(" ERROR al actualizar el índice:", e)
    sys.exit(2)

try:
    log(" Buscando paquete ES->EN en el índice...")
    available = pkg.get_available_packages()
    match = None
    for p in available:
        if str(p.from_code).startswith("es") and str(p.to_code).startswith("en"):
            match = p
            break
    if not match:
        print(" No encontré paquete ES->EN en el índice.")
        print("Paquetes disponibles (primeros 15):", [(p.from_code, p.to_code) for p in available[:15]])
        sys.exit(3)

    log(f" Descargando paquete: {match.from_code}->{match.to_code} ...")
    zip_path = match.download()  # descarga el .argosmodel
    log(f" Descargado: {zip_path}")
    log(" Instalando paquete...")
    pkg.install_from_path(zip_path)
    log(" Instalación completada.")
except Exception as e:
    print(" ERROR durante descarga/instalación:", e)
    sys.exit(4)

try:
    log(" Comprobación de idiomas instalados...")
    installed = tr.get_installed_languages()
    codes = [l.code for l in installed]
    log(f"Idiomas instalados: {codes}")
    es = next((l for l in installed if str(l.code).startswith("es")), None)
    en = next((l for l in installed if str(l.code).startswith("en")), None)
    if es and en:
        t = es.get_translation(en)
        result = t.translate("Hola, ¿cómo estás?")
        log(f"Prueba de traducción ES->EN: {result}")
    else:
        log(" No se detectaron 'es' y/o 'en' en los idiomas instalados.")
except Exception as e:
    print(" ERROR en la prueba de traducción:", e)
    sys.exit(5)

print("== FIN install_es_en.py ==")
