# ============================================
# marketplace_ecuador - Filtros de Ropa
# ============================================

import re

# ------------------------------------
# MARCAS y su precio retail referencial en Ecuador (USD)
# ------------------------------------
MARCAS_PRECIO_RETAIL = {
    # Premium
    "ralph lauren": 75,
    "tommy hilfiger": 65,
    "lacoste": 80,
    "calvin klein": 60,
    "hugo boss": 90,
    "versace": 150,
    "gucci": 300,
    "louis vuitton": 400,
    "burberry": 250,
    "armani": 120,

    # Deportivas
    "nike": 55,
    "adidas": 50,
    "jordan": 80,
    "under armour": 50,
    "puma": 45,
    "new balance": 55,
    "reebok": 45,
    "converse": 50,

    # Casuales populares
    "zara": 40,
    "h&m": 25,
    "levis": 55,
    "wrangler": 45,
    "lee": 40,
    "dockers": 45,
    "polo": 60,

    # Ropa de bebe/ninos premium
    "carter": 25,
    "oshkosh": 22,
    "gap kids": 30,
    "chicco": 20,

    # Zapatos
    "adidas": 80,
    "nike air": 120,
    "vans": 70,
    "timberland": 100,
    "dr martens": 120,
}

# ------------------------------------
# TALLAS validas para filtrar
# ------------------------------------
TALLAS_ROPA = [
    "xs", "s", "m", "l", "xl", "xxl", "xxxl",
    "28", "29", "30", "31", "32", "33", "34", "36", "38", "40", "42",
    "talla s", "talla m", "talla l", "talla xl",
    "small", "medium", "large",
    "6", "8", "10", "12", "14",  # tallas de ninos
]

# ------------------------------------
# ESTADOS de la prenda
# ------------------------------------
KEYWORDS_NUEVO = [
    "nuevo", "nueva", "sin usar", "con etiqueta", "etiquetado",
    "nunca usado", "nunca usada", "original", "importado"
]

KEYWORDS_BUEN_ESTADO = [
    "buen estado", "excelente estado", "casi nuevo", "poco uso",
    "impecable", "perfecto estado", "como nuevo"
]

KEYWORDS_MAL_ESTADO = [
    "manchado", "roto", "desgastado", "faded", "decolorado",
    "reparado", "cosido", "parchado"
]


def detectar_marca(titulo: str, descripcion: str = '') -> dict:
    """
    Detecta la marca de la prenda y retorna marca + precio retail.
    """
    texto = (titulo + ' ' + descripcion).lower()
    for marca, precio_retail in MARCAS_PRECIO_RETAIL.items():
        if marca in texto:
            return {
                "marca": marca,
                "precio_retail": precio_retail
            }
    return {
        "marca": "sin marca",
        "precio_retail": None
    }


def detectar_talla(titulo: str, descripcion: str = '') -> str:
    """Detecta la talla de la prenda."""
    texto = (titulo + ' ' + descripcion).lower()
    for talla in TALLAS_ROPA:
        # Buscar talla como palabra completa
        if re.search(rf'\b{re.escape(talla)}\b', texto):
            return talla.upper()
    return "desconocida"


def detectar_estado(titulo: str, descripcion: str = '') -> str:
    """Detecta el estado de la prenda."""
    texto = (titulo + ' ' + descripcion).lower()
    if any(k in texto for k in KEYWORDS_NUEVO):
        return "nuevo"
    elif any(k in texto for k in KEYWORDS_BUEN_ESTADO):
        return "buen_estado"
    elif any(k in texto for k in KEYWORDS_MAL_ESTADO):
        return "mal_estado"
    else:
        return "desconocido"


def calcular_descuento(precio_venta: float, precio_retail: float) -> float:
    """Calcula el porcentaje de descuento vs precio retail."""
    if not precio_venta or not precio_retail or precio_retail == 0:
        return 0.0
    descuento = ((precio_retail - precio_venta) / precio_retail) * 100
    return round(descuento, 1)


def es_oportunidad_ropa(listing: dict) -> bool:
    """
    Determina si una prenda es oportunidad de arbitraje.
    Criterios: marca conocida + descuento > 40% + buen estado + precio razonable
    """
    precio = listing.get('precio')
    marca_info = listing.get('marca_info', {})
    precio_retail = marca_info.get('precio_retail')
    estado = listing.get('estado_prenda', 'desconocido')
    descuento = listing.get('descuento_pct', 0)

    # Debe tener marca conocida
    if not precio_retail:
        return False

    # Descuento mayor al 40% del retail
    if descuento < 40:
        return False

    # No debe estar en mal estado
    if estado == 'mal_estado':
        return False

    # Precio minimo razonable (no regalos trampa)
    if not precio or precio < 3:
        return False

    # Precio maximo para que haya margen de ganancia
    if precio_retail and precio > precio_retail * 0.7:
        return False

    return True


def puntaje_ropa(listing: dict) -> int:
    """Puntaje de calidad 0-10 para listings de ropa."""
    puntaje = 0

    # Marca reconocida
    marca_info = listing.get('marca_info', {})
    if marca_info.get('precio_retail', 0) >= 80:
        puntaje += 4  # marca premium
    elif marca_info.get('precio_retail', 0) >= 40:
        puntaje += 2  # marca media

    # Descuento
    descuento = listing.get('descuento_pct', 0)
    if descuento >= 60:
        puntaje += 3
    elif descuento >= 40:
        puntaje += 2
    elif descuento >= 20:
        puntaje += 1

    # Estado
    estado = listing.get('estado_prenda', '')
    if estado == 'nuevo':
        puntaje += 2
    elif estado == 'buen_estado':
        puntaje += 1

    # Fotos
    if listing.get('tiene_suficientes', False):
        puntaje += 1

    return min(puntaje, 10)


def analizar_listing_ropa(listing: dict) -> dict:
    """
    Funcion principal: analiza un listing de ropa y agrega todos los campos.
    """
    titulo = listing.get('titulo', '')
    texto = listing.get('texto_completo', '')

    marca_info = detectar_marca(titulo, texto)
    talla = detectar_talla(titulo, texto)
    estado = detectar_estado(titulo, texto)
    precio = listing.get('precio')
    precio_retail = marca_info.get('precio_retail')
    descuento = calcular_descuento(precio, precio_retail) if precio and precio_retail else 0

    listing['marca_info'] = marca_info
    listing['marca'] = marca_info['marca']
    listing['precio_retail_ref'] = precio_retail
    listing['talla'] = talla
    listing['estado_prenda'] = estado
    listing['descuento_pct'] = descuento
    listing['puntaje'] = puntaje_ropa(listing)
    listing['es_oportunidad'] = es_oportunidad_ropa(listing)

    return listing
