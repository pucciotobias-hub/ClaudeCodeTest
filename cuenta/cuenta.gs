// ============================================================
// DASHBOARD DE CUENTA — Posiciones, Operaciones y P&L
// Cocos Capital / Matriz — ROFEX Futuros
//
// SETUP (hacerlo una sola vez):
//   1. Abrí un Google Sheets NUEVO en blanco
//   2. Extensiones → Apps Script
//   3. Borrá el código de ejemplo y pegá TODO este archivo
//   4. Guardá (Ctrl+S)
//   5. Completá USERNAME, PASSWORD y COMITENTE abajo
//   6. Corré diagnosticarAPI() para verificar los endpoints
//   7. Corré actualizarTodo() para cargar los datos
//   8. Corré activarAutoRefresh() y activarTriggerCierre() (una sola vez)
// ============================================================

const CONFIG = {
  USERNAME:  'TU_USUARIO',          // mismo usuario que usás en Matriz
  PASSWORD:  'TU_CONTRASEÑA',       // misma contraseña que usás en Matriz
  COMITENTE: 'TU_NUMERO_COMITENTE', // número de cuenta comitente
  BASE_URL:  'https://api.cocos.xoms.com.ar',

  // Endpoints de cuenta — correr diagnosticarAPI() primero para confirmar cuáles funcionan.
  // Si los de abajo no traen datos, actualizarlos con los que marcó verde el diagnóstico.
  EP_POSITIONS: '/rest/portfolio/positions',
  EP_ORDERS:    '/rest/orders',
};

