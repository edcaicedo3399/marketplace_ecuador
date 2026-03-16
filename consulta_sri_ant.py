"""
consulta_sri_ant.py - URL y selectores REALES verificados en el portal SRI en Linea
URL: https://srienlinea.sri.gob.ec/sri-en-linea/SriVehiculosWeb/ConsultaValoresPagarVehiculo/Consultas/consultaRubros
Campo placa verificado: id=busqueda
Rubros reales: TASA SPPAT + IMPUESTO A LA PROPIEDAD + TASAS ANT
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from config import TELEGRAM_TOKEN
import httpx

SRI_URL = "https://srienlinea.sri.gob.ec/sri-en-linea/SriVehiculosWeb/ConsultaValoresPagarVehiculo/Consultas/consultaRubros"
ANT_URL = "https://www.ant.gob.ec/index.php/servicios-soporte/consultas/vehiculos-consulta/datos-de-un-vehiculo-por-placa"

COSTOS_TRAMITES = {
    "notaria": 120,
    "ant_cambio_dueno": 50,
    "soat": 85,
    "revision_vehicular": 35,
    "mecanico": 80,
}
COSTOS_MATRICULA = {
    "quito":     170,
    "guayaquil": 155,
    "cuenca":    163,
    "default":   170,
}

async def consultar_sri(placa: str) -> dict:
    res = {"placa": placa.upper(), "existe": False, "marca": "", "modelo": "",
           "anio": "", "total_sri": 0.0, "tasa_sppat": 0.0,
           "impuesto_propiedad": 0.0, "tasas_ant_sri": 0.0,
           "estado": "desconocido", "error": None}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(SRI_URL, timeout=30000, wait_until="networkidle")
            # Campo verificado: id=busqueda
            await page.wait_for_selector("#busqueda", timeout=10000)
            await page.fill("#busqueda", placa.upper())
            # Boton Consultar
            await page.get_by_role("button", name="Consultar").click()
            # Esperar resultados
            try:
                await page.wait_for_selector("table", timeout=12000)
                res["existe"] = True
            except Exception:
                res["estado"] = "no_encontrada"
                await browser.close()
                return res
            html = await page.content()
            # Extraer datos del vehiculo
            tds = await page.query_selector_all("table td")
            vals = [await td.inner_text() for td in tds]
            if len(vals) >= 3:
                res["marca"] = vals[0].strip()
                res["modelo"] = vals[1].strip()
                res["anio"] = vals[2].strip()
            # Total a pagar
            m = re.search(r"A pagar\s*:\s*USD\s*\$?([\d,\.]+)", html)
            if m:
                res["total_sri"] = float(m.group(1).replace(",", ""))
            # Rubros verificados en la pagina real
            m2 = re.search(r"TASA SPPAT[\s\S]{1,50}USD\s+\$([\d,\.]+)", html)
            if m2:
                res["tasa_sppat"] = float(m2.group(1).replace(",", ""))
            m3 = re.search(r"IMPUESTO A LA PROPIEDAD[\s\S]{1,50}USD\s+\$([\d,\.]+)", html)
            if m3:
                res["impuesto_propiedad"] = float(m3.group(1).replace(",", ""))
            m4 = re.search(r"TASAS ANT[\s\S]{1,50}USD\s+\$([\d,\.]+)", html)
            if m4:
                res["tasas_ant_sri"] = float(m4.group(1).replace(",", ""))
            res["estado"] = "tiene_deuda" if res["total_sri"] > 0 else "al_dia"
            await browser.close()
    except Exception as e:
        res["error"] = str(e)[:120]
        res["estado"] = "error"
    return res

async def consultar_ant(placa: str) -> dict:
    res = {"placa": placa.upper(), "estado_matricula": "desconocido",
           "fecha_vencimiento": None, "multas": 0.0, "error": None}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            url = f"{ANT_URL}?placa={placa.upper()}"
            await page.goto(url, timeout=20000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            if "vigente" in html.lower():
                res["estado_matricula"] = "vigente"
            elif "vencida" in html.lower() or "caducada" in html.lower():
                res["estado_matricula"] = "vencida"
            m = re.search(r"(\d{2}/\d{2}/\d{4})", html)
            if m:
                res["fecha_vencimiento"] = m.group(1)
            m2 = re.search(r"multa[^\d]*([\d,\.]+)", html, re.IGNORECASE)
            if m2:
                res["multas"] = float(m2.group(1).replace(",", ""))
            await browser.close()
    except Exception as e:
        res["error"] = str(e)[:80]
    return res

def calcular_costo_total(precio, ciudad, sri, ant, precio_mercado=None):
    ciudad_k = ciudad.lower() if ciudad.lower() in COSTOS_MATRICULA else "default"
    mat_vencida = ant.get("estado_matricula") == "vencida"
    mat_costo = COSTOS_MATRICULA[ciudad_k] if mat_vencida else 0
    deuda = sri.get("total_sri", 0) if sri.get("estado") == "tiene_deuda" else 0
    tramites = sum(COSTOS_TRAMITES.values())
    total = precio + mat_costo + deuda + tramites
    ahorro = (precio_mercado - total) if precio_mercado else None
    return {
        "precio": precio, "matricula": mat_costo, "deuda_sri": deuda,
        "notaria": COSTOS_TRAMITES["notaria"],
        "cambio_propietario": COSTOS_TRAMITES["ant_cambio_dueno"],
        "soat": COSTOS_TRAMITES["soat"],
        "revision": COSTOS_TRAMITES["revision_vehicular"],
        "mecanico": COSTOS_TRAMITES["mecanico"],
        "total": round(total, 2),
        "ahorro": round(ahorro, 2) if ahorro is not None else None,
        "mat_vencida": mat_vencida,
    }

def formatear_alerta(vehiculo, placa, sri, ant, costos, ciudad):
    marca_modelo = f"{sri.get(chr(109)+chr(97)+chr(114)+chr(99)+chr(97),chr(39))} {sri.get(chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(111),chr(39))} {sri.get(chr(97)+chr(110)+chr(105)+chr(111),chr(39))}".strip()
    est_sri = "OK" if "al_dia" in sri.get("estado","") else "DEBE"
    est_mat = "OK" if ant.get("estado_matricula") == "vigente" else "VENCIDA"
    lineas = [
        "ANALISIS COMPLETO DE COMPRA",
        f"Vehiculo: {vehiculo}",
        f"Placa: {placa.upper()}",
        f"Datos SRI: {marca_modelo}",
        "",
        "ESTADO LEGAL",
        f"  SRI impuestos: {est_sri}",
        f"  Matricula ANT: {est_mat}",
    ]
    if sri.get("total_sri", 0) > 0:
        lineas.append(f"  Deuda SRI: ${sri[chr(116)+chr(111)+chr(116)+chr(97)+chr(108)+chr(95)+chr(115)+chr(114)+chr(105)]:,.2f}")
    lineas += [
        "",
        "COSTO TOTAL REAL",
        f"  Precio:              ${costos[chr(112)+chr(114)+chr(101)+chr(99)+chr(105)+chr(111)]:>8,.0f}",
    ]
    if costos["matricula"] > 0:
        lineas.append(f"  Matricula vencida:   ${costos[chr(109)+chr(97)+chr(116)+chr(114)+chr(105)+chr(99)+chr(117)+chr(108)+chr(97)]:>8,.0f}")
    lineas += [
        f"  Notaria:             ${costos[chr(110)+chr(111)+chr(116)+chr(97)+chr(114)+chr(105)+chr(97)]:>8,.0f}",
        f"  Cambio propietario:  ${costos[chr(99)+chr(97)+chr(109)+chr(98)+chr(105)+chr(111)+chr(95)+chr(112)+chr(114)+chr(111)+chr(112)+chr(105)+chr(101)+chr(116)+chr(97)+chr(114)+chr(105)+chr(111)]:>8,.0f}",
        f"  SOAT:                ${costos[chr(115)+chr(111)+chr(97)+chr(116)]:>8,.0f}",
        f"  Revision:            ${costos[chr(114)+chr(101)+chr(118)+chr(105)+chr(115)+chr(105)+chr(111)+chr(110)]:>8,.0f}",
        f"  Mecanico:            ${costos[chr(109)+chr(101)+chr(99)+chr(97)+chr(110)+chr(105)+chr(99)+chr(111)]:>8,.0f}",
        "  --------------------------------",
        f"  TOTAL REAL:          ${costos[chr(116)+chr(111)+chr(116)+chr(97)+chr(108)]:>8,.0f}",
    ]
    if costos.get("ahorro") is not None:
        tag = "AHORRO" if costos["ahorro"] > 0 else "SOBREPRECIO"
        lineas.append(f"  {tag}:            ${abs(costos[chr(97)+chr(104)+chr(111)+chr(114)+chr(114)+chr(111)]):>8,.0f}")
    pasos = [
        "",
        "GUIA DE COMPRA",
        "1. Negocia el precio",
        "2. Mecanico de confianza (~$80)",
        "3. Matricula y multas verificadas automaticamente",
    ]
    if costos["mat_vencida"]:
        pasos.append("4. Pagar matricula vencida")
    pasos += [
        "5. Contrato notaria (~$120)",
        "6. ANT cambio propietario (~$50)",
        "7. SOAT nuevo (~$85)",
        f"Tiempo: 3-5 dias | Ciudad: {ciudad.title()}",
        f"TOTAL: ${costos[chr(116)+chr(111)+chr(116)+chr(97)+chr(108)]:,.0f}",
    ]
    lineas.extend(pasos)
    lineas.append("MarketplaceEC Bot - Analisis automatico")
    return chr(10).join(lineas)

async def enviar_telegram(chat_id, mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as c:
        r = await c.post(url, json={"chat_id": chat_id, "text": mensaje}, timeout=10)
        return r.status_code == 200

async def analizar_vehiculo_completo(vehiculo, placa, precio, ciudad,
                                      chat_id=None, precio_mercado=None):
    print(f"Consultando SRI/ANT para {placa}...")
    sri, ant = await asyncio.gather(consultar_sri(placa), consultar_ant(placa))
    print(f"  SRI: {sri[chr(101)+chr(115)+chr(116)+chr(97)+chr(100)+chr(111)]} | ANT: {ant[chr(101)+chr(115)+chr(116)+chr(97)+chr(100)+chr(111)+chr(95)+chr(109)+chr(97)+chr(116)+chr(114)+chr(105)+chr(99)+chr(117)+chr(108)+chr(97)]}")
    costos = calcular_costo_total(precio, ciudad, sri, ant, precio_mercado)
    mensaje = formatear_alerta(vehiculo, placa, sri, ant, costos, ciudad)
    if chat_id:
        await enviar_telegram(chat_id, mensaje)
    return {"sri": sri, "ant": ant, "costos": costos, "mensaje": mensaje}

if __name__ == "__main__":
    async def test():
        r = await analizar_vehiculo_completo(
            "Toyota Fortuner 4.0 2017",
            "PDM1522",
            28500, "quito", precio_mercado=32000
        )
        print(r["mensaje"])
    asyncio.run(test())
