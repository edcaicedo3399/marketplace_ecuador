# ============================================
# marketplace_ecuador - Detector de Duplicados y Estafas
# ============================================
# Detecta el mismo carro publicado en varias ciudades
# o a precios muy distintos = posible estafa o arbitraje
# ============================================

import json
import os
import re
from difflib import SequenceMatcher
from datetime import datetime

DB_DUPLICADOS = 'duplicados.json'

# Diferencia de precio que activa alerta de duplicado sospechoso
DIFERENCIA_PRECIO_ALERTA = 0.20  # 20% de diferencia entre ciudades

# Similitud minima de titulo para considerar mismo vehiculo
SIMILITUD_TITULO_MIN = 0.65


# ============================================
# SENALES DE ESTAFA conocidas en Marketplace EC
# ============================================
SENALES_ESTAFA = [
    # Precios trampa
    "precio negociable fuera",
    "pago por adelantado",
    "deposito primero",
    "transfiera primero",
    "deposite para reservar",
    "senal para apartar",
    "envio a domicilio gratis",
    "entrega a domicilio gratis",

    # Contacto sospechoso
    "whatsapp only",
    "solo whatsapp",
    "no llame",
    "mensaje solo",
    "telegram",

    # Urgencia falsa
    "urgente vendo",
    "viaje urgente",
    "necesito vender hoy",
    "ultimo precio",
    "me voy del pais",
    "emigro",
    "divorci",

    # Precio irreal
    "regalo",
    "regalado",

    # Documentos sospechosos
    "sin papeles",
    "tramite pendiente",
    "matricula pendiente",
    "sin matricula",
    "papeles en tramite",
]


