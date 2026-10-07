---
name: semanal
description: Republica la página del reporte semanal de GGAL con la última semana. Usar cuando el usuario pide "/semanal", "republicá el semanal", "actualizá la página del reporte semanal", o los lunes después de la corrida semanal.
---

# Republicar el reporte semanal de GGAL

La corrida de los lunes escribe `estudios/ggal/semanal/<fecha>.json` y lo mete
adentro de `scripts/ggal_semanal_pagina.html`, pero no puede publicar: la
herramienta `Artifact` no existe en `claude -p`. La página
https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67 queda en la semana anterior
hasta que una sesión interactiva la republica. Eso es lo que hace este comando.

No toques el diseño de la página ni el contenido del JSON: solo se publica.

## Pasos

1. **Ubicar la última semana.** El JSON más nuevo de `estudios/ggal/semanal/`.
   Si el usuario pasó una fecha (`/semanal 2026-10-05`), ese.
   Si el más nuevo tiene más de 7 días, la corrida del lunes no salió: decilo,
   mostrá lo que dice `logs/ggal_estudio.log` sobre el turno `semanal` y
   ofrecé correrlo con `/estudio semanal`. No publiques una semana vieja como
   si fuera la nueva.

2. **Asegurar que la página trae esa semana.** Compará el campo `semana` del
   JSON con el del bloque `<script type="application/json" id="datos">` de
   `scripts/ggal_semanal_pagina.html`. Si no coinciden:

   ```
   python scripts/ggal_semanal_incorporar.py estudios/ggal/semanal/<fecha>.json
   ```

3. **Publicar.** Con la herramienta `Artifact`:
   - primero `action: "read"` con `url: "https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67"`
     (sin esa lectura la publicación se rechaza);
   - después publicar `file_path: scripts/ggal_semanal_pagina.html` con ese
     mismo `url`, sin `icon` ni título nuevos.

   Si la lectura muestra que la página publicada ya tiene la misma `semana`,
   no hay nada que republicar: decilo y terminá.

4. **Commit.** Si el paso 2 cambió `scripts/ggal_semanal_pagina.html`,
   commitealo y pushealo (solo ese archivo, por ruta).

5. **Avisar.** Una línea: qué semana quedó publicada y el link. Agregá el
   `titular` del JSON para que se sepa de qué va sin abrirla.
