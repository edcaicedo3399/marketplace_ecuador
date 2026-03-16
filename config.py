# ============================================
# marketplace_ecuador - Configuracion
# ============================================

# Tu token de bot de Telegram (obtenerlo con @BotFather)
TELEGRAM_TOKEN = "TU_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"

# Busquedas a monitorear
BUSQUEDAS = [
    {
        "nombre": "Fortuner 4.0",
        "query": "fortuner",
        "motor_objetivo": "4.0",
        "precio_min": 20000,
        "precio_max": 40000,
        "anio_min": 2014,
        "anio_max": 2020,
    },
]

# Ubicacion
CIUDAD = "quito"
RADIO_KM = 500

# Intervalo de revision en minutos
INTERVALO_MINUTOS = 30

# Archivos de salida
CSV_SALIDA = "resultados.csv"
JSON_SALIDA = "resultados.json"
DB_VISTOS = "vistos.txt"
