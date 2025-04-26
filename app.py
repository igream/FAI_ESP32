import os
import time
import random
import math
import uuid
from datetime import datetime
from flask import Flask, jsonify
from pymongo import MongoClient
from threading import Thread

# Crear app de Flask
app = Flask(__name__)

# Configurar conexión a MongoDB
mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['BasePryEsp32']
collection = db['Datos']

dispositivo_id = "ESP32_01"

def generar_dato(timestamp_actual):
    hora_actual = timestamp_actual.hour + timestamp_actual.minute / 60.0

    # Simular temperatura
    temperatura_base = 16 + 11 * math.sin((math.pi / 12) * (hora_actual - 6))
    temperatura = round(random.normalvariate(temperatura_base, 1.0), 1)
    temperatura = max(5.0, min(27.0, temperatura))

    # Humedad baja
    humedad = round(random.uniform(0.0, 7.0), 1)

    # Luz basada en hora
    if 6 <= timestamp_actual.hour <= 18:
        luz = random.randint(1500, 4000)
    else:
        luz = random.randint(0, 800)

    # Movimiento con baja probabilidad
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
        ahora = datetime.now()
        dato = generar_dato(ahora)
        collection.insert_one(dato)
        print(f"[{ahora}] Dato insertado: {dato}")
        time.sleep(60)

@app.route("/api/datos", methods=["GET"])
def obtener_datos():
    datos = list(collection.find().sort("timestamp", -1).limit(100))  # Últimos 100 datos
    for dato in datos:
        dato["_id"] = str(dato["_id"])  # Convertir ObjectId a string
    return jsonify(datos)

if __name__ == "__main__":
    # Ejecutar simulador en segundo plano
    Thread(target=simulador, daemon=True).start()

    # Correr el servidor Flask
    app.run(host="0.0.0.0", port=10000)
