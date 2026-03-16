# ============================================
# marketplace_ecuador - Filtros de motor
# ============================================

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

def detectar_motor(titulo: str, descripcion: str = "") -> str:
    """
    Retorna '4.0', '2.7', o 'desconocido' segun el texto del anuncio.
    """
    texto = (titulo + " " + descripcion).lower()

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
    import re
    anios = re.findall(r'\b(20[0-1][0-9]|202[0-6])\b', texto)
    if anios:
        return int(anios[0])
    return None


def extraer_precio(texto: str):
    """Extrae el precio numerico del texto."""
    import re
    precios = re.findall(r'\$?\s*([\d]{2,3}[.,]?[\d]{3})', texto)
    if precios:
        precio_str = precios[0].replace('.', '').replace(',', '')
        try:
            return float(precio_str)
        except:
            return None
    return None


def es_oportunidad(listing: dict, config_busqueda: dict) -> bool:
    """
    Determina si un listing es una oportunidad segun los filtros configurados.
    """
    motor = listing.get("motor", "desconocido")
    precio = listing.get("precio")
    anio = listing.get("anio")

    if motor != config_busqueda["motor_objetivo"]:
        return False

    if precio:
        if precio < config_busqueda["precio_min"]:
            return False
        if precio > config_busqueda["precio_max"]:
            return False

    if anio:
        if anio < config_busqueda["anio_min"]:
            return False
        if anio > config_busqueda["anio_max"]:
            return False

    return True
