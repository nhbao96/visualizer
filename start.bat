@echo off
echo Đang cài đặt các thư viện cần thiết...
python -m venv my_env
call my_env\Scripts\activate
pip install -r requirements.txt
echo Đang khởi động ứng dụng...
python app.py
pause