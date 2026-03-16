# ============================================
# marketplace_ecuador - Gestor de Clientes
# ============================================
# Maneja suscripciones, filtros por cliente
# y envia alertas personalizadas a cada uno
# ============================================

import json, os, requests
from datetime import datetime, timedelta
from config import TELEGRAM_TOKEN

DB_CLIENTES = 'clientes.json'

# Planes disponibles
PLANES = {
    'basico':    {'precio': 5,  'nombre': 'Basico',    'alertas_dia': 3},
    'pro':       {'precio': 35, 'nombre': 'Pro',       'alertas_dia': 999},
    'empresarial': {'precio': 120, 'nombre': 'Empresarial', 'alertas_dia': 999},
}


def cargar_clientes():
    if os.path.exists(DB_CLIENTES):
        with open(DB_CLIENTES, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}


def guardar_clientes(db):
    with open(DB_CLIENTES, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def registrar_cliente(telegram_chat_id, nombre, plan='basico', busquedas_personalizadas=None):
    db = cargar_clientes()
    cid = str(telegram_chat_id)
    hoy = datetime.now()
    vencimiento = hoy + timedelta(days=30)

    db[cid] = {
        'chat_id': cid,
        'nombre': nombre,
        'plan': plan,
        'plan_info': PLANES.get(plan, PLANES['basico']),
        'activo': True,
        'fecha_registro': hoy.isoformat(),
        'fecha_vencimiento': vencimiento.isoformat(),
        'alertas_hoy': 0,
        'alertas_fecha': hoy.strftime('%Y-%m-%d'),
        'total_alertas_recibidas': 0,
        'busquedas': busquedas_personalizadas or [],
        # Ejemplo de busqueda personalizada:
        # {'tipo': 'vehiculo', 'query': 'fortuner', 'motor': '4.0',
        #  'precio_min': 25000, 'precio_max': 38000, 'anio_min': 2015}
    }
    guardar_clientes(db)
    print(f'Cliente registrado: {nombre} | Plan: {plan}')
    return db[cid]


def cliente_activo(chat_id):
    db = cargar_clientes()
    cid = str(chat_id)
    if cid not in db: return False
    cliente = db[cid]
    if not cliente.get('activo'): return False
    venc = datetime.fromisoformat(cliente['fecha_vencimiento'])
    if datetime.now() > venc:
        db[cid]['activo'] = False
        guardar_clientes(db)
        _notificar_vencimiento(cliente)
        return False
    return True


def puede_recibir_alerta(chat_id):
    db = cargar_clientes()
    cid = str(chat_id)
    if not cliente_activo(cid): return False
    cliente = db[cid]
    hoy = datetime.now().strftime('%Y-%m-%d')
    if cliente.get('alertas_fecha') != hoy:
        db[cid]['alertas_hoy'] = 0
        db[cid]['alertas_fecha'] = hoy
        guardar_clientes(db)
    limite = PLANES.get(cliente['plan'], PLANES['basico'])['alertas_dia']
    return db[cid]['alertas_hoy'] < limite


def registrar_alerta_enviada(chat_id):
    db = cargar_clientes()
    cid = str(chat_id)
    hoy = datetime.now().strftime('%Y-%m-%d')
    if db[cid].get('alertas_fecha') != hoy:
        db[cid]['alertas_hoy'] = 0
        db[cid]['alertas_fecha'] = hoy
    db[cid]['alertas_hoy'] = db[cid].get('alertas_hoy', 0) + 1
    db[cid]['total_alertas_recibidas'] = db[cid].get('total_alertas_recibidas', 0) + 1
    guardar_clientes(db)


def listing_es_relevante_para_cliente(listing, cliente):
    busquedas = cliente.get('busquedas', [])
    if not busquedas: return True  # Sin filtros = recibe todo
    titulo = listing.get('titulo', '').lower()
    for b in busquedas:
        query = b.get('query', '').lower()
        if query and query not in titulo: continue
        motor_buscado = b.get('motor')
        if motor_buscado and listing.get('motor') != motor_buscado: continue
        precio = listing.get('precio', 0) or 0
        if b.get('precio_min') and precio < b['precio_min']: continue
        if b.get('precio_max') and precio > b['precio_max']: continue
        anio = listing.get('anio', 0) or 0
        if b.get('anio_min') and anio < b['anio_min']: continue
        return True
    return False


def enviar_alerta_a_cliente(chat_id, mensaje):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI': return False
    if not puede_recibir_alerta(chat_id): return False
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        r = requests.post(url, json={
            'chat_id': str(chat_id),
            'text': mensaje,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }, timeout=10)
        if r.status_code == 200:
            registrar_alerta_enviada(chat_id)
            return True
        return False
    except: return False


def broadcast_oportunidad(listing, vendedor=None, score_combinado=None):
    db = cargar_clientes()
    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
    fotos = listing.get('cantidad_fotos', 0)
    puntaje = listing.get('puntaje', 0)
    motor = listing.get('motor', 'N/A')
    anio = listing.get('anio', 'N/A')

    if vendedor:
        vend_score = vendedor.get('score_vendedor', 0)
        vend_nivel = vendedor.get('nivel_confianza', '')
        vend_txt = f'Vendedor: {vend_score}/100 | {vend_nivel}'
    else:
        vend_txt = ''

    if score_combinado:
        score_txt = f"Score final: {score_combinado.get('score_final', 0)}/100 | {score_combinado.get('recomendacion', '')}"
    else:
        score_txt = f'Puntaje: {puntaje}/10'

    mensaje = (
        f'NUEVA OPORTUNIDAD\n'
        f'========================\n\n'
        f'{listing["titulo"]}\n'
        f'Precio: {precio} | Motor: {motor} | Anio: {anio}\n'
        f'Fotos verificadas: {fotos}\n'
        f'{vend_txt}\n'
        f'{score_txt}\n\n'
        f'Ver: {listing["url"]}'
    )

    enviados = 0
    for cid, cliente in db.items():
        if not cliente_activo(cid): continue
        if not listing_es_relevante_para_cliente(listing, cliente): continue
        if enviar_alerta_a_cliente(cid, mensaje):
            enviados += 1
    print(f'   Alerta enviada a {enviados} clientes')
    return enviados


def broadcast_estafa(listing, riesgo, duplicado=None):
    db = cargar_clientes()
    precio = f"${listing['precio']:,.0f}" if listing.get('precio') else 'N/A'
    nivel = riesgo.get('nivel', '')
    senales = ' | '.join(riesgo.get('senales_encontradas', [])[:3])

    dup_txt = ''
    if duplicado and duplicado.get('es_sospechoso'):
        precio_otro = f"${duplicado['precio_similar']:,.0f}" if duplicado.get('precio_similar') else 'N/A'
        diff = duplicado.get('diferencia_precio_pct', 0)
        dup_txt = f'\nDOBLE PUBLICACION: precio anterior {precio_otro} | diferencia {diff}%'

    mensaje = (
        f'ALERTA DE ESTAFA DETECTADA\n'
        f'========================\n\n'
        f'Titulo: {listing["titulo"]}\n'
        f'Precio publicado: {precio}\n'
        f'Riesgo: {nivel}\n'
        f'Senales: {senales}'
        f'{dup_txt}\n\n'
        f'ACCION: No contactar - reportar esta publicacion\n'
        f'URL: {listing["url"]}'
    )

    enviados = 0
    for cid in db:
        if cliente_activo(cid) and PLANES.get(db[cid]['plan'], {}).get('precio', 0) >= 35:
            if enviar_alerta_a_cliente(cid, mensaje):
                enviados += 1
    print(f'   Alerta estafa enviada a {enviados} clientes Pro/Empresarial')
    return enviados


def _notificar_vencimiento(cliente):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI': return
    mensaje = (
        f'Hola {cliente["nombre"]}!\n\n'
        f'Tu suscripcion a marketplace_ecuador ha vencido.\n'
        f'Renueva por solo ${PLANES[cliente["plan"]]["precio"]}/mes\n'
        f'para seguir recibiendo alertas.\n\n'
        f'Renueva aqui: [link de pago]'
    )
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    try:
        requests.post(url, json={'chat_id': cliente['chat_id'], 'text': mensaje}, timeout=10)
    except: pass


def reporte_clientes():
    db = cargar_clientes()
    activos = [c for c in db.values() if cliente_activo(c['chat_id'])]
    inactivos = [c for c in db.values() if not cliente_activo(c['chat_id'])]
    ingreso_mensual = sum(PLANES.get(c['plan'], PLANES['basico'])['precio'] for c in activos)
    print(f'\nREPORTE DE CLIENTES')
    print(f'Activos: {len(activos)} | Inactivos: {len(inactivos)}')
    print(f'Ingreso mensual estimado: ${ingreso_mensual}')
    for c in activos:
        venc = c.get('fecha_vencimiento', '')[:10]
        print(f'  {c["nombre"]} | {c["plan"]} | vence: {venc} | alertas recibidas: {c.get("total_alertas_recibidas", 0)}')
    return {'activos': len(activos), 'inactivos': len(inactivos), 'ingreso_mensual': ingreso_mensual}
