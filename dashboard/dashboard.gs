// ============================================================
// CONFIGURACIÓN — completá con tus credenciales de Cocos
// ============================================================
const CONFIG = {
  USERNAME:  'TU_USUARIO',
  PASSWORD:  'TU_CONTRASEÑA',
  COMITENTE: 'TU_NUMERO_COMITENTE',
  BASE_URL:  'https://api.cocos.xoms.com.ar',
  // Endpoints de cuenta — correr diagnosticarAPI() para confirmar cuáles funcionan
  EP_POSITIONS: '/rest/portfolio/positions',
  EP_ORDERS:    '/rest/orders',
};

// Futuros activos (actualizar cuando venzan los contratos)
const FUTUROS = [
  { symbol: 'DLR/JUN26',   vto: '30/06/2026' },
  { symbol: 'DLR/JUL26',   vto: '31/07/2026' },
  { symbol: 'DLR/AGO26',   vto: '29/08/2026' },
  { symbol: 'RFX20/JUN26', vto: '19/06/2026' },
  { symbol: 'RFX20/AGO26', vto: '21/08/2026' },
  { symbol: 'GGAL/JUN26',  vto: '30/06/2026' },
  { symbol: 'GGAL/AGO26',  vto: '29/08/2026' },
  { symbol: 'YPFD/JUN26',  vto: '30/06/2026' },
  { symbol: 'YPFD/AGO26',  vto: '29/08/2026' },
  { symbol: 'PAMP/JUN26',  vto: '30/06/2026' },
  { symbol: 'PAMP/AGO26',  vto: '29/08/2026' },
  { symbol: 'AL30/JUN26',  vto: '30/06/2026' },
];

const MERVAL_TICKERS = ['BBAR','BMA','CEPU','CRESY','EDN','GGAL','LOMA','PAM','SUPV','TEO','TGS','TX','YPF'];

// Pares de bonos para calcular MEP y CCL
const BONOS_DIVISAS = [
  { label: 'MEP (AL30)', ars: 'MERV - XMEV - AL30 - 24hs',  usd: 'MERV - XMEV - AL30D - 24hs' },
  { label: 'MEP (GD30)', ars: 'MERV - XMEV - GD30 - 24hs',  usd: 'MERV - XMEV - GD30D - CI'   },
  { label: 'CCL (AL30)', ars: 'MERV - XMEV - AL30 - CI',    usd: 'MERV - XMEV - AL30D - CI'   },
];

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
    throw new Error('Login fallido. Verificá usuario y contraseña.');
  const token = res.getHeaders()['x-auth-token'];
  if (!token) throw new Error('No se recibió token.');
  return token;
}

// Headers de cuenta comunes a todas las llamadas de cuenta
function accountHeaders_(token) {
  return {
    'X-Auth-Token':  token,
    'X-Account-Id':  CONFIG.COMITENTE,
    'X-Comitente-Id': CONFIG.COMITENTE,
  };
}

// ============================================================
// MARKET DATA
// ============================================================
function getMD_(symbol, marketId, token) {
  const url = CONFIG.BASE_URL + '/rest/marketdata/get?symbol='
            + encodeURIComponent(symbol) + '&marketId=' + marketId
            + '&entries=BI,OF,LA,CL,TV,OI&depth=1';
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

function getLA_(symbol, token) {
  const md = getMD_(symbol, 'ROFX', token);
  Utilities.sleep(80);
  return (md && md.marketData && md.marketData.LA) ? md.marketData.LA.price : null;
}

// Intenta ROFX primero, luego MERV (para posiciones mixtas)
function getCurrentPrice_(symbol, token) {
  let md = getMD_(symbol, 'ROFX', token);
  if (!md || !md.marketData || !md.marketData.LA)
    md = getMD_(symbol, 'MERV', token);
  Utilities.sleep(80);
  return (md && md.marketData && md.marketData.LA) ? md.marketData.LA.price : null;
}

// ============================================================
// ACCOUNT DATA — POSICIONES
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
    const qty    = Number(p.quantity   || p.qty       || p.size     || 0);
    const avg    = Number(p.avgCost    || p.averageCost|| p.precioProm || p.openingPrice || 0);
    const market = p.marketId || p.market || (symbol.includes('/') ? 'ROFX' : 'MERV');
    return { symbol, qty, avg, market };
  }).filter(p => p.symbol && p.qty !== 0);
}

