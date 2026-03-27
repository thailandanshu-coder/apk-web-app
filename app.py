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

@app.route('/run', methods=['POST'])
def run_tool():
    os.system("python apk_login_remover.py")
    return "Task Completed ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)