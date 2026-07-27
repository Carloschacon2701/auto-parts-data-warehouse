"""Genera el informe PDF de respuestas a las preguntas de negocio.

Lee directamente del esquema `marts` (y algunos totales de `core`), por lo que el
informe siempre refleja el último `python run_pipeline.py`.

Uso:
    python reports/generate_report.py
"""
import os
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv

load_dotenv(RAIZ / ".env")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from etl.db import get_db_engine

OUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUT_DIR / "figuras"
PDF_PATH = OUT_DIR / "Informe_Preguntas_Negocio.pdf"

# Paleta
AZUL      = colors.HexColor("#1F3B57")
AZUL_CLARO= colors.HexColor("#2E6DA4")
GRIS      = colors.HexColor("#4A4A4A")
GRIS_SUAVE= colors.HexColor("#EDF1F5")
NARANJA   = colors.HexColor("#C8672A")
VERDE     = colors.HexColor("#2E7D5B")
ROJO      = colors.HexColor("#A62B2B")

PLT_AZUL = "#2E6DA4"
PLT_NARANJA = "#C8672A"
PLT_VERDE = "#2E7D5B"
PLT_GRIS = "#8A9AA8"


# --------------------------------------------------------------------------- #
# Datos
# --------------------------------------------------------------------------- #
def cargar_datos(engine) -> dict:
    q = lambda sql: pd.read_sql(sql, engine)
    d = {}

    d["totales"] = q("""
        SELECT COUNT(*) lineas,
               COUNT(DISTINCT fv.nro_factura) facturas,
               SUM(fv.cantidad) unidades,
               ROUND(SUM(fv.subtotal_usd), 2) ingreso_usd,
               MIN(dt.fecha) desde, MAX(dt.fecha) hasta
        FROM core.fact_ventas fv
        JOIN core.dim_tiempo dt ON dt.sk_fecha = fv.sk_fecha
    """).iloc[0]

    d["conteos"] = q("""
        SELECT 'dim_producto' tabla, COUNT(*) filas FROM core.dim_producto
        UNION ALL SELECT 'dim_clientes',        COUNT(*) FROM core.dim_clientes
        UNION ALL SELECT 'dim_proveedor',       COUNT(*) FROM core.dim_proveedor
        UNION ALL SELECT 'dim_usuarios',        COUNT(*) FROM core.dim_usuarios
        UNION ALL SELECT 'dim_tiempo',          COUNT(*) FROM core.dim_tiempo
        UNION ALL SELECT 'fact_ventas',         COUNT(*) FROM core.fact_ventas
        UNION ALL SELECT 'fact_compras',        COUNT(*) FROM core.fact_compras
        UNION ALL SELECT 'fact_mov_inventario', COUNT(*) FROM core.fact_mov_inventario
    """)

    d["margen_global"] = q("""
        SELECT ROUND(SUM(fv.subtotal_usd), 2) ingreso,
               ROUND(SUM(fv.cantidad * dp.costo_usd), 2) costo,
               ROUND(SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd), 2) margen,
               ROUND(100 * (SUM(fv.subtotal_usd) - SUM(fv.cantidad * dp.costo_usd))
                     / NULLIF(SUM(fv.subtotal_usd), 0), 2) margen_pct
        FROM core.fact_ventas fv
        JOIN core.dim_producto dp ON dp.sk_producto = fv.sk_producto
    """).iloc[0]

    # P1
    d["p1_cant"] = q("""
        SELECT ranking_por_cantidad rk, codigo, descripcion, marca,
               unidades_vendidas, monto_vendido_usd, nro_facturas
        FROM marts.p01_top_productos WHERE top10_por_cantidad
        ORDER BY ranking_por_cantidad
    """)
    d["p1_monto"] = q("""
        SELECT ranking_por_monto rk, codigo, descripcion, marca,
               unidades_vendidas, monto_vendido_usd, nro_facturas
        FROM marts.p01_top_productos WHERE top10_por_monto
        ORDER BY ranking_por_monto
    """)
    d["p1_solape"] = q("""
        SELECT COUNT(*) FILTER (WHERE top10_por_cantidad AND top10_por_monto) en_ambos,
               COUNT(*) FILTER (WHERE top10_por_cantidad AND NOT top10_por_monto) solo_cantidad,
               COUNT(*) FILTER (WHERE top10_por_monto AND NOT top10_por_cantidad) solo_monto
        FROM marts.p01_top_productos
    """).iloc[0]
    d["p1_diverge"] = q("""
        SELECT codigo, descripcion, unidades_vendidas, monto_vendido_usd,
               ranking_por_cantidad, ranking_por_monto,
               ABS(ranking_por_cantidad - ranking_por_monto) brecha
        FROM marts.p01_top_productos
        ORDER BY brecha DESC LIMIT 6
    """)

    # P4
    d["p4_cat"] = q("""
        SELECT categoria, unidades_vendidas, ingreso_usd, costo_mercancia_usd,
               margen_usd, margen_pct_sobre_ingreso
        FROM marts.p04_margen WHERE nivel = 'CATEGORIA'
        ORDER BY margen_usd DESC LIMIT 12
    """)
    d["p4_marca"] = q("""
        SELECT marca, unidades_vendidas, ingreso_usd, margen_usd, margen_pct_sobre_ingreso
        FROM marts.p04_margen WHERE nivel = 'MARCA'
        ORDER BY margen_usd DESC LIMIT 12
    """)
    d["p4_prod_top"] = q("""
        SELECT codigo, descripcion, marca, unidades_vendidas, ingreso_usd,
               margen_usd, margen_pct_sobre_ingreso
        FROM marts.p04_margen WHERE nivel = 'PRODUCTO'
        ORDER BY margen_usd DESC LIMIT 10
    """)
    d["p4_prod_neg"] = q("""
        SELECT codigo, descripcion, marca, unidades_vendidas, ingreso_usd,
               margen_usd, margen_pct_sobre_ingreso
        FROM marts.p04_margen WHERE nivel = 'PRODUCTO' AND margen_usd < 0
        ORDER BY margen_usd ASC LIMIT 10
    """)
    d["p4_stats"] = q("""
        SELECT COUNT(*) productos,
               COUNT(*) FILTER (WHERE margen_usd < 0) con_perdida,
               COUNT(*) FILTER (WHERE margen_pct_sobre_ingreso BETWEEN 22.5 AND 23.5) en_banda,
               ROUND(MIN(margen_pct_sobre_ingreso), 2) pct_min,
               ROUND(MAX(margen_pct_sobre_ingreso), 2) pct_max,
               ROUND(AVG(margen_pct_sobre_ingreso), 2) pct_prom,
               ROUND(STDDEV_POP(margen_pct_sobre_ingreso), 2) pct_desv,
               ROUND(SUM(margen_usd) FILTER (WHERE margen_usd < 0), 2) perdida_usd
        FROM marts.p04_margen WHERE nivel = 'PRODUCTO'
    """).iloc[0]
    d["p4_niveles"] = q("""
        SELECT nivel, COUNT(*) filas FROM marts.p04_margen GROUP BY nivel
    """).set_index("nivel")["filas"].to_dict()

    # P6
    d["p6_resumen"] = q("SELECT * FROM marts.p06_inventario_muerto_resumen ORDER BY capital_inmovilizado_usd DESC")
    d["p6_top"] = q("""
        SELECT codigo, descripcion, marca, stock_actual, costo_usd,
               capital_inmovilizado_usd, fecha_ultima_venta, dias_sin_vender, clasificacion
        FROM marts.p06_inventario_muerto
        WHERE es_inventario_muerto AND capital_inmovilizado_usd > 0
        ORDER BY capital_inmovilizado_usd DESC LIMIT 15
    """)
    d["p6_kpi"] = q("""
        SELECT COUNT(*) FILTER (WHERE es_inventario_muerto) productos_muertos,
               ROUND(SUM(capital_inmovilizado_usd) FILTER (WHERE es_inventario_muerto), 2) capital_muerto,
               ROUND(SUM(capital_inmovilizado_usd), 2) capital_total,
               MAX(dias_sin_vender) dias_max,
               MAX(fecha_corte) fecha_corte
        FROM marts.p06_inventario_muerto
    """).iloc[0]

    # P13
    d["p13_anio"] = q("""
        SELECT periodo, nro_facturas, unidades_vendidas, ingreso_usd, margen_usd,
               ticket_promedio_usd, variacion_pct_vs_periodo_anterior
        FROM marts.p13_evolucion_ventas WHERE granularidad = 'ANIO' ORDER BY periodo_inicio
    """)
    d["p13_mes"] = q("""
        SELECT periodo, periodo_inicio, nro_facturas, unidades_vendidas, ingreso_usd,
               margen_usd, ticket_promedio_usd, variacion_pct_vs_periodo_anterior
        FROM marts.p13_evolucion_ventas WHERE granularidad = 'MES' ORDER BY periodo_inicio
    """)
    d["p13_stats"] = q("""
        SELECT granularidad, COUNT(*) periodos,
               ROUND(AVG(ingreso_usd), 2) promedio,
               ROUND(MIN(ingreso_usd), 2) minimo,
               ROUND(MAX(ingreso_usd), 2) maximo
        FROM marts.p13_evolucion_ventas GROUP BY granularidad
    """)

    # P15
    d["p15_dia"] = q("SELECT * FROM marts.p15_ventas_por_dia_semana ORDER BY dia_semana")
    d["p15_tipo"] = q("SELECT * FROM marts.p15_ventas_feriado_vs_normal ORDER BY ingreso_prom_por_dia_usd DESC")
    d["p15_fer"] = q("SELECT * FROM marts.p15_ventas_por_feriado ORDER BY ingreso_usd DESC")

    # P16
    d["p16"] = q("SELECT * FROM marts.p16_ticket_por_tipo_cliente ORDER BY ticket_promedio_usd DESC")

    # P18
    d["p18"] = q("SELECT * FROM marts.p18_mix_monedas ORDER BY pct_por_monto DESC")
    d["p18_mes"] = q("SELECT * FROM marts.p18_mix_monedas_mensual ORDER BY mes_inicio, moneda")

    # P19
    d["p19_mes"] = q("SELECT * FROM marts.p19_tipo_cambio_mensual ORDER BY mes_inicio")
    d["p19_corr"] = q("SELECT * FROM marts.p19_correlacion_fx").iloc[0]
    d["p19_moneda"] = q("SELECT * FROM marts.p19_margen_por_moneda ORDER BY margen_pct DESC")

    return d


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def _estilo_ejes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#C9D2DA")
    ax.spines["bottom"].set_color("#C9D2DA")
    ax.tick_params(colors="#4A4A4A", labelsize=8)
    ax.grid(axis="y", color="#E4E9ED", linewidth=0.8)
    ax.set_axisbelow(True)


