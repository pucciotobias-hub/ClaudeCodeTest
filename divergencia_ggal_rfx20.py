# =============================================================================
# Monitor de Divergencia GGAL vs RFX20 — Matba Rofex / pyRofex
# Detecta desfasajes de precio entre ambos futuros en tiempo real via WebSocket
# =============================================================================

import time                          # Para timestamps y el loop principal
from collections import deque        # Estructura de historial circular (FIFO, tamaño fijo)
from datetime import datetime        # Para imprimir hora legible en los logs
import pyRofex                       # Librería oficial de Matba Rofex para Python
from pyRofex import MarketDataEntry  # Enum con los tipos de datos de mercado disponibles

# --- CONFIGURACIÓN -----------------------------------------------------------

USUARIO   = "pucciotobias23427"
PASSWORD  = "mndnoL2$"
CUENTA    = "REM23427"

# Los dos instrumentos que queremos monitorear
TICKERS = ["GGAL/JUN26", "RFX20/JUN26"]

# Umbral de divergencia en puntos porcentuales: si la diferencia de variación
# entre GGAL y RFX20 supera este valor, se considera una posible oportunidad
UMBRAL_DIVERGENCIA = 0.8   # 0.8%

# Ventana temporal hacia atrás para calcular el cambio porcentual (en segundos)
VENTANA_SEGUNDOS = 60      # 1 minuto


# --- HISTORIAL DE PRECIOS ----------------------------------------------------

# Diccionario: cada ticker mapea a un deque de tuplas (timestamp_unix, precio).
# maxlen=500 garantiza que el deque nunca crezca indefinidamente en memoria;
# si llega el item 501, el más antiguo se descarta automáticamente.
historial = {
    ticker: deque(maxlen=500)   # Deque vacío por ticker
    for ticker in TICKERS       # Se crea uno por cada instrumento
}


# --- FUNCIONES DE CÁLCULO ----------------------------------------------------

def obtener_precio_hace_un_minuto(ticker):
    """
    Busca en el historial el precio registrado más cercano a (ahora - 60 segundos).
    Retorna el precio como float, o None si no hay datos suficientes todavía.
    """
    cola = historial[ticker]          # Deque del ticker pedido

    if len(cola) < 2:                 # Necesitamos al menos 2 puntos para comparar
        return None

    ahora = time.time()               # Timestamp actual en segundos (Unix epoch)
    objetivo = ahora - VENTANA_SEGUNDOS   # El momento que queremos (hace 1 minuto)

    # Recorremos el deque buscando la primera entrada cuyo timestamp
    # sea >= al objetivo; eso es lo más cercano al minuto atrás que tenemos.
    # El deque está ordenado cronológicamente (el más antiguo al inicio).
    for timestamp, precio in cola:
        if timestamp >= objetivo:     # Encontramos el punto más cercano al minuto
            return precio

    return None   # Todos los registros son más viejos de 1 minuto (caso raro)


def calcular_variacion(ticker):
    """
    Calcula la variación porcentual del precio actual vs el de hace 1 minuto.
    Retorna el porcentaje como float, o None si no hay datos suficientes.
    """
    cola = historial[ticker]          # Deque del ticker

    if not cola:                      # Si el deque está vacío, no hay precio actual
        return None

    precio_actual = cola[-1][1]       # El último elemento del deque es el más reciente; [1] es el precio
    precio_base   = obtener_precio_hace_un_minuto(ticker)   # Precio de hace 1 min

    if precio_base is None:           # Si no tenemos referencia de hace 1 minuto, salimos
        return None

    if precio_base == 0:              # Evitar división por cero (no debería ocurrir en mercado real)
        return None

    variacion = (precio_actual - precio_base) / precio_base * 100   # Fórmula de variación %
    return variacion


def verificar_divergencia():
    """
    Compara la variación porcentual de GGAL y RFX20.
    Si la diferencia supera el umbral configurado, imprime la alerta de arbitraje.
    """
    var_ggal  = calcular_variacion("GGAL/JUN26")    # Variación % de GGAL en el último minuto
    var_rfx20 = calcular_variacion("RFX20/JUN26")   # Variación % de RFX20 en el último minuto

    if var_ggal is None or var_rfx20 is None:        # Si alguno no tiene datos todavía, salir
        return

    diferencia = abs(var_ggal - var_rfx20)           # Diferencia en puntos porcentuales (valor absoluto)

    if diferencia > UMBRAL_DIVERGENCIA:              # Si supera el umbral → hay divergencia
        hora = datetime.now().strftime("%H:%M:%S")   # Hora legible para el log
        print(
            f"[{hora}] ALERTA DE DIVERGENCIA: "
            f"GGAL movió {var_ggal:+.2f}% y RFX20 movió {var_rfx20:+.2f}%. "
            f"Posible oportunidad de arbitraje"
        )


# --- HANDLERS DEL WEBSOCKET --------------------------------------------------

