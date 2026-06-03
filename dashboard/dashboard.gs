// ============================================================
// CONFIGURACIÓN — completá con tus credenciales de Cocos
// ============================================================
const CONFIG = {
  USERNAME: 'TU_USUARIO',
  PASSWORD: 'TU_CONTRASEÑA',
  BASE_URL: 'https://api.cocos.xoms.com.ar'
};

// Futuros activos (actualizar cuando venzan los contratos)
const FUTUROS = [
  { symbol: 'DLR/JUN26',  vto: '30/06/2026' },
  { symbol: 'DLR/JUL26',  vto: '31/07/2026' },
  { symbol: 'DLR/AGO26',  vto: '29/08/2026' },
  { symbol: 'RFX20/JUN26', vto: '19/06/2026' },
  { symbol: 'RFX20/AGO26', vto: '21/08/2026' },
  { symbol: 'GGAL/JUN26', vto: '30/06/2026' },
  { symbol: 'GGAL/AGO26', vto: '29/08/2026' },
  { symbol: 'YPFD/JUN26', vto: '30/06/2026' },
  { symbol: 'YPFD/AGO26', vto: '29/08/2026' },
  { symbol: 'PAMP/JUN26', vto: '30/06/2026' },
  { symbol: 'PAMP/AGO26', vto: '29/08/2026' },
  { symbol: 'AL30/JUN26', vto: '30/06/2026' },
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
// ACTUALIZAR TODO
// ============================================================
function actualizarTodo() {
  try {
    actualizarFuturos();
    actualizarMerval();
    SpreadsheetApp.getActiveSpreadsheet().toast('Datos actualizados ✓', '', 3);
  } catch(e) {
    SpreadsheetApp.getActiveSpreadsheet().toast('Error: ' + e.message, 'Error', 10);
  }
}

// ============================================================
// AUTO-REFRESH cada 5 minutos (ejecutar una sola vez)
// ============================================================
function activarAutoRefresh() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('actualizarTodo').timeBased().everyMinutes(5).create();
  SpreadsheetApp.getActiveSpreadsheet().toast('Auto-refresh activado (cada 5 min) ✓', '', 5);
}