def _guardar(fig, nombre):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ruta = FIG_DIR / nombre
    fig.savefig(ruta, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(ruta)


def fig_p1(d):
    df = d["p1_cant"].head(10).iloc[::-1]
    etiquetas = [f"{r.codigo}" for r in df.itertuples()]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.0))
    a1.barh(etiquetas, df["unidades_vendidas"], color=PLT_AZUL, height=0.65)
    a1.set_title("Top 10 por unidades vendidas", fontsize=10, color="#1F3B57", pad=10)
    a1.set_xlabel("unidades", fontsize=8)
    dm = d["p1_monto"].head(10).iloc[::-1]
    a2.barh([f"{r.codigo}" for r in dm.itertuples()], dm["monto_vendido_usd"],
            color=PLT_NARANJA, height=0.65)
    a2.set_title("Top 10 por monto facturado (USD)", fontsize=10, color="#1F3B57", pad=10)
    a2.set_xlabel("USD", fontsize=8)
    for a in (a1, a2):
        _estilo_ejes(a)
        a.grid(axis="x", color="#E4E9ED", linewidth=0.8)
        a.grid(axis="y", visible=False)
    fig.tight_layout()
    return _guardar(fig, "p1_top.png")


def fig_p4(d):
    df = d["p4_cat"].head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    ax.barh(df["categoria"], df["margen_usd"], color=PLT_VERDE, height=0.6)
    for i, (m, p) in enumerate(zip(df["margen_usd"], df["margen_pct_sobre_ingreso"])):
        ax.text(float(m) * 1.01, i, f"{float(p):.1f}%", va="center", fontsize=7.5, color="#4A4A4A")
    ax.set_title("Margen absoluto por categoría (USD) — la etiqueta es el margen %",
                 fontsize=10, color="#1F3B57", pad=10)
    ax.set_xlabel("margen USD", fontsize=8)
    _estilo_ejes(ax)
    ax.grid(axis="x", color="#E4E9ED", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, float(df["margen_usd"].max()) * 1.12)
    fig.tight_layout()
    return _guardar(fig, "p4_margen.png")


def fig_p6(d):
    df = d["p6_resumen"].sort_values("capital_inmovilizado_usd")
    fig, ax = plt.subplots(figsize=(9.2, 3.2))
    colores = ["#A62B2B" if "MUERTO" in c or "NUNCA" in c
               else "#C8672A" if "LENTA" in c
               else "#D9B44A" if "ATENCI" in c
               else "#2E7D5B" for c in df["clasificacion"]]
    ax.barh(df["clasificacion"], df["capital_inmovilizado_usd"], color=colores, height=0.6)
    for i, (v, p) in enumerate(zip(df["capital_inmovilizado_usd"], df["pct_del_capital_total"])):
        ax.text(float(v) * 1.01, i, f"{float(p):.1f}%", va="center", fontsize=8, color="#4A4A4A")
    ax.set_title("Capital inmovilizado por clase de rotación (USD)",
                 fontsize=10, color="#1F3B57", pad=10)
    _estilo_ejes(ax)
    ax.grid(axis="x", color="#E4E9ED", linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, float(df["capital_inmovilizado_usd"].max()) * 1.15)
    fig.tight_layout()
    return _guardar(fig, "p6_capital.png")


def fig_p13(d):
    df = d["p13_mes"]
    x = pd.to_datetime(df["periodo_inicio"])
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.plot(x, df["ingreso_usd"].astype(float), color=PLT_AZUL, linewidth=2, marker="o",
            markersize=4, label="Ingreso USD")
    ax.plot(x, df["margen_usd"].astype(float), color=PLT_VERDE, linewidth=1.6,
            linestyle="--", label="Margen USD")
    prom = float(df["ingreso_usd"].astype(float).mean())
    ax.axhline(prom, color=PLT_GRIS, linewidth=1, linestyle=":", label=f"Promedio ({prom:,.0f})")
    ax.set_title("Evolución mensual del ingreso y el margen (USD)",
                 fontsize=10, color="#1F3B57", pad=10)
    ax.legend(fontsize=8, frameon=False)
    _estilo_ejes(ax)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    return _guardar(fig, "p13_evolucion.png")


def fig_p15(d):
    df = d["p15_dia"]
    fig, ax = plt.subplots(figsize=(9.2, 3.2))
    colores = [PLT_NARANJA if b else PLT_AZUL for b in df["es_fin_de_semana"]]
    ax.bar(df["nombre_dia"], df["ingreso_prom_por_dia_usd"].astype(float), color=colores, width=0.6)
    for i, v in enumerate(df["ingreso_prom_por_dia_usd"].astype(float)):
        ax.text(i, v * 1.02, f"{v:,.0f}", ha="center", fontsize=8, color="#4A4A4A")
    ax.set_title("Ingreso promedio por día calendario (USD) — naranja = fin de semana",
                 fontsize=10, color="#1F3B57", pad=10)
    _estilo_ejes(ax)
    ax.set_ylim(0, float(df["ingreso_prom_por_dia_usd"].astype(float).max()) * 1.15)
    fig.tight_layout()
    return _guardar(fig, "p15_dias.png")