def similitud_texto(a: str, b: str) -> float:
    """Calcula similitud entre dos strings. 1.0 = identicos."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalizar_titulo(titulo: str) -> str:
    """Limpia el titulo para comparacion."""
    titulo = titulo.lower()
    # Quitar caracteres especiales
    titulo = re.sub(r'[^a-z0-9 ]', ' ', titulo)
    # Quitar palabras comunes que no aportan
    stopwords = ['vendo', 'venta', 'se', 'de', 'la', 'el', 'en', 'y', 'a', 'con', 'por']
    palabras = [p for p in titulo.split() if p not in stopwords and len(p) > 2]
    return ' '.join(palabras)


def detectar_senales_estafa(listing: dict) -> list:
    """
    Revisa el titulo y descripcion buscando senales de estafa.
    Retorna lista de senales encontradas.
    """
    texto = (listing.get('titulo', '') + ' ' + listing.get('texto_completo', '')).lower()
    encontradas = []
    for senal in SENALES_ESTAFA:
        if senal in texto:
            encontradas.append(senal)
    return encontradas


def nivel_riesgo_estafa(senales: list, listing: dict) -> dict:
    """
    Calcula nivel de riesgo: BAJO / MEDIO / ALTO / MUY_ALTO
    """
    puntos = len(senales) * 2

    precio = listing.get('precio', 0) or 0
    anio = listing.get('anio', 0) or 0

    # Precio demasiado bajo para el tipo de vehiculo
    if precio and precio < 8000 and 'fortuner' in listing.get('titulo', '').lower():
        puntos += 3
    if precio and precio < 5000 and 'hilux' in listing.get('titulo', '').lower():
        puntos += 3

    # Precio $1 o muy bajo
    if precio and precio < 100:
        puntos += 4

    # Sin anio identificado en vehiculos
    if not anio and listing.get('busqueda', '') in ['Fortuner 4.0', 'Fortuner 2.7', 'Hilux 4x4']:
        puntos += 1

    if puntos == 0:
        nivel = 'LIMPIO'
        emoji = 'OK'
    elif puntos <= 2:
        nivel = 'BAJO'
        emoji = 'REVISAR'
    elif puntos <= 4:
        nivel = 'MEDIO'
        emoji = 'CUIDADO'
    elif puntos <= 6:
        nivel = 'ALTO'
        emoji = 'SOSPECHOSO'
    else:
        nivel = 'MUY_ALTO'
        emoji = 'PROBABLE ESTAFA'

    return {
        'nivel': nivel,
        'emoji': emoji,
        'puntos_riesgo': puntos,
        'senales_encontradas': senales
    }


def cargar_db_duplicados() -> list:
    """Carga la base de datos de listings guardados para comparar."""
    if os.path.exists(DB_DUPLICADOS):
        with open(DB_DUPLICADOS, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def guardar_en_db_duplicados(listing: dict):
    """Agrega un listing a la base de datos de comparacion."""
    db = cargar_db_duplicados()
    # Guardar solo los campos necesarios para comparacion
    entrada = {
        'id': listing.get('id'),
        'titulo_normalizado': normalizar_titulo(listing.get('titulo', '')),
        'titulo_original': listing.get('titulo', ''),
        'precio': listing.get('precio'),
        'anio': listing.get('anio'),
        'motor': listing.get('motor'),
        'url': listing.get('url'),
        'fecha': datetime.now().isoformat(),
        'texto': listing.get('texto_completo', '')[:200]
    }
    db.append(entrada)
    with open(DB_DUPLICADOS, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def buscar_duplicados(listing: dict) -> list:
    """
    Busca si el listing ya existe en la DB con titulo similar
    pero en distinta ciudad o a distinto precio.
    Retorna lista de posibles duplicados.
    """
    db = cargar_db_duplicados()
    titulo_nuevo = normalizar_titulo(listing.get('titulo', ''))
    precio_nuevo = listing.get('precio', 0) or 0
    id_nuevo = listing.get('id', '')
    duplicados = []

    for entrada in db:
        if entrada.get('id') == id_nuevo:
            continue  # Es el mismo listing

        titulo_db = entrada.get('titulo_normalizado', '')
        similitud = similitud_texto(titulo_nuevo, titulo_db)

        if similitud >= SIMILITUD_TITULO_MIN:
            precio_db = entrada.get('precio', 0) or 0

            # Calcular diferencia de precio
            if precio_nuevo and precio_db:
                precio_mayor = max(precio_nuevo, precio_db)
                precio_menor = min(precio_nuevo, precio_db)
                diff_pct = (precio_mayor - precio_menor) / precio_mayor
            else:
                diff_pct = 0

            duplicados.append({
                'id_similar': entrada.get('id'),
                'titulo_similar': entrada.get('titulo_original'),
                'precio_similar': precio_db,
                'url_similar': entrada.get('url'),
                'similitud_pct': round(similitud * 100, 1),
                'diferencia_precio_pct': round(diff_pct * 100, 1),
                'fecha_original': entrada.get('fecha'),
                'es_sospechoso': diff_pct >= DIFERENCIA_PRECIO_ALERTA
            })

    # Ordenar por similitud descendente
    duplicados.sort(key=lambda x: x['similitud_pct'], reverse=True)
    return duplicados[:5]  # Retornar max 5 duplicados


def analizar_listing_completo(listing: dict) -> dict:
    """
    Funcion principal: analiza estafa + duplicados de un listing.
    Agrega campos: riesgo_estafa, duplicados_encontrados
    """
    # 1. Detectar senales de estafa
    senales = detectar_senales_estafa(listing)
    riesgo = nivel_riesgo_estafa(senales, listing)
    listing['riesgo_estafa'] = riesgo

    # 2. Buscar duplicados en la DB
    duplicados = buscar_duplicados(listing)
    listing['duplicados_encontrados'] = duplicados

    # 3. Marcar si tiene duplicado sospechoso
    tiene_dup_sospechoso = any(d.get('es_sospechoso') for d in duplicados)
    listing['tiene_duplicado_sospechoso'] = tiene_dup_sospechoso

    # 4. Guardar en DB para futuras comparaciones
    guardar_en_db_duplicados(listing)

    return listing


def reporte_duplicados_por_ciudad(json_file: str = 'resultados.json') -> dict:
    """
    Lee todos los resultados guardados y genera un reporte de
    listings que aparecen en multiples ciudades con precios distintos.
    """
    if not os.path.exists(json_file):
        return {}

    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            datos = json.load(f)
        except:
            return {}

    # Agrupar por titulo normalizado
    grupos = {}
    for listing in datos:
        titulo_norm = normalizar_titulo(listing.get('titulo', ''))
        if not titulo_norm:
            continue
        if titulo_norm not in grupos:
            grupos[titulo_norm] = []
        grupos[titulo_norm].append(listing)

    # Filtrar grupos con mas de 1 listing
    sospechosos = {}
    for titulo, grupo in grupos.items():
        if len(grupo) > 1:
            precios = [l.get('precio') for l in grupo if l.get('precio')]
            if precios:
                precio_max = max(precios)
                precio_min = min(precios)
                diff = ((precio_max - precio_min) / precio_max) * 100 if precio_max else 0
                if diff >= 15:  # mas de 15% diferencia = sospechoso
                    sospechosos[titulo] = {
                        'cantidad_publicaciones': len(grupo),
                        'precio_min': precio_min,
                        'precio_max': precio_max,
                        'diferencia_pct': round(diff, 1),
                        'listings': [{
                            'titulo': l.get('titulo'),
                            'precio': l.get('precio'),
                            'url': l.get('url'),
                        } for l in grupo]
                    }

    return dict(sorted(sospechosos.items(),
                        key=lambda x: x[1]['diferencia_pct'],
                        reverse=True))
