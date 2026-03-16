# marketplace_ecuador - Calificacion de Vendedores
import json, os, re, time
from datetime import datetime

DB_VENDEDORES = 'vendedores.json'

SENALES_NEGATIVAS_PERFIL = [
    'se unio recientemente', 'cuenta nueva', 'sin calificaciones', '0 calificaciones'
]

def scrape_perfil_vendedor(listing_url, page):
    vendedor = {
        'nombre': 'Desconocido',
        'perfil_url': None,
        'antiguedad_texto': None,
        'calificacion_estrellas': None,
        'num_calificaciones': 0,
        'articulos_activos': 0,
        'tiempo_respuesta': None,
        'es_tienda': False,
        'senales_negativas': [],
        'score_vendedor': 0,
        'nivel_confianza': 'DESCONOCIDO',
    }
    try:
        page.goto(listing_url, wait_until='domcontentloaded', timeout=15000)
        time.sleep(2)
        texto = page.inner_text('body') or ''

        # Nombre y URL del vendedor
        for sel in ['a[href*="/user/"]', 'a[href*="profile.php"]']:
            for el in page.query_selector_all(sel):
                t = el.inner_text() or ''
                h = el.get_attribute('href') or ''
                if 2 < len(t) < 60 and ('/user/' in h or 'profile' in h):
                    vendedor['nombre'] = t.strip()
                    vendedor['perfil_url'] = 'https://www.facebook.com' + h if h.startswith('/') else h
                    break
            if vendedor['nombre'] != 'Desconocido':
                break

        # Calificacion estrellas y numero de resenas
        m = re.search(r'(\d+\.?\d*)\s*\(?\s*(\d+)\s*calificaci', texto, re.IGNORECASE)
        if m:
            vendedor['calificacion_estrellas'] = float(m.group(1))
            vendedor['num_calificaciones'] = int(m.group(2))

        # Antiguedad
        m2 = re.search(r'(miembro desde|se uni[o]+ en)\s+([\w\s]+\d{4})', texto, re.IGNORECASE)
        if m2:
            vendedor['antiguedad_texto'] = m2.group(2).strip()

        # Cuenta nueva
        if 'recientemente' in texto.lower() and 'uni' in texto.lower():
            vendedor['senales_negativas'].append('cuenta_nueva_reciente')

        # Articulos activos
        m3 = re.search(r'(\d+)\s*(art[i]culos?|publicaciones?)', texto, re.IGNORECASE)
        if m3:
            vendedor['articulos_activos'] = int(m3.group(1))

        # Tiempo de respuesta
        m4 = re.search(r'suele responder\s+([\w\s]+)', texto, re.IGNORECASE)
        if m4:
            vendedor['tiempo_respuesta'] = m4.group(1).strip()[:50]

        # Es tienda
        if any(w in texto.lower() for w in ['tienda', 'concesionario', 'automotora', 'motors']):
            vendedor['es_tienda'] = True

    except Exception as e:
        print(f'Error scrapeando vendedor: {e}')

    return calcular_score_vendedor(vendedor)


def calcular_score_vendedor(vendedor):
    score = 50
    estrellas = vendedor.get('calificacion_estrellas')
    num_calif = vendedor.get('num_calificaciones', 0)

    if estrellas:
        if estrellas >= 4.5: score += 20
        elif estrellas >= 4.0: score += 12
        elif estrellas >= 3.5: score += 5
        elif estrellas < 3.0: score -= 15

    if num_calif >= 50: score += 15
    elif num_calif >= 20: score += 10
    elif num_calif >= 5: score += 5
    elif num_calif == 0: score -= 10

    if vendedor.get('articulos_activos', 0) >= 10: score += 5
    if 'cuenta_nueva_reciente' in vendedor.get('senales_negativas', []): score -= 20
    if vendedor.get('es_tienda'): score += 10
    resp = vendedor.get('tiempo_respuesta', '') or ''
    if 'minuto' in resp.lower() or 'hora' in resp.lower(): score += 5

    score = max(0, min(100, score))
    vendedor['score_vendedor'] = score

    if score >= 80:
        vendedor['nivel_confianza'] = 'MUY_CONFIABLE'
        vendedor['emoji_confianza'] = 'VENDEDOR TOP'
    elif score >= 65:
        vendedor['nivel_confianza'] = 'CONFIABLE'
        vendedor['emoji_confianza'] = 'BUENO'
    elif score >= 50:
        vendedor['nivel_confianza'] = 'NEUTRAL'
        vendedor['emoji_confianza'] = 'VERIFICAR'
    elif score >= 35:
        vendedor['nivel_confianza'] = 'POCO_CONFIABLE'
        vendedor['emoji_confianza'] = 'CUIDADO'
    else:
        vendedor['nivel_confianza'] = 'NO_CONFIABLE'
        vendedor['emoji_confianza'] = 'EVITAR'

    return vendedor


def cargar_db_vendedores():
    if os.path.exists(DB_VENDEDORES):
        with open(DB_VENDEDORES, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}


def guardar_vendedor(vendedor):
    if not vendedor.get('perfil_url'): return
    db = cargar_db_vendedores()
    key = vendedor['perfil_url']
    if key in db:
        db[key]['veces_visto'] = db[key].get('veces_visto', 1) + 1
        db[key]['ultima_vez'] = datetime.now().isoformat()
        if vendedor.get('calificacion_estrellas'):
            db[key]['calificacion_estrellas'] = vendedor['calificacion_estrellas']
            db[key]['num_calificaciones'] = vendedor['num_calificaciones']
        db[key]['score_vendedor'] = vendedor['score_vendedor']
        db[key]['nivel_confianza'] = vendedor['nivel_confianza']
    else:
        vendedor['primera_vez'] = datetime.now().isoformat()
        vendedor['ultima_vez'] = datetime.now().isoformat()
        vendedor['veces_visto'] = 1
        db[key] = vendedor
    with open(DB_VENDEDORES, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def buscar_vendedor_en_db(perfil_url):
    if not perfil_url: return None
    return cargar_db_vendedores().get(perfil_url)


def score_combinado_listing(listing, vendedor):
    score_listing = listing.get('puntaje', 5) * 10
    score_vend = vendedor.get('score_vendedor', 50)
    score_final = round((score_listing * 0.4) + (score_vend * 0.6), 1)

    if score_final >= 75: nivel, rec = 'EXCELENTE', 'CONTACTAR YA'
    elif score_final >= 60: nivel, rec = 'BUENO', 'VALE LA PENA'
    elif score_final >= 45: nivel, rec = 'REGULAR', 'VERIFICAR ANTES'
    else: nivel, rec = 'MALO', 'EVITAR'

    return {
        'score_final': score_final,
        'nivel_final': nivel,
        'recomendacion': rec,
        'score_listing': score_listing,
        'score_vendedor': score_vend,
    }


def reporte_mejores_vendedores(top_n=10):
    db = cargar_db_vendedores()
    vendedores = sorted(db.values(), key=lambda x: x.get('score_vendedor', 0), reverse=True)
    return vendedores[:top_n]


def reporte_vendedores_sospechosos():
    db = cargar_db_vendedores()
    return sorted(
        [v for v in db.values() if v.get('score_vendedor', 50) < 35 or len(v.get('senales_negativas', [])) >= 2],
        key=lambda x: x.get('score_vendedor', 50)
    )
