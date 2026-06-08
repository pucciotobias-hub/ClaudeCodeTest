# Superbot de Equity Research

Bot autonomo que recolecta datos de mercado, aplica filtros de inversion de
gurus historicos (Buffett, Lynch), corre un modelo DCF con rigor contable,
genera un reporte PDF institucional y lo envia por Telegram todos los viernes
a las 18:00 hs.

## Estructura

```
quant_bot/
├── main.py               # Orquestador + scheduler (daemon)
├── data_fetcher.py       # yfinance + sentimiento de noticias (VADER)
├── quant_models.py       # Filtros de guru, DCF 5 anios, buscador de joyitas
├── pdf_generator.py      # Plantilla HTML/CSS + WeasyPrint
├── telegram_notifier.py  # Envio por la Bot API de Telegram
├── requirements.txt
├── .env.example
└── outputs/reports/      # PDFs generados (Quant_Research_YYYY_MM_DD.pdf)
```

## Instalacion paso a paso

### 1. Entorno virtual e instalacion de dependencias

```powershell
cd C:\Users\Tobias\Desktop\ClaudeCodeTest\quant_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. WeasyPrint en Windows (GTK3)

WeasyPrint necesita las librerias nativas **GTK3**. La forma mas simple en
Windows es via winget (ya instalado en este equipo):

```powershell
winget install --id GtkD.GtkPlusRuntime.x64 --source winget `
    --accept-source-agreements --accept-package-agreements
```

> El instalador agrega GTK al PATH del sistema. **Abri una terminal nueva**
> despues de instalar para que Python encuentre las DLLs (`libgtk-3-0.dll`).
> Verificacion rapida: `python -c "import weasyprint; print(weasyprint.__version__)"`
> (los warnings `GLib-GIO-WARNING` son inofensivos).

Alternativa: el *GTK3 Runtime* de tschoonj
(https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).

Si por algun motivo GTK no esta disponible, el bot **no crashea**: genera el
reporte como `.html` en `outputs/reports/` y lo envia igual por Telegram. (Para
PDF nativo sin dolores de cabeza, tambien podes correrlo en WSL/Linux.)

### 3. Credenciales de Telegram

```powershell
copy .env.example .env
```

Edita `.env` con tu `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`:

- **Token**: habla con [@BotFather](https://t.me/BotFather) -> `/newbot`.
- **Chat ID**: escribile a tu bot, luego abri
  `https://api.telegram.org/bot<TOKEN>/getUpdates` y busca `"chat":{"id":...}`.

## Uso

### Prueba inmediata (corre el pipeline una vez)

```powershell
python main.py --once
```

Mira `bot_activity.log` y `outputs/reports/` para verificar el resultado.

### Arrancar el daemon (corre para siempre, viernes 18:00)

```powershell
python main.py
```

Dejalo corriendo. `Ctrl+C` lo detiene.

## Como dejarlo corriendo "para siempre"

### Opcion A — Tarea Programada de Windows (recomendada)

No necesitas mantener una terminal abierta. Crea una tarea que arranque el
daemon al iniciar sesion:

```powershell
$py = "C:\Users\Tobias\Desktop\ClaudeCodeTest\quant_bot\.venv\Scripts\python.exe"
$script = "C:\Users\Tobias\Desktop\ClaudeCodeTest\quant_bot\main.py"
$action = New-ScheduledTaskAction -Execute $py -Argument $script `
    -WorkingDirectory "C:\Users\Tobias\Desktop\ClaudeCodeTest\quant_bot"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "QuantBotDaemon" -Action $action `
    -Trigger $trigger -Description "Superbot de Equity Research"
```

El propio bot se encarga de esperar al viernes 18:00. Para detenerlo:
`Unregister-ScheduledTask -TaskName "QuantBotDaemon"`.

> Alternativa sin daemon: si preferis que Windows dispare el ciclo directamente,
> usa `-Argument "$script --once"` con un `New-ScheduledTaskTrigger -Weekly
> -DaysOfWeek Friday -At 18:00`. Asi el proceso solo vive durante cada corrida.

### Opcion B — Linux/WSL con systemd o nohup

```bash
nohup python main.py > /dev/null 2>&1 &
```

O un servicio `systemd` que ejecute `python main.py` con `Restart=always`.

## Notas

- **Rate-limits de Yahoo**: el fetcher reintenta con backoff exponencial y deja
  1s entre tickers. Si Yahoo bloquea, el ciclo loguea el error y avisa por
  Telegram sin romperse.
- **Datos faltantes**: cualquier metrica ausente se reporta como `N/A` en el PDF
  (ej. bancos sin "Margen Bruto"). Nunca se muestra un `0%` enganioso.
- **No es asesoramiento financiero.** Herramienta educativa/informativa.
