# ============================================
# marketplace_ecuador - Sistema de Alertas Telegram
# ============================================

import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def _enviar(mensaje):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI':
        print('   Telegram no configurado')
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        r = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mensaje,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }, timeout=10)
        if r.status_code == 200:
            print('   Alerta Telegram enviada!')
        else:
            print(f'   Error Telegram: {r.status_code}')
    except Exception as e:
        print(f'   Error: {e}')


def enviar_alerta_oportunidad(listing, vendedor=None, score_combinado=None):
    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
    fotos = listing.get('cantidad_fotos', 0)
    puntaje = listing.get('puntaje', 0)
    motor = listing.get('motor', 'N/A')
    anio = listing.get('anio', 'N/A')

    # Info vendedor
    if vendedor:
        vend_nombre = vendedor.get('nombre', 'Desconocido')
        vend_score = vendedor.get('score_vendedor', 0)
        vend_nivel = vendedor.get('nivel_confianza', 'DESCONOCIDO')
        vend_estrellas = vendedor.get('calificacion_estrellas', 0)
        vend_resenas = vendedor.get('num_calificaciones', 0)
        vend_linea = f'Vendedor: {vend_nombre} | {vend_score}/100 pts | {vend_nivel}'
        if vend_estrellas:
            vend_linea += f' | {vend_estrellas} estrellas ({vend_resenas} resenas)'
    else:
        vend_linea = 'Vendedor: no analizado'

    # Score final combinado
    if score_combinado:
        score_final = score_combinado.get('score_final', 0)
        recomendacion = score_combinado.get('recomendacion', '')
        score_linea = f'Score final: {score_final}/100 -- {recomendacion}'
    else:
        score_linea = f'Puntaje listing: {puntaje}/10'

    mensaje = (
        f'OPORTUNIDAD DETECTADA\n'
        f'========================\n'
        f'{listing["busqueda"]}\n\n'
        f'Titulo: {listing["titulo"]}\n'
        f'Precio: {precio}\n'
        f'Motor: {motor} | Anio: {anio}\n'
        f'Fotos: {fotos} reales\n\n'
        f'{vend_linea}\n'
        f'{score_linea}\n\n'
        f'Ver: {listing["url"]}'
    )
    _enviar(mensaje)


def enviar_alerta_duplicado_sospechoso(listing_nuevo, duplicado, vendedor=None):
    precio_nuevo = f"${listing_nuevo['precio']:,.0f}" if listing_nuevo.get('precio') else 'N/A'
    precio_viejo = f"${duplicado['precio_similar']:,.0f}" if duplicado.get('precio_similar') else 'N/A'
    diff_pct = duplicado.get('diferencia_precio_pct', 0)
    similitud = duplicado.get('similitud_pct', 0)

    # Nivel de alerta segun diferencia de precio
    if diff_pct >= 40:
        nivel_alerta = 'MUY SOSPECHOSO - POSIBLE ESTAFA'
        separador = '!!!!!!!!!!!!!!!!!!!!!!!!'
    elif diff_pct >= 25:
        nivel_alerta = 'SOSPECHOSO - REVISAR'
        separador = '========================'
    else:
        nivel_alerta = 'DOBLE PUBLICACION DETECTADA'
        separador = '------------------------'

    # Info vendedor
    if vendedor:
        vend_score = vendedor.get('score_vendedor', 50)
        vend_nivel = vendedor.get('nivel_confianza', 'DESCONOCIDO')
        if vend_score < 35:
            vend_alerta = f'VENDEDOR SOSPECHOSO: {vend_score}/100 pts - {vend_nivel}'
        else:
            vend_alerta = f'Vendedor: {vend_score}/100 pts - {vend_nivel}'
    else:
        vend_alerta = 'Vendedor: no analizado'

    mensaje = (
        f'ALERTA: {nivel_alerta}\n'
        f'{separador}\n\n'
        f'PUBLICACION ACTUAL:\n'
        f'  Titulo: {listing_nuevo["titulo"]}\n'
        f'  Precio: {precio_nuevo}\n'
        f'  URL: {listing_nuevo["url"]}\n\n'
        f'PUBLICACION ANTERIOR SIMILAR ({similitud}% similitud):\n'
        f'  Titulo: {duplicado["titulo_similar"]}\n'
        f'  Precio: {precio_viejo}\n'
        f'  URL: {duplicado["url_similar"]}\n\n'
        f'Diferencia de precio: {diff_pct}%\n'
        f'{vend_alerta}\n\n'
        f'RECOMENDACION: {_recomendacion_duplicado(diff_pct, vendedor)}'
    )
    _enviar(mensaje)


def enviar_alerta_estafa(listing, riesgo, vendedor=None):
    nivel = riesgo.get('nivel', 'DESCONOCIDO')
    senales = riesgo.get('senales_encontradas', [])
    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'

    if nivel == 'MUY_ALTO':
        encabezado = 'PROBABLE ESTAFA DETECTADA'
    elif nivel == 'ALTO':
        encabezado = 'PUBLICACION MUY SOSPECHOSA'
    else:
        encabezado = 'PUBLICACION CON SENALES DE ALERTA'

    senales_txt = '\n'.join([f'  - {s}' for s in senales]) if senales else '  Ninguna especifica'

    if vendedor:
        vend_score = vendedor.get('score_vendedor', 50)
        vend_nivel = vendedor.get('nivel_confianza', '')
        vend_txt = f'Vendedor: {vend_score}/100 pts | {vend_nivel}'
    else:
        vend_txt = ''

    mensaje = (
        f'ALERTA: {encabezado}\n'
        f'========================\n\n'
        f'Titulo: {listing["titulo"]}\n'
        f'Precio: {precio}\n'
        f'URL: {listing["url"]}\n\n'
        f'Senales detectadas:\n{senales_txt}\n\n'
        f'Riesgo: {nivel} ({riesgo.get("puntos_riesgo", 0)} puntos)\n'
        f'{vend_txt}\n\n'
        f'ACCION: No contactar - reportar publicacion si es posible'
    )
    _enviar(mensaje)


def _recomendacion_duplicado(diff_pct, vendedor):
    vend_score = vendedor.get('score_vendedor', 50) if vendedor else 50
    if diff_pct >= 40 and vend_score < 50:
        return 'NO CONTACTAR - alto riesgo de estafa. Reportar ambas publicaciones.'
    elif diff_pct >= 40:
        return 'REVISAR CON CUIDADO - misma publicacion a precio muy distinto.'
    elif diff_pct >= 25:
        return 'VERIFICAR - puede ser arbitraje legitimo o estafa. Pedir fotos adicionales.'
    else:
        return 'POSIBLE REPOST - contactar y preguntar por que tiene dos publicaciones.'


def enviar_resumen_diario(total_nuevos, total_oportunidades, total_sospechosos=0, total_estafas=0):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI':
        return
    mensaje = (
        f'RESUMEN DIARIO - marketplace_ecuador\n'
        f'========================\n'
        f'Nuevos listings: {total_nuevos}\n'
        f'Oportunidades: {total_oportunidades}\n'
        f'Duplicados sospechosos: {total_sospechosos}\n'
        f'Posibles estafas: {total_estafas}\n'
    )
    _enviar(mensaje)


# Alias para compatibilidad con scraper.py anterior
def enviar_alerta_telegram(listing):
    enviar_alerta_oportunidad(listing)
