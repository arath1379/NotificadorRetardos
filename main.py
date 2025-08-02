from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = FastAPI()

# --- CONFIGURACIÓN BASE DE DATOS ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'railway'
}

# --- CONFIGURACIÓN CORREO GMAIL ---
correo_emisor = 'prototiposistema645@gmail.com'
clave_app = 'dcge rvhv akrb wuey'
correo_rh = 'rhsistemaprototipo@gmail.com'

# --- MODELO PARA RESPUESTA ---
class Notificacion(BaseModel):
    id: int
    descripcion: str
    camara_id: int
    status_id: int

# --- ENVIAR CORREO ---
def enviar_correo(correo_usuario, asunto, contenido):
    msg = MIMEMultipart()
    msg['Subject'] = asunto
    msg['From'] = correo_emisor
    msg['To'] = correo_usuario
    msg['Bcc'] = correo_rh
    msg.attach(MIMEText(contenido, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(correo_emisor, clave_app)
            server.send_message(msg)
        print(f"✅ Correo enviado a {correo_usuario} y CCO a RH: {asunto}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo a {correo_usuario}: {e}")
        return False

# --- OBTENER EMAIL DEL USUARIO ---
def obtener_email_usuario(usuario_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT correo FROM usuario WHERE id = %s", (usuario_id,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado[0] if resultado else None
    except Exception as e:
        print(f"❌ Error al obtener email de usuario {usuario_id}: {e}")
        return None

# --- ACTUALIZAR NOTIFICACIÓN COMO VISTA ---
def actualizar_notificacion_vista(notificacion_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notificaciones
            SET fecha_visualizacion = %s
            WHERE id = %s
        """, (datetime.now(), notificacion_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al actualizar notificación: {e}")

# --- PROCESAR NOTIFICACIONES ---
def procesar_notificaciones():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, descripcion, camara_id, status_id
            FROM notificaciones
            WHERE fecha_visualizacion = '1000-01-01 00:00:00'
        """)
        notificaciones = cursor.fetchall()
        cursor.close()
        conn.close()

        for notif in notificaciones:
            email_usuario = obtener_email_usuario(notif['camara_id'])
            if not email_usuario:
                print(f"⚠️ Usuario ID {notif['camara_id']} no tiene email registrado.")
                continue

            if notif['status_id'] == 2:
                asunto = "⚠️ Alerta: Retardo detectado"
            elif notif['status_id'] == 4:
                asunto = "🚫 Alerta: Acceso denegado por disciplina"
            else:
                asunto = "📢 Notificación del sistema"

            contenido = f"""
                <h3>{asunto}</h3>
                <p><strong>Descripción:</strong> {notif['descripcion']}</p>
                <p><strong>Usuario ID:</strong> {notif['camara_id']}</p>
                <p><strong>Status ID:</strong> {notif['status_id']}</p>
            """

            if enviar_correo(email_usuario, asunto, contenido):
                actualizar_notificacion_vista(notif['id'])

    except mysql.connector.Error as err:
        print(f"❌ Error de base de datos: {err}")

# --- ENDPOINT FASTAPI PARA DISPARAR NOTIFICACIONES ---
@app.post("/procesar-notificaciones")
def procesar(background_tasks: BackgroundTasks):
    background_tasks.add_task(procesar_notificaciones)
    return {"message": "⏳ Procesamiento de notificaciones en segundo plano iniciado"}
