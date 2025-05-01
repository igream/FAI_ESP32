import os
import time
import random
import uuid
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from threading import Thread
import pytz

app = Flask(__name__)

# Configuración de MongoDB
mongo_uri = os.getenv('MONGO_URI')
if not mongo_uri:
    raise ValueError("MONGO_URI no está definida en las variables de entorno")
try:
    client = MongoClient(mongo_uri)
    client.server_info()  # Verifica la conexión
except Exception as e:
    print(f"Error al conectar con MongoDB: {e}")
    exit(1)

db = client['BasePryEsp32']
collection = db['Datos']
dispositivo_id = "ESP32_01"

def generar_dato(timestamp_actual):
    """Genera un dato simulado basado en la hora del día."""
    hora_actual = timestamp_actual.hour + timestamp_actual.minute / 60.0
    temp_min, temp_max = 6, 27
    # Calcular temperatura según la hora del día
    if 6 <= hora_actual <= 15:
        progreso = (hora_actual - 6) / (15 - 6)
        temperatura = temp_min + (temp_max - temp_min) * progreso
    else:
        progreso = (hora_actual - 15) / (24 - 15 + 6) if hora_actual > 15 else (hora_actual + 9) / (24 - 15 + 6)
        temperatura = temp_max - (temp_max - temp_min) * progreso
    temperatura += random.normalvariate(0, 0.8)
    temperatura = round(max(5.0, min(27.0, temperatura)), 1)
    # Humedad en un rango más realista
    humedad = round(random.uniform(20.0, 80.0), 1)
    # Generar luz según la hora
    hora = timestamp_actual.hour
    if 5 <= hora < 8:
        luz = random.randint(300, 1000)
    elif 8 <= hora < 11:
        luz = random.randint(1000, 2500)
    elif 11 <= hora < 15:
        luz = random.randint(2500, 4000)
    elif 15 <= hora < 18:
        luz = random.randint(1500, 3000)
    elif 18 <= hora < 21:
        luz = random.randint(300, 1000)
    else:
        luz = random.randint(0, 200)
    # Movimiento con baja probabilidad
    movimiento = 1 if random.random() < 0.05 else 0
    return {
        "_id": str(uuid.uuid4().hex),
        "dispositivo": dispositivo_id,
        "temperatura": temperatura,
        "humedad": humedad,
        "luz": luz,
        "movimiento": movimiento,
        "timestamp": timestamp_actual  # Almacenar como objeto datetime
    }

def simulador():
    """Simula la generación y almacenamiento de datos cada 60 segundos."""
    print("Simulador iniciado... Enviando datos a MongoDB cada 60 segundos.")
    while True:
        try:
            ahora = datetime.now(pytz.timezone('America/Mexico_City'))
            # Generar dato
            dato = generar_dato(ahora)
            # Insertar en MongoDB
            collection.insert_one(dato)
            print(f"[{ahora}] Dato insertado: {dato}")
        except ConnectionFailure as e:
            print(f"Error de conexión a MongoDB: {e}. Reintentando en 60 segundos...")
        except ServerSelectionTimeoutError as e:
            print(f"Timeout al conectar con MongoDB: {e}. Reintentando en 60 segundos...")
        except ValueError as e:
            print(f"Error en la generación de datos: {e}. Reintentando en 60 segundos...")
        except Exception as e:
            print(f"Error inesperado en simulador: {e}. Reintentando en 60 segundos...")
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("Simulador detenido por interrupción.")
            break

@app.teardown_appcontext
def cerrar_conexion(exception):
    """Cierra la conexión a MongoDB al finalizar la aplicación."""
    client.close()

@app.route('/')
def home():
    """Ruta principal de la API."""
    return 'API Flask con MongoDB funcionando en Render', 200

@app.route("/api/datos", methods=["GET"])
def obtener_datos():
    """Obtiene los últimos 50 datos de la base de datos."""
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    # Convertir timestamp a string solo para la respuesta
    for dato in datos:
        dato["timestamp"] = dato["timestamp"].isoformat()
    return jsonify(datos)

@app.route("/datos", methods=["GET"])
def ver_datos_html():
    """Muestra los últimos 50 datos en una tabla HTML."""
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    # Convertir timestamp a string para la plantilla
    for dato in datos:
        dato["timestamp"] = dato["timestamp"].isoformat()

    template_html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Datos de sensores</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Datos Recientes del Sensor</h2>
        <table>
            <thead>
                <tr>
                    <th>Fecha y hora</th>
                    <th>Temperatura (°C)</th>
                    <th>Humedad (%)</th>
                    <th>Luz (lux)</th>
                    <th>Movimiento</th>
                </tr>
            </thead>
            <tbody>
            {% for dato in datos %}
                <tr>
                    <td>{{ dato.timestamp }}</td>
                    <td>{{ dato.temperatura }}</td>
                    <td>{{ dato.humedad }}</td>
                    <td>{{ dato.luz }}</td>
                    <td>{{ "Sí" if dato.movimiento else "No" }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    return render_template_string(template_html, datos=datos)

if __name__ == "__main__":
    # Iniciar el simulador en un hilo
    Thread(target=simulador, daemon=True).start()
    # Obtener el puerto de la variable de entorno para compatibilidad con Render
    port = int(os.getenv('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