// ============================================================
// ACCOUNT DATA — OPERACIONES DEL DÍA
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
    const qty     = Number(o.quantity  || o.qty  || o.size || 0);
    const price   = Number(o.price     || o.executedPrice || o.precio || 0);
    const amount  = Number(o.amount    || o.total || o.importe || (qty * price) || 0);
    const status  = o.status || o.estado || '';
    const rawTime = o.datetime || o.timestamp || o.fecha || o.time || '';
    let timeStr = '';
    if (rawTime) {
      try { timeStr = Utilities.formatDate(new Date(rawTime), 'America/Argentina/Buenos_Aires', 'HH:mm:ss'); }
      catch(e) { timeStr = rawTime.toString().substring(11, 19) || rawTime; }
    }
    return { symbol, side: sideStr, qty, price, amount, status, time: timeStr };
  }).filter(o => o.symbol);
}

// ============================================================
// FUTUROS + DIVISAS (misma hoja)
// ============================================================
function actualizarFuturos() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('FUTUROS') || ss.insertSheet('FUTUROS');
  sheet.clearContents();
  sheet.clearFormats();

  const token = getToken_();

  // — Sección DIVISAS (filas 1-5) —
  sheet.getRange(1,1).setValue('DÓLAR').setFontWeight('bold').setFontSize(12);
  sheet.getRange(1,6).setValue('Actualizado: ' + new Date().toLocaleTimeString('es-AR'));

  const divHeaders = ['Indicador', 'ARS', 'USD', 'Tipo de cambio'];
  sheet.getRange(2,1,1,4).setValues([divHeaders])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const divRows = [];
  for (const b of BONOS_DIVISAS) {
    const pARS = getLA_(b.ars, token);
    const pUSD = getLA_(b.usd, token);
    const tc   = (pARS && pUSD && pUSD !== 0) ? pARS / pUSD : '';
    divRows.push([b.label, pARS || '—', pUSD || '—', tc]);
  }
  sheet.getRange(3,1,divRows.length,4).setValues(divRows);
  sheet.getRange(3,4,divRows.length,1)
    .setNumberFormat('$#,##0.00').setFontWeight('bold').setFontColor('#00aa44');

  // — Sección FUTUROS (fila 7+) —
  const futHeaders = ['Ticker','Compra (BI)','Último (LA)','Venta (OF)','Var%','Volumen','Int. Abierto','Vto'];
  sheet.getRange(7,1,1,8).setValues([futHeaders])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const rows = [];
  for (const fut of FUTUROS) {
    const md = getMD_(fut.symbol, 'ROFX', token);
    if (md && md.marketData) {
      const m    = md.marketData;
      const bi   = m.BI ? m.BI[0].price : '';
      const of_  = m.OF ? m.OF[0].price : '';
      const la   = m.LA ? m.LA.price    : '';
      const cl   = m.CL ? m.CL.price    : '';
      const varP = (la !== '' && cl && cl !== 0) ? (la - cl) / cl : '';
      const vol  = m.TV ? m.TV.price    : '';
      const oi   = m.OI ? m.OI.price    : '';
      rows.push([fut.symbol, bi, la, of_, varP, vol, oi, fut.vto]);
    } else {
      rows.push([fut.symbol,'—','—','—','—','—','—', fut.vto]);
    }
    Utilities.sleep(80);
  }

  sheet.getRange(8,1,rows.length,8).setValues(rows);
  sheet.getRange(8,5,rows.length,1).setNumberFormat('0.00%');

  for (let i = 0; i < rows.length; i++) {
    const val = rows[i][4];
    if (typeof val === 'number')
      sheet.getRange(i+8,5).setFontColor(val >= 0 ? '#00aa44' : '#cc2222');
  }

  const rfxRow = rows.findIndex(r => r[0] === 'RFX20/JUN26');
  if (rfxRow >= 0)
    sheet.getRange(rfxRow+8,1,1,8).setBackground('#0d3b5e').setFontColor('#ffffff');

  sheet.autoResizeColumns(1,8);
}

