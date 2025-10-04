from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clave-super-secreta"  # Cambia esto por una clave segura

DB_PATH = "proyecto_smorgas.db"

# ------------------ Funciones auxiliares ------------------

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def date_str_to_int_yyyymmdd(date_str):
    """Convierte 'YYYY-MM-DD' a entero (ej. 2025-10-03 -> 20251003)."""
    if not date_str:
        return None
    try:
        return int(date_str.replace("-", ""))
    except Exception:
        return None

# Decorador para proteger rutas
def login_requerido(vista_func):
    @wraps(vista_func)
    def vista_protegida(*args, **kwargs):
        if not session.get("id_usuario"):
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return vista_func(*args, **kwargs)
    return vista_protegida

# ------------------ Rutas de Autenticación ------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre_usuario = request.form.get("username", "").strip()
        contrasenia = request.form.get("password", "").strip()

        if not nombre_usuario or not contrasenia:
            flash("Usuario y contraseña son obligatorios.", "danger")
            return redirect(url_for("login"))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id_usuario, nombre_usuario, contrasenia_hash FROM USUARIOS WHERE nombre_usuario = ?",
            (nombre_usuario,)
        )
        usuario = cur.fetchone()
        conn.close()

        if not usuario or not check_password_hash(usuario["contrasenia_hash"], contrasenia):
            flash("Credenciales inválidas. Intenta nuevamente.", "danger")
            return redirect(url_for("login"))

        # Guardar sesión
        session["id_usuario"] = usuario["id_usuario"]
        session["nombre_usuario"] = usuario["nombre_usuario"]
        flash(f"¡Bienvenido, {usuario['nombre_usuario']}!", "success")

        destino = request.args.get("next") or url_for("index")
        return redirect(destino)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("login"))

# Registro de usuario (para crear el primero)
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre_usuario = request.form.get("username", "").strip()
        contrasenia = request.form.get("password", "").strip()
        confirmar = request.form.get("confirm", "").strip()

        if not nombre_usuario or not contrasenia:
            flash("Usuario y contraseña son obligatorios.", "danger")
            return redirect(url_for("register"))

        if contrasenia != confirmar:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(url_for("register"))

        contrasenia_hash = generate_password_hash(contrasenia)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO USUARIOS (nombre_usuario, contrasenia_hash, fecha_creacion)
                VALUES (?, ?, ?)
            """, (nombre_usuario, contrasenia_hash, datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            conn.close()
            flash("Usuario creado exitosamente. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error al crear el usuario: {e}", "danger")
            return redirect(url_for("register"))

    return render_template("login.html", register_mode=True)

# ------------------ Rutas principales protegidas ------------------

@app.route("/")
@login_requerido
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_Folio, id_mesa, importe_total, id_modo_entrega, hora, id_Fecha
        FROM TBL_COMPRA
        ORDER BY id_Folio DESC
    """)
    ventas = cur.fetchall()
    conn.close()
    return render_template("index.html", ventas=ventas)

@app.route("/pagina2")
@login_requerido
def pagina2():
    return render_template("pagina2.html")

@app.route("/add", methods=["POST"])
@login_requerido
def add():
    id_mesa = request.form.get("id_mesa", "").strip()
    id_modo_entrega = request.form.get("id_modo_entrega", "").strip()
    importe_total = request.form.get("importe_total", "").strip()
    id_Fecha_str = request.form.get("id_Fecha", "").strip()

    if not id_mesa or not id_modo_entrega or not importe_total or not id_Fecha_str:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("pagina2"))

    try:
        id_mesa = int(id_mesa)
        id_modo_entrega = int(id_modo_entrega)
        importe_total = float(importe_total)
    except ValueError:
        flash("Datos inválidos. Revisa los valores ingresados.", "danger")
        return redirect(url_for("pagina2"))

    if importe_total <= 0:
        flash("El total debe ser mayor a 0.", "warning")
        return redirect(url_for("pagina2"))

    id_Fecha = date_str_to_int_yyyymmdd(id_Fecha_str)
    hora = datetime.now().strftime("%H:%M:%S")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO TBL_COMPRA (importe_total, hora, id_Fecha, id_modo_entrega, id_mesa)
            VALUES (?, ?, ?, ?, ?)
        """, (importe_total, hora, id_Fecha, id_modo_entrega, id_mesa))
        conn.commit()
        conn.close()
        flash("Cuenta agregada correctamente.", "success")
    except Exception as e:
        flash(f"Error al agregar la cuenta: {e}", "danger")

    return redirect(url_for("index"))

@app.route("/update/<int:folio>", methods=["POST"])
@login_requerido
def update(folio):
    id_mesa = request.form.get("id_mesa", "").strip()
    id_modo_entrega = request.form.get("id_modo_entrega", "").strip()
    importe_total = request.form.get("importe_total", "").strip()

    if not id_mesa or not id_modo_entrega or not importe_total:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("index"))

    try:
        id_mesa = int(id_mesa)
        id_modo_entrega = int(id_modo_entrega)
        importe_total = float(importe_total)
    except ValueError:
        flash("Datos inválidos.", "danger")
        return redirect(url_for("index"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE TBL_COMPRA
            SET id_mesa = ?, importe_total = ?, id_modo_entrega = ?
            WHERE id_Folio = ?
        """, (id_mesa, importe_total, id_modo_entrega, folio))
        conn.commit()
        conn.close()
        flash(f"Cuenta #{folio} actualizada correctamente.", "success")
    except Exception as e:
        flash(f"Error al actualizar la cuenta: {e}", "danger")

    return redirect(url_for("index"))

@app.route("/delete/<int:folio>")
@login_requerido
def delete(folio):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM TBL_COMPRA WHERE id_Folio = ?", (folio,))
        conn.commit()
        conn.close()
        flash(f"Cuenta #{folio} eliminada correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar la cuenta: {e}", "danger")

    return redirect(url_for("index"))

# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
