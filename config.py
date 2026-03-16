# ============================================
# marketplace_ecuador - Configuracion
# ============================================

# Tu token de bot de Telegram (obtenerlo con @BotFather)
TELEGRAM_TOKEN = "TU_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUI"

# Ubicacion
CIUDAD = "quito"
RADIO_KM = 500

# Intervalo de revision en minutos
INTERVALO_MINUTOS = 30

# Archivos de salida
CSV_SALIDA = "resultados.csv"
JSON_SALIDA = "resultados.json"
DB_VISTOS = "vistos.txt"

# ============================================
# BUSQUEDAS DE VEHICULOS
# ============================================
BUSQUEDAS_VEHICULOS = [
    {
        "nombre": "Fortuner 4.0",
        "query": "fortuner",
        "motor_objetivo": "4.0",
        "precio_min": 20000,
        "precio_max": 40000,
        "anio_min": 2014,
        "anio_max": 2020,
    },
    {
        "nombre": "Fortuner 2.7",
        "query": "fortuner 2.7",
        "motor_objetivo": "2.7",
        "precio_min": 15000,
        "precio_max": 30000,
        "anio_min": 2014,
        "anio_max": 2020,
    },
    {
        "nombre": "Hilux 4x4",
        "query": "hilux 4x4",
        "motor_objetivo": "desconocido",
        "precio_min": 18000,
        "precio_max": 45000,
        "anio_min": 2015,
        "anio_max": 2023,
    },
    {
        "nombre": "Land Cruiser Prado",
        "query": "prado txl",
        "motor_objetivo": "desconocido",
        "precio_min": 25000,
        "precio_max": 60000,
        "anio_min": 2010,
        "anio_max": 2022,
    },
]

# ============================================
# BUSQUEDAS DE ROPA
# ============================================
BUSQUEDAS_ROPA = [
    {
        "nombre": "Ralph Lauren",
        "query": "ralph lauren",
        "precio_min": 5,
        "precio_max": 60,
        "descuento_min": 40,
        "categoria": "ropa",
    },
    {
        "nombre": "Tommy Hilfiger",
        "query": "tommy hilfiger",
        "precio_min": 5,
        "precio_max": 50,
        "descuento_min": 40,
        "categoria": "ropa",
    },
    {
        "nombre": "Nike original",
        "query": "nike original",
        "precio_min": 5,
        "precio_max": 45,
        "descuento_min": 40,
        "categoria": "ropa",
    },
    {
        "nombre": "Lacoste",
        "query": "lacoste",
        "precio_min": 5,
        "precio_max": 65,
        "descuento_min": 40,
        "categoria": "ropa",
    },
    {
        "nombre": "Calvin Klein",
        "query": "calvin klein",
        "precio_min": 5,
        "precio_max": 50,
        "descuento_min": 40,
        "categoria": "ropa",
    },
    {
        "nombre": "Jordan",
        "query": "jordan original",
        "precio_min": 10,
        "precio_max": 70,
        "descuento_min": 35,
        "categoria": "ropa",
    },
    {
        "nombre": "Ropa bebe marca",
        "query": "carter oshkosh bebe",
        "precio_min": 2,
        "precio_max": 20,
        "descuento_min": 30,
        "categoria": "ropa_bebe",
    },
]

# ============================================
# BUSQUEDAS DE CELULARES (bonus)
# ============================================
BUSQUEDAS_CELULARES = [
    {
        "nombre": "iPhone barato",
        "query": "iphone",
        "precio_min": 100,
        "precio_max": 600,
        "categoria": "celular",
    },
    {
        "nombre": "Samsung Galaxy",
        "query": "samsung galaxy",
        "precio_min": 80,
        "precio_max": 400,
        "categoria": "celular",
    },
]

# Todas las busquedas activas juntas
BUSQUEDAS = BUSQUEDAS_VEHICULOS + BUSQUEDAS_ROPA + BUSQUEDAS_CELULARES
