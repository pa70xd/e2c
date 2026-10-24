from config.customers.heineken.columns_names import COL_ARCHIVO, COL_FILA_EXCEL
from config.customers.heineken.reglas_heineken import SERIE_GENERICA
from repository.heineken.consultas_postgre import DB_HEINEKEN

db = DB_HEINEKEN()
ACTIVO_RELLENO = "123456789"


def asignar_series_genericas(duck_conn, tabla: str, request_code: str | None = None) -> dict[str, dict[int, str]]:
    """Reemplaza SERIE_GENERICA por una serie de Postgres (prefijo HEI/MOB según la FALLA).
    En un reenvío reutiliza la serie pendiente del mismo cliente/ACTIVO/FALLA.
    Regresa {archivo: {fila_excel: serie}} para escribirla en el original."""

    filas = duck_conn.execute(f"""
        SELECT rowid, "PREFIJO_SERIE", "CLIENTE DETALLISTA", "ACTIVO", "FALLA",
               "{COL_ARCHIVO}", "{COL_FILA_EXCEL}"
        FROM "{tabla}"
        WHERE UPPER(TRIM("SERIE")) = ? AND "PREFIJO_SERIE" IS NOT NULL
        ORDER BY CAST("{COL_FILA_EXCEL}" AS INTEGER)
    """, [SERIE_GENERICA]).fetchall()

    asignadas: dict[str, dict[int, str]] = {}
    usadas: list[str] = []
    for rowid, prefijo, cliente, activo, falla, archivo, fila in filas:
        serie = None
        if request_code:
            activo = None if activo == ACTIVO_RELLENO else activo
            serie = db.serie_generica_pendiente(request_code, cliente, activo, falla, usadas)
        serie = serie or db.generar_serie_generica(prefijo)
        usadas.append(serie)
        duck_conn.execute(f'UPDATE "{tabla}" SET "SERIE" = ? WHERE rowid = ?', [serie, rowid])
        asignadas.setdefault(archivo, {})[int(fila)] = serie

    return asignadas


def es_serie_generica(serie: str | None) -> bool:
    return (serie or "").strip().upper() == SERIE_GENERICA
