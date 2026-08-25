from flask import Flask, render_template, request, jsonify

from zaberONE import ZaberXYStage


app = Flask(__name__)

stage = None

# Your Mac serial port
DEFAULT_PORT = "/dev/tty.usbserial-AG0KQW8J"

# State for the manual step sequence
scan_state = {
    "active": False,
    "current": 0,
    "num_positions": 0,
    "start_x": 0.0,
    "start_y": 0.0,
    "step_x": 5.0,
    "step_y": 0.0,
    "velocity": 5.0,
}


@app.route("/")
def index():
    return render_template("index.html", default_port=DEFAULT_PORT)


@app.route("/connect", methods=["POST"])
def connect():
    global stage

    try:
        data = request.get_json()
        port = data.get("port", DEFAULT_PORT)

        if stage is not None:
            stage.close()

        stage = ZaberXYStage(port=port)
        stage.connect()

        position = stage.position()

        return jsonify({
            "success": True,
            "message": "Stage connected.",
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        stage = None
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/disconnect", methods=["POST"])
def disconnect():
    global stage

    try:
        if stage is not None:
            stage.close()
            stage = None

        return jsonify({
            "success": True,
            "message": "Stage disconnected."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


def require_stage():
    if stage is None:
        raise RuntimeError("Stage is not connected.")


@app.route("/status", methods=["GET"])
def status():
    try:
        require_stage()

        position = stage.position()

        return jsonify({
            "success": True,
            "connected": True,
            "homed": stage.is_homed(),
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "connected": False,
            "message": str(e)
        }), 500


@app.route("/home", methods=["POST"])
def home():
    try:
        require_stage()

        stage.home()
        position = stage.position()

        return jsonify({
            "success": True,
            "message": "Homing complete.",
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/stop", methods=["POST"])
def stop():
    try:
        require_stage()

        stage.stop()

        return jsonify({
            "success": True,
            "message": "STOP command sent."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/move_absolute", methods=["POST"])
def move_absolute():
    try:
        require_stage()

        data = request.get_json()

        x = float(data["x"])
        y = float(data["y"])
        velocity = float(data.get("velocity", 5))

        position = stage.move_absolute(
            x,
            y,
            velocity
        )

        return jsonify({
            "success": True,
            "message": "Absolute move complete.",
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/move_relative", methods=["POST"])
def move_relative():
    try:
        require_stage()

        data = request.get_json()

        dx = float(data["dx"])
        dy = float(data["dy"])
        velocity = float(data.get("velocity", 5))

        position = stage.move_relative(
            dx,
            dy,
            velocity
        )

        return jsonify({
            "success": True,
            "message": "Relative move complete.",
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/scan/start", methods=["POST"])
def start_scan():
    try:
        require_stage()

        data = request.get_json()

        scan_state["active"] = True
        scan_state["current"] = 0

        scan_state["start_x"] = float(data["start_x"])
        scan_state["start_y"] = float(data["start_y"])

        scan_state["step_x"] = float(data["step_x"])
        scan_state["step_y"] = float(data["step_y"])

        scan_state["num_positions"] = int(data["num_positions"])
        scan_state["velocity"] = float(data.get("velocity", 5))

        position = stage.move_absolute(
            scan_state["start_x"],
            scan_state["start_y"],
            scan_state["velocity"]
        )

        return jsonify({
            "success": True,
            "message": "Moved to starting position.",
            "position_number": 1,
            "x": position.x_mm,
            "y": position.y_mm,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/scan/next", methods=["POST"])
def next_scan_position():
    try:
        require_stage()

        if not scan_state["active"]:
            raise RuntimeError("No step sequence is active.")

        scan_state["current"] += 1

        if scan_state["current"] >= scan_state["num_positions"]:
            scan_state["active"] = False

            return jsonify({
                "success": True,
                "finished": True,
                "message": "Sequence complete."
            })

        i = scan_state["current"]

        x = scan_state["start_x"] + i * scan_state["step_x"]
        y = scan_state["start_y"] + i * scan_state["step_y"]

        position = stage.move_absolute(
            x,
            y,
            scan_state["velocity"]
        )

        return jsonify({
            "success": True,
            "finished": False,
            "position_number": i + 1,
            "x": position.x_mm,
            "y": position.y_mm,
            "message": "Moved to next position."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )