# -*- coding: utf-8 -*-
"""
Datos extraidos de:
  Fresia_SAAG_Estados_Contables_2026_formato_uniforme_con_Anexo_II_FINAL_v21 (1).pdf

REGLA DE ORO: todos los importes se almacenan como CADENAS DE TEXTO, exactamente
como figuran en el PDF original. No se parsean a numero, no se recalculan, no se
redondean y no se reformatean. El generador solo los ubica en la grilla.

Las notas al pie (2) y (3) del Anexo II se recuperan de la version v14 del mismo
documento: en v19/v21 los marcadores "(2)" y "(3)" quedaron en el cuadro pero el
texto que los explica se habia perdido.
"""

EMPRESA = "FRESIA S.A. A.G."
SUB_COMP = "Por el ejercicio finalizado el 31 de enero de 2026 comparativo con el ejercicio anterior"
SUB_SIMPLE = "Por el ejercicio finalizado el 31 de enero de 2026"

PIE_NOTAS = ("Las notas 1 a 6 adjuntas y los anexos I, II, III, IV, V, VI y VII "
             "forman parte integrante de estos Estados Contables.")
PIE_DICTAMEN = "DICTAMEN PROFESIONAL POR SEPARADO DE FECHA 05/06/2026"

FIRMAS = [
    ("IGNACIO MACKEY", "Presidente"),
    ("MARIELA RUZZI", "Síndico Titular"),
    ("", "Contador Público"),
]

