---
name: diario
description: Diario de trades del día. Usar cuando el usuario dicta una operación ("compré 5 futuros de Galicia a 4510", "vendí 10 rofex a tal precio", "cerré ese trade a 4532", "salí de la mitad"), pide ver cómo va el día, o pide el feedback de sus trades al final de la rueda ("/diario", "/diario cierre", "dame el feedback del día").
---

# Diario de trades

El usuario opera futuros en Matba Rofex (GGAL, RFX20, dólar) y va contando sus
trades en el chat. Cada uno se anota con `diario/diario.py`, que calcula el
resultado y actualiza la planilla de Google Sheets. Al final de la rueda se
revisan contra lo que hizo el mercado.

Esto es un registro: **nunca envíes, modifiques ni canceles órdenes** en ningún
sistema.

## Anotar

Traducí lo que dice a una llamada. La hora es la del mensaje, salvo que diga otra
("a las 11:20 compré…"): en ese caso pasá `--hora`.

```
python diario/diario.py abrir GGAL compra 5 4510 [--hora 11:32] [--nota "..."]
python diario/diario.py cerrar <n> 4532 [--cantidad 2] [--hora 12:05] [--nota "..."]
python diario/diario.py nota <n> "texto"
python diario/diario.py borrar <n>
python diario/diario.py ver
```

- **Instrumento:** "Galicia" → `GGAL`, "el índice"/"rofex" → `RFX20`, "dólar" → `DLR`.
- **Lado:** "compré", "me puse comprado", "long" → `compra`; "vendí", "me puse
  vendido", "short" → `venta`.
- **Cerrar:** "cerré ese" es el último abierto de ese instrumento. Si hay más de
  uno abierto y no queda claro cuál, preguntá; no adivines. Un cierre parcial va
  con `--cantidad`: el resto queda abierto como un trade nuevo.
- **Si falta un dato** (cantidad o precio), preguntalo. No anotes con un número
  supuesto.
- Cualquier razón que dé ("entré porque rebotó en el piso", "salí por el stop")
  va en `--nota`: es lo que más sirve para el feedback.

Contestá corto: el trade anotado, el resultado si se cerró y cómo va el día. Si
la salida del script dice que la planilla no se actualizó, decilo.

## Feedback de fin de día

Cuando lo pida, o cuando avise que terminó de operar:

1. `python diario/diario.py ver` para tener los trades con sus horarios.
2. **Qué hizo el mercado en esos horarios.** Con el gráfico de TradingView, velas
   de 5 minutos del día de `NASDAQ:GGAL`, `BATS:SPY`, `AMEX:EWZ` y `BATS:ARGT`
   (`data_get_ohlcv`; nunca `data_get_study_values`, que borra los dibujos).
   - Antes, mirá `logs/ggal_estudio.log`: si hay una corrida en curso (`INICIO`
     sin `FIN` en los últimos 45 minutos), esperá; no toques el gráfico.
   - Al terminar, dejá el gráfico como estaba: `NASDAQ:GGAL` en diario.
   - No saques capturas.
   - El futuro de GGAL cotiza en pesos y el ADR en dólares: compará dirección y
     momento, no precios. El tablero de flujo (`http://127.0.0.1:8767/datos`)
     suma delta y volumen relativo por vela si está levantado.
3. **Leé los informes del día** (`estudios/ggal/<fecha>-*.md`): qué niveles y
   escenarios estaban planteados antes de cada trade.
4. **Por cada trade:** qué hacía el ADR y el resto del mercado al entrar y al
   salir, si fue a favor o en contra de lo que pasaba afuera, cuánto del
   movimiento posterior se capturó o se dejó (qué pasó en los 30 minutos
   siguientes a la salida) y si respetó lo que decía el estudio.
5. **Del día entero:** resultado, acierto, relación entre ganancia y pérdida
   promedio, si las pérdidas vienen de pocos trades grandes, horarios en que
   operó mejor y peor, y si hubo trades seguidos después de una pérdida.

Escribilo directo y concreto: qué estuvo bien, qué estuvo mal y **una o dos
cosas** para probar mañana. Con números y horarios, sin sermones. Si un día
tiene dos o tres trades, no saques conclusiones estadísticas de eso: decí que
la muestra es chica.

## Datos que no están confirmados

Los multiplicadores por contrato están en `MULTIPLICADOR` de `diario/diario.py`
(GGAL 100, RFX20 1, DLR 1000). El resultado no descuenta comisiones ni derechos
de mercado. Si el usuario corrige alguno, cambialo ahí.
