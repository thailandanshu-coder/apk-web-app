from flask import Flask, request

import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h2>APK Login Remover Tool</h2>
    <form action="/run" method="post">
        <button type="submit">Run Tool</button>
    </form>
    '''
import subprocess

@app.route('/run', methods=['POST'])
def run_tool():
    result = subprocess.run(
        ["python3", "apk_login_remover.py"],
        capture_output=True,
        text=True
    )

    return f"""
    <h3>Output:</h3>
    <pre>{result.stdout}</pre>

    <h3>Error (if any):</h3>
    <pre>{result.stderr}</pre>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