def fig_p18(d):
    df = d["p18"]
    mapa = {"BS": PLT_AZUL, "USD": PLT_VERDE, "COP": PLT_NARANJA}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.4),
                                 gridspec_kw={"width_ratios": [1, 1.5]})
    a1.pie(df["pct_por_monto"].astype(float), labels=df["moneda"],
           colors=[mapa.get(m, PLT_GRIS) for m in df["moneda"]],
           autopct="%1.1f%%", startangle=90,
           textprops={"fontsize": 9, "color": "#333333"},
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    a1.set_title("Mix por monto facturado", fontsize=10, color="#1F3B57")

    piv = d["p18_mes"].pivot(index="mes_inicio", columns="moneda", values="pct_del_mes").fillna(0)
    x = pd.to_datetime(piv.index)
    abajo = pd.Series(0.0, index=piv.index)
    for m in ["BS", "USD", "COP"]:
        if m in piv.columns:
            a2.bar(x, piv[m].astype(float), bottom=abajo, width=22,
                   color=mapa[m], label=m)
            abajo = abajo + piv[m].astype(float)
    a2.set_title("Mix mensual (% del ingreso del mes) — mismos colores que el gráfico de la izquierda",
                 fontsize=9, color="#1F3B57")
    a2.set_ylim(0, 100)
    _estilo_ejes(a2)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    return _guardar(fig, "p18_monedas.png")


def fig_p19(d):
    df = d["p19_mes"]
    x = pd.to_datetime(df["mes_inicio"])
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.plot(x, df["tasa_bs_usd_prom"].astype(float), color=PLT_NARANJA, linewidth=2,
            marker="o", markersize=3.5, label="Tasa Bs/USD (prom. mensual)")
    ax.set_ylabel("Bs por USD", fontsize=8, color=PLT_NARANJA)
    ax.tick_params(axis="y", labelcolor=PLT_NARANJA)
    _estilo_ejes(ax)

    ax2 = ax.twinx()
    ax2.plot(x, df["margen_pct"].astype(float), color=PLT_AZUL, linewidth=1.8, label="Margen %")
    ax2.set_ylabel("margen %", fontsize=8, color=PLT_AZUL)
    ax2.tick_params(axis="y", labelcolor=PLT_AZUL, labelsize=8)
    ax2.set_ylim(20, 26)
    ax2.spines["top"].set_visible(False)

    ax.set_title("Devaluación del bolívar frente al margen porcentual",
                 fontsize=10, color="#1F3B57", pad=10)
    lineas = ax.get_lines() + ax2.get_lines()
    ax.legend(lineas, [l.get_label() for l in lineas], fontsize=8, frameon=False, loc="upper left")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    return _guardar(fig, "p19_fx.png")


# --------------------------------------------------------------------------- #
# Estilos de documento
# --------------------------------------------------------------------------- #
def construir_estilos():
    s = getSampleStyleSheet()
    e = {}
    e["titulo_portada"] = ParagraphStyle("tp", parent=s["Title"], fontName="Helvetica-Bold",
                                         fontSize=26, leading=31, textColor=AZUL, alignment=TA_CENTER)
    e["sub_portada"] = ParagraphStyle("sp", parent=s["Normal"], fontSize=13, leading=18,
                                      textColor=GRIS, alignment=TA_CENTER)
    e["meta_portada"] = ParagraphStyle("mp", parent=s["Normal"], fontSize=9.5, leading=15,
                                       textColor=GRIS, alignment=TA_CENTER)
    e["h1"] = ParagraphStyle("h1", parent=s["Heading1"], fontName="Helvetica-Bold",
                             fontSize=16, leading=20, textColor=AZUL, spaceBefore=4, spaceAfter=10)
    e["h2"] = ParagraphStyle("h2", parent=s["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11.5, leading=15, textColor=AZUL_CLARO,
                             spaceBefore=12, spaceAfter=6, keepWithNext=1)
    e["body"] = ParagraphStyle("body", parent=s["BodyText"], fontSize=9.5, leading=14.5,
                               textColor=GRIS, alignment=TA_JUSTIFY, spaceAfter=7)
    e["pregunta"] = ParagraphStyle("pg", parent=s["Normal"], fontName="Helvetica-Oblique",
                                   fontSize=11, leading=15, textColor=colors.white,
                                   leftIndent=8, rightIndent=8, spaceBefore=6, spaceAfter=6)
    e["nota"] = ParagraphStyle("nt", parent=s["Normal"], fontSize=8.2, leading=11.5,
                               textColor=colors.HexColor("#6B7885"))
    e["celda"] = ParagraphStyle("cl", parent=s["Normal"], fontSize=7.4, leading=9.4,
                                textColor=GRIS)
    e["celda_cab"] = ParagraphStyle("clc", parent=s["Normal"], fontName="Helvetica-Bold",
                                    fontSize=7.4, leading=9.4, textColor=colors.white)
    e["kpi_num"] = ParagraphStyle("kn", parent=s["Normal"], fontName="Helvetica-Bold",
                                  fontSize=15, leading=18, textColor=AZUL, alignment=TA_CENTER)
    e["kpi_lbl"] = ParagraphStyle("kl", parent=s["Normal"], fontSize=7.6, leading=10,
                                  textColor=GRIS, alignment=TA_CENTER)
    return e


def banner_pregunta(numero, texto, est):
    p = Paragraph(f"<b>Pregunta {numero}.</b> {texto}", est["pregunta"])
    t = Table([[p]], colWidths=[17.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def tabla(df, est, columnas=None, anchos=None, alinear_der=None, resaltar=None):
    """DataFrame -> Table con estilo uniforme."""
    cols = columnas or list(df.columns)
    cab = [Paragraph(str(c), est["celda_cab"]) for c in cols]
    filas = [cab]
    for _, r in df.iterrows():
        filas.append([Paragraph("" if pd.isna(v) else str(v), est["celda"]) for v in r.tolist()])

    t = Table(filas, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D3DBE2")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_SUAVE]),
    ]
    if alinear_der:
        for c in alinear_der:
            estilo.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    if resaltar:
        for fila, color in resaltar:
            estilo.append(("TEXTCOLOR", (0, fila), (-1, fila), color))
    t.setStyle(TableStyle(estilo))
    return t


def bloque(S, titulo, df, est, anchos, alinear_der=None, nota=None, juntar=True):
    """Agrega un h2 + tabla, manteniéndolos en la misma página si la tabla es corta."""
    piezas = [Paragraph(titulo, est["h2"]), tabla(df, est, anchos=anchos, alinear_der=alinear_der)]
    if nota:
        piezas.append(Spacer(1, 0.1 * cm))
        piezas.append(Paragraph(nota, est["nota"]))
    if juntar and len(df) <= 12:
        S.append(KeepTogether(piezas))
    else:
        S.extend(piezas)
    S.append(Spacer(1, 0.4 * cm))


def fila_kpi(items, est):
    """items: lista de (valor, etiqueta)."""
    celdas = []
    for valor, etiqueta in items:
        celdas.append([Paragraph(valor, est["kpi_num"]), Paragraph(etiqueta, est["kpi_lbl"])])
    fila = [Table([[c[0]], [c[1]]], colWidths=[17.4 / len(items) * cm - 6]) for c in celdas]
    t = Table([fila], colWidths=[17.4 / len(items) * cm] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_SUAVE),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D3DBE2")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def hallazgo(texto, est, color=AZUL_CLARO):
    p = Paragraph(texto, est["body"])
    t = Table([[p]], colWidths=[17.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8FA")),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


# --------------------------------------------------------------------------- #
# Formateo
# --------------------------------------------------------------------------- #
def usd(v, dec=2):
    if pd.isna(v):
        return "-"
    return f"{float(v):,.{dec}f}"


def pct(v, dec=2):
    if pd.isna(v):
        return "-"
    return f"{float(v):,.{dec}f}%"


def ent(v):
    if pd.isna(v):
        return "-"
    return f"{int(v):,}"


def corta(s, n=38):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# Documento
# --------------------------------------------------------------------------- #
def pie_pagina(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(colors.HexColor("#D3DBE2"))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(2.1 * cm, 1.55 * cm, A4[0] - 2.1 * cm, 1.55 * cm)
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(colors.HexColor("#6B7885"))
    canvas_obj.drawString(2.1 * cm, 1.1 * cm,
                          "Data Warehouse de Repuestos Automotrices  ·  Respuestas a las preguntas de negocio")
    canvas_obj.drawRightString(A4[0] - 2.1 * cm, 1.1 * cm, f"Pág. {canvas_obj.getPageNumber()}")
    canvas_obj.restoreState()


def construir(d, est):
    doc = BaseDocTemplate(str(PDF_PATH), pagesize=A4,
                          leftMargin=2.1 * cm, rightMargin=2.1 * cm,
                          topMargin=1.9 * cm, bottomMargin=2.1 * cm,
                          title="Respuestas a las preguntas de negocio - Data Warehouse de repuestos",
                          author="Data Warehouse de Repuestos Automotrices")
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="portada", frames=[marco]),
        PageTemplate(id="cuerpo", frames=[marco], onPage=pie_pagina),
    ])

    S = []
    t = d["totales"]
    mg = d["margen_global"]

    # ---------------- Portada ----------------
    S.append(Spacer(1, 4.2 * cm))
    S.append(Paragraph("Data Warehouse de<br/>Repuestos Automotrices", est["titulo_portada"]))
    S.append(Spacer(1, 0.5 * cm))
    S.append(Paragraph("Respuestas a las preguntas de negocio", est["sub_portada"]))
    S.append(Spacer(1, 0.25 * cm))
    linea = Table([[""]], colWidths=[5 * cm], rowHeights=[2])
    linea.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NARANJA)]))
    linea.hAlign = "CENTER"
    S.append(linea)
    S.append(Spacer(1, 1.3 * cm))
    S.append(Paragraph(
        f"Preguntas 1, 4, 6, 13, 15, 16, 18 y 19<br/><br/>"
        f"Período analizado: {t['desde']:%d/%m/%Y} — {t['hasta']:%d/%m/%Y}<br/>"
        f"Fuente: esquema <b>marts</b> del data warehouse<br/>"
        f"Generado el {date.today():%d/%m/%Y}",
        est["meta_portada"]))
    S.append(Spacer(1, 2.6 * cm))
    S.append(fila_kpi([
        (ent(t["facturas"]), "facturas"),
        (usd(t["ingreso_usd"], 0), "ingreso USD"),
        (ent(t["unidades"]), "unidades"),
        (pct(mg["margen_pct"], 1), "margen global"),
    ], est))
    S.append(NextPageTemplate("cuerpo"))
    S.append(PageBreak())

    # ---------------- Resumen ejecutivo ----------------
    S.append(Paragraph("Resumen ejecutivo", est["h1"]))
    S.append(Paragraph(
        f"El data warehouse consolida <b>{ent(t['lineas'])} líneas de venta</b> repartidas en "
        f"<b>{ent(t['facturas'])} facturas</b> emitidas entre el {t['desde']:%d/%m/%Y} y el "
        f"{t['hasta']:%d/%m/%Y} — 24 meses completos. El ingreso acumulado, normalizado a dólares "
        f"con la tasa del día de cada operación, asciende a <b>USD {usd(t['ingreso_usd'], 0)}</b>, "
        f"sobre el que se obtiene un margen bruto de <b>USD {usd(mg['margen'], 0)}</b> "
        f"({pct(mg['margen_pct'], 2)}).", est["body"]))
    S.append(Paragraph(
        "Las ocho preguntas seleccionadas se responden con tablas materializadas en el esquema "
        "<b>marts</b>, alimentadas por el modelo estrella del esquema <b>core</b>. Cada sección de "
        "este informe indica la tabla exacta de la que provienen sus cifras, de modo que cualquier "
        "número sea reproducible con una consulta.", est["body"]))

    S.append(Spacer(1, 0.2 * cm))
    S.append(Paragraph("Hallazgos principales", est["h2"]))

    p1c = d["p1_cant"].iloc[0]
    p1m = d["p1_monto"].iloc[0]
    p6k = d["p6_kpi"]
    p15 = d["p15_dia"].sort_values("ingreso_prom_por_dia_usd", ascending=False).iloc[0]
    p15b = d["p15_dia"].sort_values("ingreso_prom_por_dia_usd").iloc[0]
    p16 = d["p16"]
    p18 = d["p18"]
    p19c = d["p19_corr"]
    p4s = d["p4_stats"]

    fx_ini = float(d["p19_mes"].iloc[0]["tasa_bs_usd_prom"])
    fx_fin = float(d["p19_mes"].iloc[-1]["tasa_bs_usd_prom"])

    p1div = d["p1_diverge"].iloc[0]
    puntos = [
        ("1", f"{corta(p1c['descripcion'], 34)} encabeza <b>ambos</b> rankings "
              f"({ent(p1c['unidades_vendidas'])} u. y USD {usd(p1c['monto_vendido_usd'], 0)}), pero las "
              f"dos listas solo coinciden en {ent(d['p1_solape']['en_ambos'])} de 13 productos. El caso "
              f"extremo: {corta(p1div['descripcion'], 30)} es apenas el "
              f"#{ent(p1div['ranking_por_cantidad'])} en unidades y el "
              f"#{ent(p1div['ranking_por_monto'])} en facturación."),
        ("4", f"El margen es <b>estructuralmente uniforme</b>: {pct(mg['margen_pct'], 2)} global, y "
              f"{ent(p4s['en_banda'])} de {ent(p4s['productos'])} productos "
              f"({100 * float(p4s['en_banda']) / float(p4s['productos']):.1f}%) caen en la banda "
              f"22,5–23,5%. La lista de precios aplica un recargo fijo sobre el costo, así que "
              f"comparar el margen <i>porcentual</i> entre categorías no discrimina: lo que decide "
              f"es el margen <b>absoluto</b>."),
        ("6", f"<b>{ent(p6k['productos_muertos'])} productos</b> llevan 180 días o más sin venderse "
              f"(o nunca se vendieron) e inmovilizan <b>USD {usd(p6k['capital_muerto'], 0)}</b>, el "
              f"{100 * float(p6k['capital_muerto']) / float(p6k['capital_total']):.1f}% del capital "
              f"total en inventario."),
        ("13", f"El negocio crece de forma sostenida: el ingreso mensual promedio pasó de "
               f"USD {usd(d['p13_mes'].head(6)['ingreso_usd'].astype(float).mean(), 0)} en el primer "
               f"semestre a USD {usd(d['p13_mes'].tail(6)['ingreso_usd'].astype(float).mean(), 0)} en "
               f"el último, con estacionalidad marcada en diciembre."),
        ("15", f"El <b>{p15['nombre_dia'].lower()}</b> es el mejor día: USD {usd(p15['ingreso_prom_por_dia_usd'], 0)} "
               f"por jornada, un {100 * (float(p15['ingreso_prom_por_dia_usd']) / float(p15b['ingreso_prom_por_dia_usd']) - 1):.0f}% "
               f"por encima del {p15b['nombre_dia'].lower()}. Los feriados, en cambio, rinden por debajo del promedio."),
        ("16", f"El ticket promedio es notablemente parejo entre segmentos "
               f"(USD {usd(p16['ticket_promedio_usd'].min(), 0)}–{usd(p16['ticket_promedio_usd'].max(), 0)}). "
               f"La diferencia entre tipos de cliente está en el <b>volumen</b>, no en el tamaño de la compra."),
        ("18", f"Más de la mitad de la facturación se cobra en bolívares ({pct(p18.iloc[0]['pct_por_monto'], 1)}); "
               f"el dólar aporta {pct(float(p18[p18['moneda'] == 'USD']['pct_por_monto'].iloc[0]), 1)} y el peso "
               f"colombiano {pct(float(p18[p18['moneda'] == 'COP']['pct_por_monto'].iloc[0]), 1)}."),
        ("19", f"El bolívar se devaluó de {usd(fx_ini, 2)} a {usd(fx_fin, 2)} Bs/USD "
               f"({100 * (fx_fin / fx_ini - 1):,.0f}% en 24 meses) sin que el margen porcentual se erosione "
               f"(correlación con el ingreso: {float(p19c['corr_devaluacion_vs_var_ingreso']):.3f}). "
               f"La indexación al dólar está funcionando."),
    ]
    for num, txt in puntos:
        S.append(hallazgo(f"<b><font color='#C8672A'>P{num}</font></b> &nbsp; {txt}", est))
        S.append(Spacer(1, 0.15 * cm))

    S.append(PageBreak())

    # ---------------- Metodología ----------------
    S.append(Paragraph("Metodología y arquitectura", est["h1"]))
    S.append(Paragraph(
        "El pipeline se ejecuta en tres etapas encadenadas por <b>run_pipeline.py</b>:", est["body"]))
    etapas = pd.DataFrame([
        ["1. staging", "ETL en Python (pandas + SQLAlchemy)",
         "Carga cruda de los Excel de origen. Normaliza nombres de columna, descarta filas vacías y añade columnas de auditoría. Sin castings ni reglas de negocio."],
        ["2. core", "SQL — sql/core/*.sql",
         "Modelo estrella: 6 dimensiones y 3 tablas de hechos. Aquí ocurren el tipado, la deduplicación por clave natural, la resolución de claves subrogadas y la conversión de todo importe a USD con la tasa del día."],
        ["3. marts", "SQL — sql/marts/*.sql",
         "Una o más tablas por pregunta de negocio. Es la capa que consume este informe."],
    ], columns=["Etapa", "Implementación", "Qué hace"])
    S.append(tabla(etapas, est, anchos=[2.4 * cm, 4.6 * cm, 10.4 * cm]))
    S.append(Spacer(1, 0.45 * cm))

    S.append(Paragraph("Volumen del modelo", est["h2"]))
    cts = d["conteos"].copy()
    cts["filas"] = cts["filas"].apply(ent)
    mitad = (len(cts) + 1) // 2
    izq = cts.iloc[:mitad].reset_index(drop=True)
    der = cts.iloc[mitad:].reset_index(drop=True)
    combinado = pd.DataFrame({
        "Tabla": izq["tabla"], "Filas": izq["filas"],
        "Tabla ": der["tabla"], "Filas ": der["filas"],
    })
    S.append(tabla(combinado, est, anchos=[5.2 * cm, 3.5 * cm, 5.2 * cm, 3.5 * cm],
                   alinear_der=[1, 3]))
    S.append(Spacer(1, 0.45 * cm))

    S.append(Paragraph("Criterios de cálculo comunes", est["h2"]))
    criterios = pd.DataFrame([
        ["Ingreso", "fact_ventas.subtotal_usd — importe normalizado a USD con la tasa vigente el día de la venta. El monto en la moneda de cobro se conserva en subtotal_mon."],
        ["Margen bruto", "subtotal_usd − (cantidad × dim_producto.costo_usd). Es el margen de lo efectivamente vendido, no el teórico de la lista de precios."],
        ["Ticket", "Total de la factura completa (nro_factura), no de la línea. Las consultas consolidan a nivel de factura antes de promediar."],
        ["Fecha de corte", f"{p6k['fecha_corte']:%d/%m/%Y} — última fecha con ventas registradas. Se usa como \"hoy\" en la pregunta 6 para no depender de CURRENT_DATE."],
        ["Tipo de cliente", "Prefijo del documento: J = taller/empresa, V = particular, E = extranjero."],
    ], columns=["Concepto", "Definición operativa"])
    S.append(tabla(criterios, est, anchos=[3.3 * cm, 14.1 * cm]))

    S.append(PageBreak())

    # =================== P1 ===================
    S.append(banner_pregunta(1, "¿Cuáles son los 10 repuestos más vendidos por cantidad y por monto?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "Ambos rankings se calculan sobre la misma tabla <b>marts.p01_top_productos</b>, que conserva "
        "las dos posiciones para cada producto. Separarlos importa: un repuesto barato de alta "
        "rotación domina el ranking por unidades pero puede aportar menos facturación que uno caro "
        "de rotación media.", est["body"]))
    S.append(Image(fig_p1(d), width=17.4 * cm, height=7.55 * cm))
    S.append(Spacer(1, 0.35 * cm))

    anchos_top = [0.9 * cm, 2.2 * cm, 7.0 * cm, 2.3 * cm, 1.6 * cm, 2.2 * cm, 1.2 * cm]
    for titulo, clave in [("Top 10 por cantidad vendida", "p1_cant"),
                          ("Top 10 por monto facturado", "p1_monto")]:
        df = d[clave].head(10)
        tb = pd.DataFrame({
            "#": df["rk"].apply(ent),
            "Código": df["codigo"],
            "Descripción": df["descripcion"].apply(lambda s: corta(s, 44)),
            "Marca": df["marca"],
            "Unid.": df["unidades_vendidas"].apply(ent),
            "Monto USD": df["monto_vendido_usd"].apply(lambda v: usd(v, 0)),
            "Fact.": df["nro_facturas"].apply(ent),
        })
        bloque(S, titulo, tb, est, anchos_top, [4, 5, 6])

    df = d["p1_diverge"]
    tb = pd.DataFrame({
        "Código": df["codigo"],
        "Descripción": df["descripcion"].apply(lambda s: corta(s, 40)),
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Monto USD": df["monto_vendido_usd"].apply(lambda v: usd(v, 0)),
        "Puesto x cantidad": df["ranking_por_cantidad"].apply(lambda v: f"#{ent(v)}"),
        "Puesto x monto": df["ranking_por_monto"].apply(lambda v: f"#{ent(v)}"),
        "Brecha": df["brecha"].apply(ent),
    })
    bloque(S, "Dónde más se separan los dos rankings", tb, est,
           [2.2 * cm, 5.4 * cm, 1.5 * cm, 2.1 * cm, 2.4 * cm, 2.2 * cm, 1.6 * cm], [2, 3, 4, 5, 6])

    sol = d["p1_solape"]
    S.append(hallazgo(
        f"<b>Lectura.</b> {corta(p1c['descripcion'], 40)} encabeza las dos listas, así que es la "
        f"referencia crítica del inventario: lidera en rotación <i>y</i> en facturación. Pero el "
        f"solapamiento no va mucho más allá — de los 13 productos que entran en algún top 10, solo "
        f"<b>{ent(sol['en_ambos'])} aparecen en ambos</b>; {ent(sol['solo_cantidad'])} entran únicamente "
        f"por volumen y {ent(sol['solo_monto'])} únicamente por monto.<br/><br/>"
        f"El contraste más ilustrativo son los kits de embrague: {corta(p1div['descripcion'], 34)} vende "
        f"apenas {ent(p1div['unidades_vendidas'])} unidades —puesto "
        f"#{ent(p1div['ranking_por_cantidad'])} en rotación— pero factura "
        f"USD {usd(p1div['monto_vendido_usd'], 0)}, que lo coloca "
        f"#{ent(p1div['ranking_por_monto'])} por monto. Son piezas caras de baja rotación: un quiebre de "
        f"stock ahí cuesta mucho más que en un repuesto de mostrador. Por eso la tabla conserva los dos "
        f"rankings en lugar de uno solo.", est, NARANJA))
    S.append(Paragraph("Fuente: <b>marts.p01_top_productos</b>", est["nota"]))

    S.append(PageBreak())

    # =================== P4 ===================
    S.append(banner_pregunta(4, "¿Cuál es el margen de ganancia por producto, marca y categoría?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "Los tres niveles se resuelven en una sola tabla, <b>marts.p04_margen</b>, mediante "
        "GROUPING SETS; la columna <i>nivel</i> distingue a qué agregación pertenece cada fila "
        f"({ent(d['p4_niveles'].get('PRODUCTO', 0))} productos, "
        f"{ent(d['p4_niveles'].get('MARCA', 0))} marcas y "
        f"{ent(d['p4_niveles'].get('CATEGORIA', 0))} categorías). "
        "El margen es el <i>realizado</i>: ingreso facturado menos costo de la mercancía "
        "efectivamente despachada.", est["body"]))
    S.append(Image(fig_p4(d), width=17.4 * cm, height=7.2 * cm))
    S.append(Spacer(1, 0.3 * cm))

    df = d["p4_cat"].head(10)
    tb = pd.DataFrame({
        "Categoría": df["categoria"],
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Costo USD": df["costo_mercancia_usd"].apply(lambda v: usd(v, 0)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 0)),
        "Margen %": df["margen_pct_sobre_ingreso"].apply(lambda v: pct(v, 2)),
    })
    bloque(S, "Margen por categoría (top 10 en margen absoluto)", tb, est,
           [4.4 * cm, 2.0 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm, 2.6 * cm], [1, 2, 3, 4, 5])

    df = d["p4_marca"].head(10)
    tb = pd.DataFrame({
        "Marca": df["marca"],
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 0)),
        "Margen %": df["margen_pct_sobre_ingreso"].apply(lambda v: pct(v, 2)),
    })
    bloque(S, "Margen por marca (top 10 en margen absoluto)", tb, est,
           [5.0 * cm, 2.6 * cm, 3.4 * cm, 3.4 * cm, 3.0 * cm], [1, 2, 3, 4])

    S.append(Paragraph("El margen porcentual no discrimina: es un recargo fijo", est["h2"]))
    S.append(Paragraph(
        f"Conviene ser explícito con este resultado, porque condiciona cómo debe leerse toda la "
        f"pregunta. El margen porcentual <b>no varía de forma significativa entre categorías, marcas "
        f"ni productos</b>: {ent(p4s['en_banda'])} de {ent(p4s['productos'])} referencias vendidas "
        f"({100 * float(p4s['en_banda']) / float(p4s['productos']):.1f}%) caen dentro de la banda "
        f"22,5%–23,5%, un rango de un solo punto porcentual. La lista de precios de origen aplica un "
        f"recargo prácticamente constante sobre el costo, y eso se propaga intacto a cualquier "
        f"agregación. La desviación estándar del conjunto ({usd(p4s['pct_desv'], 2)} p.p.) parece alta "
        f"solo porque la inflan las {ent(int(p4s['productos']) - int(p4s['en_banda']))} referencias que "
        f"quedan fuera de esa banda, todas ellas artículos de precio unitario muy bajo.", est["body"]))
    S.append(Paragraph(
        f"La consecuencia práctica: <b>ordenar categorías o marcas por margen porcentual no aporta "
        f"información</b> —todas rinden igual— y la decisión de surtido debe apoyarse en el margen "
        f"<i>absoluto</i> en dólares, que sí discrimina y es el criterio usado en las tablas "
        f"anteriores. Las categorías KIT y BASE aportan margen no por ser más rentables por unidad "
        f"vendida, sino por mover más volumen y mayor valor.", est["body"]))
    S.append(Spacer(1, 0.15 * cm))

    S.append(Paragraph("Las únicas excepciones: ventas por debajo del costo", est["h2"]))
    S.append(Paragraph(
        f"Los extremos del rango ({pct(p4s['pct_min'], 1)} a {pct(p4s['pct_max'], 1)}) corresponden a "
        f"un puñado de casos aislados. Solo <b>{ent(p4s['con_perdida'])} referencias de "
        f"{ent(p4s['productos'])} generaron margen negativo</b>, y la pérdida acumulada es de "
        f"USD {usd(abs(float(p4s['perdida_usd'])), 2)} — una cifra irrelevante frente al margen total "
        f"de USD {usd(mg['margen'], 0)}. Se listan por completitud y como control de calidad del dato: "
        f"son artículos de muy bajo precio unitario donde el costo quedó desactualizado, no una fuga "
        f"de rentabilidad.", est["body"]))
    S.append(Spacer(1, 0.15 * cm))
    df = d["p4_prod_neg"]
    tb = pd.DataFrame({
        "Código": df["codigo"],
        "Descripción": df["descripcion"].apply(lambda s: corta(s, 40)),
        "Marca": df["marca"],
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 2)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 2)),
        "Margen %": df["margen_pct_sobre_ingreso"].apply(lambda v: pct(v, 1)),
    })
    S.append(tabla(tb, est, anchos=[2.2 * cm, 6.2 * cm, 2.4 * cm, 1.5 * cm, 2.0 * cm, 1.9 * cm, 1.8 * cm],
                   alinear_der=[3, 4, 5, 6]))
    S.append(Spacer(1, 0.4 * cm))

    S.append(Paragraph("Productos más rentables en margen absoluto", est["h2"]))
    df = d["p4_prod_top"]
    tb = pd.DataFrame({
        "Código": df["codigo"],
        "Descripción": df["descripcion"].apply(lambda s: corta(s, 40)),
        "Marca": df["marca"],
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 0)),
        "Margen %": df["margen_pct_sobre_ingreso"].apply(lambda v: pct(v, 1)),
    })
    S.append(tabla(tb, est, anchos=[2.2 * cm, 6.2 * cm, 2.4 * cm, 1.5 * cm, 2.0 * cm, 1.9 * cm, 1.8 * cm],
                   alinear_der=[3, 4, 5, 6]))
    S.append(Spacer(1, 0.4 * cm))

    cat1 = d["p4_cat"].iloc[0]
    mar1 = d["p4_marca"].iloc[0]
    S.append(hallazgo(
        f"<b>Lectura.</b> El margen bruto global es de USD {usd(mg['margen'], 0)} sobre "
        f"USD {usd(mg['ingreso'], 0)} facturados, es decir {pct(mg['margen_pct'], 2)}. Ese "
        f"porcentaje se repite casi sin variación en los tres niveles pedidos, porque la política de "
        f"precios es un recargo fijo sobre costo — un hallazgo en sí mismo, y el que hay que reportar "
        f"al responder esta pregunta.<br/><br/>"
        f"Con el porcentaje neutralizado, el ranking relevante es el de margen absoluto: la categoría "
        f"<b>{cat1['categoria']}</b> aporta USD {usd(cat1['margen_usd'], 0)} y la marca "
        f"<b>{mar1['marca']}</b> USD {usd(mar1['margen_usd'], 0)}, encabezando cada nivel. La palanca "
        f"para mejorar rentabilidad no está en cambiar el mix hacia categorías «más rentables» —no las "
        f"hay— sino en subir volumen donde el margen unitario ya es mayor en dólares, o en revisar el "
        f"recargo mismo.", est, VERDE))
    S.append(Paragraph("Fuente: <b>marts.p04_margen</b> (niveles PRODUCTO, MARCA y CATEGORIA)", est["nota"]))

    S.append(PageBreak())

    # =================== P6 ===================
    S.append(banner_pregunta(6, "¿Qué productos llevan más tiempo sin venderse (inventario muerto) y cuánto capital inmovilizan?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        f"El stock actual de cada producto se toma del <i>stock_resultante</i> de su último "
        f"movimiento de inventario, y los días sin vender se miden contra la fecha de corte "
        f"({p6k['fecha_corte']:%d/%m/%Y}). El capital inmovilizado es stock × costo unitario en USD. "
        f"Se considera <b>inventario muerto</b> todo producto con 180 días o más sin una venta, más "
        f"los que nunca se vendieron.", est["body"]))
    S.append(Spacer(1, 0.2 * cm))
    S.append(fila_kpi([
        (ent(p6k["productos_muertos"]), "productos sin rotar"),
        (usd(p6k["capital_muerto"], 0), "USD inmovilizados"),
        (f"{100 * float(p6k['capital_muerto']) / float(p6k['capital_total']):.1f}%", "del capital en inventario"),
        (ent(p6k["dias_max"]), "días del caso extremo"),
    ], est))
    S.append(Spacer(1, 0.45 * cm))
    S.append(Image(fig_p6(d), width=17.4 * cm, height=6.0 * cm))
    S.append(Spacer(1, 0.3 * cm))

    df = d["p6_resumen"]
    tb = pd.DataFrame({
        "Clasificación": df["clasificacion"],
        "Productos": df["nro_productos"].apply(ent),
        "Unid. en stock": df["unidades_en_stock"].apply(ent),
        "Capital USD": df["capital_inmovilizado_usd"].apply(lambda v: usd(v, 0)),
        "% capital": df["pct_del_capital_total"].apply(lambda v: pct(v, 1)),
        "Días s/vender (prom.)": df["dias_sin_vender_prom"].apply(lambda v: usd(v, 0)),
    })
    bloque(S, "Capital inmovilizado por clase de rotación", tb, est,
           [5.4 * cm, 2.0 * cm, 2.6 * cm, 2.6 * cm, 2.0 * cm, 2.8 * cm], [1, 2, 3, 4, 5])

    S.append(Paragraph("Los 15 productos que más capital inmovilizan", est["h2"]))
    df = d["p6_top"]
    tb = pd.DataFrame({
        "Código": df["codigo"],
        "Descripción": df["descripcion"].apply(lambda s: corta(s, 34)),
        "Stock": df["stock_actual"].apply(ent),
        "Costo USD": df["costo_usd"].apply(lambda v: usd(v, 2)),
        "Capital USD": df["capital_inmovilizado_usd"].apply(lambda v: usd(v, 0)),
        "Últ. venta": df["fecha_ultima_venta"].apply(lambda v: "nunca" if pd.isna(v) else f"{v:%d/%m/%Y}"),
        "Días": df["dias_sin_vender"].apply(ent),
    })
    S.append(tabla(tb, est, anchos=[2.1 * cm, 5.5 * cm, 1.4 * cm, 1.9 * cm, 2.1 * cm, 2.3 * cm, 1.4 * cm],
                   alinear_der=[2, 3, 4, 6]))
    S.append(Spacer(1, 0.4 * cm))

    fila_muerto = df.iloc[0]
    S.append(hallazgo(
        f"<b>Lectura.</b> Cerca de <b>USD {usd(p6k['capital_muerto'], 0)}</b> están dormidos en "
        f"estantería —el {100 * float(p6k['capital_muerto']) / float(p6k['capital_total']):.1f}% de todo "
        f"el capital en inventario— repartidos en {ent(p6k['productos_muertos'])} referencias. "
        f"El peor caso individual es {corta(fila_muerto['descripcion'], 36)}, con "
        f"{ent(fila_muerto['stock_actual'])} unidades y USD {usd(fila_muerto['capital_inmovilizado_usd'], 0)} "
        f"detenidos. Este es el insumo natural para una campaña de liquidación o para renegociar "
        f"devoluciones con el proveedor.", est, ROJO))
    S.append(Paragraph("Fuente: <b>marts.p06_inventario_muerto</b> y <b>marts.p06_inventario_muerto_resumen</b>",
                       est["nota"]))

    S.append(PageBreak())

    # =================== P13 ===================
    S.append(banner_pregunta(13, "¿Cómo evolucionan las ventas por día, semana, mes y año?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "La tabla <b>marts.p13_evolucion_ventas</b> apila las cuatro granularidades en una sola "
        "estructura (columna <i>granularidad</i>), cada una con su variación respecto al período "
        "anterior y su acumulado. Esto permite responder la pregunta completa sin cambiar de tabla.",
        est["body"]))
    S.append(Image(fig_p13(d), width=17.4 * cm, height=6.8 * cm))
    S.append(Spacer(1, 0.3 * cm))

    df = d["p13_stats"].set_index("granularidad").reindex(["DIA", "SEMANA", "MES", "ANIO"]).reset_index()
    tb = pd.DataFrame({
        "Granularidad": df["granularidad"],
        "Períodos": df["periodos"].apply(ent),
        "Ingreso promedio USD": df["promedio"].apply(lambda v: usd(v, 2)),
        "Mínimo USD": df["minimo"].apply(lambda v: usd(v, 2)),
        "Máximo USD": df["maximo"].apply(lambda v: usd(v, 2)),
    })
    bloque(S, "Resumen por granularidad", tb, est,
           [3.4 * cm, 2.6 * cm, 4.2 * cm, 3.6 * cm, 3.6 * cm], [1, 2, 3, 4])

    df = d["p13_anio"]
    tb = pd.DataFrame({
        "Año": df["periodo"],
        "Facturas": df["nro_facturas"].apply(ent),
        "Unidades": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 0)),
        "Ticket USD": df["ticket_promedio_usd"].apply(lambda v: usd(v, 2)),
    })
    bloque(S, "Evolución anual", tb, est,
           [2.0 * cm, 2.8 * cm, 2.8 * cm, 3.4 * cm, 3.4 * cm, 3.0 * cm], [1, 2, 3, 4, 5],
           nota="Nota: 2024 recoge solo julio–diciembre y 2026 solo enero–junio. La comparación año "
                "contra año no es homogénea; la lectura válida es la mensual.")

    S.append(Paragraph("Evolución mensual", est["h2"]))
    df = d["p13_mes"]
    tb = pd.DataFrame({
        "Mes": df["periodo"],
        "Fact.": df["nro_facturas"].apply(ent),
        "Unid.": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 0)),
        "Ticket USD": df["ticket_promedio_usd"].apply(lambda v: usd(v, 2)),
        "Var. %": df["variacion_pct_vs_periodo_anterior"].apply(lambda v: "—" if pd.isna(v) else pct(v, 1)),
    })
    S.append(tabla(tb, est, anchos=[2.0 * cm, 1.7 * cm, 1.7 * cm, 3.2 * cm, 3.2 * cm, 3.0 * cm, 2.6 * cm],
                   alinear_der=[1, 2, 3, 4, 5, 6]))
    S.append(Spacer(1, 0.4 * cm))

    mejor = d["p13_mes"].loc[d["p13_mes"]["ingreso_usd"].astype(float).idxmax()]
    peor = d["p13_mes"].loc[d["p13_mes"]["ingreso_usd"].astype(float).idxmin()]
    S.append(hallazgo(
        f"<b>Lectura.</b> El ingreso mensual oscila entre USD {usd(peor['ingreso_usd'], 0)} "
        f"({peor['periodo']}) y USD {usd(mejor['ingreso_usd'], 0)} ({mejor['periodo']}), con una "
        f"tendencia claramente ascendente: el promedio del primer semestre analizado "
        f"(USD {usd(d['p13_mes'].head(6)['ingreso_usd'].astype(float).mean(), 0)}) queda por debajo del "
        f"último (USD {usd(d['p13_mes'].tail(6)['ingreso_usd'].astype(float).mean(), 0)}). Diciembre repunta "
        f"los dos años, y enero–febrero caen: es el patrón estacional típico del sector.", est))
    S.append(Paragraph("Fuente: <b>marts.p13_evolucion_ventas</b>", est["nota"]))

    S.append(PageBreak())

    # =================== P15 ===================
    S.append(banner_pregunta(15, "¿Qué días de la semana o feriados presentan mayor volumen de ventas?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "Se reporta el total y el <b>promedio por día calendario</b>. La distinción es necesaria: el "
        "total crudo premia al día de la semana que más veces cae dentro del período, mientras que el "
        "promedio mide la productividad real de esa jornada.", est["body"]))
    S.append(Image(fig_p15(d), width=17.4 * cm, height=6.0 * cm))
    S.append(Spacer(1, 0.3 * cm))

    df = d["p15_dia"]
    tb = pd.DataFrame({
        "Día": df["nombre_dia"],
        "Jornadas": df["dias_con_ventas"].apply(ent),
        "Facturas": df["nro_facturas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Prom./día USD": df["ingreso_prom_por_dia_usd"].apply(lambda v: usd(v, 2)),
        "Ticket USD": df["ticket_promedio_usd"].apply(lambda v: usd(v, 2)),
        "% ingreso": df["pct_del_ingreso_total"].apply(lambda v: pct(v, 1)),
    })
    bloque(S, "Volumen por día de la semana", tb, est,
           [2.3 * cm, 2.0 * cm, 2.2 * cm, 2.8 * cm, 3.0 * cm, 2.6 * cm, 2.5 * cm], [1, 2, 3, 4, 5, 6],
           nota="El domingo no aparece porque no hay ninguna venta registrada en domingo en los "
                "24 meses: el local no abre.")

    df = d["p15_tipo"]
    tb = pd.DataFrame({
        "Tipo de día": df["tipo_dia"],
        "Jornadas": df["dias_con_ventas"].apply(ent),
        "Facturas": df["nro_facturas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Prom./día USD": df["ingreso_prom_por_dia_usd"].apply(lambda v: usd(v, 2)),
        "Ticket USD": df["ticket_promedio_usd"].apply(lambda v: usd(v, 2)),
        "% ingreso": df["pct_del_ingreso_total"].apply(lambda v: pct(v, 1)),
    })
    bloque(S, "Feriado, fin de semana y día laborable", tb, est,
           [3.2 * cm, 2.0 * cm, 2.2 * cm, 2.8 * cm, 2.8 * cm, 2.3 * cm, 2.1 * cm], [1, 2, 3, 4, 5, 6])

    df = d["p15_fer"]
    tb = pd.DataFrame({
        "Feriado": df["nombre_feriado"],
        "Jornadas": df["dias_con_ventas"].apply(ent),
        "Facturas": df["nro_facturas"].apply(ent),
        "Unidades": df["unidades_vendidas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 2)),
        "Prom./día USD": df["ingreso_prom_por_dia_usd"].apply(lambda v: usd(v, 2)),
    })
    bloque(S, "Detalle por feriado con actividad", tb, est,
           [5.6 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.6 * cm, 2.6 * cm], [1, 2, 3, 4, 5])

    fer = d["p15_tipo"][d["p15_tipo"]["tipo_dia"] == "FERIADO"]
    lab = d["p15_tipo"][d["p15_tipo"]["tipo_dia"] == "DIA LABORABLE"]
    S.append(hallazgo(
        f"<b>Lectura.</b> El {p15['nombre_dia'].lower()} concentra la mayor productividad diaria "
        f"(USD {usd(p15['ingreso_prom_por_dia_usd'], 0)}), seguido del viernes: el cliente compra "
        f"repuestos al cierre de la semana, cuando dispone de tiempo para el taller. En el extremo "
        f"opuesto, los feriados rinden USD {usd(fer.iloc[0]['ingreso_prom_por_dia_usd'], 0)} por jornada "
        f"frente a USD {usd(lab.iloc[0]['ingreso_prom_por_dia_usd'], 0)} de un día laborable normal — "
        f"y los únicos dos feriados con actividad son de media jornada (Nochebuena y Fin de Año). "
        f"Abrir en feriado no rinde; reforzar personal el sábado, sí.", est, NARANJA))
    S.append(Paragraph("Fuente: <b>marts.p15_ventas_por_dia_semana</b>, "
                       "<b>marts.p15_ventas_feriado_vs_normal</b> y <b>marts.p15_ventas_por_feriado</b>",
                       est["nota"]))

    S.append(PageBreak())

    # =================== P16 ===================
    S.append(banner_pregunta(16, "¿Cuál es el ticket promedio por tipo de cliente (taller/empresa, particular, extranjero)?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "El ticket se calcula sobre la <b>factura completa</b>: <b>marts.p16_ticket_por_tipo_cliente</b> "
        "consolida primero las líneas de venta por <i>nro_factura</i> y recién después promedia por "
        "segmento. Promediar líneas en lugar de facturas habría dado un valor mucho menor y sin "
        "significado comercial.", est["body"]))
    S.append(Spacer(1, 0.2 * cm))

    df = d["p16"]
    tb = pd.DataFrame({
        "Tipo de cliente": df["tipo_cliente"],
        "Facturas": df["nro_facturas"].apply(ent),
        "Ingreso USD": df["ingreso_total_usd"].apply(lambda v: usd(v, 0)),
        "Ticket prom.": df["ticket_promedio_usd"].apply(lambda v: usd(v, 2)),
        "Ticket mediano": df["ticket_mediano_usd"].apply(lambda v: usd(v, 2)),
        "Ticket máx.": df["ticket_maximo_usd"].apply(lambda v: usd(v, 2)),
        "% ingreso": df["pct_del_ingreso_total"].apply(lambda v: pct(v, 1)),
    })
    bloque(S, "Ticket promedio por segmento", tb, est,
           [4.4 * cm, 1.9 * cm, 2.4 * cm, 2.3 * cm, 2.4 * cm, 2.1 * cm, 1.9 * cm], [1, 2, 3, 4, 5, 6])

    tb = pd.DataFrame({
        "Tipo de cliente": df["tipo_cliente"],
        "Líneas por factura": df["lineas_promedio_por_factura"].apply(lambda v: usd(v, 2)),
        "Unidades por factura": df["unidades_promedio_por_factura"].apply(lambda v: usd(v, 2)),
        "Unidades totales": df["unidades_vendidas"].apply(ent),
        "Ticket mínimo USD": df["ticket_minimo_usd"].apply(lambda v: usd(v, 2)),
    })
    bloque(S, "Composición de la compra", tb, est,
           [4.6 * cm, 3.4 * cm, 3.6 * cm, 3.0 * cm, 2.8 * cm], [1, 2, 3, 4])

    jur = df[df["codigo_tipo"] == "J"].iloc[0]
    par = df[df["codigo_tipo"] == "V"].iloc[0]
    ext = df[df["codigo_tipo"] == "E"].iloc[0]
    sd = df[df["codigo_tipo"] == "SD"]
    S.append(hallazgo(
        f"<b>Lectura.</b> El ticket promedio apenas se mueve entre segmentos: "
        f"particular USD {usd(par['ticket_promedio_usd'], 2)}, extranjero "
        f"USD {usd(ext['ticket_promedio_usd'], 2)}, taller/empresa USD {usd(jur['ticket_promedio_usd'], 2)}. "
        f"La mediana confirma el patrón (~USD {usd(df['ticket_mediano_usd'].median(), 0)} en todos). "
        f"Lo que diferencia a los segmentos es el <b>volumen de operaciones</b>: los particulares "
        f"aportan {ent(par['nro_facturas'])} facturas y el {pct(par['pct_del_ingreso_total'], 1)} del "
        f"ingreso, los talleres {ent(jur['nro_facturas'])} y {pct(jur['pct_del_ingreso_total'], 1)}. "
        f"Contrario a lo esperado, <b>el taller no compra más grande que el particular</b> — compra "
        f"igual de grande, pero con la misma frecuencia. Eso abre una oportunidad clara de venta "
        f"cruzada y de listas de precio diferenciadas por volumen.", est))
    if len(sd):
        S.append(Spacer(1, 0.15 * cm))
        S.append(Paragraph(
            f"Nota metodológica: {ent(sd.iloc[0]['nro_facturas'])} facturas "
            f"({pct(sd.iloc[0]['pct_del_ingreso_total'], 1)} del ingreso) no traen documento de cliente "
            f"en el archivo de origen — son ventas de mostrador. Se muestran como categoría propia en "
            f"lugar de excluirlas, para que los porcentajes sumen el 100% de la facturación real.",
            est["nota"]))
    S.append(Spacer(1, 0.2 * cm))
    S.append(Paragraph("Fuente: <b>marts.p16_ticket_por_tipo_cliente</b>", est["nota"]))

    S.append(PageBreak())

    # =================== P18 ===================
    S.append(banner_pregunta(18, "¿Qué porcentaje de las ventas se realiza en bolívares, dólares y pesos colombianos?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "La tabla <b>marts.p18_mix_monedas</b> ofrece tres lecturas del mismo mix —por monto "
        "facturado, por número de facturas y por unidades— porque no tienen por qué coincidir: si "
        "una moneda concentrara las operaciones grandes, su peso por monto superaría al de facturas.",
        est["body"]))
    S.append(Image(fig_p18(d), width=17.4 * cm, height=6.4 * cm))
    S.append(Spacer(1, 0.3 * cm))

    df = d["p18"]
    tb = pd.DataFrame({
        "Moneda": df["moneda_nombre"] + " (" + df["moneda"] + ")",
        "Facturas": df["nro_facturas"].apply(ent),
        "Monto en moneda original": df["monto_en_moneda_original"].apply(lambda v: usd(v, 2)),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 2)),
        "% monto": df["pct_por_monto"].apply(lambda v: pct(v, 2)),
        "% facturas": df["pct_por_nro_facturas"].apply(lambda v: pct(v, 2)),
        "% unidades": df["pct_por_unidades"].apply(lambda v: pct(v, 2)),
    })
    bloque(S, "Mix de monedas", tb, est,
           [3.6 * cm, 1.8 * cm, 3.6 * cm, 2.6 * cm, 1.95 * cm, 1.95 * cm, 1.9 * cm], [1, 2, 3, 4, 5, 6])

    bs = df[df["moneda"] == "BS"].iloc[0]
    us = df[df["moneda"] == "USD"].iloc[0]
    cop = df[df["moneda"] == "COP"].iloc[0]
    S.append(hallazgo(
        f"<b>Lectura.</b> El bolívar sigue siendo la moneda dominante con "
        f"{pct(bs['pct_por_monto'], 2)} del monto facturado, seguido del dólar "
        f"({pct(us['pct_por_monto'], 2)}) y el peso colombiano ({pct(cop['pct_por_monto'], 2)}). "
        f"El dato relevante es que las tres lecturas coinciden casi exactamente —monto, facturas y "
        f"unidades difieren en menos de un punto porcentual— lo que significa que <b>la moneda de "
        f"cobro no depende del tamaño de la compra</b>: no hay un segmento que reserve el dólar para "
        f"operaciones grandes. La presencia del peso colombiano en uno de cada siete dólares "
        f"facturados confirma además el peso del cliente fronterizo.", est, VERDE))
    S.append(Spacer(1, 0.2 * cm))
    S.append(Paragraph(
        "El gráfico de la derecha muestra el mix mes a mes: la proporción se mantiene estable a lo "
        "largo de los 24 meses, sin desplazamiento hacia la dolarización pese a la devaluación del "
        "período (ver pregunta 19).", est["body"]))
    S.append(Paragraph("Fuente: <b>marts.p18_mix_monedas</b> y <b>marts.p18_mix_monedas_mensual</b>",
                       est["nota"]))

    S.append(PageBreak())

    # =================== P19 ===================
    S.append(banner_pregunta(19, "¿Cómo afecta la variación del tipo de cambio a los ingresos y márgenes de ganancia?", est))
    S.append(Spacer(1, 0.35 * cm))
    S.append(Paragraph(
        "Se construye una serie mensual con la tasa Bs/USD promedio, su variación intermensual y, en "
        "paralelo, el ingreso, el costo y el margen expresados en dólares. Como todo importe se "
        "normaliza a USD con la tasa del día de la operación, el efecto del tipo de cambio no "
        "desaparece: se manifiesta en el margen cuando el precio de lista no se ajusta al mismo ritmo "
        "que la tasa.", est["body"]))
    S.append(Image(fig_p19(d), width=17.4 * cm, height=6.8 * cm))
    S.append(Spacer(1, 0.25 * cm))

    corr = pd.DataFrame([
        ["Devaluación mensual  vs  variación del ingreso USD",
         f"{float(p19c['corr_devaluacion_vs_var_ingreso']):.4f}",
         "Sin relación: el ingreso en dólares es indiferente a la tasa."],
        ["Devaluación mensual  vs  variación del margen USD",
         f"{float(p19c['corr_devaluacion_vs_var_margen']):.4f}",
         "Sin relación: el margen absoluto tampoco depende de la tasa."],
        ["Devaluación mensual  vs  cambio en el margen %",
         f"{float(p19c['corr_devaluacion_vs_delta_margen_pct']):.4f}",
         "Relación moderada y positiva: en los meses de salto cambiario el margen porcentual mejora ligeramente."],
        ["Devaluación mensual  vs  exposición a moneda extranjera",
         f"{float(p19c['corr_devaluacion_vs_exposicion_fx']):.4f}",
         "Relación débil: la clientela no migra al dólar cuando la tasa salta."],
    ], columns=["Par analizado", "r", "Interpretación"])
    bloque(S, "Correlaciones observadas", corr, est, [6.4 * cm, 1.6 * cm, 9.4 * cm], [1],
           nota=f"Calculado sobre {ent(p19c['meses_comparables'])} meses comparables (el primero no "
                f"tiene mes previo con el cual variar).")

    df = d["p19_moneda"]
    tb = pd.DataFrame({
        "Moneda": df["moneda"],
        "Facturas": df["nro_facturas"].apply(ent),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 2)),
        "Costo USD": df["costo_usd"].apply(lambda v: usd(v, 2)),
        "Margen USD": df["margen_usd"].apply(lambda v: usd(v, 2)),
        "Margen %": df["margen_pct"].apply(lambda v: pct(v, 2)),
        "Desvío vs lista": df["desvio_pct_vs_precio_lista_usd"].apply(lambda v: pct(v, 2)),
    })
    bloque(S, "Margen según la moneda de cobro", tb, est,
           [1.9 * cm, 2.0 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm, 2.2 * cm, 2.3 * cm], [1, 2, 3, 4, 5, 6])

    S.append(Paragraph("Serie mensual completa", est["h2"]))
    df = d["p19_mes"]
    tb = pd.DataFrame({
        "Mes": df["mes"],
        "Tasa Bs/USD": df["tasa_bs_usd_prom"].apply(lambda v: usd(v, 2)),
        "Δ tasa": df["var_pct_tasa_bs_usd"].apply(lambda v: "—" if pd.isna(v) else pct(v, 1)),
        "Ingreso USD": df["ingreso_usd"].apply(lambda v: usd(v, 0)),
        "Δ ingreso": df["var_pct_ingreso_usd"].apply(lambda v: "—" if pd.isna(v) else pct(v, 1)),
        "Margen %": df["margen_pct"].apply(lambda v: pct(v, 2)),
        "Δ margen (p.p.)": df["delta_puntos_margen_pct"].apply(lambda v: "—" if pd.isna(v) else usd(v, 2)),
        "% expuesto FX": df["pct_ingreso_expuesto_a_fx"].apply(lambda v: pct(v, 1)),
    })
    S.append(tabla(tb, est, anchos=[1.9 * cm, 2.3 * cm, 1.9 * cm, 2.5 * cm, 2.1 * cm, 2.0 * cm, 2.4 * cm, 2.3 * cm],
                   alinear_der=[1, 2, 3, 4, 5, 6, 7]))
    S.append(Spacer(1, 0.4 * cm))

    dev_total = 100 * (fx_fin / fx_ini - 1)
    mg_ini = float(d["p19_mes"].iloc[0]["margen_pct"])
    mg_fin = float(d["p19_mes"].iloc[-1]["margen_pct"])
    exp_prom = float(d["p19_mes"]["pct_ingreso_expuesto_a_fx"].astype(float).mean())
    S.append(hallazgo(
        f"<b>Lectura.</b> En los 24 meses el bolívar pasó de {usd(fx_ini, 2)} a {usd(fx_fin, 2)} Bs/USD, "
        f"una devaluación acumulada del <b>{dev_total:,.0f}%</b>. Pese a ello el margen porcentual se "
        f"mantuvo entre {pct(mg_ini, 2)} y {pct(mg_fin, 2)}, prácticamente plano, y la correlación entre "
        f"devaluación y variación del ingreso en dólares es nula "
        f"({float(p19c['corr_devaluacion_vs_var_ingreso']):.3f}). La conclusión es que <b>la política de "
        f"precios indexados al dólar está protegiendo la rentabilidad</b>: el negocio piensa en dólares "
        f"y solo cobra en bolívares.<br/><br/>"
        f"El riesgo, sin embargo, es real y cuantificable: en promedio el <b>{exp_prom:.1f}% del ingreso "
        f"mensual se cobra en moneda distinta al dólar</b> (Bs o COP). Ese porcentaje es la exposición "
        f"efectiva al tipo de cambio — el tramo de la facturación donde un desfase entre la fijación "
        f"del precio y el momento del cobro se traduce directamente en pérdida de margen. La "
        f"correlación positiva de {float(p19c['corr_devaluacion_vs_delta_margen_pct']):.2f} entre "
        f"devaluación y cambio del margen porcentual sugiere que el ajuste de precios se aplica con "
        f"cierta anticipación al salto de la tasa, no después.", est, VERDE))
    S.append(Paragraph("Fuente: <b>marts.p19_tipo_cambio_mensual</b>, <b>marts.p19_correlacion_fx</b> "
                       "y <b>marts.p19_margen_por_moneda</b>", est["nota"]))

    S.append(PageBreak())

    # ---------------- Cierre ----------------
    S.append(Paragraph("Reproducibilidad y limitaciones", est["h1"]))
    S.append(Paragraph("Cómo reproducir estas cifras", est["h2"]))
    S.append(Paragraph(
        "Todo el contenido de este informe se genera desde el esquema <b>marts</b>. Para regenerarlo "
        "de cero:", est["body"]))
    pasos = pd.DataFrame([
        ["1", "docker compose up -d", "Levanta la instancia de PostgreSQL."],
        ["2", "python run_pipeline.py", "Ejecuta staging (Python), luego sql/core y sql/marts en orden alfabético."],
        ["3", "python reports/generate_report.py", "Consulta las tablas de marts y produce este PDF."],
    ], columns=["#", "Comando", "Qué hace"])
    S.append(tabla(pasos, est, anchos=[0.9 * cm, 6.5 * cm, 10.0 * cm]))
    S.append(Spacer(1, 0.45 * cm))

    S.append(Paragraph("Limitaciones a tener presentes", est["h2"]))
    lims = pd.DataFrame([
        ["Años parciales",
         "El período cubre julio 2024 – junio 2026. Los años 2024 y 2026 están incompletos, por lo que la comparación interanual de la pregunta 13 no es homogénea. La serie mensual sí lo es."],
        ["Margen uniforme por lista",
         f"La lista de precios de origen aplica un recargo prácticamente constante ({ent(p4s['en_banda'])} de {ent(p4s['productos'])} productos entre 22,5% y 23,5%). El margen porcentual, por tanto, no discrimina entre categorías, marcas ni productos: la pregunta 4 debe leerse en margen absoluto."],
        ["Ventas sin cliente",
         f"{ent(int(sd.iloc[0]['nro_facturas'])) if len(sd) else '0'} facturas no traen documento de cliente en el origen. Se reportan como segmento propio en la pregunta 16 en lugar de excluirse."],
        ["Stock puntual, no histórico",
         "El capital inmovilizado de la pregunta 6 usa el último stock conocido de cada producto. No es una valoración de inventario a una fecha arbitraria del pasado."],
        ["Tasa promedio mensual",
         "La pregunta 19 promedia la tasa sobre el calendario completo del mes, sin ponderar por volumen de ventas. Una ponderación por facturación desplazaría levemente los valores."],
    ], columns=["Aspecto", "Alcance"])
    S.append(tabla(lims, est, anchos=[3.8 * cm, 13.6 * cm]))
    S.append(Spacer(1, 0.6 * cm))

    S.append(Paragraph("Índice de tablas del esquema marts", est["h2"]))
    idx = pd.DataFrame([
        ["1", "p01_top_productos", "02_p01_top_productos.sql"],
        ["4", "p04_margen", "03_p04_margen.sql"],
        ["6", "p06_inventario_muerto · p06_inventario_muerto_resumen", "04_p06_inventario_muerto.sql"],
        ["13", "p13_evolucion_ventas", "05_p13_evolucion_ventas.sql"],
        ["15", "p15_ventas_por_dia_semana · p15_ventas_feriado_vs_normal · p15_ventas_por_feriado", "06_p15_dias_feriados.sql"],
        ["16", "p16_ticket_por_tipo_cliente", "07_p16_ticket_tipo_cliente.sql"],
        ["18", "p18_mix_monedas · p18_mix_monedas_mensual", "08_p18_mix_monedas.sql"],
        ["19", "p19_tipo_cambio_mensual · p19_correlacion_fx · p19_margen_por_moneda", "09_p19_impacto_tipo_cambio.sql"],
    ], columns=["Preg.", "Tablas", "Archivo fuente"])
    S.append(tabla(idx, est, anchos=[1.3 * cm, 9.6 * cm, 6.5 * cm]))

    doc.build(S)


def main():
    os.chdir(Path(__file__).resolve().parent.parent)
    engine = get_db_engine()
    print("Consultando el data warehouse...")
    d = cargar_datos(engine)
    est = construir_estilos()
    print("Generando PDF...")
    construir(d, est)
    print(f"Listo: {PDF_PATH}")


if __name__ == "__main__":
    main()
