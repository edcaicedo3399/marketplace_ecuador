"""
consulta_sri_ant.py
Modulo estrella: consulta SRI/ANT automatica + calculo costo total real de compra
Incluye: matricula, multas, prendas, notaria, SOAT, gastos ANT
"""

import asyncio
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright
from config import TELEGRAM_TOKEN
import httpx

# COSTOS FIJOS ECUADOR 2024
COSTOS_TRAMITES = {
    "contrato_notaria":       120,
    "cambio_propietario_ant":  50,
    "soat_promedio":           85,
    "revision_vehicular":      35,
    "inspeccion_mecanico":     80,
}

COSTOS_MATRICULA = {
    "quito":     {"base": 120, "municipio": 40, "bomberos": 10},
    "guayaquil": {"base": 110, "municipio": 35, "bomberos": 10},
    "cuenca":    {"base": 115, "municipio": 38, "bomberos": 10},
    "default":   {"base": 120, "municipio": 40, "bomberos": 10},
}

# CONSULTA SRI
async def consultar_sri(placa: str) -> dict:
    resultado = {
        "placa": placa.upper(),
        "avaluo": 0,
        "impuesto_vehicular": 0,
        "anio_pago": None,
        "estado_pago": "desconocido",
        "multas": 0,
        "error": None
    }
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(
                "https://declaraciones.sri.gob.ec/tuportal-internet/menuAction.do",
                timeout=20000
            )
            await page.wait_for_selector("input[name*=placa], input[id*=placa]", timeout=8000)
            await page.fill("input[name*=placa], input[id*=placa]", placa.upper())
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
            content = await page.content()
            match_avaluo = re.search(r"[Aa]valuo[^0-9]*([0-9,\.]+)", content)
            if match_avaluo:
                resultado["avaluo"] = float(match_avaluo.group(1).replace(",", ""))
            match_imp = re.search(r"[Ii]mpuesto[^0-9]*([0-9,\.]+)", content)
            if match_imp:
                resultado["impuesto_vehicular"] = float(match_imp.group(1).replace(",", ""))
            if "pagado" in content.lower() or "cancelado" in content.lower():
                resultado["estado_pago"] = "al_dia"
            elif "pendiente" in content.lower() or "debe" in content.lower():
                resultado["estado_pago"] = "pendiente"
            await browser.close()
    except Exception as e:
        resultado["error"] = f"SRI no disponible: {str(e)[:80]}"
        resultado["estado_pago"] = "verificar_manualmente"
    return resultado

# CONSULTA ANT
async def consultar_ant(placa: str) -> dict:
    resultado = {
        "placa": placa.upper(),
        "propietario": "No disponible",
        "matricula_vence": None,
        "estado_matricula": "desconocido",
        "multas_ant": 0,
        "historial_propietarios": 1,
        "error": None
    }
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(
                "https://www.ant.gob.ec/index.php/servicios-soporte/consultas",
                timeout=20000
            )
            await page.wait_for_selector("input[name*=placa], input[id*=placa]", timeout=8000)
            await page.fill("input[name*=placa], input[id*=placa]", placa.upper())
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
            content = await page.content()
            match_vence = re.search(r"vence?[^0-9]*(\d{2}/\d{2}/\d{4})", content, re.IGNORECASE)
            if match_vence:
                resultado["matricula_vence"] = match_vence.group(1)
            if "vigente" in content.lower():
                resultado["estado_matricula"] = "vigente"
            elif "vencida" in content.lower() or "caducada" in content.lower():
                resultado["estado_matricula"] = "vencida"
            match_multas = re.search(r"multa[^0-9]*([0-9,\.]+)", content, re.IGNORECASE)
            if match_multas:
                resultado["multas_ant"] = float(match_multas.group(1).replace(",", ""))
            await browser.close()
    except Exception as e:
        resultado["error"] = f"ANT no disponible: {str(e)[:80]}"
        resultado["estado_matricula"] = "verificar_manualmente"
    return resultado

# CALCULAR COSTO TOTAL REAL
def calcular_costo_total(precio_negociado, ciudad, datos_sri, datos_ant, precio_promedio_mercado=None):
    ciudad_key = ciudad.lower() if ciudad.lower() in COSTOS_MATRICULA else "default"
    costos_m = COSTOS_MATRICULA[ciudad_key]
    matricula_vencida = datos_ant.get("estado_matricula") == "vencida"
    costo_matricula = sum(costos_m.values()) if matricula_vencida else 0
    multas_sri = datos_sri.get("multas", 0)
    multas_ant = datos_ant.get("multas_ant", 0)
    impuesto_vehicular = datos_sri.get("impuesto_vehicular", 0)
    tramites = (
        COSTOS_TRAMITES["contrato_notaria"] +
        COSTOS_TRAMITES["cambio_propietario_ant"] +
        COSTOS_TRAMITES["soat_promedio"] +
        COSTOS_TRAMITES["revision_vehicular"]
    )
    inspeccion = COSTOS_TRAMITES["inspeccion_mecanico"]
    total = (precio_negociado + costo_matricula + multas_sri +
             multas_ant + impuesto_vehicular + tramites + inspeccion)
    ahorro = None
    if precio_promedio_mercado:
        ahorro = precio_promedio_mercado - total
    return {
        "precio_negociado":    precio_negociado,
        "matricula":           costo_matricula,
        "multas_sri":          multas_sri,
        "multas_ant":          multas_ant,
        "impuesto_vehicular":  impuesto_vehicular,
        "notaria":             COSTOS_TRAMITES["contrato_notaria"],
        "cambio_propietario":  COSTOS_TRAMITES["cambio_propietario_ant"],
        "soat":                COSTOS_TRAMITES["soat_promedio"],
        "revision_vehicular":  COSTOS_TRAMITES["revision_vehicular"],
        "inspeccion_mecanico": inspeccion,
        "total_real":          round(total, 2),
        "ahorro_vs_mercado":   round(ahorro, 2) if ahorro is not None else None,
        "matricula_vencida":   matricula_vencida,
    }

