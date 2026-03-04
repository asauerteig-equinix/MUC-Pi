#!/usr/bin/env python3
"""
app.py - Flask Webserver für das Smartmeter-Dashboard
"""

from flask import Flask, render_template, request, jsonify, session
import time
from datetime import datetime
import json
import logging
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from db import (
    get_sensors, add_sensor, update_sensor, delete_sensor,
    get_latest_measurement, get_measurements, db_health_check
)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "smartmeter-secret-2025"

def process_measurements(measurements):
    """
    Extrahiert Zeit, Temperatur und Luftfeuchtigkeit aus den Messungen.
    Zeitstempel werden in Millisekunden umgerechnet für Plotly.
    """
    times = [row["timestamp"] * 1000 for row in measurements]
    temperatures = [row["temperature"] if row["temperature"] is not None else 0 for row in measurements]
    humidities = [row["humidity"] if row["humidity"] is not None else 0 for row in measurements]
    return times, temperatures, humidities

@app.route("/")
def index():
    """Dashboard mit Diagrammen für alle Sensoren."""
    try:
        db_ok, db_status = db_health_check()
        if not db_ok:
            return render_template("error.html", error=f"Datenbankfehler: {db_status}"), 500
        
        sensors = get_sensors()
        sensors_data = []
        
        for sensor in sensors:
            device_id = sensor["device_id"]
            sensor_name = sensor["sensor_name"]
            
            # Neueste Messung
            latest = get_latest_measurement(device_id)
            if latest:
                latest_temp = latest["temperature"]
                latest_hum = latest["humidity"]
                latest_time = datetime.fromtimestamp(latest["timestamp"]).strftime("%d.%m.%Y %H:%M:%S")
            else:
                latest_temp = None
                latest_hum = None
                latest_time = "Keine Messung"
            
            # Messungen für verschiedene Zeiträume
            meas_1h = get_measurements(device_id, 3600)           # 1 Stunde
            meas_1d = get_measurements(device_id, 86400)          # 1 Tag
            meas_7d = get_measurements(device_id, 604800)         # 7 Tage
            meas_1m = get_measurements(device_id, 2592000)        # 30 Tage
            
            times_1h, temps_1h, hums_1h = process_measurements(meas_1h)
            times_1d, temps_1d, hums_1d = process_measurements(meas_1d)
            times_7d, temps_7d, hums_7d = process_measurements(meas_7d)
            times_1m, temps_1m, hums_1m = process_measurements(meas_1m)
            
            sensors_data.append({
                "device_id": device_id,
                "sensor_name": sensor_name,
                "latest_temp": f"{latest_temp:.1f}" if latest_temp is not None else "N/A",
                "latest_hum": f"{latest_hum:.1f}" if latest_hum is not None else "N/A",
                "latest_time": latest_time,
                "times_1h": times_1h,
                "temps_1h": temps_1h,
                "hums_1h": hums_1h,
                "times_1d": times_1d,
                "temps_1d": temps_1d,
                "hums_1d": hums_1d,
                "times_7d": times_7d,
                "temps_7d": temps_7d,
                "hums_7d": hums_7d,
                "times_1m": temps_1m,
                "temps_1m": temps_1m,
                "hums_1m": hums_1m,
            })
        
        return render_template("index.html", sensors_data=sensors_data)
    except Exception as e:
        logger.error(f"Fehler im Dashboard: {e}")
        return render_template("error.html", error=str(e)), 500

@app.route("/sensors")
def sensors_page():
    """Sensoren-Verwaltungsseite."""
    try:
        db_ok, db_status = db_health_check()
        if not db_ok:
            return render_template("error.html", error=f"Datenbankfehler: {db_status}"), 500
        
        sensors = get_sensors()
        return render_template("sensors.html", sensors=sensors)
    except Exception as e:
        logger.error(f"Fehler in der Sensoren-Seite: {e}")
        return render_template("error.html", error=str(e)), 500

@app.route("/api/sensor/add", methods=["POST"])
def api_add_sensor():
    """API: Sensor hinzufügen."""
    try:
        data = request.json
        device_id = data.get("device_id", "").strip()
        sensor_name = data.get("sensor_name", "").strip()
        
        if not device_id or not sensor_name:
            return jsonify({"success": False, "error": "Device ID und Name erforderlich"}), 400
        
        if add_sensor(device_id, sensor_name):
            return jsonify({"success": True, "message": "Sensor hinzugefügt"})
        else:
            return jsonify({"success": False, "error": "Sensor konnte nicht hinzugefügt werden"}), 400
    except Exception as e:
        logger.error(f"API-Fehler beim Hinzufügen: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sensor/update", methods=["POST"])
def api_update_sensor():
    """API: Sensor aktualisieren."""
    try:
        data = request.json
        device_id = data.get("device_id", "").strip()
        sensor_name = data.get("sensor_name", "").strip()
        
        if not device_id or not sensor_name:
            return jsonify({"success": False, "error": "Device ID und Name erforderlich"}), 400
        
        if update_sensor(device_id, sensor_name):
            return jsonify({"success": True, "message": "Sensor aktualisiert"})
        else:
            return jsonify({"success": False, "error": "Sensor nicht gefunden"}), 404
    except Exception as e:
        logger.error(f"API-Fehler beim Aktualisieren: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sensor/delete/<device_id>", methods=["DELETE"])
def api_delete_sensor(device_id):
    """API: Sensor löschen."""
    try:
        if delete_sensor(device_id):
            return jsonify({"success": True, "message": "Sensor gelöscht"})
        else:
            return jsonify({"success": False, "error": "Sensor nicht gefunden"}), 404
    except Exception as e:
        logger.error(f"API-Fehler beim Löschen: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/status")
def api_status():
    """API: Status der Anwendung."""
    try:
        db_ok, db_status = db_health_check()
        sensor_count = len(get_sensors())
        return jsonify({
            "status": "OK" if db_ok else "ERROR",
            "database": db_status,
            "sensors": sensor_count
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "error": str(e)})

@app.errorhandler(404)
def not_found(error):
    """404 Error Handler."""
    return render_template("error.html", error="Seite nicht gefunden"), 404

@app.errorhandler(500)
def internal_error(error):
    """500 Error Handler."""
    return render_template("error.html", error="Interner Fehler"), 500

if __name__ == "__main__":
    logger.info(f"Starte Flask-App auf {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
