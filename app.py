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

tz_mx = pytz.timezone('America/Mexico_City')

app = Flask(__name__)

mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['BasePryEsp32']
collection = db['Datos']
dispositivo_id = "ESP32_01"

def generar_dato(timestamp_actual):
    hora_actual = timestamp_actual.hour + timestamp_actual.minute / 60.0
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
    movimiento = 1 if random.random() < 0.05 else 0
    return {
        "_id": str(uuid.uuid4().hex),
        "dispositivo": dispositivo_id,
        "temperatura": temperatura,
        "humedad": humedad,
        "luz": luz,
        "movimiento": movimiento,
        "timestamp": timestamp_actual.isoformat()
    }

def simulador():
    print("Simulador iniciado... Enviando datos a MongoDB cada 60 segundos.")
    while True:
        ahora = datetime.now(tz_mx)  
        dato = generar_dato(ahora)
        collection.insert_one(dato)
        print(f"[{ahora}] Dato insertado: {dato}")
        time.sleep(60)

@app.route('/')
def home():
    return 'API Flask con MongoDB funcionando en Render', 200

@app.route("/api/datos", methods=["GET"])
def obtener_datos():
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    for dato in datos:
        dato["_id"] = str(dato["_id"])
    return jsonify(datos)

@app.route("/datos", methods=["GET"])
def ver_datos_html():
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    for dato in datos:
        dato["_id"] = str(dato["_id"])
        # Formatear el timestamp
        dt = datetime.fromisoformat(dato["timestamp"].replace("Z", "+00:00")).astimezone(tz_mx)
        dato["timestamp"] = dt.strftime("%d/%m/%Y %H:%M")
    
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
    Thread(target=simulador, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