// ============================================================
// AUTH
// ============================================================
function getToken_() {
  const res = UrlFetchApp.fetch(CONFIG.BASE_URL + '/auth/getToken', {
    method: 'post',
    headers: { 'X-Username': CONFIG.USERNAME, 'X-Password': CONFIG.PASSWORD },
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200)
    throw new Error('Login fallido. Verificá usuario y contraseña en CONFIG.');
  const token = res.getHeaders()['x-auth-token'];
  if (!token) throw new Error('No se recibió token.');
  return token;
}

function accountHeaders_(token) {
  return {
    'X-Auth-Token':   token,
    'X-Account-Id':   CONFIG.COMITENTE,
    'X-Comitente-Id': CONFIG.COMITENTE,
  };
}

// ============================================================
// PRECIO ACTUAL (para calcular P&L no realizado)
// ============================================================
function getMD_(symbol, marketId, token) {
  const url = CONFIG.BASE_URL + '/rest/marketdata/get?symbol='
            + encodeURIComponent(symbol) + '&marketId=' + marketId
            + '&entries=LA,CL&depth=1';
  const res = UrlFetchApp.fetch(url, {
    headers: { 'X-Auth-Token': token },
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) return null;
  try {
    const json = JSON.parse(res.getContentText());
    return json.status === 'OK' ? json : null;
  } catch(e) { return null; }
}

function getCurrentPrice_(symbol, token) {
  // Intenta ROFX primero (futuros), luego MERV (acciones)
  let md = getMD_(symbol, 'ROFX', token);
  if (!md || !md.marketData || !md.marketData.LA)
    md = getMD_(symbol, 'MERV', token);
  Utilities.sleep(80);
  return (md && md.marketData && md.marketData.LA) ? md.marketData.LA.price : null;
}

// ============================================================
// DATOS DE CUENTA — POSICIONES
// ============================================================
function getPositions_(token) {
  const res = UrlFetchApp.fetch(CONFIG.BASE_URL + CONFIG.EP_POSITIONS, {
    headers: accountHeaders_(token),
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) return null;
  try { return JSON.parse(res.getContentText()); } catch(e) { return null; }
}

// Parseo defensivo: maneja distintos formatos de respuesta XOMS
function parsePositions_(json) {
  if (!json) return [];
  const arr = json.positions || json.portfolio || json.data || (Array.isArray(json) ? json : null);
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map(p => {
    const symbol = p.symbol || (p.instrument && p.instrument.symbol) || p.ticker || '';
    const qty    = Number(p.quantity    || p.qty         || p.size        || 0);
    const avg    = Number(p.avgCost     || p.averageCost || p.precioProm  || p.openingPrice || 0);
    const market = p.marketId || p.market || (symbol.includes('/') ? 'ROFX' : 'MERV');
    return { symbol, qty, avg, market };
  }).filter(p => p.symbol && p.qty !== 0);
}

// ============================================================
// DATOS DE CUENTA — OPERACIONES DEL DÍA
// ============================================================
function getTodayTrades_(token) {
  const tz    = 'America/Argentina/Buenos_Aires';
  const today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  const url   = CONFIG.BASE_URL + CONFIG.EP_ORDERS
              + '?dateFrom=' + today + '&dateTo=' + today + '&status=FILLED';
  const res   = UrlFetchApp.fetch(url, {
    headers: accountHeaders_(token),
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) return null;
  try { return JSON.parse(res.getContentText()); } catch(e) { return null; }
}

function parseTrades_(json) {
  if (!json) return [];
  const arr = json.orders || json.trades || json.data || (Array.isArray(json) ? json : null);
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map(o => {
    const symbol  = o.symbol || (o.instrument && o.instrument.symbol) || o.ticker || '';
    const side    = (o.side || o.operationType || '').toString().toUpperCase();
    const sideStr = (side === 'BUY' || side === 'C' || side === 'COMPRA') ? 'COMPRA' : 'VENTA';
    const qty     = Number(o.quantity     || o.qty   || o.size    || 0);
    const price   = Number(o.price        || o.executedPrice || o.precio || 0);
    const amount  = Number(o.amount       || o.total || o.importe || qty * price || 0);
    const status  = o.status || o.estado || '';
    const rawTime = o.datetime || o.timestamp || o.fecha || o.time || '';
    let timeStr = '';
    if (rawTime) {
      try { timeStr = Utilities.formatDate(new Date(rawTime), 'America/Argentina/Buenos_Aires', 'HH:mm:ss'); }
      catch(e) { timeStr = String(rawTime).substring(11, 19) || rawTime; }
    }
    return { symbol, side: sideStr, qty, price, amount, status, time: timeStr };
  }).filter(o => o.symbol);
}

// ============================================================
// HOJA: POSICIONES ABIERTAS
// ============================================================
function actualizarPosiciones() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('POSICIONES') || ss.insertSheet('POSICIONES');
  sheet.clearContents();
  sheet.clearFormats();

  const token = getToken_();
  const raw   = getPositions_(token);
  const poses = parsePositions_(raw);

  sheet.getRange(1,1).setValue('POSICIONES ABIERTAS')
    .setFontWeight('bold').setFontSize(13).setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(1,7).setValue('Actualizado: ' + new Date().toLocaleTimeString('es-AR'))
    .setFontColor('#aaaaaa');

  const headers = ['Ticker','Mercado','Cantidad','Precio Prom.','Precio Actual','Var$','P&L No Real.','P&L%'];
  sheet.getRange(2,1,1,8).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  if (!raw) {
    sheet.getRange(3,1).setValue('Sin datos — correr diagnosticarAPI() para verificar los endpoints.')
      .setFontColor('#cc2222');
    sheet.autoResizeColumns(1,8);
    return;
  }
  if (poses.length === 0) {
    sheet.getRange(3,1).setValue('Sin posiciones abiertas.').setFontColor('#aaaaaa');
    sheet.autoResizeColumns(1,8);
    return;
  }

  const rows = [];
  let totalPnl = 0;
  for (const p of poses) {
    const current = getCurrentPrice_(p.symbol, token);
    const varDol  = (current && p.avg) ? (current - p.avg) * p.qty : '';
    const pnlPct  = (current && p.avg && p.avg !== 0) ? (current - p.avg) / p.avg : '';
    if (typeof varDol === 'number') totalPnl += varDol;
    rows.push([p.symbol, p.market, p.qty, p.avg, current || '—', varDol, varDol, pnlPct]);
  }

  sheet.getRange(3,1,rows.length,8).setValues(rows);
  sheet.getRange(3,4,rows.length,2).setNumberFormat('#,##0.00');
  sheet.getRange(3,6,rows.length,2).setNumberFormat('#,##0.00');
  sheet.getRange(3,8,rows.length,1).setNumberFormat('0.00%');

  for (let i = 0; i < rows.length; i++) {
    const val   = rows[i][5];
    const color = (typeof val === 'number' && val >= 0) ? '#00aa44' : '#cc2222';
    sheet.getRange(i+3,6).setFontColor(color);
    sheet.getRange(i+3,7).setFontColor(color);
    sheet.getRange(i+3,8).setFontColor(color);
  }

  const totalRow = poses.length + 3;
  sheet.getRange(totalRow,1,1,8).setBackground('#0d3b5e').setFontColor('#ffffff').setFontWeight('bold');
  sheet.getRange(totalRow,1).setValue('TOTAL P&L NO REALIZADO');
  sheet.getRange(totalRow,7).setValue(totalPnl).setNumberFormat('#,##0.00')
    .setFontColor(totalPnl >= 0 ? '#00aa44' : '#cc2222');

  sheet.autoResizeColumns(1,8);
}

// ============================================================
// HOJA: OPERACIONES DEL DÍA
// ============================================================
function actualizarOperaciones() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('OPERACIONES') || ss.insertSheet('OPERACIONES');
  sheet.clearContents();
  sheet.clearFormats();

  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy');

  sheet.getRange(1,1).setValue('OPERACIONES DEL DÍA — ' + fecha)
    .setFontWeight('bold').setFontSize(13).setBackground('#1a1a2e').setFontColor('#ffffff');

  const headers = ['Hora','Ticker','Lado','Cantidad','Precio','Importe','Estado'];
  sheet.getRange(2,1,1,7).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const token  = getToken_();
  const raw    = getTodayTrades_(token);
  const trades = parseTrades_(raw);

  if (!raw) {
    sheet.getRange(3,1).setValue('Sin datos — correr diagnosticarAPI() para verificar los endpoints.')
      .setFontColor('#cc2222');
    sheet.autoResizeColumns(1,7);
    return;
  }
  if (trades.length === 0) {
    sheet.getRange(3,1).setValue('Sin operaciones registradas hoy.').setFontColor('#aaaaaa');
    sheet.autoResizeColumns(1,7);
    return;
  }

  const rows = trades.map(t => [t.time, t.symbol, t.side, t.qty, t.price, t.amount, t.status]);
  sheet.getRange(3,1,rows.length,7).setValues(rows);
  sheet.getRange(3,5,rows.length,2).setNumberFormat('#,##0.00');

  for (let i = 0; i < rows.length; i++) {
    sheet.getRange(i+3,3)
      .setFontColor(rows[i][2] === 'COMPRA' ? '#00aa44' : '#e94560')
      .setFontWeight('bold');
  }

  sheet.autoResizeColumns(1,7);
}

// ============================================================
// HOJA: P&L DIARIO
// ============================================================
function actualizarPnL() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('PNL_DIARIO') || ss.insertSheet('PNL_DIARIO');
  sheet.clearContents();
  sheet.clearFormats();

  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy HH:mm');

  sheet.getRange(1,1).setValue('P&L DEL DÍA — ' + fecha)
    .setFontWeight('bold').setFontSize(14).setBackground('#1a1a2e').setFontColor('#ffffff');

  const token  = getToken_();
  const trades = parseTrades_(getTodayTrades_(token));
  const poses  = parsePositions_(getPositions_(token));

  // P&L realizado: cruza compras y ventas del día por ticker
  const tickerMap = {};
  for (const t of trades) {
    if (!tickerMap[t.symbol]) tickerMap[t.symbol] = { compras: [], ventas: [] };
    if (t.side === 'COMPRA') tickerMap[t.symbol].compras.push({ qty: t.qty, price: t.price });
    else                     tickerMap[t.symbol].ventas.push({ qty: t.qty, price: t.price });
  }

  let pnlRealizado = 0;
  const pnlDetalles = [];
  for (const [sym, ops] of Object.entries(tickerMap)) {
    const totalQtyC = ops.compras.reduce((s, o) => s + o.qty, 0);
    const totalQtyV = ops.ventas.reduce((s,  o) => s + o.qty, 0);
    const avgC = totalQtyC ? ops.compras.reduce((s, o) => s + o.price * o.qty, 0) / totalQtyC : 0;
    const avgV = totalQtyV ? ops.ventas.reduce((s,  o) => s + o.price * o.qty, 0) / totalQtyV : 0;
    const qMin = Math.min(totalQtyC, totalQtyV);
    const pnl  = qMin > 0 ? (avgV - avgC) * qMin : 0;
    pnlRealizado += pnl;
    if (qMin > 0) pnlDetalles.push([sym, qMin, avgC, avgV, pnl]);
  }

  // P&L no realizado: posiciones abiertas vs precio actual
  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  const pnlTotal = pnlRealizado + pnlNoReal;

  // Resumen ejecutivo (filas 2-6)
  sheet.getRange(2,1,1,2).setValues([['Métrica','Importe ($)']])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const resumen = [
    ['P&L Realizado hoy',                    pnlRealizado],
    ['P&L No Realizado (posiciones abiertas)', pnlNoReal],
    ['P&L TOTAL',                             pnlTotal],
    ['Operaciones del día',                   trades.length],
  ];
  sheet.getRange(3,1,resumen.length,2).setValues(resumen);
  sheet.getRange(3,2,3,1).setNumberFormat('#,##0.00');

  [[pnlRealizado,3],[pnlNoReal,4],[pnlTotal,5]].forEach(([val,row]) =>
    sheet.getRange(row,2).setFontColor(val >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold')
  );
  sheet.getRange(5,1,1,2).setBackground('#0d3b5e').setFontColor('#ffffff').setFontWeight('bold');

  // Detalle por ticker (fila 9+)
  if (pnlDetalles.length) {
    sheet.getRange(9,1).setValue('DETALLE REALIZADO POR TICKER')
      .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
    sheet.getRange(10,1,1,5).setValues([['Ticker','Contratos','Avg Compra','Avg Venta','P&L']])
      .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
    sheet.getRange(11,1,pnlDetalles.length,5).setValues(pnlDetalles);
    sheet.getRange(11,3,pnlDetalles.length,3).setNumberFormat('#,##0.00');
    for (let i = 0; i < pnlDetalles.length; i++)
      sheet.getRange(i+11,5).setFontColor(pnlDetalles[i][4] >= 0 ? '#00aa44' : '#cc2222');
  }

  sheet.autoResizeColumns(1,5);
}

// ============================================================
// HOJA: HISTORIAL (una fila por día, se acumula)
// ============================================================
function registrarHistorial() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('HISTORIAL') || ss.insertSheet('HISTORIAL');
  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy');

  if (sheet.getLastRow() === 0) {
    sheet.getRange(1,1,1,5)
      .setValues([['Fecha','P&L Realizado','P&L No Real.','P&L Total','Operaciones']])
      .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
    sheet.autoResizeColumns(1,5);
  }

  const token  = getToken_();
  const trades = parseTrades_(getTodayTrades_(token));
  const poses  = parsePositions_(getPositions_(token));

  const tickerMap = {};
  for (const t of trades) {
    if (!tickerMap[t.symbol]) tickerMap[t.symbol] = { compras: [], ventas: [] };
    if (t.side === 'COMPRA') tickerMap[t.symbol].compras.push({ qty: t.qty, price: t.price });
    else                     tickerMap[t.symbol].ventas.push({ qty: t.qty, price: t.price });
  }

  let pnlRealizado = 0;
  for (const ops of Object.values(tickerMap)) {
    const totalQtyC = ops.compras.reduce((s,o) => s + o.qty, 0);
    const totalQtyV = ops.ventas.reduce((s,o)  => s + o.qty, 0);
    const avgC = totalQtyC ? ops.compras.reduce((s,o) => s + o.price * o.qty, 0) / totalQtyC : 0;
    const avgV = totalQtyV ? ops.ventas.reduce((s,o)  => s + o.price * o.qty, 0) / totalQtyV : 0;
    const qMin = Math.min(totalQtyC, totalQtyV);
    if (qMin > 0) pnlRealizado += (avgV - avgC) * qMin;
  }

  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  const pnlTotal = pnlRealizado + pnlNoReal;
  const newRow   = [fecha, pnlRealizado, pnlNoReal, pnlTotal, trades.length];

  // Si ya existe una fila para hoy la pisa; si no, agrega al final
  const lastRow   = sheet.getLastRow();
  const fechaCol  = lastRow > 1 ? sheet.getRange(2,1,lastRow-1,1).getValues().flat() : [];
  const existIdx  = fechaCol.indexOf(fecha);
  const targetRow = existIdx >= 0 ? existIdx + 2 : lastRow + 1;

  sheet.getRange(targetRow,1,1,5).setValues([newRow]);
  sheet.getRange(targetRow,2,1,3).setNumberFormat('#,##0.00');
  sheet.getRange(targetRow,4).setFontColor(pnlTotal >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold');

  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Historial registrado: ' + fecha + ' | P&L Total: $' + pnlTotal.toFixed(2), '', 5
  );
}

// ============================================================
// DIAGNÓSTICO — correr UNA VEZ para encontrar los endpoints correctos
// ============================================================
function diagnosticarAPI() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('DIAGNOSTICO') || ss.insertSheet('DIAGNOSTICO');
  sheet.clearContents();
  sheet.clearFormats();

  sheet.getRange(1,1).setValue('DIAGNÓSTICO — ' + new Date().toLocaleString('es-AR'))
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(2,1,1,4)
    .setValues([['Endpoint','HTTP Status','Bytes respuesta','Respuesta (primeros 300 chars)']])
    .setFontWeight('bold').setBackground('#2a2a4e').setFontColor('#ffffff');

  const token = getToken_();
  const tz    = 'America/Argentina/Buenos_Aires';
  const today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');

  const candidates = [
    '/rest/portfolio/positions',
    '/rest/account/positions',
    '/rest/portfolio',
    '/rest/positions',
    `/rest/orders?dateFrom=${today}&dateTo=${today}`,
    `/rest/account/orders?dateFrom=${today}`,
    `/rest/trades?dateFrom=${today}`,
    '/rest/account/state',
    '/rest/account/balance',
    '/rest/account',
  ];

  const results = [];
  for (const ep of candidates) {
    try {
      const res  = UrlFetchApp.fetch(CONFIG.BASE_URL + ep, {
        headers: accountHeaders_(token),
        muteHttpExceptions: true
      });
      const code = res.getResponseCode();
      const body = res.getContentText();
      results.push([ep, code, body.length, body.substring(0, 300)]);
    } catch(e) {
      results.push([ep, 'ERROR', 0, e.message]);
    }
    Utilities.sleep(200);
  }

  sheet.getRange(3,1,results.length,4).setValues(results);
  for (let i = 0; i < results.length; i++) {
    const code = results[i][1];
    sheet.getRange(i+3,2).setFontColor(code === 200 ? '#00aa44' : '#cc2222').setFontWeight('bold');
  }
  sheet.autoResizeColumns(1,4);

  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Diagnóstico listo. Los que marcaron 200 (verde) son los endpoints válidos. ' +
    'Actualizá CONFIG.EP_POSITIONS y CONFIG.EP_ORDERS con los correctos.', '', 15
  );
}