# --------------------------------------------------------------------------
# ANEXO I - INVERSIONES FINANCIERAS
# --------------------------------------------------------------------------
ANEXO_I = {
    "anexo": "ANEXO I",
    "titulo": "INVERSIONES FINANCIERAS",
    "subtitulo": SUB_COMP,
    "concept_width": "58%",
    "head": [
        [("", 1, "concept"), ("2026", 1, "num"), ("2025", 1, "num")],
    ],
    "rows": [
        ("head", "INVERSIONES CORRIENTES", []),
        ("data", "Fondos comunes de inversión", ["47.586.832,40", "107.331.521,96"]),
        ("data", "Obligaciones negociables", ["-", "2.251.795,07"]),
        ("data", "Bonos", ["-", "6.198.724,68"]),
        ("data", "Acciones", ["59.700,00", "767.028.108,86"]),
        ("data", "Cuenta comitente Rosental", ["260.574.723,03", "16.752.671,04"]),
        ("data", "Cuenta comitente Balanz", ["97.976.431,00", "78.233.131,26"]),
        ("total", "TOTAL INVERSIONES CORRIENTES", ["406.197.686,43", "977.795.952,87"]),
        ("spacer", "", []),
        ("head", "INVERSIONES NO CORRIENTES", []),
        ("data", "No existen", ["-", "-"]),
        ("total", "TOTAL INVERSIONES NO CORRIENTES", ["-", "-"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ANEXO II - ACTIVOS Y PASIVOS EN MONEDA EXTRANJERA
# --------------------------------------------------------------------------
ANEXO_II = {
    "anexo": "ANEXO II",
    "titulo": "ACTIVOS Y PASIVOS EN MONEDA EXTRANJERA",
    "subtitulo": SUB_COMP,
    "concept_width": "34%",
    "head": [
        [("CONCEPTOS", 1, "concept", 2), ("Clase", 1, "cls", 2),
         ("2026", 3, "num"), ("2025", 1, "num")],
        [("Monto en<br>moneda<br>extranjera", 1, "num"),
         ("Cambio<br>vigente (2)", 1, "num"),
         ("Monto en<br>moneda nacional", 1, "num"),
         ("Monto en<br>moneda nacional", 1, "num")],
    ],
    "rows": [
        ("head", "Activos corrientes", []),
        ("head", "Caja y bancos", []),
        ("data-i", "Caja", ["U$S", "10.138,50", "1.415,00", "14.345.977,50", "13.854.156,59"]),
        ("data-i", "Banco Galicia Cta Cte en USD", ["U$S", "1.547,14", "1.415,00", "2.189.203,10", "2.535.344,14"]),
        ("total", "TOTAL ACTIVOS", ["", "11.685,64", "", "16.535.180,60", "16.389.500,73"]),
        ("spacer", "", []),
        ("head", "Pasivos", []),
        ("head", "Deudas financieras", []),
        ("data-i", "Préstamo Banco Galicia", ["U$S", "417.098,02", "1.415,00", "590.193.698,30", "814.624.563,12&nbsp;&nbsp;(3)"]),
        ("data-i", "Préstamo Banco Macro", ["U$S", "66.161,70", "1.415,00", "93.618.805,50", "-"]),
        ("total", "TOTAL PASIVOS", ["", "483.259,72", "", "683.812.503,80", "814.624.563,12"]),
    ],
    "notas_pie": [
        "(2) Tipo de cambio comprador/vendedor Banco Nación al cierre del ejercicio.",
        "(3) En el ejercicio anterior el saldo de $606.139.098,70 expuesto como Préstamo Banco Galicia "
        "incluía $543.465.748,80 en dólares (que no se expusieron como tal) y $62.673.349,20 de deuda "
        "genuina en pesos. La porción en dólares, junto con $71.754.770,16 que además figuraban por "
        "error dentro de Deudas comerciales - Proveedores (ambos importes correspondientes a la misma "
        "deuda con el Banco Galicia), totalizan U$S equivalentes a $615.220.518,96 históricos, que se "
        "reclasifican en su totalidad como Préstamo Banco Galicia en moneda extranjera y se actualizan "
        "por el coeficiente de la nota (1), a los efectos comparativos. Los $62.673.349,20 de deuda "
        "genuina en pesos no integran este anexo; se exponen reexpresados en la Nota 2.8 Préstamos y "
        "otros pasivos financieros corrientes en moneda.",
    ],
}

# --------------------------------------------------------------------------
# ANEXO III - BIENES DE USO   /   ANEXO V - PROPIEDADES DE INVERSION
# (misma estructura de columnas)
# --------------------------------------------------------------------------
_HEAD_BIENES = [
    [("CONCEPTOS", 1, "concept", 2), ("COSTO", 4, "num"),
     ("DEPRECIACIONES", 4, "num"), ("VALOR<br>RESIDUAL<br>NETO 2026", 1, "num", 2)],
    [("VALOR AL<br>INICIO DEL<br>EJERCICIO", 1, "num"),
     ("ALTAS DEL<br>EJERCICIO", 1, "num"),
     ("BAJAS DEL<br>EJERCICIO", 1, "num"),
     ("VALOR AL<br>CIERRE DEL<br>EJERCICIO", 1, "num"),
     ("ACUM. AL<br>INICIO DEL<br>EJERCICIO", 1, "num"),
     ("BAJAS DEL<br>EJERCICIO", 1, "num"),
     ("MONTO DEL<br>EJERCICIO", 1, "num"),
     ("VALOR AL<br>CIERRE DEL<br>EJERCICIO", 1, "num")],
]

ANEXO_III = {
    "anexo": "ANEXO III",
    "titulo": "BIENES DE USO",
    "subtitulo": SUB_SIMPLE,
    "concept_width": "19%",
    "head": _HEAD_BIENES,
    "rows": [
        ("data", "Inmuebles rurales", ["3.032.776.412,29", "0,00", "0,00", "3.032.776.412,29",
                                       "24.947.617,42", "0,00", "1.727.530,17", "26.675.147,59", "3.006.101.264,70"]),
        ("data", "Mejoras sobre inmuebles", ["1.172.112.170,58", "0,00", "0,00", "1.172.112.170,58",
                                             "812.323.082,21", "0,00", "27.583.789,58", "839.906.871,79", "332.205.298,79"]),
        ("data", "Máquinas y herramientas", ["1.731.331.078,12", "0,00", "0,00", "1.731.331.078,12",
                                                  "1.011.402.563,08", "0,00", "108.433.676,86", "1.119.836.239,94", "611.494.838,18"]),
        ("data", "Rodados", ["336.836.568,67", "55.555.712,81", "71.083.365,99", "321.308.915,49",
                             "280.756.810,32", "42.650.019,59", "24.934.348,54", "263.041.139,27", "58.267.776,22"]),
        ("data", "Muebles y útiles", ["116.534.389,25", "0,00", "0,00", "116.534.389,25",
                                          "71.136.559,87", "0,00", "7.934.678,39", "79.071.238,26", "37.463.150,99"]),
        ("data", "Reproductores", ["137.942.816,54", "25.600.000,00", "0,00", "163.542.816,54",
                                   "108.170.992,11", "0,00", "5.867.980,49", "114.038.972,60", "49.503.843,94"]),
        ("data", "Hardware y software", ["1.920.509,29", "0,00", "0,00", "1.920.509,29",
                                         "1.920.509,29", "0,00", "0,00", "1.920.509,29", "0,00"]),
        ("data", "Bienes de uso desafectados", ["2.880.668,95", "0,00", "0,00", "2.880.668,95",
                                                "-", "-", "-", "-", "2.880.668,95"]),
        ("total", "TOTALES AL 31/01/2026", ["6.532.334.613,69", "81.155.712,81", "71.083.365,99", "6.542.406.960,51",
                                            "2.310.658.134,30", "42.650.019,59", "176.482.004,03", "2.444.490.118,74", "4.097.916.841,77"]),
    ],
    "notas_pie": [],
}

ANEXO_V = {
    "anexo": "ANEXO V",
    "titulo": "PROPIEDADES DE INVERSIÓN",
    "subtitulo": SUB_SIMPLE,
    "concept_width": "19%",
    "head": _HEAD_BIENES,
    "rows": [
        ("data", "Inmuebles urbanos (San Lorenzo 1250)",
         ["313.469.682,77", "0,00", "0,00", "313.469.682,77",
          "144.604.612,81", "0,00", "4.800.727,61", "149.405.340,42", "164.064.342,35"]),
        ("total", "TOTALES AL 31/01/2026",
         ["313.469.682,77", "0,00", "0,00", "313.469.682,77",
          "144.604.612,81", "0,00", "4.800.727,61", "149.405.340,42", "164.064.342,35"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ANEXO IV - PREVISIONES
# --------------------------------------------------------------------------
ANEXO_IV = {
    "anexo": "ANEXO IV",
    "titulo": "PREVISIONES",
    "subtitulo": SUB_COMP,
    "concept_width": "30%",
    "head": [
        [("", 1, "concept", 2), ("2026", 4, "num"), ("2025", 1, "num", 2)],
        [("VALOR AL INICIO DEL<br>EJERCICIO", 1, "num"),
         ("AUMENTOS DEL EJERCICIO", 1, "num"),
         ("UTILIZACIONES DEL<br>EJERCICIO", 1, "num"),
         ("VALOR AL CIERRE DEL<br>EJERCICIO", 1, "num")],
    ],
    "rows": [
        ("head", "- Incluidas en el pasivo:", []),
        ("data", "Previsión para indemnizaciones",
         ["46.346,28", "-", "(11.344,66)", "35.001,62", "46.346,28"]),
        ("spacer", "", []),
        ("total", "TOTALES AL 31/01/2026", ["46.346,28", "-", "(11.344,66)", "35.001,62", ""]),
        ("total", "TOTALES AL 31/01/2025", ["85.526,25", "-", "(39.179,98)", "", "46.346,28"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ANEXO VI - GASTOS Y SU APLICACION
# Solo ejercicio 2026 (columna comparativa 2025 eliminada por consigna).
# Sin marcador "(1)" ni la referencia "(1) Modificado su valor original ...".
# --------------------------------------------------------------------------
ANEXO_VI = {
    "anexo": "ANEXO VI",
    "titulo": "GASTOS Y SU APLICACIÓN (Art. 64, inc. b, Ley 19.550)",
    "subtitulo": SUB_SIMPLE,
    "concept_width": "26%",
    # El cuadro de gastos tiene 42 filas: no entra en una hoja A4 apaisada a
    # 7,6 pt. Se parte en dos hojas del mismo formato, repitiendo el encabezado
    # completo de columnas. No se achica ni la fuente ni el ancho del cuadro.
    "partir_en": 22,
    "head": [
        [("CONCEPTOS", 1, "concept", 2), ("2026", 6, "num")],
        [("COSTO PROD.<br>SOJA", 1, "num"),
         ("COSTO PROD.<br>MAIZ", 1, "num"),
         ("COSTO PROD.<br>GANADO", 1, "num"),
         ("GASTOS DE<br>COMERCIALIZ.", 1, "num"),
         ("GASTOS DE<br>ADMINISTR.", 1, "num"),
         ("TOTALES", 1, "num")],
    ],
    "rows": [
        ("data", "Consumo sementeras", ["-", "-", "-", "-", "-", "-"]),
        ("data", "Fletes y acarreos", ["112.736.725,94", "153.460.039,52", "-", "-", "-", "266.196.765,46"]),
        ("data", "Honorarios y retribuciones agrícolas", ["12.375.303,95", "16.845.571,99", "-", "-", "-", "29.220.875,94"]),
        ("data", "Gastos generales", ["161.874.775,81", "220.347.976,98", "-", "-", "-", "382.222.752,79"]),
        ("data", "Gastos romaneo, secados y otros", ["292.330,53", "760.642,02", "-", "-", "-", "1.052.972,55"]),
        ("data", "Fumigación", ["2.164.535,72", "2.946.419,94", "-", "-", "-", "5.110.955,66"]),
        ("data", "Siembra", ["11.744.833,50", "15.987.359,91", "-", "-", "-", "27.732.193,41"]),
        ("data", "Laboreos varios", ["23.727.409,55", "32.298.340,90", "-", "-", "-", "56.025.750,45"]),
        ("data", "Sanidad animal", ["-", "-", "33.986.651,45", "-", "-", "33.986.651,45"]),
        ("data", "Forrajes", ["-", "-", "49.296.806,44", "-", "-", "49.296.806,44"]),
        ("data", "Fletes y acarreos (Ganadería)", ["-", "-", "21.416.854,09", "-", "-", "21.416.854,09"]),
        ("data", "Gastos generales (Ganadería)", ["-", "-", "191.633.736,49", "-", "-", "191.633.736,49"]),
        ("data", "Sueldos, Aguinaldos y Cargas Sociales", ["162.379.083,17", "221.034.452,72", "162.618.806,04", "-", "-", "546.032.341,93"]),
        ("data", "Reparaciones y repuestos", ["106.575.492,06", "145.073.214,48", "106.732.831,18", "-", "-", "358.381.537,72"]),
        ("data", "Combustibles y lubricantes", ["44.195.698,87", "60.160.286,17", "44.260.945,70", "-", "-", "148.616.930,74"]),
        ("data", "Otros gastos generales de explotación", ["12.740.945,48", "17.343.292,35", "12.759.755,14", "-", "-", "42.843.992,97"]),
        ("data", "Indemnizaciones y despidos", ["1.865.795,91", "2.539.767,87", "1.868.550,42", "-", "-", "6.274.114,20"]),
        ("data", "Seguros", ["38.859.202,90", "52.896.114,93", "38.916.571,37", "-", "-", "130.671.889,20"]),
        ("data", "Impuestos y tasas", ["4.726.875,50", "6.434.340,67", "4.733.853,86", "-", "-", "15.895.070,03"]),
        ("data", "Ropa de trabajo", ["24.272,15", "33.039,86", "24.307,99", "-", "-", "81.620,00"]),
        ("data", "Alquileres rurales", ["50.671.802,59", "68.975.719,87", "50.746.610,19", "-", "-", "170.394.132,65"]),
        ("data", "Amortizaciones (Anexo III)", ["51.629.372,11", "70.279.187,35", "46.638.766,17", "-", "12.735.406,01", "181.282.731,64"]),
        ("data", "Gastos de venta Soja", ["-", "-", "-", "42.053.411,80", "-", "42.053.411,80"]),
        ("data", "Gastos de venta Maíz", ["-", "-", "-", "30.970.675,98", "-", "30.970.675,98"]),
        ("data", "Gastos de venta Ganado", ["-", "-", "-", "6.315.410,27", "-", "6.315.410,27"]),
        ("data", "Gasto de venta Ganadería", ["-", "-", "-", "2.858.454,40", "-", "2.858.454,40"]),
        ("data", "Gastos comerciales", ["-", "-", "-", "(232.941,16)", "-", "(232.941,16)"]),
        ("data", "Impuesto a los ingresos brutos", ["-", "-", "-", "58.098.428,72", "-", "58.098.428,72"]),
        ("data", "Débitos y gastos bancarios", ["-", "-", "-", "-", "17.871.343,92", "17.871.343,92"]),
        ("data", "Gastos de movilidad y representación", ["-", "-", "-", "-", "1.747.738,36", "1.747.738,36"]),
        ("data", "Honorarios y retribuciones administración", ["-", "-", "-", "-", "63.999.060,12", "63.999.060,12"]),
        ("data", "Gastos generales de administración", ["-", "-", "-", "-", "46.296.679,83", "46.296.679,83"]),
        ("data", "Gastos de comunicaciones e internet", ["-", "-", "-", "-", "338.756,45", "338.756,45"]),
        ("data", "Gastos de refrigerios", ["-", "-", "-", "-", "2.017.387,74", "2.017.387,74"]),
        ("data", "Luz, gas y fuerza motriz", ["-", "-", "-", "-", "18.053.785,09", "18.053.785,09"]),
        ("data", "Honorarios por desarrollo inmobiliario", ["-", "-", "-", "-", "15.224.973,73", "15.224.973,73"]),
        ("data", "Agasajos y atenciones", ["-", "-", "-", "-", "-", "-"]),
        ("data", "Impuesto débito y crédito bancario", ["-", "-", "-", "-", "6.249.539,36", "6.249.539,36"]),
        ("data", "Intereses, multas y recargos impositivos", ["-", "-", "-", "-", "461.868,10", "461.868,10"]),
        ("data", "Donaciones efectuadas", ["-", "-", "-", "-", "2.702.069,47", "2.702.069,47"]),
        ("total", "TOTALES AL 31/01/2026", ["798.584.455,74", "1.087.415.767,53", "765.635.046,53",
                                            "140.063.440,01", "187.698.608,18", "2.979.397.317,99"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ANEXO VII - COSTO DE VENTAS AGROPECUARIAS
# --------------------------------------------------------------------------
ANEXO_VII = {
    "anexo": "ANEXO VII",
    "titulo": "COSTO DE VENTAS AGROPECUARIAS",
    "subtitulo": SUB_SIMPLE,
    "concept_width": "36%",
    "head": [
        [("CONCEPTO", 1, "concept"), ("SOJA", 1, "num"), ("MAIZ", 1, "num"),
         ("GANADO", 1, "num"), ("TOTALES", 1, "num")],
    ],
    "rows": [
        ("data", "Existencias al Inicio (actualizadas)",
         ["123.282.267,44", "542.192.255,42", "2.247.002.837,41", "2.912.477.360,27"]),
        ("data", "Resultado medición bienes de cambio a VNR",
         ["21.610.011,44", "95.124.920,35", "394.140.043,28", "510.874.975,07"]),
        ("data", "Gastos Imp. al Costo (del Cuadro de Gastos)",
         ["798.584.455,74", "1.087.415.767,53", "765.635.046,53", "2.651.635.269,80"]),
        ("data", "Existencia al Cierre",
         ["299.324.971,14", "729.630.000,00", "2.169.194.246,43", "3.198.149.217,57"]),
        ("total", "COSTO DE VENTAS",
         ["644.151.763,48", "995.102.943,30", "1.237.583.680,79", "2.876.838.387,57"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ESTADO DE SITUACION PATRIMONIAL  (dos paneles: Activos | Pasivos)
# --------------------------------------------------------------------------
ESP = {
    "anexo": None,
    "titulo": "ESTADO DE SITUACIÓN PATRIMONIAL",
    "subtitulo": "Al 31 de enero de 2026 comparativo con el ejercicio anterior",
    "izq": [
        ("head", "ACTIVOS", []),
        ("head", "ACTIVOS CORRIENTES", []),
        ("data", "CAJA Y BANCOS (Nota 2.1. y Anexo II)", ["98.557.263,73", "85.076.411,79"]),
        ("data", "CUENTAS POR COBRAR Y DERECHOS A FACTURAR EN MONEDA (Nota 2.2.)", ["270.870.884,28", "186.882.444,88"]),
        ("data", "OTRAS CUENTAS POR COBRAR EN MONEDA (Nota 2.3.)", ["429.627.253,63", "309.309.698,17"]),
        ("data", "ACTIVOS BIOLÓGICOS (Nota 2.4.)", ["3.198.149.217,57", "2.912.477.360,27"]),
        ("data", "INVERSIONES FINANCIERAS (Nota 2.13. y Anexo I)", ["406.197.686,43", "977.795.952,87"]),
        ("total", "TOTAL DE ACTIVOS CORRIENTES", ["4.403.402.305,64", "4.471.541.867,98"]),
        ("spacer", "", []),
        ("head", "ACTIVOS NO CORRIENTES", []),
        ("data", "BIENES DE USO (Nota 2.14. y Anexo III)", ["4.097.916.841,77", "4.230.949.242,30"]),
        ("data", "PROPIEDADES DE INVERSIÓN (Nota 2.15. y Anexo V)", ["164.064.342,35", "168.867.365,54"]),
        ("spacer", "", []),
        ("total", "TOTAL DE ACTIVOS NO CORRIENTES", ["4.261.981.184,12", "4.399.816.607,84"]),
        ("spacer", "", []),
        ("spacer", "", []),
        ("total", "TOTAL DE ACTIVOS", ["8.665.383.489,76", "8.871.358.475,82"]),
    ],
    "der": [
        ("head", "PASIVOS", []),
        ("head", "PASIVOS CORRIENTES", []),
        ("data", "DEUDAS CON PROVEEDORES DE BIENES O SERVICIOS (Nota 2.5.)", ["1.465.243.080,38", "664.185.359,05"]),
        ("data", "DEUDAS FISCALES (Nota 2.6.)", ["11.057.118,64", "9.625.648,80"]),
        ("data", "DEUDAS LABORALES Y PREVISIONALES (Nota 2.7.)", ["16.936.506,80", "50.573.555,24"]),
        ("data", "PRÉSTAMOS Y OTROS PASIVOS FINANCIEROS (Nota 2.8. y Anexo II)", ["649.423.093,75", "1.315.483.236,06"]),
        ("data", "PREVISIONES (Nota 2.10. y Anexo IV)", ["35.001,62", "46.346,28"]),
        ("data", "OTRAS DEUDAS (Nota 2.11.)", ["20.000,00", "611.160.886,79"]),
        ("total", "TOTAL DE PASIVOS CORRIENTES", ["2.142.714.801,19", "2.651.075.032,22"]),
        ("spacer", "", []),
        ("head", "PASIVOS NO CORRIENTES", []),
        ("data", "PRÉSTAMOS Y OTROS PASIVOS FINANCIEROS (Nota 2.9. y Anexo II)", ["34.389.410,05", "-"]),
        ("data", "OTRAS DEUDAS (Nota 2.12.)", ["3.335.000,00", "4.415.933,57"]),
        ("total", "TOTAL PASIVOS NO CORRIENTES", ["37.724.410,05", "4.415.933,57"]),
        ("total", "TOTAL DE PASIVOS", ["2.180.439.211,24", "2.655.490.965,79"]),
        ("head", "PATRIMONIO NETO", []),
        ("data", "Según estado correspondiente", ["6.484.944.278,52", "6.215.867.510,03"]),
        ("total", "TOTAL PASIVO Y PATRIMONIO NETO", ["8.665.383.489,76", "8.871.358.475,82"]),
    ],
}

# --------------------------------------------------------------------------
# ESTADO DE RESULTADOS
# --------------------------------------------------------------------------
ER = {
    "anexo": None,
    "titulo": "ESTADO DE RESULTADOS",
    "subtitulo": SUB_COMP,
    "concept_width": "58%",
    "head": [
        [("", 1, "concept"), ("2026", 1, "num"), ("2025", 1, "num")],
    ],
    "rows": [
        ("data", "Ventas Agricultura", ["3.111.366.101,57", "1.860.634.447,51"]),
        ("data", "Ventas Ganadería", ["1.319.638.678,66", "1.333.472.754,56"]),
        ("data", "Costo de Ventas (Cuadro de Costos)", ["(2.876.838.387,57)", "(4.462.876.186,53)"]),
        ("total", "RESULTADO BRUTO", ["1.554.166.392,66", "(1.268.768.984,46)"]),
        ("data", "Gastos de Comercialización (Cuadro de Gastos)", ["(140.063.440,01)", "(84.215.388,82)"]),
        ("data", "Gastos de Administración (Cuadro de Gastos)", ["(187.698.608,18)", "(223.437.116,50)"]),
        ("data", "Resultados Financieros y por Tenencia (incluido RECPAM)", ["(1.072.511.076,70)", "179.178.724,07"]),
        ("data", "Ingresos por Actividad Inmobiliaria", ["181.410.750,69", "52.347.072,79"]),
        ("data", "Otros Ingresos y Egresos", ["125.030.532,63", "48.737.110,09"]),
        ("total", "RESULTADO ANTES IMPUESTO A LAS GANANCIAS", ["460.334.551,09", "(1.296.158.582,82)"]),
        ("data", "Impuesto a las Ganancias", ["(138.100.365,33)", "-"]),
        ("total", "RESULTADO DEL EJERCICIO", ["322.234.185,76", "(1.296.158.582,82)"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ESTADO DE EVOLUCION DEL PATRIMONIO NETO
# --------------------------------------------------------------------------
EPN = {
    "anexo": None,
    "titulo": "ESTADO DE EVOLUCIÓN DEL PATRIMONIO NETO",
    "subtitulo": SUB_COMP,
    "concept_width": "16%",
    "head": [
        [("CONCEPTOS", 1, "concept", 3), ("2026", 8, "num"), ("2025", 1, "num")],
        [("APORTES DE LOS PROPIETARIOS", 3, "num"),
         ("GANANCIAS RESERVADAS", 3, "num"),
         ("RESULTADOS NO<br>ASIGNADOS", 1, "num", 2),
         ("TOTAL DEL<br>PATRIMONIO<br>NETO", 1, "num", 2),
         ("TOTAL DEL<br>PATRIMONIO<br>NETO", 1, "num", 2)],
        [("CAPITAL<br>SUSCRIPTO", 1, "num"),
         ("AJUSTES AL<br>CAPITAL", 1, "num"),
         ("TOTAL", 1, "num"),
         ("RESERVA<br>LEGAL", 1, "num"),
         ("OTRAS", 1, "num"),
         ("TOTAL DE<br>GANANCIAS<br>RESERVADAS", 1, "num")],
    ],
    "head_last_col": "TOTAL DEL<br>PATRIMONIO<br>NETO",
    "rows": [
        ("data", "Saldos al inicio",
         ["1.309.803,00", "813.984.329,42", "815.294.132,42", "328.940.649,26", "2.419.260.766,18",
          "2.748.201.415,44", "2.652.371.962,16", "6.215.867.510,02", "8.121.123.628,06"]),
        ("data", "Distribución de resultados",
         ["-", "-", "-", "-", "-", "-", "(191.257.782,59)", "(191.257.782,59)", "(609.097.535,21)"]),
        ("data", "Resultado del ejercicio",
         ["-", "-", "-", "-", "-", "-", "460.334.551,09", "460.334.551,09", "(1.296.158.582,82)"]),
        ("total", "SALDOS AL CIERRE DEL EJERCICIO",
         ["1.309.803,00", "813.984.329,42", "815.294.132,42", "328.940.649,26", "2.419.260.766,18",
          "2.748.201.415,44", "2.921.448.730,66", "6.484.944.278,52", "6.215.867.510,03"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# ESTADO DE FLUJO DE EFECTIVO
# --------------------------------------------------------------------------
EFE = {
    "anexo": None,
    "titulo": "ESTADO DE FLUJO DE EFECTIVO",
    "subtitulo": SUB_COMP,
    "concept_width": "58%",
    "head": [
        [("", 1, "concept"), ("2026", 1, "num"), ("2025", 1, "num")],
    ],
    "rows": [
        ("head", "VARIACIÓN DEL EFECTIVO", []),
        ("data-i", "Efectivo al inicio del ejercicio (Notas 1.4.1.)", ["85.076.411,79", "137.283.645,91"]),
        ("data-i", "Efectivo al cierre del ejercicio (Notas 1.4.1. y 2.1.)", ["98.557.263,73", "85.076.411,79"]),
        ("total", "VARIACIÓN NETA DEL EFECTIVO", ["13.480.851,94", "(52.207.234,12)"]),
        ("spacer", "", []),
        ("head", "CAUSAS DE VARIACIÓN DEL EFECTIVO", []),
        ("head", "Actividades operativas", []),
        ("data-i", "Resultado del ejercicio", ["460.334.551,09", "(1.296.158.582,82)"]),
        ("head", "Ajustes para conciliar el resultado con el efectivo originado<br>por las actividades operativas", []),
        ("data-i", "Depreciación de bienes de uso", ["181.282.731,64", "187.472.186,91"]),
        ("head", "Cambios netos en activos y pasivos operativos:", []),
        ("data-i", "(Aumento) Disminución de créditos por ventas", ["(83.988.439,40)", "140.478.742,13"]),
        ("data-i", "(Aumento) Disminución de créditos fiscales", ["(120.317.555,46)", "(105.710.937,79)"]),
        ("data-i", "(Aumento) Disminución de bienes de cambio", ["(285.671.857,30)", "1.049.036.682,62"]),
        ("data-i", "Aumento (Disminución) de deudas comerciales", ["801.057.721,33", "199.888.431,11"]),
        ("data-i", "Aumento (Disminución) de deudas fiscales y sociales", ["(32.205.578,60)", "(233.988,23)"]),
        ("data-i", "Aumento (Disminución) de deudas financieras", ["(631.670.732,26)", "788.445.868,97"]),
        ("data-i", "Aumento (Disminución) de otras deudas", ["(602.760.054,26)", "603.580.929,55"]),
        ("total", "FLUJO NETO DE EFECTIVO GENERADO POR LAS ACTIVIDADES OPERATIVAS",
         ["(313.939.213,22)", "1.566.799.332,45"]),
        ("spacer", "", []),
        ("head", "Actividades de inversión", []),
        ("data-i", "Adquisiciones bienes de uso", ["(81.155.712,81)", "(638.530.669,68)"]),
        ("data-i", "Venta de bienes de uso", ["28.235.294,12", "-"]),
        ("data-i", "Disminución de inversiones corrientes", ["571.598.266,44", "(371.378.361,68)"]),
        ("total", "FLUJO NETO DE EFECTIVO APLICADO POR ACTIVIDADES DE INVERSIÓN",
         ["518.677.847,75", "(1.009.909.031,36)"]),
        ("spacer", "", []),
        ("head", "Actividades de Financiación", []),
        ("data-i", "Distribución de resultados", ["(191.257.782,59)", "(609.097.535,21)"]),
        ("total", "FLUJO NETO DE EFECTIVO APLICADO POR ACTIVIDADES DE FINANCIACIÓN",
         ["(191.257.782,59)", "(609.097.535,21)"]),
        ("spacer", "", []),
        ("data-i", "Resultado por Tenencia", ["", ""]),
        ("grand", "VARIACIÓN NETA DEL EFECTIVO", ["13.480.851,94", "(52.207.234,12)"]),
    ],
    "notas_pie": [],
}

# --------------------------------------------------------------------------
# NOTAS A LOS ESTADOS CONTABLES
# --------------------------------------------------------------------------
NOTA_1_PARRAFOS = [
    ("h1", "1. NOTAS GENERALES."),
    ("h2", "1.1. Bases de preparación de los estados contables."),
    ("p", "Los presentes estados contables han sido preparados de conformidad con la Resolución Técnica "
          "N° 54, Norma Unificada Argentina de Contabilidad (RT 54), emitida por la Federación Argentina "
          "de Consejos Profesionales de Ciencias Económicas (FACPCE), texto ordenado según Resolución "
          "Técnica N° 59, tal como fue aprobada por el Consejo Profesional de Ciencias Económicas de la "
          "Provincia de Santa Fe. Este es el primer ejercicio en el que la Sociedad aplica la RT 54, siendo "
          "de aplicación obligatoria para los ejercicios iniciados a partir del 1° de enero de 2025 inclusive."),
    ("h2", "1.2. Clasificación de la entidad."),
    ("p", "De acuerdo con lo establecido por la RT 54 y la Resolución de Junta de Gobierno de FACPCE "
          "N° 608/22, la Sociedad reviste el carácter de entidad pequeña."),
    ("h2", "1.3. Unidad de medida."),
    ("p", "Los presentes estados contables han sido preparados en moneda homogénea (pesos de cierre del "
          "ejercicio, 31 de enero de 2026), reconociendo en forma integral los efectos de la inflación de "
          "conformidad con lo establecido en la RT 54, en virtud de haberse determinado la existencia de un "
          "contexto de alta inflación."),
    ("p", "Con fines comparativos, se incluyen cifras patrimoniales al 31 de enero de 2025 y de resultados, "
          "de evolución del patrimonio neto y de flujos de efectivo por el ejercicio económico finalizado "
          "en esa fecha, expresadas en moneda de cierre del presente ejercicio, de acuerdo al señalado en el "
          "párrafo siguiente, a fin de permitir su comparabilidad y sin que el ajuste practicado modifique "
          "las decisiones tomadas con base en la información contable correspondiente al ejercicio comparativo."),
    ("p", "Para la determinación de los coeficientes de ajuste se utilizó la serie de índices definida por "
          "la FACPCE en la Resolución JG N° 539/2018 y sus modificatorias (índice IPC Nacional empalmado "
          "con IPIM). El coeficiente de ajuste aplicado a las partidas del ejercicio comparativo fue de "
          "1,324118 (índice de enero de 2026 sobre índice de enero de 2025)."),
    ("p", "La aplicación del proceso de ajuste por inflación establecido en la RT 54 permite el "
          "reconocimiento de las ganancias y pérdidas derivadas del mantenimiento de activos y pasivos "
          "monetarios a lo largo del ejercicio. Tales ganancias y pérdidas (RECPAM) se exponen en el rubro "
          "“Otros resultados financieros y por tenencia (incluyendo el resultado por los cambios en el poder "
          "adquisitivo de la moneda)” del Estado de Resultados, en una sola línea, de acuerdo a la opción "
          "de simplificación admitida por la RT 54."),
    ("p", "Se han adoptado los siguientes criterios de valuación:"),
    ("li", "I - Activos y Pasivos Monetarios. Se encuentran valuados a su valor nominal."),
    ("li", "II - Activos Biológicos. Los cereales, oleaginosas y hacienda vacuna se encuentran valuados al "
           "valor neto de realización a la fecha de cierre del ejercicio y las sementeras al costo de "
           "reposición de los bienes y servicios invertidos en las mismas."),
    ("li", "III - Inversiones Financieras. Las inversiones financieras están valuadas a su valor de "
           "cotización a la fecha de cierre del ejercicio. La totalidad de las inversiones financieras de "
           "la Sociedad reviste el carácter de corriente."),
    ("li", "IV - Bienes de Uso. Los bienes de uso están valuados a su costo de adquisición reexpresado en "
           "moneda de cierre, menos la correspondiente amortización acumulada. La amortización se calcula "
           "por el método de la línea recta."),
    ("li", "V - Propiedades de Inversión. Corresponde a un inmueble urbano destinado a la obtención de "
           "renta por locación a terceros. La Sociedad mide sus propiedades de inversión al modelo de "
           "costo: costo de adquisición reexpresado en moneda de cierre, menos la correspondiente "
           "amortización acumulada, calculada por el método de la línea recta."),
    ("h2", "1.4. Uso de estimaciones en la preparación de los presentes estados contables."),
    ("p", "La preparación de los estados contables requiere que la Dirección de la Sociedad realice "
          "estimaciones que afectan los importes de los activos, pasivos y resultados, y la exposición de "
          "activos y pasivos contingentes a la fecha de los presentes estados contables. Los resultados "
          "reales futuros pueden diferir de las estimaciones y evaluaciones realizadas a la fecha de su "
          "preparación."),
    ("h2", "1.5. Modificación a la información de ejercicios anteriores."),
    ("p", "Como consecuencia de la aplicación por primera vez de la RT 54, la Sociedad reclasificó un "
          "inmueble urbano destinado a locación a terceros (previamente expuesto dentro de Bienes de Uso) "
          "al rubro Propiedades de Inversión (Nota 2.15 y Anexo V), de acuerdo con la definición contenida "
          "en dicha norma. Los importes del ejercicio comparativo fueron modificados a fin de uniformar su "
          "presentación con la del presente ejercicio; esta reclasificación no tiene efecto sobre el "
          "resultado del ejercicio."),
    ("h2", "1.6. Empresa en marcha."),
    ("p", "No existen incertidumbres significativas relativas a eventos o condiciones que puedan generar "
          "dudas sobre la posibilidad de que la Sociedad continúe funcionando normalmente en el futuro "
          "previsible."),
    ("h1", "2. COMPOSICIÓN DE LOS PRINCIPALES RUBROS."),
    ("p", "A continuación se detalla la composición de los principales rubros de los estados contables:"),
]

# Cuadros de notas: (titulo, [(concepto, v2026, v2025), ...], total_label)
NOTAS_CUADROS = [
    ("2.1. Caja y bancos.", [
        ("Dinero en efectivo", "79.648.011,95", "63.435.976,92"),
        ("Moneda extranjera (Anexo II)", "14.345.977,50", "13.854.156,59"),
        ("Banco de Boston cta. cte.", "92.643,32", "-"),
        ("Banco ICBC cta. cte.", "269,83", "252.490,83"),
        ("Banco Nación Argentina cta. cte.", "296.944,65", "180.391,55"),
        ("Banco Galicia cta. cte. en $", "1.447.285,30", "4.490.479,31"),
        ("Banco Galicia caja de ahorro en USD (Anexo II)", "2.189.203,10", "2.535.344,14"),
        ("Banco Francés cta. cte.", "380.281,29", "181.895,22"),
        ("Banco Macro cta. cte.", "156.646,79", "145.677,24"),
    ], ("Total del rubro", "98.557.263,73", "85.076.411,79")),

    ("2.2. Cuentas por cobrar a clientes en moneda.", [
        ("Deudores por ventas", "243.641.891,07", "151.064.156,68"),
        ("Créditos por alquileres", "27.228.993,21", "35.818.288,20"),
    ], ("Total del rubro", "270.870.884,28", "186.882.444,88")),

    ("2.3. Otras cuentas por cobrar en moneda.", [
        ("Saldo a favor IVA", "253.663.339,86", "238.931.201,15"),
        ("Saldo a favor impuesto a las ganancias", "39.276.447,82", "58.036.867,78"),
        ("Retenciones de ganancias", "84.663.992,37", "-"),
        ("Impuesto Ley 25.413 débitos y créditos bancarios", "29.736.763,38", "-"),
        ("Percepciones de ganancias", "16.319,42", "-"),
        ("Transferencias a empleados para gastos", "313.227,62", "-"),
        ("Saldo a favor ingresos brutos Formosa", "2.238.946,88", "3.585.205,48"),
        ("Retención de SUSS", "1.829.579,00", "-"),
        ("Anticipo impuesto rural Formosa", "350.381,00", "-"),
        ("Carmen Flanagan - cuenta particular", "17.538.132,69", "8.756.348,31"),
        ("Carlos Daminato - cuenta particular", "123,59", "75,45"),
    ], ("Total del rubro", "429.627.253,63", "309.309.698,17")),

    ("2.4. Activos biológicos.", [
        ("__label__Terminados:", "", ""),
        ("Cereales maíz", "-", "322.219.348,48"),
        ("Cereales soja", "-", "51.340.490,66"),
        ("__label__En producción:", "", ""),
        ("Hacienda vacuna", "1.874.248.046,43", "1.888.371.965,29"),
        ("__label__En desarrollo:", "", ""),
        ("Sementera de maíz", "729.630.000,00", "219.972.906,94"),
        ("Sementera de soja", "290.986.421,14", "71.941.776,78"),
        ("Sementera de sorgo", "8.338.550,00", "-"),
        ("Hacienda vacuna", "294.946.200,00", "358.630.872,12"),
    ], ("Total del rubro", "3.198.149.217,57", "2.912.477.360,27")),

    ("2.5. Deudas con proveedores de bienes o servicios en moneda.", [
        ("Proveedores", "1.431.742.950,61", "571.359.822,62"),
        ("Anticipo de clientes", "-", "1.706.110,99"),
        ("Cheques diferidos a pagar", "33.500.129,77", "91.119.425,45"),
    ], ("Total del rubro", "1.465.243.080,38", "664.185.359,05")),

    ("2.6. Deudas fiscales.", [
        ("Ingresos brutos a pagar", "3.265.980,42", "1.311.722,97"),
        ("Otros impuestos a pagar", "1.879.052,53", "4.625.795,86"),
        ("Plan de facilidades AFIP a pagar", "5.912.085,69", "3.688.129,97"),
    ], ("Total del rubro", "11.057.118,64", "9.625.648,80")),

    ("2.7. Deudas laborales y previsionales.", [
        ("Leyes sociales a pagar", "16.936.506,80", "18.504.439,74"),
        ("Sueldos a pagar", "-", "32.069.115,50"),
    ], ("Total del rubro", "16.936.506,80", "50.573.555,24")),

    ("2.8. Préstamos y otros pasivos financieros corrientes en moneda.", [
        ("Préstamo Banco Galicia", "555.804.288,25", "897.611.472,92"),
        ("Préstamo Banco Macro", "93.618.805,50", "-"),
        ("Tarjeta Banco Francés a pagar", "-", "417.871.763,14"),
    ], ("Total del rubro", "649.423.093,75", "1.315.483.236,06")),

    ("2.9. Préstamos y otros pasivos financieros no corrientes en moneda.", [
        ("Préstamo Banco Galicia", "34.389.410,05", "-"),
    ], ("Total del rubro", "34.389.410,05", "-")),

    ("2.10. Previsiones.", [
        ("Previsión para despidos", "35.001,62", "46.346,28"),
    ], ("Total del rubro", "35.001,62", "46.346,28")),

    ("2.11. Otras deudas corrientes en moneda.", [
        ("Finca Cerro Medina", "20.000,00", "26.482,36"),
        ("Dividendos a pagar", "-", "609.097.535,21"),
        ("Préstamo Carmen Flanagan", "-", "2.036.869,22"),
    ], ("Total del rubro", "20.000,00", "611.160.886,79")),

    ("2.12. Otras deudas no corrientes en moneda.", [
        ("Depósito garantía directores", "-", "0,04"),
        ("Préstamo C. Daminato y C. Flanagan S.H.", "3.335.000,00", "4.415.933,53"),
    ], ("Total del rubro", "3.335.000,00", "4.415.933,57")),
]

# Notas que solo remiten a un anexo
NOTAS_REMISION = [
    ("2.13. Inversiones financieras.", "Ver Anexo I – Inversiones."),
    ("2.14. Bienes de uso.", "Ver Anexo III – Bienes de Uso."),
    ("2.15. Propiedades de inversión.", "Ver Anexo V – Propiedades de Inversión."),
]

NOTA_210_REMISION = "Ver Anexo IV – Previsiones."

NOTAS_FINALES = [
    ("3. VENTAS NETAS.", [
        ("Venta de cereales soja", "1.317.693.010,95", "1.313.324.815,58"),
        ("Venta de cereales maíz", "1.793.673.090,62", "547.309.631,93"),
        ("Venta de ganado", "1.319.638.678,66", "1.333.472.754,56"),
    ], ("Total del rubro", "4.431.004.780,23", "3.194.107.202,07")),

    ("4. INGRESOS ACTIVIDAD INMOBILIARIA.", [
        ("Ingresos por alquileres", "181.410.750,69", "52.347.072,79"),
    ], ("Total del rubro", "181.410.750,69", "52.347.072,79")),

    ("5. OTROS INGRESOS Y EGRESOS.", [
        ("Ingresos por labores realizados", "-", "48.737.110,09"),
        ("Otros ingresos", "125.228.584,91", "-"),
        ("Resultado por venta de bienes de uso", "(198.052,28)", "-"),
    ], ("Total del rubro", "125.030.532,63", "48.737.110,09")),
]

NOTA_6 = ("6. CAPITAL SOCIAL.",
          "Al 31 de enero de 2026, el Capital Social de $1.309.803,00 se hallaba integrado en su totalidad.")