# GENERAR GUIA PASO A PASO
def generar_guia_compra(ciudad, datos_ant, costos):
    pasos = [
        "GUIA DE COMPRA PASO A PASO",
        "",
        "PASO 1: Negocia el precio con el vendedor",
        "PASO 2: Inspeccion con mecanico de confianza (~$80)",
        "PASO 3: Verificar matricula y multas (ya lo hacemos por ti)",
    ]
    if costos.get("matricula_vencida"):
        pasos.append("PASO 4: Pagar matricula vencida antes de transferir")
    pasos += [
        "PASO 5: Firma contrato compraventa en notaria (~$120)",
        "PASO 6: Tramite ANT cambio de propietario (~$50)",
        "PASO 7: Obtener nuevo SOAT (~$85)",
        "PASO 8: Revision vehicular si aplica (~$35)",
        "",
        f"Tiempo estimado: 3-5 dias habiles en {ciudad.title()}",
        f"COSTO TOTAL ESTIMADO: ${costos['total_real']:,.0f}",
    ]
    return "\n".join(pasos)

# FORMATO MENSAJE TELEGRAM
def formatear_mensaje_costos(vehiculo, placa, datos_sri, datos_ant, costos, guia):
    estado_sri = "Impuestos al dia" if datos_sri.get("estado_pago") == "al_dia" else "Verificar SRI"
    estado_mat = "Matricula vigente" if datos_ant.get("estado_matricula") == "vigente" else "Matricula vencida"
    msg = [
        "ANALISIS COMPLETO DE COMPRA",
        f"Vehiculo: {vehiculo}",
        f"Placa: {placa.upper()}",
        "",
        "ESTADO LEGAL",
        f"  SRI (impuestos): {estado_sri}",
        f"  Matricula ANT:   {estado_mat}",
        "",
        "DESGLOSE DE COSTOS",
        f"  Precio negociado:      ${costos['precio_negociado']:>8,.0f}",
    ]
    if costos["matricula"] > 0:
        msg.append(f"  Matricula vencida:     ${costos['matricula']:>8,.0f}")
    if costos["multas_sri"] > 0:
        msg.append(f"  Multas SRI:            ${costos['multas_sri']:>8,.0f}")
    if costos["multas_ant"] > 0:
        msg.append(f"  Multas ANT:            ${costos['multas_ant']:>8,.0f}")
    msg += [
        f"  Contrato notaria:      ${costos['notaria']:>8,.0f}",
        f"  Cambio propietario:    ${costos['cambio_propietario']:>8,.0f}",
        f"  SOAT nuevo:            ${costos['soat']:>8,.0f}",
        f"  Revision vehicular:    ${costos['revision_vehicular']:>8,.0f}",
        f"  Inspeccion mecanico:   ${costos['inspeccion_mecanico']:>8,.0f}",
        "  --------------------------------",
        f"  COSTO TOTAL REAL:      ${costos['total_real']:>8,.0f}",
    ]
    if costos.get("ahorro_vs_mercado") is not None:
        signo = "AHORRO" if costos["ahorro_vs_mercado"] > 0 else "SOBRE PRECIO"
        msg.append(f"  {signo} vs mercado:    ${abs(costos['ahorro_vs_mercado']):>8,.0f}")
    msg.append("")
    msg.append(guia)
    msg.append("")
    msg.append("Analisis generado por MarketplaceEC Bot")
    return "\n".join(msg)

# ENVIAR POR TELEGRAM
async def enviar_analisis_telegram(chat_id, mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=10)
        return resp.status_code == 200

# FUNCION PRINCIPAL
async def analizar_vehiculo_completo(
    vehiculo, placa, precio_negociado, ciudad,
    chat_id=None, precio_promedio_mercado=None
):
    """Recibe datos del vehiculo y retorna analisis completo. Envia por Telegram si hay chat_id."""
    print(f"Consultando SRI y ANT para placa {placa}...")
    datos_sri, datos_ant = await asyncio.gather(
        consultar_sri(placa),
        consultar_ant(placa)
    )
    costos = calcular_costo_total(precio_negociado, ciudad, datos_sri, datos_ant, precio_promedio_mercado)
    guia = generar_guia_compra(ciudad, datos_ant, costos)
    mensaje = formatear_mensaje_costos(vehiculo, placa, datos_sri, datos_ant, costos, guia)
    if chat_id:
        await enviar_analisis_telegram(chat_id, mensaje)
        print(f"Analisis enviado a cliente {chat_id}")
    return {"vehiculo": vehiculo, "placa": placa, "datos_sri": datos_sri,
            "datos_ant": datos_ant, "costos": costos, "mensaje": mensaje}

# TEST LOCAL
if __name__ == "__main__":
    async def test():
        r = await analizar_vehiculo_completo(
            vehiculo="Toyota Fortuner 4.0 2017",
            placa="PBC1234",
            precio_negociado=28500,
            ciudad="quito",
            precio_promedio_mercado=32000
        )
        print("\n" + r["mensaje"])
    asyncio.run(test())