// ============================================================
// ACTUALIZAR TODO (llamado automáticamente cada 5 min)
// ============================================================
function actualizarTodo() {
  try {
    actualizarPosiciones();
    actualizarOperaciones();
    actualizarPnL();
    SpreadsheetApp.getActiveSpreadsheet().toast('Datos actualizados ✓', '', 3);
  } catch(e) {
    SpreadsheetApp.getActiveSpreadsheet().toast('Error: ' + e.message, 'Error', 10);
  }
}

// ============================================================
// TRIGGERS — ejecutar UNA SOLA VEZ para activar la automatización
// ============================================================

// Actualiza POSICIONES, OPERACIONES y PNL_DIARIO cada 5 minutos
function activarAutoRefresh() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'actualizarTodo')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('actualizarTodo').timeBased().everyMinutes(5).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Auto-refresh activado (cada 5 min) ✓', '', 5);
}

// Guarda una fila en HISTORIAL a las 18:15 hora Argentina, todos los días
// IMPORTANTE: verificar que la timezone de tu cuenta Google sea America/Argentina/Buenos_Aires
function activarTriggerCierre() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'registrarHistorial')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('registrarHistorial').timeBased().atHour(18).nearMinute(15).everyDays(1).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Trigger de cierre activado (18:15 AR todos los días) ✓', '', 5);
}