// ============================================================
// MERVAL
// ============================================================
function actualizarMerval() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('MERVAL') || ss.insertSheet('MERVAL');
  sheet.clearContents();

  const headers = ['Ticker','Compra','Venta','Último','Var%','Volumen'];
  sheet.getRange(1,1,1,6).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const token = getToken_();
  const rows  = [];

  for (const ticker of MERVAL_TICKERS) {
    const md = getMD_(ticker, 'MERV', token);
    if (md && md.marketData) {
      const m    = md.marketData;
      const bi   = m.BI ? m.BI[0].price : '';
      const of_  = m.OF ? m.OF[0].price : '';
      const la   = m.LA ? m.LA.price    : '';
      const cl   = m.CL ? m.CL.price    : '';
      const varP = (la !== '' && cl && cl !== 0) ? (la - cl) / cl : '';
      const vol  = m.TV ? m.TV.price    : '';
      rows.push([ticker, bi, of_, la, varP, vol]);
    } else {
      rows.push([ticker,'—','—','—','—','—']);
    }
    Utilities.sleep(80);
  }

  sheet.getRange(2,1,rows.length,6).setValues(rows);
  sheet.getRange(2,5,rows.length,1).setNumberFormat('0.00%');
  for (let i = 0; i < rows.length; i++) {
    const val = rows[i][4];
    if (typeof val === 'number')
      sheet.getRange(i+2,5).setFontColor(val >= 0 ? '#00aa44' : '#cc2222');
  }
  sheet.autoResizeColumns(1,6);
}

// ============================================================
// POSICIONES ABIERTAS
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
    .setFontWeight('bold').setFontSize(13).setFontColor('#ffffff').setBackground('#1a1a2e');
  sheet.getRange(1,7).setValue('Actualizado: ' + new Date().toLocaleTimeString('es-AR'))
    .setFontColor('#aaaaaa');

  const headers = ['Ticker','Mercado','Cantidad','Precio Prom.','Precio Actual','Var$','P&L No Real.','P&L%'];
  sheet.getRange(2,1,1,8).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  if (!raw) {
    sheet.getRange(3,1).setValue(
      'Sin datos — correr diagnosticarAPI() para verificar los endpoints de cuenta.'
    ).setFontColor('#cc2222');
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
    const val = rows[i][5];
    const color = (typeof val === 'number' && val >= 0) ? '#00aa44' : '#cc2222';
    sheet.getRange(i+3,6).setFontColor(color);
    sheet.getRange(i+3,7).setFontColor(color);
    sheet.getRange(i+3,8).setFontColor(color);
  }

  // Fila de total
  const totalRow = poses.length + 3;
  sheet.getRange(totalRow,1,1,8).setBackground('#0d3b5e').setFontColor('#ffffff').setFontWeight('bold');
  sheet.getRange(totalRow,1).setValue('TOTAL');
  sheet.getRange(totalRow,7).setValue(totalPnl).setNumberFormat('#,##0.00')
    .setFontColor(totalPnl >= 0 ? '#00aa44' : '#cc2222');

  sheet.autoResizeColumns(1,8);
}

// ============================================================
// OPERACIONES DEL DÍA
// ============================================================
function actualizarOperaciones() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('OPERACIONES') || ss.insertSheet('OPERACIONES');
  sheet.clearContents();
  sheet.clearFormats();

  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy');

  sheet.getRange(1,1).setValue('OPERACIONES DEL DÍA — ' + fecha)
    .setFontWeight('bold').setFontSize(13).setFontColor('#ffffff').setBackground('#1a1a2e');

  const headers = ['Hora','Ticker','Lado','Cantidad','Precio','Importe','Estado'];
  sheet.getRange(2,1,1,7).setValues([headers])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');

  const token  = getToken_();
  const raw    = getTodayTrades_(token);
  const trades = parseTrades_(raw);

  if (!raw) {
    sheet.getRange(3,1).setValue(
      'Sin datos — correr diagnosticarAPI() para verificar los endpoints de cuenta.'
    ).setFontColor('#cc2222');
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
    const lado = rows[i][2];
    sheet.getRange(i+3,3).setFontColor(lado === 'COMPRA' ? '#00aa44' : '#e94560').setFontWeight('bold');
  }

  sheet.autoResizeColumns(1,7);
}

