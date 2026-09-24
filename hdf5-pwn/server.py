import os
import tempfile

import h5py
from flask import Flask, render_template_string, request

app = Flask(__name__)


INDEX_HTML = """
<!doctype html>
<html>
<head><title>HDF5 Viewer</title></head>
<body>
  <h1>Upload an HDF5 file</h1>
  <form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
    <input type="file" name="file" accept=".h5,.hdf5" required>
    <button type="submit">Upload</button>
  </form>
</body>
</html>
"""

RESULT_HTML = """
<!doctype html>
<html>
<head><title>HDF5 Preview</title></head>
<body>
  <h1>Preview of {{ filename }}</h1>
  <p><a href="{{ url_for('index') }}">Upload another file</a></p>
  {% for r in results %}
    <h2>/{{ r.path }}</h2>
    <p>{{ r.data }}</p>
  {% else %}
    <p>No datasets found.</p>
  {% endfor %}
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return "No file provided", 400

    results = []
    try:
        with h5py.File(f, "r") as h5:

            def visit(name, obj):
                if not isinstance(obj, h5py.Dataset):
                    return
                dataset = obj
                entry = {
                    "path": name,
                    "data": bytes(dataset[()]).decode().replace("\x00", "\n"),
                }
                results.append(entry)

            h5.visititems(visit)
    except Exception as e:
        return f"Failed to open HDF5 file: {type(e).__name__}: {e}", 400

    return render_template_string(RESULT_HTML, filename=f.filename, results=results)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
