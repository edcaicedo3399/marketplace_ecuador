# ============================================
# marketplace_ecuador - Canal Publico Telegram
# ============================================
# Publica automaticamente en canal publico de Telegram
# como vitrina gratuita para atraer clientes
# ============================================

import requests
import json
import os
from datetime import datetime
from config import TELEGRAM_TOKEN

# ID del canal publico de Telegram (ej: @marketplace_ecuador_bot)
# Diferente al chat privado de clientes
CANAL_PUBLICO_ID = os.getenv('CANAL_PUBLICO_ID', 'TU_CANAL_PUBLICO_AQUI')

# Cuantas publicaciones hacer por dia en el canal
MAX_POSTS_DIA = 5

DB_PUBLICADO = 'canal_publicado.json'


def _publicar_en_canal(mensaje):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI':
        print('   Canal no configurado')
        return False
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        r = requests.post(url, json={
            'chat_id': CANAL_PUBLICO_ID,
            'text': mensaje,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f'   Error canal: {e}')
        return False


def cargar_publicados():
    if os.path.exists(DB_PUBLICADO):
        with open(DB_PUBLICADO, 'r') as f:
            try: return json.load(f)
            except: return {'ids': [], 'hoy': 0, 'fecha': ''}
    return {'ids': [], 'hoy': 0, 'fecha': ''}


def guardar_publicado(listing_id):
    db = cargar_publicados()
    hoy = datetime.now().strftime('%Y-%m-%d')
    if db.get('fecha') != hoy:
        db['hoy'] = 0
        db['fecha'] = hoy
    db['ids'].append(listing_id)
    db['hoy'] = db.get('hoy', 0) + 1
    with open(DB_PUBLICADO, 'w') as f:
        json.dump(db, f)


def puede_publicar_hoy():
    db = cargar_publicados()
    hoy = datetime.now().strftime('%Y-%m-%d')
    if db.get('fecha') != hoy:
        return True
    return db.get('hoy', 0) < MAX_POSTS_DIA


def ya_fue_publicado(listing_id):
    return listing_id in cargar_publicados().get('ids', [])


def publicar_oportunidad_canal(listing, vendedor=None):
    if not puede_publicar_hoy() or ya_fue_publicado(listing.get('id', '')):
        return False

    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
    fotos = listing.get('cantidad_fotos', 0)
    puntaje = listing.get('puntaje', 0)
    motor = listing.get('motor', '')
    anio = listing.get('anio', '')

    # Score vendedor
    if vendedor:
        vend_score = vendedor.get('score_vendedor', 50)
        vend_nivel = vendedor.get('nivel_confianza', '')
        vend_linea = f'Vendedor: {vend_score}/100 | {vend_nivel}'
    else:
        vend_linea = ''

    mensaje = (
        f'OPORTUNIDAD DEL DIA\n'
        f'marketplace_ecuador\n'
        f'========================\n\n'
        f'{listing["titulo"]}\n'
        f'Precio: {precio}\n'
        f'Motor: {motor} | Anio: {anio}\n'
        f'Fotos verificadas: {fotos}\n'
        f'Puntaje calidad: {puntaje}/10\n'
        f'{vend_linea}\n\n'
        f'Ver publicacion: {listing["url"]}\n\n'
        f'---\n'
        f'Quieres alertas personalizadas?\n'
        f'Suscribete por solo $5 el primer mes\n'
        f'Escribe /start a @marketplace_ec_bot'
    )
    ok = _publicar_en_canal(mensaje)
    if ok:
        guardar_publicado(listing.get('id', ''))
        print(f'   Publicado en canal publico!')
    return ok


def publicar_alerta_estafa_canal(listing, riesgo, duplicado=None):
    if not puede_publicar_hoy() or ya_fue_publicado('estafa_' + listing.get('id', '')):
        return False

    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
    nivel = riesgo.get('nivel', '')
    senales = riesgo.get('senales_encontradas', [])

    if nivel in ['MUY_ALTO', 'ALTO']:
        encabezado = 'ALERTA DE ESTAFA DETECTADA'
    else:
        return False  # Solo publicar las mas graves en el canal

    senales_txt = ' | '.join(senales[:3]) if senales else 'precio sospechoso'

    # Si tiene duplicado en otra ciudad
    duplicado_txt = ''
    if duplicado and duplicado.get('es_sospechoso'):
        precio_otro = f"${duplicado['precio_similar']:,.0f}" if duplicado.get('precio_similar') else 'N/A'
        diff = duplicado.get('diferencia_precio_pct', 0)
        duplicado_txt = (
            f'\nDOBLE PUBLICACION DETECTADA:\n'
            f'  Este carro ya fue visto a {precio_otro}\n'
            f'  Diferencia de precio: {diff}% -- SOSPECHOSO'
        )

    mensaje = (
        f'ALERTA: {encabezado}\n'
        f'marketplace_ecuador\n'
        f'========================\n\n'
        f'Publicacion: {listing["titulo"]}\n'
        f'Precio publicado: {precio}\n'
        f'Senales: {senales_txt}'
        f'{duplicado_txt}\n\n'
        f'RECOMENDACION: No contactar a este vendedor\n\n'
        f'---\n'
        f'Recibe alertas de estafas y oportunidades\n'
        f'antes que nadie por $5/mes\n'
        f'Escribe /start a @marketplace_ec_bot'
    )
    ok = _publicar_en_canal(mensaje)
    if ok:
        guardar_publicado('estafa_' + listing.get('id', ''))
        print(f'   Alerta estafa publicada en canal!')
    return ok


def publicar_resumen_diario_canal(stats):
    hoy = datetime.now().strftime('%d/%m/%Y')
    mensaje = (
        f'RESUMEN DEL DIA - {hoy}\n'
        f'marketplace_ecuador\n'
        f'========================\n\n'
        f'Listings analizados hoy: {stats.get("total", 0)}\n'
        f'Oportunidades detectadas: {stats.get("oportunidades", 0)}\n'
        f'Estafas/sospechosos: {stats.get("estafas", 0)}\n'
        f'Duplicados detectados: {stats.get("duplicados", 0)}\n\n'
        f'Categorias monitoreadas:\n'
        f'  Vehiculos: Fortuner, Hilux, Prado\n'
        f'  Ropa: Ralph Lauren, Nike, Tommy, Lacoste\n'
        f'  Celulares: iPhone, Samsung\n\n'
        f'---\n'
        f'Quieres las alertas en tiempo real?\n'
        f'Solo $5 el primer mes\n'
        f'Escribe /start a @marketplace_ec_bot'
    )
    _publicar_en_canal(mensaje)
    print('   Resumen diario publicado en canal!')
