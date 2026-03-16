# ============================================
# marketplace_ecuador - Sistema de Alertas
# ============================================

import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def enviar_alerta_telegram(listing: dict):
    """
    Envia una alerta por Telegram cuando se encuentra una oportunidad.
    """
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "TU_TOKEN_AQUI":
        print("   Telegram no configurado, saltando alerta")
        return

    precio = listing.get('precio')
    anio = listing.get('anio')
    precio_str = f"${precio:,.0f}" if precio else "No especificado"
    anio_str = str(anio) if anio else "No especificado"

    mensaje = (
        f"OPORTUNIDAD - {listing['busqueda']}\n\n"
        f"{listing['titulo']}\n"
        f"Precio: {precio_str}\n"
        f"Motor: {listing['motor']}\n"
        f"Anio: {anio_str}\n\n"
        f"Ver publicacion: {listing['url']}\n\n"
        f"marketplace_ecuador bot"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("   Alerta Telegram enviada!")
        else:
            print(f"   Error Telegram: {response.status_code}")
    except Exception as e:
        print(f"   Error enviando Telegram: {e}")


def enviar_resumen_diario(total_nuevos: int, total_oportunidades: int):
    """Envia un resumen diario de actividad."""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "TU_TOKEN_AQUI":
        return

    mensaje = (
        f"Resumen Diario - marketplace_ecuador\n\n"
        f"Nuevos listings: {total_nuevos}\n"
        f"Oportunidades: {total_oportunidades}\n"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass
