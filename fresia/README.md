# Estados Contables FRESIA S.A. A.G. 2026 — reconstrucción de formato

Regenera los Estados Contables con un diseño uniforme, **sin tocar un solo importe**.
Fuente: `Fresia_SAAG_Estados_Contables_2026_formato_uniforme_con_Anexo_II_FINAL_v21 (1).pdf`.

## Uso

```bash
python build.py              # valida y genera el PDF
python build.py --html       # además guarda el HTML intermedio
python assertions.py         # solo los puntos de control contables
python verify.py             # compara importe por importe contra el PDF original
```

`build.py` aborta sin generar nada si algún punto de control falla.

## Archivos

| Archivo | Qué hace |
|---|---|
| `data.py` | Contenido extraído del PDF. **Todos los importes son cadenas de texto**: nunca se parsean a número, no se recalculan ni se reformatean. |
| `styles.css` | Sistema de diseño único (Times, escala de cuerpos, marcos, márgenes). |
| `build.py` | Arma el HTML y exporta a PDF con WeasyPrint. |
| `assertions.py` | Puntos de control contables. |
| `verify.py` | Verificación de fidelidad token por token contra el PDF original. |

## Sistema de diseño

- **Una sola tipografía**: Times New Roman en todo el documento.
- Sociedad 13 pt bold · títulos 13 pt bold (12 pt si son largos) · subtítulos 8,5 pt ·
  cuerpo y encabezados de cuadro 7,6 pt · notas al pie 7,6 pt · firmas 7,6 pt.
- **Cuadros**: grilla completa (todas las horizontales y verticales), borde exterior
  de 1 pt, separación reforzada entre encabezado / cuerpo / totales. No se borra
  ninguna línea; las filas de subtítulo y las filas en blanco conservan sus celdas
  para que las verticales no se corten.
- **Título centrado respecto del cuadro**: el título vive dentro del marco y ocupa
  exactamente el ancho del cuadro, así que centrarlo en el marco es centrarlo en la
  tabla, no en la página.
- **Pie alineado al cuadro**: el pie arranca en `margen de página + borde del marco +
  padding del marco`, la misma coordenada X que el borde izquierdo de la tabla.
- Todos los cuadros ocupan el 100 % del ancho útil, con los mismos márgenes.

## Paginación

- **A4 apaisada**: Anexos I–VII, Estado de Situación Patrimonial, Estado de Resultados,
  EPN y Estado de Flujo de Efectivo.
- **A4 vertical**: Notas 1 a 6.

El original mezclaba tres tamaños de hoja (A4 apaisada, A4 vertical y una hoja
apaisada de 297 × 240 mm solo para el Anexo VI). Ahora hay dos, y todos los cuadros
comparten formato.

El orden de páginas es Anexos I–VII → ESP → ER → EPN → EFE → Notas. Para volver al
orden del PDF original (Anexos → EFE → ER → EPN → ESP → Notas) basta cambiar
`ORDEN_ESTADOS = "original"` en `build.py`.

## Decisiones que conviene revisar

1. **Anexo VI en dos hojas.** El cuadro de gastos tiene 42 filas y no entra en una A4
   apaisada a 7,6 pt. Como está prohibido achicar la fuente o el cuadro, se parte en
   dos hojas del mismo formato repitiendo íntegro el encabezado de columnas, con
   "(Continúa en hoja 2 de 2)" / "(Continuación — hoja 2 de 2)" en el subtítulo. El
   original resolvía lo mismo usando una hoja más alta que el resto del documento.
   Se controla con `"partir_en": 22` en `data.py`.

2. **Notas al pie del Anexo II recuperadas.** El cuadro tiene los marcadores `(2)` y
   `(3)`, pero el texto que los explica se había perdido entre v14 y v19/v21. Se
   restauró textual desde v14. El texto de la nota (3) menciona "el coeficiente de la
   nota (1)"; esa nota (1) ya no existe en el Anexo II (v21 quitó el marcador del
   encabezado 2025). Se dejó la redacción tal cual — corregirla es una decisión
   contable, no de diseño.

3. **Diferencia de 1 centavo en el EPN.** El PN al cierre 2025 figura como
   `6.215.867.510,03` en la columna comparativa, mientras que el mismo saldo aparece
   como `6.215.867.510,02` en "Saldos al inicio" de 2026. Está así en el original y se
   respetó. El punto de control de la consigna usa `,02` y cierra exacto.

4. **Correcciones sobreimpresas del original.** En 7 lugares el PDF original tiene un
   importe viejo pintado debajo de un rectángulo blanco, con el valor corregido
   encima. El extractor de texto ve los dos. Se tomó el valor **visible**, que además
   coincide con los puntos de control en 6 de los 7 casos. `verify.py` los lista uno
   por uno.

5. **Basura tipográfica del original eliminada**: pies duplicados y superpuestos,
   "BIENES DE USO" impreso dos veces en el Anexo III, "S ndico Titular" y "Contador
   Pœblico" por errores de codificación en el Anexo VI, y el doble render con
   desplazamiento de 4,2 pt que afectaba toda esa página.

## Garantías de integridad

`assertions.py` verifica los puntos de control de la consigna leyendo las cadenas de
`data.py`. La única aritmética del proyecto es la comprobación de la fórmula del EPN
(`6.215.867.510,02 − 191.257.782,59 + 460.334.551,09 = 6.484.944.278,52`), hecha con
`Decimal` y en modo lectura: si no cierra, se reporta el error, nunca se reescribe un
importe.

`verify.py` extrae todos los importes del PDF generado y del original y comprueba que
ninguno sea ajeno al original y que ninguno se haya perdido sin explicación.
