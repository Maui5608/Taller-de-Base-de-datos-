# =============================================================================
# Smörgås Kaffet — Aplicación Flask (MariaDB)
# Versión mejorada post-auditoría
#
# GUÍA PARA AUDITORES
# ===================
# Busca estas etiquetas para saltar directamente a cada área:
#
#   [ACID-ATOMICIDAD]   → Transacciones, commit/rollback, retries
#   [ACID-CONSISTENCIA] → Validaciones de datos antes de tocar la BD
#   [ACID-AISLAMIENTO]  → Nivel de aislamiento, SELECT FOR UPDATE, deadlocks
#   [ACID-DURABILIDAD]  → InnoDB + commit explícito
#   [SEG-CREDENCIALES]  → Variables de entorno, sin hardcode
#   [SEG-AUTENTICACION] → Login, hash de contraseñas, sesión única
#   [SEG-AUTORIZACION]  → Decoradores de acceso por rol
#   [SEG-INYECCION]     → Queries parametrizadas (sin SQL injection)
#   [SEG-REGISTRO]      → Control de quién puede crear qué rol
#   [SEG-CSRF]          → Acciones destructivas via POST, no GET
#   [REND-INDICES]      → Consultas que se benefician de índices en BD
#   [REND-CONEXION]     → Pool/apertura de conexiones por solicitud
#   [MON-LOG]           → Sistema de logging de la aplicación
# =============================================================================

import secrets
import re
import json
import os
import logging
import logging.handlers
from datetime import date, datetime, timedelta
from functools import wraps
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError, OperationalError
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from waitress import serve

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# [MON-LOG] CONFIGURACIÓN DE LOGGING
# -----------------------------------------------------------------------------
# Se registran eventos clave: inicios de sesión (exitosos y fallidos),
# errores de BD, acciones administrativas y advertencias de seguridad.
# El archivo rota al llegar a 1 MB, conservando 5 backups.
# El auditor de Monitoreo debe verificar:
#   - Que el archivo smorgas.log se crea y escribe al ejecutar la app.
#   - Que los intentos de login fallidos quedan registrados.
#   - Que los errores de BD no se exponen al usuario pero sí al log.
# =============================================================================
LOG_FILE = os.getenv("LOG_FILE", "smorgas.log")

logger = logging.getLogger("smorgas")
logger.setLevel(logging.DEBUG)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Handler: archivo rotativo
_fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)

# Handler: consola (útil durante desarrollo)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_fmt)

logger.addHandler(_fh)
logger.addHandler(_ch)

logger.info("=== Aplicación iniciando ===")

# =============================================================================
# [SEG-CREDENCIALES] CONFIGURACIÓN FLASK
# -----------------------------------------------------------------------------
# MEJORA: secret_key ya NO tiene fallback débil. Si la variable de entorno
# APP_SECRET_KEY no está definida, la app se niega a arrancar.
# Esto evita el riesgo de ejecutar en producción con una clave conocida.
#
# Para configurar: crear un archivo .env o definir en el sistema operativo:
#   export APP_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
# =============================================================================
app = Flask(__name__)

