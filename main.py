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

# --- OBTENER EMAIL Y NOMBRE DEL USUARIO ---
def obtener_datos_usuario(usuario_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT correo, nombre FROM usuario WHERE id = %s", (usuario_id,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        if resultado:
            return {'correo': resultado[0], 'nombre': resultado[1]}
        else:
            return None
    except Exception as e:
        print(f"❌ Error al obtener datos de usuario {usuario_id}: {e}")
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
            datos_usuario = obtener_datos_usuario(notif['camara_id'])
            if not datos_usuario or not datos_usuario['correo']:
                print(f"⚠️ Usuario ID {notif['camara_id']} no tiene email registrado.")
                continue

            nombre_usuario = datos_usuario['nombre'] if datos_usuario['nombre'] else "Empleado/a"

            if notif['status_id'] == 2:
                asunto = "⚠️ Alerta: Retardo detectado"
                contenido = f"""
                    <p>Hola estimado/a empleado/a <strong>{nombre_usuario}</strong>,</p>
                    <p>Se te notifica que has registrado tu retardo número <strong>{notif['descripcion'].split()[-1]}</strong>.</p>
                    <p>Por favor, procura mejorar tu puntualidad para evitar inconvenientes futuros.</p>
                    <p>Saludos cordiales,</p>
                    <p>Área de Recursos Humanos</p>
                """
            elif notif['status_id'] == 4:
                asunto = "🚫 Alerta: Acceso denegado por disciplina"
                contenido = f"""
                    <p>Hola estimado/a empleado/a <strong>{nombre_usuario}</strong>,</p>
                    <p>Te informamos que debido a que has acumulado <strong>{notif['descripcion'].split('Retardos: ')[1].split(',')[0]}</strong> retardos y <strong>{notif['descripcion'].split('Faltas: ')[1]}</strong> falta(s), tu acceso a la planta ha sido denegado.</p>
                    <p>Te recomendamos acudir a la oficina de Recursos Humanos para aclarar esta situación.</p>
                    <p>Saludos cordiales,</p>
                    <p>Área de Recursos Humanos</p>
                """
            else:
                asunto = "📢 Notificación del sistema"
                contenido = f"""
                    <p>Hola estimado/a empleado/a <strong>{nombre_usuario}</strong>,</p>
                    <p>{notif['descripcion']}</p>
                    <p>Saludos cordiales,</p>
                    <p>Área de Recursos Humanos</p>
                """

            if enviar_correo(datos_usuario['correo'], asunto, contenido):
                actualizar_notificacion_vista(notif['id'])

    except mysql.connector.Error as err:
        print(f"❌ Error de base de datos: {err}")

# --- ENDPOINT FASTAPI PARA DISPARAR NOTIFICACIONES ---
@app.post("/procesar-notificaciones")
def procesar(background_tasks: BackgroundTasks):
    background_tasks.add_task(procesar_notificaciones)
    return {"message": "⏳ Procesamiento de notificaciones en segundo plano iniciado"}
