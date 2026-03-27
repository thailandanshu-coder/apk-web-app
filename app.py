from flask import Flask, request
import subprocess
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return '''
    <h2>APK Login Remover</h2>
    <form action="/run" method="post" enctype="multipart/form-data">
        <input type="file" name="apk_file" required>
        <button type="submit">Upload & Run</button>
    </form>
    '''

@app.route('/run', methods=['POST'])
def run_tool():
    file = request.files['apk_file']

    if file.filename == '':
        return "No file selected ❌"

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    result = subprocess.run(
        ["python3", "apk_login_remover.py", filepath],
        capture_output=True,
        text=True
    )

    return f"""
    <h3>Output:</h3>
    <pre>{result.stdout}</pre>

    <h3>Error:</h3>
    <pre>{result.stderr}</pre>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
