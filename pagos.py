# ============================================
# marketplace_ecuador - Gestor de Pagos
# ============================================
# Integracion con Stripe para cobro automatico
# El cliente paga -> se activa solo -> recibe alertas
# ============================================
# Requiere: pip install stripe
# Configurar en config.py:
#   STRIPE_SECRET_KEY = 'sk_live_...'
#   STRIPE_WEBHOOK_SECRET = 'whsec_...'
# ============================================

import os
import json
import requests
from datetime import datetime
from gestor_clientes import registrar_cliente, cargar_clientes, guardar_clientes, PLANES
from config import TELEGRAM_TOKEN

# Stripe keys desde variables de entorno (mas seguro que en config)
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'TU_STRIPE_KEY_AQUI')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'TU_WEBHOOK_SECRET')

# Price IDs de Stripe (se crean una vez en el dashboard de Stripe)
# stripe.com/dashboard -> Products -> crear precio recurrente
STRIPE_PRICES = {
    'basico':      os.getenv('STRIPE_PRICE_BASICO', 'price_basico_aqui'),
    'pro':         os.getenv('STRIPE_PRICE_PRO', 'price_pro_aqui'),
    'empresarial': os.getenv('STRIPE_PRICE_EMP', 'price_emp_aqui'),
}


def crear_link_pago(plan, telegram_chat_id, nombre_cliente):
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        price_id = STRIPE_PRICES.get(plan)
        if not price_id or price_id.startswith('price_'):
            return _link_pago_manual(plan)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url='https://t.me/marketplace_ec_bot?start=activado',
            cancel_url='https://t.me/marketplace_ec_bot?start=cancelado',
            metadata={
                'telegram_chat_id': str(telegram_chat_id),
                'nombre': nombre_cliente,
                'plan': plan
            }
        )
        return session.url
    except ImportError:
        print('stripe no instalado. Agrega stripe a requirements.txt')
        return _link_pago_manual(plan)
    except Exception as e:
        print(f'Error Stripe: {e}')
        return _link_pago_manual(plan)


def _link_pago_manual(plan):
    precio = PLANES.get(plan, PLANES['basico'])['precio']
    nombre_plan = PLANES.get(plan, PLANES['basico'])['nombre']
    return (
        f'Para suscribirte al Plan {nombre_plan} (${precio}/mes):\n'
        f'Paga por PayPal o transferencia y envia el comprobante.\n'
        f'Te activamos en menos de 1 hora.'
    )


def procesar_webhook_stripe(payload, sig_header):
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        evento = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

        if evento['type'] == 'checkout.session.completed':
            session = evento['data']['object']
            meta = session.get('metadata', {})
            chat_id = meta.get('telegram_chat_id')
            nombre = meta.get('nombre', 'Cliente')
            plan = meta.get('plan', 'basico')
            if chat_id:
                activar_cliente_por_pago(chat_id, nombre, plan)

        elif evento['type'] == 'invoice.payment_succeeded':
            sub = evento['data']['object']
            renovar_suscripcion_stripe(sub)

        elif evento['type'] in ['customer.subscription.deleted', 'invoice.payment_failed']:
            sub = evento['data']['object']
            desactivar_cliente_stripe(sub)

        return True
    except Exception as e:
        print(f'Error webhook: {e}')
        return False


def activar_cliente_por_pago(chat_id, nombre, plan):
    cliente = registrar_cliente(chat_id, nombre, plan)
    precio = PLANES.get(plan, PLANES['basico'])['precio']
    nombre_plan = PLANES.get(plan, PLANES['basico'])['nombre']
    mensaje = (
        f'Pago confirmado! Bienvenido {nombre}\n\n'
        f'Plan activado: {nombre_plan} (${precio}/mes)\n'
        f'Valido por 30 dias\n\n'
        f'Ya estas recibiendo alertas en tiempo real de:\n'
        f'  Vehiculos: Fortuner, Hilux, Prado\n'
        f'  Ropa: Nike, Ralph Lauren, Tommy y mas\n'
        f'  Celulares: iPhone, Samsung\n\n'
        f'Tambien recibiras alertas de estafas y duplicados.\n'
        f'marketplace_ecuador'
    )
    _enviar_mensaje_telegram(chat_id, mensaje)
    print(f'Cliente activado: {nombre} | Plan: {plan}')
    return cliente


def renovar_suscripcion_stripe(invoice):
    customer_id = invoice.get('customer')
    db = cargar_clientes()
    for cid, cliente in db.items():
        if cliente.get('stripe_customer_id') == customer_id:
            from datetime import timedelta
            nueva_fecha = (datetime.now() + timedelta(days=30)).isoformat()
            db[cid]['fecha_vencimiento'] = nueva_fecha
            db[cid]['activo'] = True
            guardar_clientes(db)
            _enviar_mensaje_telegram(cid, 'Tu suscripcion fue renovada por 30 dias mas!')
            print(f'Suscripcion renovada: {cid}')
            break


def desactivar_cliente_stripe(subscription):
    customer_id = subscription.get('customer')
    db = cargar_clientes()
    for cid, cliente in db.items():
        if cliente.get('stripe_customer_id') == customer_id:
            db[cid]['activo'] = False
            guardar_clientes(db)
            _enviar_mensaje_telegram(
                cid,
                'Tu suscripcion fue cancelada.\nEscribe /suscribir para renovar.'
            )
            print(f'Cliente desactivado: {cid}')
            break


def activar_cliente_manual(chat_id, nombre, plan):
    cliente = registrar_cliente(chat_id, nombre, plan)
    activar_cliente_por_pago(chat_id, nombre, plan)
    return cliente


def _enviar_mensaje_telegram(chat_id, mensaje):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TU_TOKEN_AQUI': return
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': str(chat_id), 'text': mensaje},
            timeout=10
        )
    except: pass


def reporte_ingresos():
    db = cargar_clientes()
    activos = [c for c in db.values() if c.get('activo')]
    ingreso = sum(PLANES.get(c['plan'], PLANES['basico'])['precio'] for c in activos)
    por_plan = {}
    for c in activos:
        plan = c['plan']
        por_plan[plan] = por_plan.get(plan, 0) + 1
    print(f'\nREPORTE DE INGRESOS')
    print(f'Clientes activos: {len(activos)}')
    print(f'Ingreso mensual: ${ingreso}')
    for plan, cant in por_plan.items():
        precio = PLANES.get(plan, {}).get('precio', 0)
        print(f'  {plan}: {cant} clientes x ${precio} = ${cant * precio}/mes')
    return {'clientes_activos': len(activos), 'ingreso_mensual': ingreso, 'por_plan': por_plan}
