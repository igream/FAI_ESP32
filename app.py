import os
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# MongoDB Atlas URI desde variable de entorno
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["BasePryEsp32"]
collection = db["Datos"]

# Ruta para recibir datos del ESP32
@app.route("/api/data", methods=["POST"])
def recibir_dato():
    try:
        data = request.get_json()
        print("JSON recibido:", data)

        required_keys = ["dispositivo", "temperatura", "humedad", "luz", "movimiento"]
        if not all(k in data for k in required_keys):
            return jsonify({"error": "Faltan campos"}), 400

        if not (isinstance(data["temperatura"], (int, float)) and
                isinstance(data["humedad"], (int, float)) and
                isinstance(data["luz"], int) and
                isinstance(data["movimiento"], int)):
            return jsonify({"error": "Tipos inválidos"}), 400

        documento = {
            "dispositivo": data["dispositivo"],
            "temperatura": float(data["temperatura"]),
            "humedad": float(data["humedad"]),
            "luz": int(data["luz"]),
            "movimiento": int(data["movimiento"]),
            "timestamp": datetime.utcnow() - timedelta(hours=6)
        }
        result = collection.insert_one(documento)
        return jsonify({"message": "Guardado", "id": str(result.inserted_id)}), 200
    except Exception as e:
        print("Error MongoDB:", str(e))
        return jsonify({"error": str(e)}), 500

# Ruta para ver los últimos 50 datos en JSON
@app.route("/api/datos", methods=["GET"])
def ver_datos():
    datos = list(collection.find().sort("timestamp", -1).limit(50)) 

    for d in datos:
        d["_id"] = str(d["_id"])
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            d["timestamp"] = ts.isoformat()
        elif isinstance(ts, str):
            try:
                d["timestamp"] = datetime.fromisoformat(ts).isoformat()
            except ValueError:
                d["timestamp"] = "INVALID_TIMESTAMP"

    return jsonify(datos), 200

# Filtro para formatear fecha en plantilla
@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.fromisoformat(value).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Fecha inválida"

# Ruta HTML para visualizar los datos
@app.route("/datos", methods=["GET"])
def ver_datos_html():
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    for d in datos:
        d["_id"] = str(d["_id"])
        ts = d.get("timestamp")
        if isinstance(ts, datetime):
            d["timestamp"] = ts.isoformat()
        elif isinstance(ts, str):
            try:
                d["timestamp"] = datetime.fromisoformat(ts).isoformat()
            except ValueError:
                d["timestamp"] = "INVALID_TIMESTAMP"

    template_html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Datos de sensores</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9; }
            h2 { color: #333; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background-color: #e0e0e0; }
            tr:nth-child(even) { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Últimos 50 datos del sensor</h2>
        <table>
            <thead>
                <tr>
                    <th>Fecha y Hora</th>
                    <th>Temperatura (°C)</th>
                    <th>Humedad (%)</th>
                    <th>Luz (lux)</th>
                    <th>Movimiento</th>
                </tr>
            </thead>
            <tbody>
                {% for dato in datos %}
                <tr>
                    <td>{{ dato.timestamp | datetimeformat }}</td>
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

# Ruta de inicio
@app.route("/", methods=["GET"])
def index():
    return "API Flask con MongoDB funcionando en Render", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
