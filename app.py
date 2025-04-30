import os
import time
import random
import math
import uuid
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from pymongo import MongoClient
from threading import Thread
import pytz
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')  # Valor por defecto para pruebas locales
try:
    client = MongoClient(mongo_uri)
    db = client['BasePryEsp32']
    collection = db['Datos']
    logger.info("Conexión a MongoDB establecida correctamente.")
except Exception as e:
    logger.error(f"Error al conectar con MongoDB: {e}")
    raise

dispositivo_id = "ESP32_01"
tz_mexico = pytz.timezone('America/Mexico_City')

def generar_dato(timestamp_actual):
    try:
        timestamp_mexico = timestamp_actual.astimezone(tz_mexico)
        hora_actual = timestamp_mexico.hour + timestamp_mexico.minute / 60.0
        temp_min = 6   
        temp_max = 27 
        if 6 <= hora_actual <= 15:
            progreso = (hora_actual - 6) / (15 - 6)  
            temperatura = temp_min + (temp_max - temp_min) * progreso
        else:
            if hora_actual > 15:
                progreso = (hora_actual - 15) / (24 - 15 + 6) 
            else:  
                progreso = (hora_actual + 9) / (24 - 15 + 6)
            temperatura = temp_max - (temp_max - temp_min) * progreso
        temperatura += random.normalvariate(0, 0.8)
        temperatura = round(max(5.0, min(27.0, temperatura)), 1)
        humedad = round(random.uniform(0.0, 1.5), 1)
        hora = timestamp_mexico.hour
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
        movimiento = 1 if random.random() < 0.05 else 0
        return {
            "_id": str(uuid.uuid4().hex),
            "dispositivo": dispositivo_id,
            "temperatura": temperatura,
            "humedad": humedad,
            "luz": luz,
            "movimiento": movimiento,
            "timestamp": timestamp_mexico.isoformat()
        }
    except Exception as e:
        logger.error(f"Error en generar_dato: {e}")
        raise

def simulador():
    logger.info("Simulador iniciado... Enviando datos a MongoDB cada 60 segundos.")
    while True:
        try:
            ahora = datetime.now(tz_mexico)
            dato = generar_dato(ahora)
            collection.insert_one(dato)
            logger.info(f"[{ahora}] Dato insertado: {dato}")
        except Exception as e:
            logger.error(f"Error en simulador al insertar dato: {e}")
        time.sleep(60)

@app.route('/')
def home():
    return 'API Flask con MongoDB funcionando en Render', 200

@app.route("/api/datos", methods=["GET"])
def obtener_datos():
    try:
        datos = list(collection.find().sort("timestamp", -1).limit(50))
        for dato in datos:
            dato["_id"] = str(dato["_id"])
        logger.info("Datos obtenidos correctamente.")
        return jsonify(datos)
    except Exception as e:
        logger.error(f"Error en obtener_datos: {e}")
        return jsonify({"error": "No se pudieron obtener los datos"}), 500

@app.route("/datos", methods=["GET"])
def ver_datos_html():
    try:
        datos = list(collection.find().sort("timestamp", -1).limit(50))
        for dato in datos:
            dato["_id"] = str(dato["_id"])

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
        logger.info("Página HTML generada correctamente.")
        return render_template_string(template_html, datos=datos)
    except Exception as e:
        logger.error(f"Error en ver_datos_html: {e}")
        return "Error al generar la página", 500

if __name__ == "__main__":
    try:
        logger.info("Iniciando el hilo del simulador...")
        Thread(target=simulador, daemon=True).start()
        logger.info("Iniciando el servidor Flask...")
        app.run(host="0.0.0.0", port=10000)
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}")
