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
    # Limpiar campos que no van bien en CSV
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
            try:
                datos = json.load(f)
            except:
                datos = []
    datos.append(listing)
    with open(JSON_SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def scrapear_marketplace(page, busqueda: dict) -> list:
    """Scrapea Facebook Marketplace y verifica fotos de cada listing."""
    query = busqueda["query"].replace(" ", "%20")
    url = f"https://www.facebook.com/marketplace/{CIUDAD}/search?query={query}&radius={RADIO_KM}"

    print(f"\nBuscando: {busqueda['nombre']}")
    page.goto(url, wait_until='domcontentloaded')
    time.sleep(random.uniform(3, 6))

    # Scroll para cargar mas resultados
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(2, 3))

    items = page.query_selector_all('a[href*="/marketplace/item/"]')
    print(f"   Cards encontradas: {len(items)}")

    listings_base = []
    ids_vistos_en_pagina = set()

    for item in items:
        try:
            href = item.get_attribute("href") or ""
            match = re.search(r'/marketplace/item/(\d+)', href)
            if not match:
                continue
            listing_id = match.group(1)
            if listing_id in ids_vistos_en_pagina:
                continue
            ids_vistos_en_pagina.add(listing_id)

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
                "busqueda": busqueda["nombre"],
            })
        except Exception as e:
            continue

    print(f"   Listings unicos: {len(listings_base)}")

    # Ahora entrar a cada listing para verificar fotos
    listings_completos = []
    for i, listing in enumerate(listings_base):
        try:
            print(f"   [{i+1}/{len(listings_base)}] Verificando fotos: {listing['titulo'][:50]}")

            info_fotos = verificar_fotos(listing['url'], page)
            listing.update(info_fotos)
            listing['puntaje'] = puntaje_calidad(listing)
            listing["fecha_encontrado"] = datetime.now().isoformat()

            print(f"      Fotos: {info_fotos['cantidad_fotos']} | Puntaje: {listing['puntaje']}/10")
            listings_completos.append(listing)

            # Pausa entre requests para no ser bloqueado
            time.sleep(random.uniform(1.5, 3))

        except Exception as e:
            print(f"      Error: {e}")
            listings_completos.append(listing)
            continue

    return listings_completos


def run():
    """Funcion principal del scraper."""
    print("=" * 55)
    print("  marketplace_ecuador - Iniciando con filtro de fotos")
    print("=" * 55)

    vistos = cargar_vistos()

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

        print("\nAbre Facebook y asegurate de estar logueado...")
        page.goto("https://www.facebook.com/marketplace/")
        time.sleep(5)

        while True:
            print(f"\nRevision: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

                            if es_oportunidad(listing, busqueda):
                                oportunidades += 1
                                fotos = listing.get('cantidad_fotos', 0)
                                puntaje = listing.get('puntaje', 0)
                                print(f"\n   OPORTUNIDAD [{puntaje}/10 pts | {fotos} fotos]")
                                print(f"   Titulo: {listing['titulo']}")
                                print(f"   Motor:  {listing['motor']}")
                                print(f"   Precio: ${listing.get('precio', 'N/A')}")
                                print(f"   URL:    {listing['url']}")
                                enviar_alerta_telegram(listing)

                    print(f"\n   Nuevos: {nuevos} | Oportunidades con buenas fotos: {oportunidades}")

                except Exception as e:
                    print(f"   Error: {e}")

            print(f"\nEsperando {INTERVALO_MINUTOS} min...")
            time.sleep(INTERVALO_MINUTOS * 60)

        browser.close()


if __name__ == "__main__":
    run()
