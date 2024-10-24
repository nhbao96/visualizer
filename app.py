import pandas as pd
import matplotlib.pyplot as plt
import os
import tempfile
from flask import Flask, jsonify, request, render_template, send_from_directory
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

socketio = SocketIO(app)

import matplotlib
matplotlib.use('Agg')


class DataPreprocessingFramework:
    def __init__(self, file_path):
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)
        self.sheet_names = self.excel_data.sheet_names
        self.cleaned_sheets = {}

    def clean_data(self, data):
        data_cleaned = data.dropna(how='all', axis=1).dropna(how='all', axis=0)
        data_cleaned.reset_index(drop=True, inplace=True)
        if data_cleaned.iloc[0].isnull().sum() == 0:
            data_cleaned.columns = data_cleaned.iloc[0]
            data_cleaned = data_cleaned.drop(0).reset_index(drop=True)
        if data_cleaned.columns[0] not in [None, '']:
            data_cleaned.dropna(subset=[data_cleaned.columns[0]], inplace=True)
        data_cleaned = data_cleaned.drop_duplicates()
        return data_cleaned

    def preprocess_all_sheets(self):
        for sheet in self.sheet_names:
            sheet_data = pd.read_excel(self.file_path, sheet_name=sheet)
            self.cleaned_sheets[sheet] = self.clean_data(sheet_data)

    def save_cleaned_data(self, output_file):
        with pd.ExcelWriter(output_file) as writer:
            for sheet_name, df in self.cleaned_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)


def process_excel_file(input_file, output_folder):
    data_processor = DataPreprocessingFramework(input_file)
    data_processor.preprocess_all_sheets()

    base_filename = os.path.splitext(os.path.basename(input_file))[0]
    cleaned_filename = f"{base_filename}_Cleaned.xlsx"
    output_file = os.path.join(output_folder, cleaned_filename)
    data_processor.save_cleaned_data(output_file)

    return output_file


def analyze_and_visualize(file_path):
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    for sheet_name, df in all_sheets.items():
        process_sheet_and_visualize(df, sheet_name)

def process_sheet_and_visualize(df, sheet_name):
    potential_quantity_cols = [col for col in df.columns if 'lượng' in str(col).lower()]
    potential_price_cols = [col for col in df.columns if 'thành' in str(col).lower() or 'tiền' in str(col).lower()]
    potential_product_cols = [col for col in df.columns if 'sản phẩm' in str(col).lower() or 'sp' in str(col).lower()]

    if potential_quantity_cols:
        plot_histogram(df, potential_quantity_cols[0], f'Số lượng - {sheet_name}', sheet_name)

    if potential_price_cols:
        plot_line_chart(df, potential_price_cols[0], f'Tổng tiền - {sheet_name}', sheet_name)

    if potential_product_cols:
        plot_bar_chart(df, potential_product_cols[0], f'Sản phẩm bán chạy nhất - {sheet_name}', sheet_name)

def plot_histogram(df, column_name, title, sheet_name):
    df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
    plt.figure(figsize=(10, 6))
    df[column_name].dropna().plot(kind='hist', bins=15, color='skyblue', edgecolor='black')
    plt.title(title)
    plt.xlabel(column_name)
    plt.ylabel('Tần suất')
    plt.grid(True)
    save_chart(sheet_name, 'histogram')

def plot_bar_chart(df, column_name, title, sheet_name):
    plt.figure(figsize=(10, 6))
    product_counts = df[column_name].value_counts().head(10)
    product_counts.plot(kind='bar', color='skyblue', edgecolor='black')
    plt.title(title)
    plt.xlabel('Sản phẩm')
    plt.ylabel('Số lượng bán')
    plt.xticks(rotation=45)
    plt.grid(True)
    save_chart(sheet_name, 'bar_chart')

def plot_line_chart(df, column_name, title, sheet_name):
    df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
    plt.figure(figsize=(10, 6))
    df[column_name].dropna().plot(kind='line', marker='o', linestyle='-', color='green')
    plt.title(title)
    plt.xlabel('Index')
    plt.ylabel(column_name)
    plt.grid(True)
    save_chart(sheet_name, 'line_chart')

def save_chart(sheet_name, chart_type):
    safe_sheet_name = secure_filename(sheet_name)
    chart_path = os.path.join(app.config['RESULT_FOLDER'], f'{safe_sheet_name}_{chart_type}.png')
    plt.savefig(chart_path)
    plt.close()
    socketio.emit('update', {'status': 'new_data'})

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
        cleaned_file_path = process_excel_file(file_path, UPLOAD_FOLDER)
        analyze_and_visualize(cleaned_file_path)
        return jsonify({'message': 'Xử lý file thành công'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list_charts', methods=['GET'])
def list_charts():
    charts = [f for f in os.listdir(app.config['RESULT_FOLDER']) if f.endswith('.png')]
    return jsonify({'charts': charts})

@app.route('/chart/<path:filename>')
def get_chart(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True)
