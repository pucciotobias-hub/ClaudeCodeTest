/**
 * Diario de trades: recibe el dia entero desde diario/diario.py y lo escribe en
 * una hoja con el nombre de la fecha (la mas nueva queda primera).
 *
 * Instalacion, una sola vez:
 *   1. Crear una planilla nueva en https://sheets.new y ponerle nombre.
 *   2. Extensiones > Apps Script. Borrar lo que haya, pegar este archivo, guardar.
 *   3. Implementar > Nueva implementacion > tipo "Aplicacion web".
 *        Ejecutar como: yo.   Quien tiene acceso: cualquier usuario.
 *      Autorizar cuando lo pida y copiar la URL que termina en /exec.
 *   4. Pegar esa URL en el .env de la raiz del repo:  DIARIO_SHEET_URL=https://script.google.com/macros/s/.../exec
 *
 * La URL es la llave: quien la tenga puede escribir en esta planilla (y solo en
 * esta). No se sube al repo. Si se filtra, se borra la implementacion y se crea otra.
 */

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d.fecha) || !Array.isArray(d.encabezado) || !Array.isArray(d.filas)) {
      return salida({ ok: false, error: 'formato' });
    }
    const libro = SpreadsheetApp.getActiveSpreadsheet();
    const hoja = libro.getSheetByName(d.fecha) || libro.insertSheet(d.fecha, 0);
    hoja.clear();
    hoja.clearConditionalFormatRules();

    const ancho = d.encabezado.length;
    hoja.getRange(1, 1, 1, ancho).setValues([d.encabezado]).setFontWeight('bold').setBackground('#1b2733').setFontColor('#ffffff');
    hoja.setFrozenRows(1);
    if (d.filas.length) {
      hoja.getRange(2, 1, d.filas.length, ancho).setValues(d.filas);
      // Resultado $ en verde o rojo; los abiertos, en gris.
      const col = d.encabezado.indexOf('Resultado $') + 1;
      const rango = hoja.getRange(2, col, d.filas.length, 1).setNumberFormat('#,##0.00');
      hoja.setConditionalFormatRules([
        SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setFontColor('#0a7a0a').setBold(true).setRanges([rango]).build(),
        SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0).setFontColor('#c62828').setBold(true).setRanges([rango]).build(),
      ]);
      const estado = d.encabezado.indexOf('Estado');
      d.filas.forEach(function (f, i) {
        if (f[estado] === 'abierto') hoja.getRange(i + 2, 1, 1, ancho).setFontColor('#777777').setFontStyle('italic');
      });
    }

    // Resumen del dia, dos filas mas abajo.
    const desde = d.filas.length + 4;
    const resumen = d.resumen || [];
    if (resumen.length) {
      hoja.getRange(desde - 1, 1).setValue('Resumen del día').setFontWeight('bold');
      hoja.getRange(desde, 1, resumen.length, 2).setValues(resumen.map(function (r) { return [r[0], r[1]]; }));
      hoja.getRange(desde, 2, resumen.length, 1).setHorizontalAlignment('right');
      const total = hoja.getRange(desde, 2).setFontWeight('bold').setNumberFormat('#,##0.00');
      const v = Number(resumen[0][1]);
      total.setFontColor(v > 0 ? '#0a7a0a' : v < 0 ? '#c62828' : '#000000');
    }
    hoja.autoResizeColumns(1, ancho);
    return salida({ ok: true, url: libro.getUrl() + '#gid=' + hoja.getSheetId() });
  } catch (err) {
    return salida({ ok: false, error: String(err) });
  }
}

function salida(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
