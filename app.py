import threading
from flask import Flask, request, jsonify, render_template, send_from_directory
import pandas as pd
import matplotlib.pyplot as plt
import os
from werkzeug.utils import secure_filename
import logging
from flask_socketio import SocketIO
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

app = Flask(__name__)
socketio = SocketIO(app)
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

import matplotlib
matplotlib.use('Agg')

logging.basicConfig(level=logging.DEBUG)

def process_excel(file_path):
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    sheet_data = {}

    for sheet_name, df in all_sheets.items():
        sheet_data[sheet_name] = df.head().to_dict(orient='records')
        numeric_cols = df.select_dtypes(include=['number', 'datetime']).columns

        if len(numeric_cols) > 0:
            plt.figure(figsize=(10, 6))
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            df[numeric_cols].dropna().hist(bins=15, edgecolor='black')
            plt.suptitle(f'Biểu đồ Histogram - Sheet: {sheet_name}')
            plt.tight_layout()

            safe_sheet_name = secure_filename(sheet_name)
            chart_path = os.path.join(app.config['RESULT_FOLDER'], f'{safe_sheet_name}_histogram.png')
            plt.savefig(chart_path)
            plt.close()

            socketio.emit('update_window', {'message': 'Biểu đồ mới đã được tạo!'})
        else:
            print(f"Không có cột số hoặc thời gian trong sheet: {sheet_name}")

    return sheet_data

class ResultsFolderHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.png'):
            socketio.emit('update_window', {'message': 'Thư mục kết quả đã thay đổi'})

def start_watching_results_folder():
    event_handler = ResultsFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, path=RESULT_FOLDER, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file được tải lên'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tên file không hợp lệ'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        data = process_excel(file_path)
        return jsonify({'data': data, 'message': 'Xử lý file thành công'}), 200
    except Exception as e:
        logging.exception("Lỗi khi xử lý file Excel")
        return jsonify({'error': str(e)}), 500

@app.route('/chart/<path:filename>')
def get_chart(filename):
    try:
        return send_from_directory(app.config['RESULT_FOLDER'], filename)
    except Exception as e:
        logging.exception("Lỗi khi trả về file biểu đồ")
        return jsonify({'error': 'Không thể tải file'}), 500

@app.route('/list_charts', methods=['GET'])
def list_charts():
    try:
        charts = [f for f in os.listdir(app.config['RESULT_FOLDER']) if f.endswith('.png')]
        return jsonify({'charts': charts})
    except Exception as e:
        logging.exception("Lỗi khi liệt kê các biểu đồ")
        return jsonify({'error': 'Không thể liệt kê các biểu đồ'}), 500

if __name__ == '__main__':
    threading.Thread(target=start_watching_results_folder, daemon=True).start()
    socketio.run(app, debug=True)
