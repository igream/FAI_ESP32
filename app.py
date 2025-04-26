import os
import time
import random
import math
import uuid
from datetime import datetime
from flask import Flask, jsonify
from pymongo import MongoClient
from threading import Thread


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
    humedad = round(random.uniform(0.0, 7.0), 1)

    if 6 <= timestamp_actual.hour <= 18:
        luz = random.randint(1500, 4000)
    else:
        luz = random.randint(0, 800)

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
    datos = list(collection.find().sort("timestamp", -1).limit(100))  
    for dato in datos:
        dato["_id"] = str(dato["_id"])  
    return jsonify(datos)

if __name__ == "__main__":
    Thread(target=simulador, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
