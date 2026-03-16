# marketplace_ecuador

Monitor automatizado de Facebook Marketplace Ecuador.
Detecta oportunidades de arbitraje en vehiculos, ropa de marca y celulares.
Filtra por motor, calidad de fotos, marca, descuento y envia alertas por Telegram.

---

## Caracteristicas

- Vehiculos: detecta motor 4.0 vs 2.7, anio, precio y calidad de fotos
- Ropa: detecta marca, talla, estado y calcula descuento vs precio retail
- Celulares: detecta modelo y rango de precio
- Sistema de puntaje 0-10 por cada publicacion
- Alertas instantaneas por Telegram
- Guarda todo en CSV y JSON para analisis
- Verifica cantidad de fotos reales por listing

---

## Instalacion

```bash
git clone https://github.com/edcaicedo3399/marketplace_ecuador.git
cd marketplace_ecuador
pip install -r requirements.txt
playwright install chromium
```

---

## Configuracion

Edita `config.py` con tus datos:

```python
TELEGRAM_TOKEN = "tu_token_aqui"   # @BotFather en Telegram
TELEGRAM_CHAT_ID = "tu_chat_id"    # @userinfobot en Telegram
CIUDAD = "quito"                   # Ciudad de busqueda
RADIO_KM = 500                     # Radio en km
INTERVALO_MINUTOS = 30             # Cada cuanto revisar
```

---

## Uso

```bash
python scraper.py
```

Se abrira Chrome. Asegurate de estar logueado en Facebook.
El bot corre en bucle automaticamente.

---

## Categorias activas

### Vehiculos
| Busqueda | Motor | Precio min | Precio max | Anos |
|---|---|---|---|---|
| Fortuner 4.0 | 4.0 | $20.000 | $40.000 | 2014-2020 |
| Fortuner 2.7 | 2.7 | $15.000 | $30.000 | 2014-2020 |
| Hilux 4x4 | cualquiera | $18.000 | $45.000 | 2015-2023 |
| Land Cruiser Prado | cualquiera | $25.000 | $60.000 | 2010-2022 |

### Ropa de Marca
| Marca | Precio retail ref. | Descuento minimo |
|---|---|---|
| Ralph Lauren | $75 | 40% |
| Tommy Hilfiger | $65 | 40% |
| Lacoste | $80 | 40% |
| Calvin Klein | $60 | 40% |
| Nike original | $55 | 40% |
| Jordan | $80 | 35% |
| Ropa bebe (Carter/OshKosh) | $25 | 30% |

### Celulares
| Busqueda | Precio min | Precio max |
|---|---|---|
| iPhone | $100 | $600 |
| Samsung Galaxy | $80 | $400 |

---

## Sistema de puntaje

Cada listing recibe un puntaje automatico de 0 a 10:

| Criterio | Puntos |
|---|---|
| 8+ fotos reales | +4 |
| Motor identificado | +2 |
| Anio identificado | +1 |
| Precio razonable | +2 |
| Titulo sin palabras sospechosas | +1 |

Solo se envian alertas con puntaje >= 4 y minimo 3 fotos.

---

## Estructura del proyecto

```
marketplace_ecuador/
├── scraper.py          # Script principal
├── filtros.py          # Filtros de vehiculos + fotos
├── filtros_ropa.py     # Filtros de ropa y marcas
├── alertas.py          # Notificaciones Telegram
├── config.py           # Configuracion y busquedas
├── requirements.txt    # Dependencias
├── resultados.csv      # Datos recolectados (auto)
├── resultados.json     # Datos en JSON (auto)
└── vistos.txt          # IDs procesados (auto)
```

---

## Modelo de negocio

Con este bot puedes:

1. **Arbitraje directo** - Comprar barato en Marketplace y revender a precio de mercado
2. **Alertas como servicio** - Cobrar $20/mes a compradores que quieren notificaciones personalizadas
3. **Reportes de precios** - Vender analisis de precios promedio por categoria a concesionarios o tasadores
4. **Ropa de marca** - Comprar prendas con 50-80% descuento y revender en Instagram/TikTok

---

## Agregar mas busquedas

En `config.py` agrega entradas a `BUSQUEDAS_VEHICULOS`, `BUSQUEDAS_ROPA` o `BUSQUEDAS_CELULARES`:

```python
{
    "nombre": "Mi busqueda",
    "query": "termino a buscar",
    "precio_min": 100,
    "precio_max": 500,
}
```

---

Hecho con Python + Playwright | Ecuador
