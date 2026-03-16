# ============================================
# marketplace_ecuador - Filtros de motor + fotos
# ============================================

import requests
import re

# Palabras clave que identifican motor 4.0 (V6)
KEYWORDS_40 = [
    "4.0", "4,0", "4000", "4000cc", "4.0l", "4.0v",
    "v6", "1gr", "1gr-fe", "sr5", "vx", "vxl",
    "cuatro litros", "4 litros"
]

# Palabras clave que identifican motor 2.7 (4 cil)
KEYWORDS_27 = [
    "2.7", "2,7", "2700", "2700cc", "2.7l",
    "2tr", "2tr-fe", "4 cil", "cuatro cilindros",
    "dos punto siete", "2.7t"
]

# Palabras negativas - publicaciones de baja calidad
KEYWORDS_MALOS = [
    "pregunte", "llamar para ver", "sin fotos", "foto referencial",
    "imagen referencial", "ver descripcion", "consultar precio",
    "publicidad", "se busca", "busco"
]

# Minimo de fotos para considerar publicacion seria
MIN_FOTOS = 3


def detectar_motor(titulo: str, descripcion: str = '') -> str:
    """
    Retorna '4.0', '2.7', o 'desconocido' segun el texto del anuncio.
    """
    texto = (titulo + ' ' + descripcion).lower()
    tiene_40 = any(k in texto for k in KEYWORDS_40)
    tiene_27 = any(k in texto for k in KEYWORDS_27)
    if tiene_40 and not tiene_27:
        return "4.0"
    elif tiene_27 and not tiene_40:
        return "2.7"
    elif tiene_40 and tiene_27:
        return "ambos_mencionados"
    else:
        return "desconocido"


def extraer_anio(texto: str):
    """Extrae el anio del vehiculo del texto."""
    anios = re.findall(r'\b(20[0-1][0-9]|202[0-6])\b', texto)
    if anios:
        return int(anios[0])
    return None


def extraer_precio(texto: str):
    """Extrae el precio numerico del texto."""
    precios = re.findall(r'\$?\s*([\d]{2,3}[.,]?[\d]{3})', texto)
    if precios:
        precio_str = precios[0].replace('.', '').replace(',', '')
        try:
            return float(precio_str)
        except:
            return None
    return None


def verificar_fotos(listing_url: str, page) -> dict:
    """
    Abre el listing y cuenta cuantas fotos tiene.
    Retorna dict con: cantidad, urls, tiene_suficientes
    """
    try:
        page.goto(listing_url, wait_until='domcontentloaded', timeout=15000)
        import time
        time.sleep(2)

        # Buscar miniaturas de fotos en el listing
        # Facebook muestra las fotos como imagenes en el carrusel
        selectores = [
            'img[data-visualcompletion="media-vc-image"]',
            'div[data-pagelet="MediaViewerPhoto"] img',
            'img[class*="x1ey2m1c"]',
            'div[role="img"]',
        ]

        foto_urls = []
        for selector in selectores:
            imgs = page.query_selector_all(selector)
            if imgs:
                for img in imgs:
                    src = img.get_attribute('src') or ''
                    # Filtrar solo imagenes reales (no iconos ni placeholders)
                    if ('scontent' in src or 'fbcdn' in src) and src not in foto_urls:
                        foto_urls.append(src)
                if foto_urls:
                    break

        cantidad = len(foto_urls)
        return {
            "cantidad_fotos": cantidad,
            "tiene_suficientes": cantidad >= MIN_FOTOS,
            "foto_urls": foto_urls[:5],  # guardar max 5 URLs
        }

    except Exception as e:
        print(f"   Error verificando fotos: {e}")
        return {
            "cantidad_fotos": 0,
            "tiene_suficientes": False,
            "foto_urls": [],
        }


def tiene_titulo_sospechoso(titulo: str) -> bool:
    """Detecta si el titulo tiene senales de publicacion de baja calidad."""
    texto = titulo.lower()
    return any(k in texto for k in KEYWORDS_MALOS)


def puntaje_calidad(listing: dict) -> int:
    """
    Calcula un puntaje de calidad del listing del 0 al 10.
    Mientras mas alto, mejor calidad de publicacion.
    """
    puntaje = 0

    # Fotos
    fotos = listing.get('cantidad_fotos', 0)
    if fotos >= 8:
        puntaje += 4
    elif fotos >= 5:
        puntaje += 3
    elif fotos >= 3:
        puntaje += 2
    elif fotos >= 1:
        puntaje += 1

    # Motor identificado
    if listing.get('motor') in ['4.0', '2.7']:
        puntaje += 2

    # Anio identificado
    if listing.get('anio'):
        puntaje += 1

    # Precio razonable (no $1 ni precio raro)
    precio = listing.get('precio')
    if precio and 5000 < precio < 100000:
        puntaje += 2

    # Titulo sin palabras sospechosas
    if not tiene_titulo_sospechoso(listing.get('titulo', '')):
        puntaje += 1

    return puntaje


def es_oportunidad(listing: dict, config_busqueda: dict) -> bool:
    """
    Determina si un listing es una oportunidad segun los filtros configurados.
    """
    motor = listing.get('motor', 'desconocido')
    precio = listing.get('precio')
    anio = listing.get('anio')

    # Filtrar por motor objetivo
    if motor != config_busqueda['motor_objetivo']:
        return False

    # Filtrar por precio
    if precio:
        if precio < config_busqueda['precio_min']:
            return False
        if precio > config_busqueda['precio_max']:
            return False

    # Filtrar por anio
    if anio:
        if anio < config_busqueda['anio_min']:
            return False
        if anio > config_busqueda['anio_max']:
            return False

    # Filtrar por calidad de publicacion
    puntaje = puntaje_calidad(listing)
    if puntaje < 4:
        return False

    # Filtrar por fotos suficientes
    if not listing.get('tiene_suficientes', False):
        return False

    return True