// ============================================================
// P&L DIARIO
// ============================================================
function actualizarPnL() {
  const ss  = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('PNL_DIARIO') || ss.insertSheet('PNL_DIARIO');
  sheet.clearContents();
  sheet.clearFormats();

  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy HH:mm');

  sheet.getRange(1,1).setValue('P&L — ' + fecha)
    .setFontWeight('bold').setFontSize(14).setFontColor('#ffffff').setBackground('#1a1a2e');

  const token  = getToken_();
  const trades = parseTrades_(getTodayTrades_(token));
  const poses  = parsePositions_(getPositions_(token));

  // P&L realizado: suma de trades cerrados del día
  // Lógica: VENTA(precio) - COMPRA(precio) × cantidad, agrupado por ticker
  const tickerMap = {};
  for (const t of trades) {
    if (!tickerMap[t.symbol]) tickerMap[t.symbol] = { compras: [], ventas: [] };
    if (t.side === 'COMPRA') tickerMap[t.symbol].compras.push({ qty: t.qty, price: t.price });
    else                     tickerMap[t.symbol].ventas.push({ qty: t.qty, price: t.price });
  }

  let pnlRealizado = 0;
  const pnlDetalles = [];
  for (const [sym, ops] of Object.entries(tickerMap)) {
    const avgCompra = ops.compras.length
      ? ops.compras.reduce((s,o) => s + o.price * o.qty, 0) / ops.compras.reduce((s,o) => s + o.qty, 0)
      : 0;
    const avgVenta = ops.ventas.length
      ? ops.ventas.reduce((s,o) => s + o.price * o.qty, 0) / ops.ventas.reduce((s,o) => s + o.qty, 0)
      : 0;
    const qtyMin = Math.min(
      ops.compras.reduce((s,o) => s + o.qty, 0),
      ops.ventas.reduce((s,o)  => s + o.qty, 0)
    );
    const pnl = qtyMin > 0 ? (avgVenta - avgCompra) * qtyMin : 0;
    pnlRealizado += pnl;
    if (qtyMin > 0) pnlDetalles.push([sym, qtyMin, avgCompra, avgVenta, pnl]);
  }

  // P&L no realizado: posiciones abiertas vs. precio actual
  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  // Resumen
  const pnlTotal = pnlRealizado + pnlNoReal;
  const resumen  = [
    ['Métrica', 'Importe ($)'],
    ['P&L Realizado hoy', pnlRealizado],
    ['P&L No Realizado (posiciones abiertas)', pnlNoReal],
    ['P&L TOTAL', pnlTotal],
    ['Operaciones del día', trades.length],
  ];

  sheet.getRange(2,1,1,2).setValues([resumen[0]])
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(3,1,resumen.length-1,2).setValues(resumen.slice(1));
  sheet.getRange(3,2,resumen.length-2,1).setNumberFormat('#,##0.00');

  // Colores P&L
  [[pnlRealizado,3],[pnlNoReal,4],[pnlTotal,5]].forEach(([val,row]) => {
    sheet.getRange(row,2).setFontColor(val >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold');
  });
  sheet.getRange(5,1,1,2).setBackground('#0d3b5e').setFontColor('#ffffff').setFontWeight('bold');

  // Detalle por ticker si hubo operaciones cerradas
  if (pnlDetalles.length) {
    sheet.getRange(8,1).setValue('DETALLE REALIZADO POR TICKER')
      .setFontWeight('bold').setFontColor('#ffffff').setBackground('#1a1a2e');
    sheet.getRange(9,1,1,5).setValues([['Ticker','Contratos','Avg Compra','Avg Venta','P&L']])
      .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
    sheet.getRange(10,1,pnlDetalles.length,5).setValues(pnlDetalles);
    sheet.getRange(10,3,pnlDetalles.length,3).setNumberFormat('#,##0.00');
    for (let i = 0; i < pnlDetalles.length; i++) {
      const val = pnlDetalles[i][4];
      sheet.getRange(i+10,5).setFontColor(val >= 0 ? '#00aa44' : '#cc2222');
    }
  }

  sheet.autoResizeColumns(1,5);
}

// ============================================================
// HISTORIAL (acumula una fila por día)
// ============================================================
function registrarHistorial() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('HISTORIAL') || ss.insertSheet('HISTORIAL');
  const tz    = 'America/Argentina/Buenos_Aires';
  const fecha = Utilities.formatDate(new Date(), tz, 'dd/MM/yyyy');

  // Crear encabezados si la hoja está vacía
  if (sheet.getLastRow() === 0) {
    const h = ['Fecha','P&L Realizado','P&L No Real.','P&L Total','Operaciones'];
    sheet.getRange(1,1,1,5).setValues([h])
      .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
    sheet.autoResizeColumns(1,5);
  }

  // Calcular P&L actual
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
    const avgC = ops.compras.length
      ? ops.compras.reduce((s,o) => s + o.price * o.qty, 0) / ops.compras.reduce((s,o) => s + o.qty, 0) : 0;
    const avgV = ops.ventas.length
      ? ops.ventas.reduce((s,o) => s + o.price * o.qty, 0) / ops.ventas.reduce((s,o) => s + o.qty, 0) : 0;
    const qMin = Math.min(
      ops.compras.reduce((s,o) => s + o.qty, 0),
      ops.ventas.reduce((s,o)  => s + o.qty, 0)
    );
    if (qMin > 0) pnlRealizado += (avgV - avgC) * qMin;
  }

  let pnlNoReal = 0;
  for (const p of poses) {
    const cur = getCurrentPrice_(p.symbol, token);
    if (cur && p.avg) pnlNoReal += (cur - p.avg) * p.qty;
  }

  const pnlTotal = pnlRealizado + pnlNoReal;

  // Buscar si ya existe una fila para hoy y actualizarla, si no agregar
  const lastRow  = sheet.getLastRow();
  const fechaCol = lastRow > 1 ? sheet.getRange(2,1,lastRow-1,1).getValues().flat() : [];
  const existing = fechaCol.indexOf(fecha);

  const newRow = [fecha, pnlRealizado, pnlNoReal, pnlTotal, trades.length];
  if (existing >= 0) {
    sheet.getRange(existing+2,1,1,5).setValues([newRow]);
  } else {
    sheet.getRange(lastRow+1,1,1,5).setValues([newRow]);
  }

  // Colorear columna P&L Total
  const targetRow = existing >= 0 ? existing+2 : lastRow+1;
  sheet.getRange(targetRow,2,1,3).setNumberFormat('#,##0.00');
  sheet.getRange(targetRow,4).setFontColor(pnlTotal >= 0 ? '#00aa44' : '#cc2222').setFontWeight('bold');

  SpreadsheetApp.getActiveSpreadsheet().toast('Historial registrado: ' + fecha + ' — P&L Total: $' + pnlTotal.toFixed(2), '', 5);
}

