from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
from bson import ObjectId
from flask_swagger_ui import get_swaggerui_blueprint
import os

# For logs
import logging
from logging.handlers import RotatingFileHandler

# Create logs folder if not exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Setup logger
log_file = os.path.join("logs", "app.log")
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)  # 5 MB per file, keep 5 backups
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
handler.setFormatter(formatter)

app = Flask(__name__)

app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["metalDB"]
metal_collection = db["metals"]

# Swagger setup
SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"   # our swagger.json file path
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={"app_name": "Metal API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Serve swagger.json
@app.route("/static/<path:filename>")
def send_static_file(filename):
    return send_from_directory(os.path.join(app.root_path, "static"), filename)


# ===== LOG ALL REQUESTS & RESPONSES =====
@app.before_request
def log_request_info():
    app.logger.info(
        f"Incoming Request: {request.method} {request.path} | "
        f"Body: {request.get_json(silent=True)} | "
        f"Args: {dict(request.args)}"
    )

@app.after_request
def log_response_info(response):
    app.logger.info(
        f"Response: {response.status} for {request.method} {request.path}"
    )
    return response
# ========================================


# ===== Your Metal APIs =====
# ➕ Add Metal
@app.route("/metals", methods=["POST"])
def add_metal():
    data = request.json
    new_metal = {
        "name": data["name"],
        "price_per_kg": data["price_per_kg"],
        "density": data["density"],
        "category": data.get("category", "General")
    }
    result = metal_collection.insert_one(new_metal)
    app.logger.info(f"New metal added: {new_metal}")  # log event
    return jsonify({"message": "Metal added", "id": str(result.inserted_id)}), 201

# 📜 Get All Metals
@app.route("/metals", methods=["GET"])
def get_metals():
    metals = [{
        "_id": str(m["_id"]),
        "name": m["name"],
        "price_per_kg": m["price_per_kg"],
        "density": m["density"],
        "category": m.get("category", "General")
    } for m in metal_collection.find()]
    return jsonify(metals), 200

# 🔍 Get a particular Metal by ID
@app.route("/metals/<id>", methods=["GET"])
def get_metal(id):
    try:
        metal = metal_collection.find_one({"_id": ObjectId(id)})
        if metal:
            return jsonify({
                "_id": str(metal["_id"]),
                "name": metal["name"],
                "price_per_kg": metal["price_per_kg"],
                "density": metal["density"],
                "category": metal.get("category", "General")
            }), 200
        else:
            return jsonify({"error": "Metal not found"}), 404
    except Exception as e:
        app.logger.error(f"Error fetching metal {id}: {e}")
        return jsonify({"error": "Invalid ID format"}), 400


# ❌ Delete Metal
@app.route("/metals/<id>", methods=["DELETE"])
def delete_metal(id):
    result = metal_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        app.logger.warning(f"Metal with id={id} deleted")
        return jsonify({"message": "Metal deleted"}), 200
    app.logger.error(f"Delete failed, metal id={id} not found")
    return jsonify({"error": "Metal not found"}), 404


# ===== ReDoc Docs =====
@app.route('/redoc')
def redoc():
    return """
    <!doctype html>
    <html>
      <head>
        <title>Metal API Docs - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <!-- ReDoc script -->
        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
      </head>
      <body>
        <redoc spec-url='http://127.0.0.1:5000/static/swagger.json'></redoc>
      </body>
    </html>
    """
# ==========================================


if __name__ == "__main__":
    app.run(debug=True)
