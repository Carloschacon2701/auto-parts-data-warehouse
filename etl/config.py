"""Single source of truth for what to load and where."""
import logging
from dotenv import load_dotenv

load_dotenv()

STG_SCHEMA = "staging"
CHUNK_SIZE = 10000
LOG_LEVEL = logging.INFO

SOURCES = [
    ("docs/raw_clientes.xlsx",                    "CLIENTES",         "stg_clientes"),
    ("docs/raw_usuarios.xlsx",                    "USUARIOS",         "stg_usuarios"),
    ("docs/raw_ventas.xlsx",                      "VENTAS",           "stg_ventas_header"),
    ("docs/raw_ventas.xlsx",                      "DETALLE_VENTAS",   "stg_ventas_detalle"),
    ("docs/raw_compras.xlsx",                     "COMPRAS",          "stg_compras_header"),
    ("docs/raw_compras.xlsx",                     "DETALLE_COMPRAS",  "stg_compras_detalle"),
    ("docs/raw_movimientos_inventario.xlsx",      "MOVIMIENTOS",      "stg_movimientos_inventario"),
    ("docs/raw_feriados.xlsx",                    "FERIADOS",         "stg_feriados"),
    ("docs/LISTA_MARINO_MOTORS_Bs_USD_COP.xlsx",  "LISTA",            "stg_productos"),
]