// ============================================================
// DIAGNÓSTICO DE API — correr una vez para encontrar los endpoints correctos
// ============================================================
function diagnosticarAPI() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  let sheet   = ss.getSheetByName('DIAGNOSTICO') || ss.insertSheet('DIAGNOSTICO');
  sheet.clearContents();
  sheet.clearFormats();

  sheet.getRange(1,1).setValue('DIAGNÓSTICO DE API — ' + new Date().toLocaleString('es-AR'))
    .setFontWeight('bold').setBackground('#1a1a2e').setFontColor('#ffffff');
  sheet.getRange(2,1,1,4).setValues([['Endpoint','HTTP Status','Tamaño (bytes)','Respuesta (primeros 300 chars)']])
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
      results.push([ep, code, body.length, body.substring(0,300)]);
    } catch(e) {
      results.push([ep, 'ERROR', 0, e.message]);
    }
    Utilities.sleep(200);
  }

  sheet.getRange(3,1,results.length,4).setValues(results);

  // Colorear OK vs error
  for (let i = 0; i < results.length; i++) {
    const code = results[i][1];
    sheet.getRange(i+3,2).setFontColor(code === 200 ? '#00aa44' : '#cc2222').setFontWeight('bold');
  }

  sheet.autoResizeColumns(1,4);
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Diagnóstico completado. Buscá los endpoints que devuelvan 200 y actualizá CONFIG.EP_POSITIONS y CONFIG.EP_ORDERS.', '', 10
  );
}

// ============================================================
// ACTUALIZAR TODO
// ============================================================
function actualizarTodo() {
  try {
    actualizarFuturos();
    actualizarMerval();
    actualizarPosiciones();
    actualizarOperaciones();
    actualizarPnL();
    SpreadsheetApp.getActiveSpreadsheet().toast('Datos actualizados ✓', '', 3);
  } catch(e) {
    SpreadsheetApp.getActiveSpreadsheet().toast('Error: ' + e.message, 'Error', 10);
  }
}

// ============================================================
// AUTO-REFRESH cada 5 minutos + trigger de cierre 18:15 AR
// ============================================================
function activarAutoRefresh() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('actualizarTodo').timeBased().everyMinutes(5).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Auto-refresh activado (cada 5 min) ✓', '', 5);
}

// Registra el historial del día a las 18:15 hora Argentina (UTC-3 = 21:15 UTC)
// Nota: Apps Script usa la timezone de la cuenta Google. Verificar que esté en America/Argentina/Buenos_Aires.
function activarTriggerCierre() {
  // Eliminar triggers de cierre existentes para no duplicar
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'registrarHistorial')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('registrarHistorial').timeBased().atHour(18).nearMinute(15).everyDays(1).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Trigger de cierre activado (18:15 AR cada día) ✓', '', 5);
}
