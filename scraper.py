# ============================================
# marketplace_ecuador - Scraper Principal
# ============================================

import time
import json
import csv
import os
import re
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from filtros import detectar_motor, extraer_anio, extraer_precio, es_oportunidad, verificar_fotos, puntaje_calidad
from alertas import enviar_alerta_telegram
from config import BUSQUEDAS, CIUDAD, RADIO_KM, CSV_SALIDA, JSON_SALIDA, DB_VISTOS, INTERVALO_MINUTOS


def cargar_vistos() -> set:
    """Carga los IDs de listings ya procesados."""
    if os.path.exists(DB_VISTOS):
        with open(DB_VISTOS, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()


def guardar_visto(listing_id: str):
    """Guarda un ID como procesado."""
    with open(DB_VISTOS, "a") as f:
        f.write(listing_id + "\n")


def guardar_resultado(listing: dict):
    """Guarda el listing en CSV y JSON."""
    listing_csv = {k: v for k, v in listing.items() if k != 'foto_urls'}
    file_exists = os.path.exists(CSV_SALIDA)
    with open(CSV_SALIDA, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=listing_csv.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(listing_csv)
    datos = []
    if os.path.exists(JSON_SALIDA):
        with open(JSON_SALIDA, "r", encoding="utf-8") as f:
            try: datos = json.load(f)
            except: datos = []
    datos.append(listing)
    with open(JSON_SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def scroll_hasta_fin(page, max_sin_cambio=3, pausa_min=2.5, pausa_max=4.0):
    """
    Hace scroll hacia abajo hasta que Facebook no cargue
    mas listings nuevos. Para cuando 3 scrolls seguidos
    no aumentan el numero de items.
    Retorna el total de items encontrados.
    """
    ultimo_total = 0
    sin_cambio = 0
    ronda = 0

    while sin_cambio < max_sin_cambio:
        ronda += 1
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(pausa_min, pausa_max))

        items_ahora = len(page.query_selector_all('a[href*="/marketplace/item/"]'))

        if items_ahora == ultimo_total:
            sin_cambio += 1
            print(f"      Scroll {ronda}: sin cambio ({sin_cambio}/{max_sin_cambio})")
        else:
            nuevos = items_ahora - ultimo_total
            print(f"      Scroll {ronda}: +{nuevos} items (total: {items_ahora})")
            sin_cambio = 0
            ultimo_total = items_ahora

    print(f"   Scroll completo: {ultimo_total} items cargados en {ronda} scrolls")
    return ultimo_total


def extraer_listings_de_pagina(page):
    """Extrae todos los listings visibles en la pagina despues del scroll."""
    items = page.query_selector_all('a[href*="/marketplace/item/"]')
    listings_base = []
    ids_vistos = set()

    for item in items:
        try:
            href = item.get_attribute("href") or ""
            match = re.search(r'/marketplace/item/(\d+)', href)
            if not match: continue
            listing_id = match.group(1)
            if listing_id in ids_vistos: continue
            ids_vistos.add(listing_id)

            texto_card = item.inner_text() or ""
            lineas = [l.strip() for l in texto_card.split('\n') if l.strip()]
            titulo = lineas[0] if lineas else "Sin titulo"
            precio = extraer_precio(texto_card)
            motor = detectar_motor(titulo, texto_card)
            anio = extraer_anio(titulo + ' ' + texto_card)

            listings_base.append({
                "id": listing_id,
                "titulo": titulo,
                "precio": precio,
                "motor": motor,
                "anio": anio,
                "url": f"https://www.facebook.com/marketplace/item/{listing_id}",
            })
        except:
            continue

    return listings_base


def scrapear_marketplace(page, busqueda: dict) -> list:
    """
    Scrapea Facebook Marketplace haciendo scroll hasta el final
    para capturar TODOS los listings disponibles, no solo los primeros.
    """
    query = busqueda["query"].replace(" ", "%20")
    url = f"https://www.facebook.com/marketplace/{CIUDAD}/search?query={query}&radius={RADIO_KM}"

    print(f"\nBuscando: {busqueda['nombre']}")
    print(f"   URL: {url}")
    page.goto(url, wait_until='domcontentloaded')
    time.sleep(random.uniform(3, 5))

    # --- SCROLL INTELIGENTE hasta el final de la pagina ---
    print(f"   Iniciando scroll inteligente...")
    total_cargados = scroll_hasta_fin(
        page,
        max_sin_cambio=3,   # Para si 3 scrolls no cargan nada nuevo
        pausa_min=2.5,
        pausa_max=4.0
    )

    # --- Extraer todos los listings ---
    listings_base = extraer_listings_de_pagina(page)
    print(f"   Cards unicas extraidas: {len(listings_base)}")

    # --- Estadisticas rapidas de lo encontrado ---
    motores = {}
    for l in listings_base:
        m = l.get('motor', 'desconocido')
        motores[m] = motores.get(m, 0) + 1
    print(f"   Distribucion por motor: {motores}")

    # --- Entrar a cada listing para verificar fotos y vendedor ---
    listings_completos = []
    for i, listing in enumerate(listings_base):
        try:
            titulo_corto = listing['titulo'][:45]
            precio_txt = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
            print(f"   [{i+1}/{len(listings_base)}] {titulo_corto} | {precio_txt}")

            # Verificar fotos
            info_fotos = verificar_fotos(listing['url'], page)
            listing.update(info_fotos)
            listing['puntaje'] = puntaje_calidad(listing)
            listing['busqueda'] = busqueda['nombre']
            listing['fecha_encontrado'] = datetime.now().isoformat()

            fotos = info_fotos['cantidad_fotos']
            puntaje = listing['puntaje']
            motor = listing.get('motor', '?')

            # Mostrar resultado del analisis
            if es_oportunidad(listing, busqueda):
                print(f"      OPORTUNIDAD Motor:{motor} | Fotos:{fotos} | Puntaje:{puntaje}/10")
            elif fotos < 3:
                print(f"      DESCARTADO pocas fotos ({fotos})")
            elif motor not in [busqueda.get('motor_objetivo'), 'desconocido']:
                print(f"      DESCARTADO motor {motor} != {busqueda.get('motor_objetivo')}")
            else:
                print(f"      Motor:{motor} | Fotos:{fotos} | Puntaje:{puntaje}/10")

            listings_completos.append(listing)
            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            print(f"      Error: {e}")
            listings_completos.append(listing)
            continue

    # Resumen final de esta busqueda
    oportunidades = [l for l in listings_completos if es_oportunidad(l, busqueda)]
    descartados = len(listings_completos) - len(oportunidades)
    print(f"")
    print(f"   RESUMEN {busqueda['nombre']}:")
    print(f"   Total analizados : {len(listings_completos)}")
    print(f"   Oportunidades    : {len(oportunidades)}")
    print(f"   Descartados      : {descartados}")
    print(f"   {'=' * 40}")

    return listings_completos


def run():
    """Funcion principal del scraper."""
    print("=" * 55)
    print("  marketplace_ecuador")
    print("  Scroll inteligente - captura TODOS los listings")
    print("=" * 55)

    vistos = cargar_vistos()
    stats_dia = {'total': 0, 'oportunidades': 0, 'estafas': 0, 'duplicados': 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-EC",
        )
        page = context.new_page()

        page.goto("https://www.facebook.com/marketplace/")
        time.sleep(5)

        while True:
            print(f"\nRevision: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            stats_dia = {'total': 0, 'oportunidades': 0, 'estafas': 0, 'duplicados': 0}

            for busqueda in BUSQUEDAS:
                try:
                    listings = scrapear_marketplace(page, busqueda)
                    nuevos = 0
                    oportunidades = 0

                    for listing in listings:
                        lid = listing["id"]
                        if lid not in vistos:
                            guardar_resultado(listing)
                            guardar_visto(lid)
                            vistos.add(lid)
                            nuevos += 1
                            stats_dia['total'] += 1
                            if es_oportunidad(listing, busqueda):
                                oportunidades += 1
                                stats_dia['oportunidades'] += 1
                                enviar_alerta_telegram(listing)

                    print(f"   Nuevos guardados: {nuevos} | Oportunidades: {oportunidades}")

                except Exception as e:
                    print(f"   Error en '{busqueda['nombre']}': {e}")

            print(f"\nEsperando {INTERVALO_MINUTOS} min para proxima revision...")
            time.sleep(INTERVALO_MINUTOS * 60)

        browser.close()


if __name__ == "__main__":
    run()
