// ============================================================
// DASHBOARD DE CUENTA — Posiciones, Operaciones y P&L
// Cocos Capital / Matriz — ROFEX Futuros
// ============================================================

const CONFIG = {
  USERNAME:     'TU_USUARIO',   // mismo usuario que usás en Matriz
  PASSWORD:     'TU_CONTRASEÑA', // misma contraseña
  API_BASE:     'https://api.cocos.xoms.com.ar',      // auth + market data
  MATRIZ_BASE:  'https://matriz.cocos.xoms.com.ar',   // datos de cuenta
  ACCOUNT_NAME: '370111',                              // nombre de cuenta
};

// ============================================================
// AUTH — dos capas: token para market data, cookie para Matriz
// ============================================================
function getToken_() {
  const res = UrlFetchApp.fetch(CONFIG.API_BASE + '/auth/getToken', {
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

// Obtiene la cookie _mtz_web_key para las llamadas a matriz.cocos.xoms.com.ar
function getMatrizCookie_() {
  // Intento 1: login directo en Matriz con credenciales
  const loginEndpoints = [
    { url: CONFIG.MATRIZ_BASE + '/api/v2/auth/sign_in',
      body: JSON.stringify({ email: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
    { url: CONFIG.MATRIZ_BASE + '/api/v2/sessions',
      body: JSON.stringify({ username: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
    { url: CONFIG.MATRIZ_BASE + '/api/v2/auth',
      body: JSON.stringify({ username: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
  ];

  for (const ep of loginEndpoints) {
    try {
      const res = UrlFetchApp.fetch(ep.url, {
        method: 'post',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        payload: ep.body,
        muteHttpExceptions: true,
        followRedirects: false,
      });
      // Buscar la cookie en los headers de respuesta
      const headers = res.getAllHeaders();
      const setCookie = headers['Set-Cookie'] || headers['set-cookie'];
      if (setCookie) {
        const cookies = Array.isArray(setCookie) ? setCookie : [setCookie];
        for (const c of cookies) {
          if (c.includes('_mtz_web_key')) {
            const match = c.match(/_mtz_web_key=([^;]+)/);
            if (match) return '_mtz_web_key=' + match[1];
          }
        }
      }
    } catch(e) {}
    Utilities.sleep(200);
  }
  return null;
}

function matrizHeaders_(cookie) {
  return {
    'Accept':          'application/json, text/plain, */*',
    'Accept-Language': 'es-AR,es;q=0.9',
    'Cookie':          cookie || '',
  };
}

// ============================================================
// PRECIO ACTUAL para P&L no realizado (market data vía API original)
// ============================================================
function getMD_(symbol, marketId, token) {
  const url = CONFIG.API_BASE + '/rest/marketdata/get?symbol='
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
  let md = getMD_(symbol, 'ROFX', token);
  if (!md || !md.marketData || !md.marketData.LA)
    md = getMD_(symbol, 'MERV', token);
  Utilities.sleep(80);
  return (md && md.marketData && md.marketData.LA) ? md.marketData.LA.price : null;
}

// ============================================================
// DATOS DE CUENTA — POSICIONES
// ============================================================
function getPositions_(cookie) {
  if (!cookie) return null;
  const ds  = Date.now() + '-' + Math.floor(Math.random() * 999999);
  const url = CONFIG.MATRIZ_BASE + '/api/v2/accounts/' + CONFIG.ACCOUNT_NAME
            + '/positions?_ds=' + ds;
  const res = UrlFetchApp.fetch(url, {
    headers: matrizHeaders_(cookie),
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) return null;
  try { return JSON.parse(res.getContentText()); } catch(e) { return null; }
}

function parsePositions_(json) {
  if (!json) return [];
  const arr = json.positions || json.data || json.items
           || (Array.isArray(json) ? json : null);
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map(p => {
    const symbol = p.symbol || p.ticker || p.instrument
                || (p.security && p.security.symbol) || '';
    const qty    = Number(p.quantity  || p.qty    || p.size   || 0);
    const avg    = Number(p.avgCost   || p.avgPrice || p.averageCost
                       || p.openPrice || p.costBasis || 0);
    const market = p.marketId || p.market
                || (symbol.includes('/') ? 'ROFX' : 'MERV');
    return { symbol, qty, avg, market };
  }).filter(p => p.symbol && p.qty !== 0);
}

// ============================================================
// DATOS DE CUENTA — OPERACIONES DEL DÍA (endpoint "report")
// ============================================================
function getTodayTrades_(cookie) {
  if (!cookie) return null;
  const ds  = Date.now() + '-' + Math.floor(Math.random() * 999999);
  const url = CONFIG.MATRIZ_BASE + '/api/v2/accounts/' + CONFIG.ACCOUNT_NAME
            + '/report?_ds=' + ds;
  const res = UrlFetchApp.fetch(url, {
    headers: matrizHeaders_(cookie),
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) return null;
  try { return JSON.parse(res.getContentText()); } catch(e) { return null; }
}

function parseTrades_(json) {
  if (!json) return [];
  const arr = json.orders  || json.trades || json.report
           || json.data    || json.items
           || (Array.isArray(json) ? json : null);
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map(o => {
    const symbol  = o.symbol || o.ticker || o.instrument
                 || (o.security && o.security.symbol) || '';
    const side    = (o.side || o.type || o.operationType || '').toString().toUpperCase();
    const sideStr = (side === 'BUY' || side === 'C' || side === 'COMPRA') ? 'COMPRA' : 'VENTA';
    const qty     = Number(o.quantity || o.qty || o.size  || 0);
    const price   = Number(o.price    || o.executedPrice  || o.avgPrice || 0);
    const amount  = Number(o.amount   || o.total || o.notional || qty * price || 0);
    const status  = o.status || o.state || '';
    const rawTime = o.datetime || o.timestamp || o.date || o.createdAt || '';
    let timeStr   = '';
    if (rawTime) {
      try { timeStr = Utilities.formatDate(new Date(rawTime), 'America/Argentina/Buenos_Aires', 'HH:mm:ss'); }
      catch(e) { timeStr = String(rawTime).substring(11,19) || String(rawTime); }
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

  const token  = getToken_();
  const cookie = getMatrizCookie_();
  const raw    = getPositions_(cookie);
  const poses  = parsePositions_(raw);

  sheet.getRange(1,1).setValue('POSICIONES ABIERTAS')
    .setFontWeight('bold').setFontSize(13).setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(1,7).setValue('Actualizado: ' + new Date().toLocaleTimeString('es-AR'))
    .setFontColor('#aaaaaa');

  const headers = ['Ticker','Mercado','Cantidad','Precio Prom.','Precio Actual','Var$','P&L No Real.','P&L%'];
  sheet.getRange(2,1,1,8).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  if (!cookie) {
    sheet.getRange(3,1).setValue('No se pudo obtener sesión de Matriz — correr diagnosticarAuth().')
      .setFontColor('#cc2222');
    sheet.autoResizeColumns(1,8);
    return;
  }
  if (!raw) {
    sheet.getRange(3,1).setValue('Sin respuesta del endpoint de posiciones.')
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

  const cookie = getMatrizCookie_();
  const raw    = getTodayTrades_(cookie);
  const trades = parseTrades_(raw);

  if (!cookie || !raw) {
    sheet.getRange(3,1).setValue('Sin sesión de Matriz — correr diagnosticarAuth().')
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
  const cookie = getMatrizCookie_();
  const trades = parseTrades_(getTodayTrades_(cookie));
  const poses  = parsePositions_(getPositions_(cookie));

  const tickerMap = {};
  for (const t of trades) {
    if (!tickerMap[t.symbol]) tickerMap[t.symbol] = { compras: [], ventas: [] };
    if (t.side === 'COMPRA') tickerMap[t.symbol].compras.push({ qty: t.qty, price: t.price });
    else                     tickerMap[t.symbol].ventas.push({ qty: t.qty, price: t.price });
  }

  let pnlRealizado = 0;
  const pnlDetalles = [];
  for (const [sym, ops] of Object.entries(tickerMap)) {
    const totalQtyC = ops.compras.reduce((s,o) => s + o.qty, 0);
    const totalQtyV = ops.ventas.reduce((s,o)  => s + o.qty, 0);
    const avgC = totalQtyC ? ops.compras.reduce((s,o) => s + o.price*o.qty, 0) / totalQtyC : 0;
    const avgV = totalQtyV ? ops.ventas.reduce((s,o)  => s + o.price*o.qty, 0) / totalQtyV : 0;
    const qMin = Math.min(totalQtyC, totalQtyV);
    const pnl  = qMin > 0 ? (avgV - avgC) * qMin : 0;
    pnlRealizado += pnl;
    if (qMin > 0) pnlDetalles.push([sym, qMin, avgC, avgV, pnl]);
  }

  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  const pnlTotal = pnlRealizado + pnlNoReal;

  sheet.getRange(2,1,1,2).setValues([['Métrica','Importe ($)']])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const resumen = [
    ['P&L Realizado hoy',                     pnlRealizado],
    ['P&L No Realizado (posiciones abiertas)', pnlNoReal],
    ['P&L TOTAL',                              pnlTotal],
    ['Operaciones del día',                    trades.length],
  ];
  sheet.getRange(3,1,resumen.length,2).setValues(resumen);
  sheet.getRange(3,2,3,1).setNumberFormat('#,##0.00');

  [[pnlRealizado,3],[pnlNoReal,4],[pnlTotal,5]].forEach(([val,row]) =>
    sheet.getRange(row,2).setFontColor(val >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold')
  );
  sheet.getRange(5,1,1,2).setBackground('#0d3b5e').setFontColor('#ffffff').setFontWeight('bold');

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
// HOJA: HISTORIAL
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
  const cookie = getMatrizCookie_();
  const trades = parseTrades_(getTodayTrades_(cookie));
  const poses  = parsePositions_(getPositions_(cookie));

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
    const avgC = totalQtyC ? ops.compras.reduce((s,o) => s + o.price*o.qty, 0) / totalQtyC : 0;
    const avgV = totalQtyV ? ops.ventas.reduce((s,o)  => s + o.price*o.qty, 0) / totalQtyV : 0;
    const qMin = Math.min(totalQtyC, totalQtyV);
    if (qMin > 0) pnlRealizado += (avgV - avgC) * qMin;
  }

  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  const pnlTotal  = pnlRealizado + pnlNoReal;
  const newRow    = [fecha, pnlRealizado, pnlNoReal, pnlTotal, trades.length];
  const lastRow   = sheet.getLastRow();
  const fechaCol  = lastRow > 1 ? sheet.getRange(2,1,lastRow-1,1).getValues().flat() : [];
  const existIdx  = fechaCol.indexOf(fecha);
  const targetRow = existIdx >= 0 ? existIdx + 2 : lastRow + 1;

  sheet.getRange(targetRow,1,1,5).setValues([newRow]);
  sheet.getRange(targetRow,2,1,3).setNumberFormat('#,##0.00');
  sheet.getRange(targetRow,4).setFontColor(pnlTotal >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold');

  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Historial: ' + fecha + ' | P&L Total: $' + pnlTotal.toFixed(2), '', 5
  );
}

// ============================================================
// DIAGNÓSTICO DE AUTH — correr si las hojas muestran error de sesión
// ============================================================
function diagnosticarAuth() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('DIAGNOSTICO') || ss.insertSheet('DIAGNOSTICO');
  sheet.clearContents();
  sheet.clearFormats();

  sheet.getRange(1,1).setValue('DIAGNÓSTICO AUTH — ' + new Date().toLocaleString('es-AR'))
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(2,1,1,4).setValues([['Paso','Status','Detalle','']])
    .setFontWeight('bold').setBackground('#2a2a4e').setFontColor('#ffffff');

  const results = [];

  // Paso 1: token API
  let token = null;
  try {
    token = getToken_();
    results.push(['1. Token API (api.cocos.xoms.com.ar)', 'OK', token.substring(0,40) + '...', '']);
  } catch(e) {
    results.push(['1. Token API', 'ERROR', e.message, '']);
  }

  // Paso 2: intentos de login en Matriz
  const loginAttempts = [
    { label: '2a. POST /api/v2/auth/sign_in',
      url: CONFIG.MATRIZ_BASE + '/api/v2/auth/sign_in',
      body: JSON.stringify({ email: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
    { label: '2b. POST /api/v2/sessions',
      url: CONFIG.MATRIZ_BASE + '/api/v2/sessions',
      body: JSON.stringify({ username: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
    { label: '2c. POST /api/v2/auth',
      url: CONFIG.MATRIZ_BASE + '/api/v2/auth',
      body: JSON.stringify({ username: CONFIG.USERNAME, password: CONFIG.PASSWORD }) },
  ];

  for (const att of loginAttempts) {
    try {
      const res     = UrlFetchApp.fetch(att.url, {
        method: 'post',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        payload: att.body,
        muteHttpExceptions: true,
        followRedirects: false,
      });
      const code    = res.getResponseCode();
      const headers = res.getAllHeaders();
      const cookie  = headers['Set-Cookie'] || headers['set-cookie'] || 'none';
      const body    = res.getContentText().substring(0, 150);
      results.push([att.label, code, 'Cookie: ' + JSON.stringify(cookie).substring(0,80), body]);
    } catch(e) {
      results.push([att.label, 'ERROR', e.message, '']);
    }
    Utilities.sleep(300);
  }

  // Paso 3: probar endpoints de Matriz con el token existente como Bearer
  if (token) {
    const ds  = Date.now();
    const url = CONFIG.MATRIZ_BASE + '/api/v2/accounts/' + CONFIG.ACCOUNT_NAME + '/positions?_ds=' + ds;
    try {
      const res  = UrlFetchApp.fetch(url, {
        headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' },
        muteHttpExceptions: true
      });
      const code = res.getResponseCode();
      const body = res.getContentText().substring(0, 200);
      results.push(['3. positions con Bearer token', code, body, '']);
    } catch(e) {
      results.push(['3. positions con Bearer token', 'ERROR', e.message, '']);
    }
  }

  sheet.getRange(3,1,results.length,4).setValues(results);
  for (let i = 0; i < results.length; i++) {
    const ok = results[i][1] === 'OK' || results[i][1] === 200;
    sheet.getRange(i+3,2).setFontColor(ok ? '#00aa44' : '#cc2222').setFontWeight('bold');
  }
  sheet.autoResizeColumns(1,4);
  SpreadsheetApp.getActiveSpreadsheet().toast('Diagnóstico auth listo.', '', 5);
}

// ============================================================
// ACTUALIZAR TODO
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
// TRIGGERS
// ============================================================
function activarAutoRefresh() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'actualizarTodo')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('actualizarTodo').timeBased().everyMinutes(5).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Auto-refresh activado (cada 5 min) ✓', '', 5);
}

function activarTriggerCierre() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'registrarHistorial')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('registrarHistorial').timeBased().atHour(18).nearMinute(15).everyDays(1).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Trigger de cierre activado (18:15 AR) ✓', '', 5);
}