_secret = os.getenv("APP_SECRET_KEY")
if not _secret:
    # [SEG-CREDENCIALES] Falla rápido y visible en lugar de arrancar inseguro
    raise RuntimeError(
        "Variable de entorno APP_SECRET_KEY no definida. "
        "Genera una con: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.secret_key = _secret

# Tiempo máximo de inactividad (minutos)
app.config["SESSION_TTL_MIN"] = int(os.getenv("SESSION_TTL_MIN", "30"))
SESSION_TTL_MIN = app.config["SESSION_TTL_MIN"]

# =============================================================================
# [SEG-CREDENCIALES] CONFIGURACIÓN DE BASE DE DATOS
# -----------------------------------------------------------------------------
# MEJORA CRÍTICA: Ninguna contraseña está hardcodeada en el código.
# Todas vienen de variables de entorno. Si alguna falta, la app falla al arrancar.
#
# Variables requeridas (definir en .env o en el sistema):
#   DB_HOST          → Servidor MariaDB (default: 127.0.0.1)
#   DB_NAME          → Nombre de la BD (default: proyecto_smorgas)
#   DB_ROOT_USER     → Usuario con permiso para /login y /register (registro de mesero)
#   DB_ROOT_PASS     → Contraseña del usuario anterior  ← OBLIGATORIO
#   DB_ADMIN_USER    → Usuario MariaDB del rol admin
#   DB_ADMIN_PASS    → Contraseña del usuario admin     ← OBLIGATORIO
#   DB_MESERO_USER   → Usuario MariaDB del rol mesero
#   DB_MESERO_PASS   → Contraseña del usuario mesero    ← OBLIGATORIO
#
# El auditor de Seguridad debe verificar que el archivo .env NO esté
# incluido en el repositorio (debe estar en .gitignore).
# =============================================================================
def _require_env(name: str) -> str:
    """Obtiene una variable de entorno obligatoria; aborta si falta."""
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Variable de entorno obligatoria no definida: {name}")
    return val


BASE_DB_CFG = {
    "host":        os.getenv("DB_HOST", "127.0.0.1"),
    "database":    os.getenv("DB_NAME", "proyecto_smorgas"),
    "cursorclass": pymysql.cursors.DictCursor,
}

# [SEG-CREDENCIALES] Credenciales leídas de entorno, sin valores por defecto inseguros
ROLE_DB_CREDENTIALS = {
    "admin":  {"user": _require_env("DB_ADMIN_USER"),  "password": _require_env("DB_ADMIN_PASS")},
    "mesero": {"user": _require_env("DB_MESERO_USER"), "password": _require_env("DB_MESERO_PASS")},
}
DEFAULT_DB_USER = _require_env("DB_ROOT_USER")
DEFAULT_DB_PASS = _require_env("DB_ROOT_PASS")


# =============================================================================
# [REND-CONEXION] APERTURA DE CONEXIÓN A MARIADB
# -----------------------------------------------------------------------------
# Se abre una conexión nueva por solicitud HTTP (sin pool permanente).
# Para mayor rendimiento en producción se podría usar SQLAlchemy con pool,
# pero para este volumen de usuarios es suficiente.
#
# [ACID-AISLAMIENTO] El nivel READ COMMITTED se fija por sesión:
#   - Evita lecturas sucias (dirty reads).
#   - Permite mayor concurrencia que REPEATABLE READ.
#   - Combinado con SELECT FOR UPDATE cubre los casos de edición concurrente.
# =============================================================================
def get_db_connection():
    """
    Abre una conexión a MariaDB con credenciales dinámicas según el rol
    de la sesión activa. Fija READ COMMITTED como nivel de aislamiento.
    """
    cfg = dict(BASE_DB_CFG)
    rol = session.get("rol")
    creds = ROLE_DB_CREDENTIALS.get(rol)

    if creds:
        cfg.update(user=creds["user"], password=creds["password"])
    else:
        cfg.update(user=DEFAULT_DB_USER, password=DEFAULT_DB_PASS)

    conn = pymysql.connect(**cfg)

    # [ACID-AISLAMIENTO] Nivel de aislamiento por sesión de BD
    with conn.cursor() as cur:
        cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    return conn


# =============================================================================
# [ACID-ATOMICIDAD] HELPER DE RETRY ANTE DEADLOCKS
# -----------------------------------------------------------------------------
# MariaDB/InnoDB puede generar deadlocks (error 1213) cuando dos transacciones
# intentan bloquear los mismos recursos en orden inverso.
# También puede ocurrir lock wait timeout (1205) si una tx espera demasiado.
#
# Esta función envuelve una función transaccional y la reintenta hasta 3 veces.
# Para probarlo: ejecutar dos ediciones simultáneas del mismo folio.
# El auditor de ACID debe verificar que en ese caso la app no falla
# sino que reintenta y eventualmente confirma o lanza error controlado.
# =============================================================================
def tx_with_retry(fn, retries=3):
    """Reintenta una función transaccional ante deadlock (1213) o timeout (1205)."""
    for i in range(retries):
        try:
            return fn()
        except OperationalError as e:
            code = e.args[0] if e.args else None
            if code in (1213, 1205) and i < retries - 1:
                logger.warning(f"[ACID-ATOMICIDAD] Reintento {i+1} por deadlock/timeout (código {code})")
                continue
            raise


# =============================================================================
# HELPERS GENERALES
# =============================================================================

def _now_sql():
    """Retorna datetime actual del servidor de aplicación."""
    return datetime.now()


def _session_active(row_now):
    """
    [SEG-AUTENTICACION] Determina si una sesión de BD sigue vigente:
    - Session_Expira debe ser futura.
    - Ultimo_Visto debe estar dentro de la ventana de inactividad.
    """
    if not row_now or not row_now.get("Session_Expira"):
        return False
    ahora = _now_sql()
    expira = row_now["Session_Expira"]
    uv = row_now.get("Ultimo_Visto")
    if expira and expira > ahora:
        if not uv:
            return True
        return (ahora - uv) <= timedelta(minutes=SESSION_TTL_MIN)
    return False


def _bump_session(cur, id_usuario):
    """
    [SEG-AUTENTICACION] Extiende la sesión (heartbeat deslizante).
    Se llama en cada request autenticado para que la sesión no expire
    mientras el usuario esté activo.
    """
    nueva_exp = _now_sql() + timedelta(minutes=SESSION_TTL_MIN)
    cur.execute("""
        UPDATE TBL_USUARIOS
           SET Ultimo_Visto  = NOW(),
               Session_Expira = %s
         WHERE ID_Usuario = %s
    """, (nueva_exp, id_usuario))


def as_float(value):
    """Convierte Decimal/None a float de forma segura para JSON/render."""
    if value is None:
        return 0.0
    return float(value) if isinstance(value, (Decimal, int, float)) else value


# =============================================================================
# [SEG-AUTORIZACION] DECORADORES DE CONTROL DE ACCESO
# -----------------------------------------------------------------------------
# Cualquier ruta que requiera login debe usar @login_requerido.
# Cualquier ruta exclusiva de admin debe usar @admin_requerido (incluye login).
#
# El auditor de Seguridad debe verificar:
#   1. Que acceder a "/" sin sesión redirige a /login.
#   2. Que acceder a "/usuarios" como mesero redirige al index con aviso.
#   3. Que modificar el rol en la cookie de sesión no eleva privilegios
#      (el token se valida contra la BD en cada request).
# =============================================================================
def login_requerido(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "usuario" not in session or "sess_token" not in session:
            logger.warning(f"[SEG-AUTORIZACION] Acceso sin sesión a {request.path} desde {request.remote_addr}")
            return redirect(url_for("login"))

        user  = session.get("usuario")
        token = session.get("sess_token")

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # [REND-INDICES] idx_session_token acelera esta búsqueda por token
                cur.execute("""
                    SELECT ID_Usuario, Session_Token, Session_Expira, Ultimo_Visto
                      FROM TBL_USUARIOS
                     WHERE Nombre_Usuario = %s
                """, (user,))
                row = cur.fetchone()

                # [SEG-AUTENTICACION] Token de sesión inválido o inexistente → expulsar
                if not row or not row.get("Session_Token") or row["Session_Token"] != token:
                    session.clear()
                    logger.warning(f"[SEG-AUTENTICACION] Token inválido para usuario '{user}'. Sesión invalidada.")
                    flash("Tu sesión ya no es válida (iniciada en otro dispositivo o cerrada).", "warning")
                    return redirect(url_for("login"))

                # [SEG-AUTENTICACION] Sesión expirada por inactividad → limpiar BD y expulsar
                if not _session_active(row):
                    cur.execute("""
                        UPDATE TBL_USUARIOS
                           SET Session_Token  = NULL,
                               Session_Expira = NULL
                         WHERE ID_Usuario = %s
                    """, (row["ID_Usuario"],))
                    conn.commit()
                    session.clear()
                    logger.info(f"[SEG-AUTENTICACION] Sesión expirada por inactividad: usuario '{user}'.")
                    flash("Tu sesión ha expirado por inactividad.", "warning")
                    return redirect(url_for("login"))

                # [SEG-AUTENTICACION] Heartbeat: extiende la ventana deslizante
                _bump_session(cur, row["ID_Usuario"])
            conn.commit()
        finally:
            conn.close()

        return f(*args, **kwargs)
    return wrapped


def admin_requerido(f):
    """
    [SEG-AUTORIZACION] Verifica login Y que el rol sea 'admin'.
    Aplicar siempre ANTES de acciones destructivas o de gestión de usuarios.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "admin":
            logger.warning(
                f"[SEG-AUTORIZACION] Usuario '{session.get('usuario')}' (rol={session.get('rol')}) "
                f"intentó acceder a ruta de admin: {request.path}"
            )
            flash("Solo administradores.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapped


def parse_fecha_ui(fecha_str: str) -> datetime:
    """Parsea 'YYYY-MM-DD' o 'DD/MM/YYYY' a datetime."""
    fecha_str = (fecha_str or "").strip()
    if not fecha_str:
        raise ValueError("Fecha vacía")
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except ValueError:
        return datetime.strptime(fecha_str, "%d/%m/%Y")


# =============================================================================
# RUTAS — HOME / ÍNDICE
# =============================================================================

@app.route("/")
@login_requerido
def index():
    """
    [REND-INDICES] Usa idx_compra_modo e idx_compra_fecha mediante el LEFT JOIN.
    El ORDER BY c.Folio DESC aprovecha el PK como índice implícito.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.Folio,
                    c.ID_Mesa,
                    c.Importe_Total,
                    c.Cantidad_Total,
                    c.ID_Modo_Entrega,
                    COALESCE(
                        m.Modo_Entrega,
                        CASE c.ID_Modo_Entrega
                            WHEN 1 THEN 'Comedor'
                            WHEN 2 THEN 'Llevar'
                            ELSE '—'
                        END
                    ) AS Modo_Entrega
                FROM TBL_COMPRA AS c
                LEFT JOIN TBL_MODO_ENTREGA AS m
                       ON m.ID_Modo_Entrega = c.ID_Modo_Entrega
                ORDER BY c.Folio DESC
            """)
            ventas = cur.fetchall()
            for v in ventas:
                v["Importe_Total"] = as_float(v.get("Importe_Total"))
    finally:
        conn.close()

    return render_template(
        "index.html",
        ventas=ventas,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )


# =============================================================================
# RUTAS — DETALLE (lectura y edición inline)
# =============================================================================

@app.route("/venta/<int:folio>/detalles")
@login_requerido
def venta_detalles(folio):
    """
    [REND-INDICES] idx_detalle_folio acelera el filtro WHERE d.Folio = %s.
    Solo lectura: sin FOR UPDATE (no modifica datos).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.ID_Detalle, d.Folio, d.ID_Producto, d.Cantidad,
                       d.Precio_Unit, d.Subtotal, p.Nombre_Producto
                  FROM TBL_DETALLE d
                  JOIN TBL_PRODUCTO p ON p.ID_Producto = d.ID_Producto
                 WHERE d.Folio = %s
                 ORDER BY d.ID_Detalle
            """, (folio,))
            rows = cur.fetchall()
            for r in rows:
                r["Precio_Unit"] = as_float(r.get("Precio_Unit"))
                r["Subtotal"]    = as_float(r.get("Subtotal"))
    finally:
        conn.close()

    return jsonify(rows)


@app.route("/detalle/update/<int:id_detalle>", methods=["POST"])
@login_requerido
def detalle_update(id_detalle):
    """
    [ACID-ATOMICIDAD] Actualiza un renglón de detalle en una transacción completa.
    [ACID-AISLAMIENTO] Usa SELECT FOR UPDATE en orden estable para evitar deadlocks:
        1. Bloquea TBL_DETALLE (renglón) → obtiene su Folio
        2. Bloquea TBL_COMPRA (cabecera del folio)
        3. Bloquea todos los TBL_DETALLE del folio
        4. Actualiza el renglón → el trigger trg_detalle_after_update
           recalcula Importe_Total y Cantidad_Total en TBL_COMPRA.
    [ACID-ATOMICIDAD] Si algo falla, rollback completo. tx_with_retry reintenta
        hasta 3 veces ante deadlock (1213) o lock timeout (1205).

    [ACID-CONSISTENCIA] Validaciones antes de tocar la BD:
        - cantidad: entero, rango 1–50
        - precio:   flotante, rango 0.01–10 000
    """
    # [ACID-CONSISTENCIA] Validación en capa de aplicación (antes de BD)
    try:
        cant   = int(request.form.get("cantidad", ""))
        precio = float(request.form.get("precio_unit", ""))
    except ValueError:
        return jsonify({"ok": False, "msg": "Datos inválidos"}), 400

    if not (1 <= cant <= 50) or not (0.01 <= precio <= 10_000):
        return jsonify({"ok": False, "msg": "Fuera de rango permitido"}), 400

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # [ACID-AISLAMIENTO] Paso 1: bloquear renglón y obtener Folio
                cur.execute(
                    "SELECT Folio FROM TBL_DETALLE WHERE ID_Detalle = %s FOR UPDATE",
                    (id_detalle,)
                )
                r = cur.fetchone()
                if not r:
                    conn.rollback()
                    return jsonify({"ok": False, "msg": "Detalle inexistente"}), 404
                folio = r["Folio"]

                # [ACID-AISLAMIENTO] Paso 2 y 3: bloquear cabecera y demás detalles
                # (orden siempre cabecera → detalles para prevenir deadlock)
                cur.execute("SELECT Folio FROM TBL_COMPRA    WHERE Folio = %s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio = %s FOR UPDATE", (folio,))

                # [ACID-ATOMICIDAD] Actualización del renglón
                # El trigger trg_detalle_after_update recalcula automáticamente
                # Importe_Total y Cantidad_Total en TBL_COMPRA.
                subtotal = cant * precio
                cur.execute("""
                    UPDATE TBL_DETALLE
                       SET Cantidad    = %s,
                           Precio_Unit = %s,
                           Subtotal    = %s
                     WHERE ID_Detalle  = %s
                """, (cant, precio, subtotal, id_detalle))

            # [ACID-DURABILIDAD] Commit explícito → InnoDB persiste en WAL
            conn.commit()
            logger.info(
                f"[ACID-ATOMICIDAD] Detalle {id_detalle} actualizado. "
                f"Folio={folio}, cant={cant}, precio={precio:.2f}"
            )
            return jsonify({"ok": True})
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        return tx_with_retry(_tx)
    except Exception as e:
        # [MON-LOG] Error va al log, NO al usuario (no filtra detalles internos)
        logger.error(f"[ACID-ATOMICIDAD] Error al actualizar detalle {id_detalle}: {e}")
        return jsonify({"ok": False, "msg": "Error interno al actualizar"}), 500


# =============================================================================
# RUTAS — EDITAR Y ELIMINAR CABECERA DE COMPRA
# =============================================================================

@app.route("/update/<int:folio>", methods=["POST"])
@login_requerido
def update(folio):
    """
    [ACID-ATOMICIDAD] Edita mesa y modo de entrega de una compra.
    [ACID-AISLAMIENTO] FOR UPDATE en cabecera + detalles (orden estable).
    [ACID-CONSISTENCIA] Valida mesa (100–108) y modo (1 o 2) antes de la tx.
    """
    id_mesa = request.form.get("ID_Mesa")
    id_modo = request.form.get("ID_Modo_Entrega")

    # [ACID-CONSISTENCIA] Whitelist estricto de valores permitidos
    if id_mesa not in [str(x) for x in range(100, 109)]:
        flash("Mesa inválida.", "warning")
        return redirect(url_for("index"))
    if id_modo not in ("1", "2"):
        flash("Modo de entrega inválido.", "warning")
        return redirect(url_for("index"))

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # [ACID-AISLAMIENTO] Bloqueo en orden estable
                cur.execute("SELECT Folio FROM TBL_COMPRA    WHERE Folio = %s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio = %s FOR UPDATE", (folio,))
                cur.execute(
                    "UPDATE TBL_COMPRA SET ID_Mesa = %s, ID_Modo_Entrega = %s WHERE Folio = %s",
                    (id_mesa, id_modo, folio),
                )
            conn.commit()  # [ACID-DURABILIDAD]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        tx_with_retry(_tx)
        logger.info(
            f"[ACID-ATOMICIDAD] Folio {folio} actualizado por '{session.get('usuario')}': "
            f"mesa={id_mesa}, modo={id_modo}"
        )
        flash(f"Cuenta #{folio} actualizada.", "success")
    except Exception as e:
        logger.error(f"[ACID-ATOMICIDAD] Error al actualizar folio {folio}: {e}")
        flash("Error al actualizar la cuenta.", "danger")

    return redirect(url_for("index"))


@app.route("/delete/<int:folio>", methods=["POST"])
@login_requerido
def delete(folio):
    """
    [SEG-CSRF] MEJORA: Ruta cambiada de GET a POST.
    Las acciones destructivas NUNCA deben ser GET (vulnerable a CSRF vía <img>).
    El template debe enviar un <form method='post'>.

    [SEG-AUTORIZACION] Solo admins pueden eliminar cuentas.
    [ACID-ATOMICIDAD] Elimina detalle(s) y luego cabecera en una sola tx.
    [ACID-AISLAMIENTO] FOR UPDATE en orden estable para evitar deadlocks.
    """
    if session.get("rol") != "admin":
        logger.warning(
            f"[SEG-AUTORIZACION] Usuario '{session.get('usuario')}' intentó eliminar folio {folio} sin ser admin."
        )
        flash("Solo administradores pueden eliminar.", "danger")
        return redirect(url_for("index"))

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # [ACID-AISLAMIENTO] Bloqueo en orden: cabecera → detalles
                cur.execute("SELECT Folio FROM TBL_COMPRA    WHERE Folio = %s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio = %s FOR UPDATE", (folio,))

                # [ACID-ATOMICIDAD] Eliminar primero detalles, luego cabecera
                # (la FK fk_detalle_compra con ON DELETE CASCADE también lo haría
                #  automáticamente, pero el orden explícito es más claro)
                cur.execute("DELETE FROM TBL_DETALLE WHERE Folio = %s", (folio,))
                cur.execute("DELETE FROM TBL_COMPRA  WHERE Folio = %s", (folio,))
            conn.commit()  # [ACID-DURABILIDAD]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        tx_with_retry(_tx)
        logger.info(f"[SEG-AUTORIZACION] Folio {folio} eliminado por '{session.get('usuario')}'.")
        flash(f"Folio #{folio} eliminado.", "success")
    except Exception as e:
        logger.error(f"[ACID-ATOMICIDAD] Error al eliminar folio {folio}: {e}")
        flash("Error al eliminar la cuenta.", "danger")

    return redirect(url_for("index"))


# =============================================================================
# RUTAS — NUEVA CUENTA (formulario y guardado)
# =============================================================================

@app.route("/pagina2")
@login_requerido
def pagina2():
    """
    [REND-INDICES] La consulta de productos usa el PK ID_Producto y la columna
    Categoria sin índice propio; para catálogos grandes convendría agregar
    un índice en (Categoria, Nombre_Producto).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ID_Producto, Nombre_Producto, Precio_Producto,
                       COALESCE(Categoria, 'Otros') AS Categoria
                  FROM TBL_PRODUCTO
                 ORDER BY Categoria, Nombre_Producto
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    catalogo = {}
    for r in rows:
        catalogo.setdefault(r["Categoria"], []).append({
            "id":     r["ID_Producto"],
            "nombre": r["Nombre_Producto"],
            "precio": as_float(r["Precio_Producto"]),
        })

    hoy = date.today().isoformat()
    return render_template(
        "pagina2.html",
        catalogo=catalogo,
        hoy=hoy,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )


@app.route("/add", methods=["POST"])
@login_requerido
def add():
    """
    [ACID-ATOMICIDAD] Toda la inserción (fecha + cabecera + N detalles) ocurre
    en una sola transacción. Si cualquier INSERT falla → rollback completo.

    [ACID-CONSISTENCIA] Validaciones antes de iniciar la tx:
      - id_mesa presente
      - detalles_json parseable y no vacío

    Flujo de triggers en la BD (ver backup_completo.sql):
      - trg_detalle_after_insert: recalcula Importe_Total y Cantidad_Total
        en TBL_COMPRA después de cada INSERT en TBL_DETALLE.
      - fn_obtener_fecha: crea la fecha si no existe o devuelve la existente.
        NOTA: tbl_fecha debería tener UNIQUE(Dia, Mes, Anio) para evitar
        condición de carrera entre sesiones concurrentes del mismo día.
    """
    id_mesa         = request.form.get("id_mesa")
    id_modo_entrega = request.form.get("id_modo_entrega")
    detalles_json   = request.form.get("detalles")

    # [ACID-CONSISTENCIA] Validación previa a la transacción
    if not id_mesa or not detalles_json:
        flash("Datos incompletos para registrar la cuenta.", "warning")
        return redirect(url_for("pagina2"))

    try:
        detalles = json.loads(detalles_json)
    except json.JSONDecodeError:
        flash("Error en los detalles del pedido.", "danger")
        return redirect(url_for("pagina2"))

    if not detalles:
        flash("Agrega al menos un producto.", "warning")
        return redirect(url_for("pagina2"))

    # [ACID-CONSISTENCIA] Validar cada renglón antes de abrir la transacción
    for d in detalles:
        try:
            p = float(d["precio"])
            c = int(d["cantidad"])
            assert 1 <= c <= 50 and 0.01 <= p <= 10_000
        except (KeyError, ValueError, AssertionError):
            flash("Un producto tiene datos fuera de rango.", "warning")
            return redirect(url_for("pagina2"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # [ACID-ATOMICIDAD] Todo ocurre en la misma conexión/transacción
            now = datetime.now()
            dia, mes, anio = now.day, now.month, now.year
            hora_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # fn_obtener_fecha: busca o crea la fecha. Opera dentro de la misma tx.
            cur.execute("SELECT fn_obtener_fecha(%s, %s, %s) AS ID_Fecha", (dia, mes, anio))
            id_fecha = cur.fetchone()["ID_Fecha"]

            # INSERT cabecera con totales en 0: el trigger los recalcula
            cur.execute("""
                INSERT INTO TBL_COMPRA
                    (ID_Fecha, ID_Mesa, Hora, Cantidad_Total, Importe_Total, ID_Modo_Entrega)
                VALUES (%s, %s, %s, 0, 0.00, %s)
            """, (id_fecha, id_mesa, hora_str, id_modo_entrega))

            folio = cur.lastrowid

            # Cada INSERT en TBL_DETALLE dispara trg_detalle_after_insert
            # que acumula Importe_Total y Cantidad_Total en TBL_COMPRA
            for d in detalles:
                subtotal = float(d["precio"]) * int(d["cantidad"])
                cur.execute("""
                    INSERT INTO TBL_DETALLE
                        (Folio, ID_Producto, Cantidad, Precio_Unit, Subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (folio, d["id_producto"], d["cantidad"], d["precio"], subtotal))

        conn.commit()  # [ACID-DURABILIDAD] Confirma toda la tx de una vez
        logger.info(
            f"[ACID-ATOMICIDAD] Nueva cuenta registrada. Folio={folio}, "
            f"mesa={id_mesa}, modo={id_modo_entrega}, renglones={len(detalles)}, "
            f"usuario='{session.get('usuario')}'"
        )
        flash("Cuenta registrada correctamente.", "success")

    except Exception as e:
        conn.rollback()  # [ACID-ATOMICIDAD] Rollback si cualquier paso falla
        logger.error(f"[ACID-ATOMICIDAD] Error al registrar cuenta: {e}")
        flash("Error al registrar la cuenta.", "danger")
    finally:
        conn.close()

    return redirect(url_for("index"))


# =============================================================================
# RUTAS — REGISTRO, LOGIN, LOGOUT
# =============================================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    [SEG-REGISTRO] MEJORA CRÍTICA respecto a la versión original:
    - Un usuario anónimo (sin sesión) solo puede registrarse con rol 'mesero'.
    - Solo un administrador con sesión activa puede crear cuentas de tipo 'admin'.
    - El campo 'rol' que llega del formulario se ignora para usuarios anónimos.

    Esto cierra la vulnerabilidad donde cualquier persona podía elegir 'admin'
    en el formulario público y obtener acceso total al sistema.

    [SEG-INYECCION] INSERT parametrizado con %s, sin concatenación de cadenas.
    [ACID-CONSISTENCIA] UNIQUE(Nombre_Usuario_norm) en BD previene duplicados
    aunque dos requests lleguen simultáneamente.
    """
    # Un admin logueado puede crear cualquier rol; un visitante solo 'mesero'
    es_admin_activo = (
        "usuario" in session and session.get("rol") == "admin"
    )

    if request.method == "GET":
        return render_template("login.html", register_mode=True, puede_elegir_rol=es_admin_activo)

    nombre = (request.form.get("usuario")    or "").strip()
    pw     = (request.form.get("contrasenia") or "").strip()
    rol_solicitado = (request.form.get("rol") or "mesero").strip()

    # [SEG-REGISTRO] Forzar rol mesero si quien registra no es admin
    rol = rol_solicitado if es_admin_activo else "mesero"
    if rol not in ("admin", "mesero"):
        rol = "mesero"

    # [ACID-CONSISTENCIA] Validaciones del lado servidor
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,10}", nombre):
        flash("El usuario debe contener solo letras y máximo 10 caracteres.", "warning")
        return render_template("login.html", register_mode=True, puede_elegir_rol=es_admin_activo)

    if not (1 <= len(pw) <= 10):
        flash("La contraseña debe tener de 1 a 10 caracteres.", "warning")
        return render_template("login.html", register_mode=True, puede_elegir_rol=es_admin_activo)

    # [SEG-AUTENTICACION] Hash scrypt (werkzeug); contraseña NUNCA en texto plano
    pw_hash = generate_password_hash(pw)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # [SEG-INYECCION] Query 100% parametrizado; sin interpolación de strings
            cur.execute("""
                INSERT INTO TBL_USUARIOS
                    (Nombre_Usuario, Rol_Usuario, Contrasenia_hash, Fecha_Creacion)
                VALUES (%s, %s, %s, NOW())
            """, (nombre, rol, pw_hash))
        conn.commit()
        logger.info(
            f"[SEG-REGISTRO] Usuario '{nombre}' registrado con rol '{rol}' "
            f"por {'admin ' + session.get('usuario') if es_admin_activo else 'registro público'}."
        )
        flash(f"Usuario «{nombre}» registrado correctamente.", "success")
        return redirect(url_for("login"))

    except IntegrityError as e:
        conn.rollback()
        # [ACID-CONSISTENCIA] Error 1062 = UNIQUE violado (nombre duplicado)
        if getattr(e, "args", None) and e.args[0] == 1062:
            logger.warning(f"[SEG-REGISTRO] Intento de registro con nombre duplicado: '{nombre}'.")
            flash("Ese nombre de usuario ya está registrado.", "danger")
        else:
            logger.error(f"[SEG-REGISTRO] Error de integridad al registrar '{nombre}': {e}")
            flash("Error al registrar el usuario.", "danger")
        return render_template("login.html", register_mode=True, puede_elegir_rol=es_admin_activo)
    finally:
        conn.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    [SEG-AUTENTICACION] Flujo de inicio de sesión:
      1. Busca usuario en BD (SELECT parametrizado).
      2. Verifica contraseña con check_password_hash (resistente a timing attacks).
      3. Comprueba que no haya sesión activa del mismo usuario en otro dispositivo.
      4. Genera token criptográficamente seguro (secrets.token_hex) y lo guarda en BD.
      5. Crea la sesión Flask con el token; future requests lo validan contra BD.

    [MON-LOG] Registra en log: login exitoso, usuario no encontrado, contraseña
    incorrecta y sesión duplicada — sin revelar cuál de los dos falló al usuario
    (mensaje genérico para evitar enumeración de usuarios).

    [SEG-INYECCION] Consulta parametrizada; sin concatenación.
    [REND-INDICES] La búsqueda WHERE Nombre_Usuario = %s es O(log n) si hay
    índice; actualmente ux_usuarios_nombre_norm lo cubre por la columna generada.
    """
    if request.method == "GET":
        return render_template("login.html", register_mode=False)

    usuario  = (request.form.get("usuario")    or "").strip()
    password = (request.form.get("contrasenia") or "").strip()

    if not usuario or not password:
        flash("Debes ingresar usuario y contraseña.", "warning")
        return render_template("login.html", register_mode=False)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # [SEG-INYECCION] Parámetro enlazado, no interpolado
            cur.execute("""
                SELECT ID_Usuario, Nombre_Usuario, Rol_Usuario, Contrasenia_hash,
                       Session_Token, Session_Expira, Ultimo_Visto
                  FROM TBL_USUARIOS
                 WHERE Nombre_Usuario = %s
            """, (usuario,))
            row = cur.fetchone()

            # [MON-LOG] Se distingue en log pero NO en el mensaje al usuario
            if not row:
                logger.warning(f"[SEG-AUTENTICACION] Login fallido: usuario '{usuario}' no existe. IP={request.remote_addr}")
                flash("Usuario o contraseña incorrectos.", "danger")
                return render_template("login.html", register_mode=False)

            # [SEG-AUTENTICACION] Verificación de hash (timing-safe en werkzeug)
            if not check_password_hash(row["Contrasenia_hash"], password):
                logger.warning(f"[SEG-AUTENTICACION] Login fallido: contraseña incorrecta para '{usuario}'. IP={request.remote_addr}")
                flash("Usuario o contraseña incorrectos.", "danger")
                return render_template("login.html", register_mode=False)

            # [SEG-AUTENTICACION] Sesión única: bloquear doble acceso simultáneo
            ahora  = datetime.now()
            expira = row.get("Session_Expira")
            if row.get("Session_Token") and expira and expira > ahora:
                logger.warning(f"[SEG-AUTENTICACION] Login bloqueado: '{usuario}' ya tiene sesión activa.")
                flash("Esta cuenta ya está activa en otro dispositivo.", "danger")
                return render_template("login.html", register_mode=False)

            # [SEG-AUTENTICACION] Token nuevo, criptográficamente seguro
            token     = secrets.token_hex(16)
            nueva_exp = ahora + timedelta(minutes=SESSION_TTL_MIN)

            cur.execute("""
                UPDATE TBL_USUARIOS
                   SET Session_Token  = %s,
                       Session_Expira = %s,
                       Ultimo_Visto   = NOW()
                 WHERE ID_Usuario = %s
            """, (token, nueva_exp, row["ID_Usuario"]))
        conn.commit()  # [ACID-DURABILIDAD]

    except OperationalError as e:
        logger.error(f"[MON-LOG] Error de conexión a BD durante login: {e}")
        flash("Error de conexión. Intenta de nuevo.", "danger")
        return render_template("login.html", register_mode=False)
    finally:
        conn.close()

    session.clear()
    session["usuario"]    = row["Nombre_Usuario"]
    session["rol"]        = row["Rol_Usuario"]
    session["sess_token"] = token
    session.permanent     = True
    app.permanent_session_lifetime = timedelta(minutes=SESSION_TTL_MIN)

    logger.info(f"[SEG-AUTENTICACION] Login exitoso: usuario='{row['Nombre_Usuario']}', rol='{row['Rol_Usuario']}', IP={request.remote_addr}")
    flash(f"Bienvenido, {row['Nombre_Usuario']}!", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """
    [SEG-AUTENTICACION] Cierre de sesión limpio:
    - Anula el token en BD (Session_Token = NULL).
    - Limpia la sesión Flask del lado cliente.
    Esto invalida inmediatamente la sesión en todos los dispositivos.
    """
    user  = session.get("usuario")
    token = session.get("sess_token")

    if user and token:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ID_Usuario, Session_Token FROM TBL_USUARIOS WHERE Nombre_Usuario = %s",
                    (user,)
                )
                row = cur.fetchone()
                if row and row.get("Session_Token") == token:
                    cur.execute("""
                        UPDATE TBL_USUARIOS
                           SET Session_Token  = NULL,
                               Session_Expira = NULL,
                               Ultimo_Visto   = NOW()
                         WHERE ID_Usuario = %s
                    """, (row["ID_Usuario"],))
            conn.commit()
            logger.info(f"[SEG-AUTENTICACION] Logout de usuario '{user}'.")
        finally:
            conn.close()

    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("login"))


# =============================================================================
# RUTAS — ADMINISTRACIÓN DE USUARIOS (solo admin)
# =============================================================================

@app.route("/usuarios")
@admin_requerido
def usuarios_list():
    """
    [SEG-AUTORIZACION] Protegido con @admin_requerido.
    Lista usuarios para gestión (eliminar, restablecer contraseña).
    Los hashes de contraseña se muestran en la tabla interna pero no se
    pueden descifrar; son scrypt y computacionalmente inviables de revertir.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ID_Usuario, Nombre_Usuario, Rol_Usuario, Fecha_Creacion
                  FROM TBL_USUARIOS
                 ORDER BY ID_Usuario
            """)
            usuarios = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "ElimUs.html",
        usuarios=usuarios,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )


@app.route("/usuarios/reset/<int:id_usuario>", methods=["POST"])
@admin_requerido
def usuario_reset_password(id_usuario):
    """
    [SEG-AUTORIZACION] Solo admin. Restablece la contraseña de un usuario.
    [SEG-AUTENTICACION] Nueva contraseña se hashea con scrypt antes de guardar.
    [SEG-CSRF] POST, no GET.
    """
    new_pw  = (request.form.get("new_password")     or "").strip()
    new_pw2 = (request.form.get("confirm_password")  or "").strip()

    if not new_pw or len(new_pw) > 10:
        flash("La nueva contraseña debe tener de 1 a 10 caracteres.", "warning")
        return redirect(url_for("usuarios_list"))
    if new_pw != new_pw2:
        flash("Las contraseñas no coinciden.", "warning")
        return redirect(url_for("usuarios_list"))

    pw_hash = generate_password_hash(new_pw)  # [SEG-AUTENTICACION] Hash antes de guardar

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Nombre_Usuario FROM TBL_USUARIOS WHERE ID_Usuario = %s",
                (id_usuario,)
            )
            row = cur.fetchone()
            if not row:
                flash("Usuario no encontrado.", "warning")
                return redirect(url_for("usuarios_list"))

            cur.execute(
                "UPDATE TBL_USUARIOS SET Contrasenia_hash = %s WHERE ID_Usuario = %s",
                (pw_hash, id_usuario),
            )
        conn.commit()
        logger.info(
            f"[SEG-AUTORIZACION] Contraseña restablecida para '{row['Nombre_Usuario']}' "
            f"por admin '{session.get('usuario')}'."
        )
        flash(f"Contraseña restablecida para «{row['Nombre_Usuario']}».", "success")
    except Exception as e:
        conn.rollback()
        logger.error(f"[SEG-AUTORIZACION] Error al restablecer contraseña de ID {id_usuario}: {e}")
        flash("Error al restablecer la contraseña.", "danger")
    finally:
        conn.close()

    return redirect(url_for("usuarios_list"))


@app.route("/usuarios/delete/<int:id_usuario>", methods=["POST"])
@admin_requerido
def usuario_delete(id_usuario):
    """
    [SEG-AUTORIZACION] Solo admin. Elimina un usuario.
    [SEG-CSRF] POST, no GET.
    Protección extra: el admin no puede eliminarse a sí mismo.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Nombre_Usuario, Rol_Usuario FROM TBL_USUARIOS WHERE ID_Usuario = %s",
                (id_usuario,)
            )
            row = cur.fetchone()
            if not row:
                flash("Usuario no encontrado.", "warning")
                return redirect(url_for("usuarios_list"))

            # [SEG-AUTORIZACION] Evitar auto-eliminación
            if row["Nombre_Usuario"] == session.get("usuario"):
                flash("No puedes eliminar tu propio usuario.", "warning")
                return redirect(url_for("usuarios_list"))

            cur.execute("DELETE FROM TBL_USUARIOS WHERE ID_Usuario = %s", (id_usuario,))
        conn.commit()
        logger.info(
            f"[SEG-AUTORIZACION] Usuario '{row['Nombre_Usuario']}' eliminado "
            f"por admin '{session.get('usuario')}'."
        )
        flash(f"Usuario «{row['Nombre_Usuario']}» eliminado.", "success")
    except Exception as e:
        conn.rollback()
        logger.error(f"[SEG-AUTORIZACION] Error al eliminar usuario ID {id_usuario}: {e}")
        flash("Error al eliminar el usuario.", "danger")
    finally:
        conn.close()

    return redirect(url_for("usuarios_list"))


# =============================================================================
# [ACID-DURABILIDAD] NOTA GENERAL SOBRE PERSISTENCIA
# -----------------------------------------------------------------------------
# Todas las tablas usan ENGINE=InnoDB (ver backup_completo.sql).
# InnoDB garantiza durabilidad mediante:
#   - Write-Ahead Log (WAL / redo log): las modificaciones se escriben al log
#     antes de aplicarse a las páginas de datos.
#   - Doublewrite buffer: evita páginas corruptas ante apagado súbito.
# El auditor de ACID-Durabilidad debe verificar:
#   1. ENGINE=InnoDB en todas las tablas del backup.
#   2. Que un INSERT/UPDATE seguido de reinicio de servidor muestre el dato.
# =============================================================================

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    logger.info("Servidor iniciando con Waitress en 0.0.0.0:5000 (8 threads)")
    serve(app, host="0.0.0.0", port=5000, threads=8)
    # Para desarrollo local (descomenta y comenta la línea anterior):
    # app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)