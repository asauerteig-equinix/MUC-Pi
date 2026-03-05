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
    get_latest_measurement, get_measurements, db_health_check,
    get_all_measurements, get_measurements_count, update_measurement, delete_measurement, insert_measurement,
    update_sensor_order
)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "smartmeter-secret-2025"

# Jinja2 Globals - Python Funktionen im Template verfügbar machen
app.jinja_env.globals.update(
    min=min,
    max=max,
    int=int,
    abs=abs,
    len=len,
    range=range
)

# Custom Jinja2 Filter für Timestamp-Formatierung
@app.template_filter('strftime')
def strftime_filter(timestamp, format='%Y-%m-%d %H:%M:%S'):
    """Konvertiert Unix-Timestamp zu lesbarem Datum."""
    if timestamp is None:
        return 'N/A'
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime(format)
    except (ValueError, TypeError, OSError):
        return str(timestamp)

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
    """Dashboard - Daten werden per API async geladen."""
    try:
        db_ok, db_status = db_health_check()
        if not db_ok:
            return render_template("error.html", error=f"Datenbankfehler: {db_status}"), 500
        
        # Template wird sofort gerendert, Daten werden per JavaScript/API nachgeladen
        return render_template("index.html")
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

@app.route("/data")
def data_page():
    """Datenverwaltungsseite - Messungen einsehen, bearbeiten, löschen."""
    try:
        db_ok, db_status = db_health_check()
        if not db_ok:
            return render_template("error.html", error=f"Datenbankfehler: {db_status}"), 500
        
        page = request.args.get('page', 1, type=int)
        limit = 50
        offset = (page - 1) * limit
        
        measurements = get_all_measurements(limit=limit, offset=offset)
        total_count = get_measurements_count()
        total_pages = (total_count + limit - 1) // limit
        
        # Umwandeln in Listen für Template
        measurements_list = [dict(m) for m in measurements]
        
        return render_template("data.html", 
                             measurements=measurements_list,
                             page=page,
                             total_pages=total_pages,
                             total_count=total_count)
    except Exception as e:
        logger.error(f"Fehler in der Datenverwaltungs-Seite: {e}")
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

@app.route("/api/dashboard/sensors")
def api_dashboard_sensors():
    """API: Sensor-Daten für Dashboard (async loading)."""
    try:
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
            
            sensors_data.append({
                "device_id": device_id,
                "sensor_name": sensor_name,
                "latest_temp": round(latest_temp, 1) if latest_temp is not None else None,
                "latest_hum": round(latest_hum, 1) if latest_hum is not None else None,
                "latest_time": latest_time
            })
        
        return jsonify({"success": True, "sensors": sensors_data})
    except Exception as e:
        logger.error(f"API-Fehler Dashboard Sensors: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/dashboard/chart/<device_id>/<timerange>")
def api_dashboard_chart(device_id, timerange):
    """API: Chart-Daten für einen Sensor (async loading)."""
    try:
        # Zeiträume in Sekunden
        timeranges = {
            "1h": 3600,
            "1d": 86400,
            "7d": 604800,
            "30d": 2592000
        }
        
        seconds = timeranges.get(timerange, 3600)
        measurements = get_measurements(device_id, seconds)
        
        times, temps, hums = process_measurements(measurements)
        
        return jsonify({
            "success": True,
            "times": times,
            "temps": temps,
            "hums": hums
        })
    except Exception as e:
        logger.error(f"API-Fehler Dashboard Chart: {e}")
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

@app.route("/api/sensor/order", methods=["POST"])
def api_update_sensor_order():
    """API: Sensor-Reihenfolge aktualisieren."""
    try:
        data = request.json
        orders = data.get("orders", [])
        
        for item in orders:
            device_id = item.get("device_id")
            sort_order = item.get("sort_order", 0)
            if device_id:
                update_sensor_order(device_id, sort_order)
        
        return jsonify({"success": True, "message": "Reihenfolge aktualisiert"})
    except Exception as e:
        logger.error(f"API-Fehler beim Aktualisieren der Reihenfolge: {e}")
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

@app.route("/api/data/all", methods=["GET"])
def api_get_all_measurements():
    """API: Alle Messungen abrufen (JSON)."""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = (page - 1) * limit
        
        measurements = get_all_measurements(limit=limit, offset=offset)
        total_count = get_measurements_count()
        
        measurements_list = [dict(m) for m in measurements]
        
        return jsonify({
            "success": True,
            "data": measurements_list,
            "page": page,
            "limit": limit,
            "total": total_count
        })
    except Exception as e:
        logger.error(f"API-Fehler beim Abrufen: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/data/update/<int:measurement_id>", methods=["PUT"])
def api_update_measurement(measurement_id):
    """API: Messung aktualisieren."""
    try:
        data = request.json
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        
        if temperature is None or humidity is None:
            return jsonify({"success": False, "error": "Temperatur und Luftfeuchtigkeit erforderlich"}), 400
        
        try:
            temperature = float(temperature)
            humidity = float(humidity)
        except ValueError:
            return jsonify({"success": False, "error": "Temperatur und Luftfeuchtigkeit müssen Zahlen sein"}), 400
        
        if update_measurement(measurement_id, temperature, humidity):
            return jsonify({"success": True, "message": "Messung aktualisiert"})
        else:
            return jsonify({"success": False, "error": "Messung nicht gefunden"}), 404
    except Exception as e:
        logger.error(f"API-Fehler beim Aktualisieren: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/data/delete/<int:measurement_id>", methods=["DELETE"])
def api_delete_measurement(measurement_id):
    """API: Messung löschen."""
    try:
        if delete_measurement(measurement_id):
            return jsonify({"success": True, "message": "Messung gelöscht"})
        else:
            return jsonify({"success": False, "error": "Messung nicht gefunden"}), 404
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