def market_data_handler(message):
    """
    Callback principal: pyRofex llama a esta función cada vez que llega
    un nuevo mensaje de mercado por el WebSocket (en un hilo separado).
    El 'message' es un diccionario Python ya parseado desde JSON.
    """
    try:
        # Extraemos el símbolo del instrumento del mensaje recibido.
        # Estructura del mensaje: {"instrumentId": {"symbol": "GGAL/JUN26"}, "marketData": {...}}
        ticker = message["instrumentId"]["symbol"]

        # Verificamos que el mensaje corresponde a uno de nuestros tickers
        if ticker not in historial:
            return   # Ignorar mensajes de otros instrumentos

        # El campo "LA" (Last) contiene el último precio operado.
        # No todos los mensajes incluyen "LA" (algunos traen solo bid/offer),
        # así que usamos .get() para no generar KeyError si falta el campo.
        market_data = message.get("marketData", {})   # Datos de mercado del mensaje
        ultimo      = market_data.get("LA")           # "LA" = Last (último precio operado)

        if ultimo is None:
            return   # Este mensaje no trae precio de última operación, ignorarlo

        precio = ultimo.get("price")   # El precio está dentro del objeto "LA"

        if precio is None or precio <= 0:   # Sanity check: precio válido
            return

        # Guardamos el precio junto al timestamp actual en el historial circular
        timestamp = time.time()              # Tiempo en segundos (Unix epoch, float)
        historial[ticker].append((timestamp, precio))   # Agrega al final del deque

        # Cada vez que llega un precio nuevo, verificamos si hay divergencia
        verificar_divergencia()

    except Exception as e:
        # Capturamos cualquier error inesperado al parsear el mensaje
        # para que no rompa el loop del WebSocket
        print(f"[ERROR] Fallo al procesar mensaje: {e} | Mensaje: {message}")


def error_handler(message):
    """
    Callback de error: pyRofex llama a esta función cuando el servidor
    envía un mensaje de tipo error (ej. suscripción rechazada, ticker inválido).
    """
    print(f"[WS ERROR] Mensaje de error recibido: {message}")


def exception_handler(e):
    """
    Callback de excepción: pyRofex llama a esta función cuando ocurre
    una excepción dentro del cliente WebSocket (ej. pérdida de conexión,
    timeout, error de red).
    """
    print(f"[WS EXCEPCIÓN] Excepción en el cliente WebSocket: {e}")


# --- PUNTO DE ENTRADA --------------------------------------------------------

if __name__ == "__main__":

    print("Inicializando conexión con Matba Rofex (entorno REMARKET)...")

    # Inicializa la sesión HTTP con las credenciales y el entorno elegido.
    # REMARKET es el entorno de pruebas/demo de Matba Rofex.
    # Esta llamada obtiene un token de sesión y configura la librería internamente.
    pyRofex.initialize(
        user=USUARIO,                         # Usuario de Remarket
        password=PASSWORD,                    # Contraseña de Remarket
        account=CUENTA,                       # Número de comitente
        environment=pyRofex.Environment.REMARKET   # Entorno de pruebas (no producción)
    )

    print("Conexión HTTP exitosa. Iniciando WebSocket...")

    # Abre la conexión WebSocket en un hilo de fondo (no bloquea este hilo).
    # Le pasamos los tres handlers que definimos arriba:
    #   - market_data_handler: para mensajes de mercado (precios)
    #   - error_handler:       para mensajes de error del servidor
    #   - exception_handler:   para excepciones del cliente (red, timeout)
    pyRofex.init_websocket_connection(
        market_data_handler=market_data_handler,
        error_handler=error_handler,
        exception_handler=exception_handler
    )

    print(f"WebSocket activo. Suscribiendo a {TICKERS}...")

    # Nos suscribimos al market data de los dos instrumentos.
    # A partir de este momento, el servidor comenzará a enviarnos
    # actualizaciones de precio en tiempo real por el WebSocket.
    # Pedimos tres tipos de datos:
    #   LAST   → último precio operado ("LA" en el JSON)
    #   BIDS   → mejor oferta compradora ("BI" en el JSON)
    #   OFFERS → mejor oferta vendedora ("OF" en el JSON)
    pyRofex.market_data_subscription(
        tickers=TICKERS,
        entries=[
            MarketDataEntry.LAST,    # Precio de última operación
            MarketDataEntry.BIDS,    # Mejor punta compradora
            MarketDataEntry.OFFERS,  # Mejor punta vendedora
        ]
    )

    print(
        f"Suscripción activa. Monitoreando divergencia GGAL vs RFX20...\n"
        f"Umbral: {UMBRAL_DIVERGENCIA}% | Ventana: {VENTANA_SEGUNDOS}s\n"
        f"(Esperá ~{VENTANA_SEGUNDOS}s para acumular historial y ver alertas)\n"
        f"Presioná Ctrl+C para detener.\n"
    )

    # Loop principal: mantiene el proceso vivo mientras el WebSocket
    # corre en su hilo de fondo. Sin este loop, el script terminaría
    # inmediatamente después de suscribirse.
    try:
        while True:
            time.sleep(1)   # Duerme 1 segundo; el WebSocket sigue activo en su hilo

    except KeyboardInterrupt:
        # Ctrl+C: cierre limpio
        print("\nMonitor detenido por el usuario.")
