# Solicitud de homologación — Monitor de divergencia GGAL / RFX20

**Solicitante:** Tobías Puccio
**Cuenta ReMarkets:** REM23427
**Conector:** pyRofex (API Primary / Matba Rofex)
**Entorno actual:** ReMarkets (homologación)

---

## 1. Qué hace el sistema

Es un **monitor de market data de solo lectura**. Se suscribe por WebSocket al
book de dos futuros listados en Matba Rofex y calcula en tiempo real el spread
entre ambos. Cuando ese spread se desvía estadísticamente de su media reciente,
emite una **señal interna** (log + aviso por consola).

Instrumentos monitoreados:

- `GGAL/JUN26` — futuro de Grupo Financiero Galicia
- `RFX20/JUN26` — futuro del índice Rofex 20

Metodología: se toma el spread `log(GGAL / RFX20)` a cadencia fija (1 muestra por
segundo), se calcula su z-score sobre una ventana móvil de 100 muestras y se
genera una señal cuando `|z| ≥ 2`, con un cooldown de 60 s entre señales.

## 2. Qué NO hace (importante)

- **No envía órdenes.** No hay alta, baja ni modificación de órdenes.
- **No rutea operaciones** de ningún tipo.
- No accede a posiciones, cartera ni datos de cuenta más allá de la
  autenticación necesaria para suscribirse al market data.

Es puramente un consumidor de datos de mercado. El código no contiene ninguna
llamada de order entry (`send_order`, `cancel_order`, etc.) y puede verificarse.

## 3. Uso de la API

| Función pyRofex | Uso |
|---|---|
| `initialize()` | Autenticación e inicio de sesión |
| `init_websocket_connection()` | Apertura del canal de market data |
| `market_data_subscription()` | Suscripción a LAST / BIDS / OFFERS de los 2 instrumentos |
| `get_all_instruments()` | Validación (al arranque) de que los símbolos estén vigentes |
| `close_websocket_connection()` | Cierre limpio / reconexión |

Consideraciones operativas ya implementadas:

- **Reconexión automática** con backoff exponencial ante caída del feed.
- **Heartbeat**: si no llegan datos por 30 s, se fuerza la reconexión.
- **Sin polling agresivo**: el market data llega por push (WebSocket); no se
  hace consulta repetida por REST.
- **Credenciales fuera del código**, vía variables de entorno / archivo `.env`.

## 4. Qué necesitamos del broker

1. Confirmación de que el conector es apto para homologación en ReMarkets.
2. Habilitación de las **credenciales productivas** de market data una vez
   aprobado, para replicar el mismo flujo sobre datos en vivo.

El objetivo de esta etapa es validar el consumo de market data. Una vez
homologado, ajustaremos parámetros para operar sobre datos en tiempo real.

## 5. Cómo correrlo

```bash
pip install -r requirements-monitor.txt      # instala pyRofex

cp .env.example .env                          # completar credenciales ReMarkets
#   ROFEX_USER=...
#   ROFEX_PASSWORD=...
#   ROFEX_ACCOUNT=REM23427
#   ROFEX_ENV=REMARKET

python monitor.py
```

Las señales se registran en `monitor_divergencia.log` y se muestran en consola.

---

*Archivo principal: `monitor.py`. `divergencia_ggal_rfx20.py` es una versión
preliminar y no forma parte del entregable.*
