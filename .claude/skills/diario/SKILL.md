---
name: diario
description: Diario de trades del dÃ­a. Usar cuando el usuario dicta una operaciÃ³n ("comprÃ© 5 futuros de Galicia a 4510", "vendÃ­ 10 rofex a tal precio", "cerrÃ© ese trade a 4532", "salÃ­ de la mitad"), pide ver cÃ³mo va el dÃ­a, o pide el feedback de sus trades al final de la rueda ("/diario", "/diario cierre", "dame el feedback del dÃ­a").
---

# Diario de trades

El usuario opera futuros en Matba Rofex (GGAL, RFX20, dÃ³lar) y va contando sus
trades en el chat. Cada uno se anota con `diario/diario.py`, que calcula el
resultado y actualiza la planilla de Google Sheets. Al final de la rueda se
revisan contra lo que hizo el mercado.

Esto es un registro: **nunca envÃ­es, modifiques ni canceles Ã³rdenes** en ningÃºn
sistema.

## Anotar

TraducÃ­ lo que dice a una llamada. La hora es la del mensaje, salvo que diga otra
("a las 11:20 comprÃ©â€¦"): en ese caso pasÃ¡ `--hora`.

```
py diario/diario.py abrir GGAL compra 5 4510 [--hora 11:32] [--nota "..."]
py diario/diario.py cerrar <n> 4532 [--cantidad 2] [--hora 12:05] [--nota "..."]
py diario/diario.py nota <n> "texto"
py diario/diario.py borrar <n>
py diario/diario.py ver
```

- **Instrumento:** "Galicia" â†’ `GGAL`, "el Ã­ndice"/"rofex" â†’ `RFX20`, "dÃ³lar" â†’ `DLR`.
- **Lado:** "comprÃ©", "me puse comprado", "long" â†’ `compra`; "vendÃ­", "me puse
  vendido", "short" â†’ `venta`.
- **Cerrar:** "cerrÃ© ese" es el Ãºltimo abierto de ese instrumento. Si hay mÃ¡s de
  uno abierto y no queda claro cuÃ¡l, preguntÃ¡; no adivines. Un cierre parcial va
  con `--cantidad`: el resto queda abierto como un trade nuevo.
- **Si falta un dato** (cantidad o precio), preguntalo. No anotes con un nÃºmero
  supuesto.
- Cualquier razÃ³n que dÃ© ("entrÃ© porque rebotÃ³ en el piso", "salÃ­ por el stop")
  va en `--nota`: es lo que mÃ¡s sirve para el feedback.

ContestÃ¡ corto: el trade anotado, el resultado si se cerrÃ³ y cÃ³mo va el dÃ­a. Si
la salida del script dice que la planilla no se actualizÃ³, decilo.

## Feedback de fin de dÃ­a

Cuando lo pida, o cuando avise que terminÃ³ de operar:

1. `py diario/diario.py ver` para tener los trades con sus horarios.
2. **QuÃ© hizo el mercado en esos horarios.** Con el grÃ¡fico de TradingView, velas
   de 5 minutos del dÃ­a de `NASDAQ:GGAL`, `BATS:SPY`, `AMEX:EWZ` y `BATS:ARGT`
   (`data_get_ohlcv`; nunca `data_get_study_values`, que borra los dibujos).
   - Antes, mirÃ¡ `logs/ggal_estudio.log`: si hay una corrida en curso (`INICIO`
     sin `FIN` en los Ãºltimos 45 minutos), esperÃ¡; no toques el grÃ¡fico.
   - Al terminar, dejÃ¡ el grÃ¡fico como estaba: `NASDAQ:GGAL` en diario.
   - No saques capturas.
   - El futuro de GGAL cotiza en pesos y el ADR en dÃ³lares: comparÃ¡ direcciÃ³n y
     momento, no precios. El tablero de flujo (`http://127.0.0.1:8767/datos`)
     suma delta y volumen relativo por vela si estÃ¡ levantado.
3. **LeÃ© los informes del dÃ­a** (`estudios/ggal/<fecha>-*.md`): quÃ© niveles y
   escenarios estaban planteados antes de cada trade.
4. **Por cada trade:** quÃ© hacÃ­a el ADR y el resto del mercado al entrar y al
   salir, si fue a favor o en contra de lo que pasaba afuera, cuÃ¡nto del
   movimiento posterior se capturÃ³ o se dejÃ³ (quÃ© pasÃ³ en los 30 minutos
   siguientes a la salida) y si respetÃ³ lo que decÃ­a el estudio.
5. **Del dÃ­a entero:** resultado, acierto, relaciÃ³n entre ganancia y pÃ©rdida
   promedio, si las pÃ©rdidas vienen de pocos trades grandes, horarios en que
   operÃ³ mejor y peor, y si hubo trades seguidos despuÃ©s de una pÃ©rdida.

Escribilo directo y concreto: quÃ© estuvo bien, quÃ© estuvo mal y **una o dos
cosas** para probar maÃ±ana. Con nÃºmeros y horarios, sin sermones. Si un dÃ­a
tiene dos o tres trades, no saques conclusiones estadÃ­sticas de eso: decÃ­ que
la muestra es chica.

## Datos que no estÃ¡n confirmados

Los multiplicadores por contrato estÃ¡n en `MULTIPLICADOR` de `diario/diario.py`
(GGAL 100, RFX20 1, DLR 1000). El resultado no descuenta comisiones ni derechos
de mercado. Si el usuario corrige alguno, cambialo ahÃ­.
