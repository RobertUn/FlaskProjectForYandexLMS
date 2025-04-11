from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
import pandas as pd
from flask_login import login_required
from core import csv_generate_certs
import os
import time

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    return render_template('index.html')


@main_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        file = request.files['csv_file']
        if file and file.filename.endswith('.csv'):
            try:
                # Сохраняем временный файл
                temp_path = 'temp_upload.csv'
                file.save(temp_path)

                # Проверяем обязательные колонки
                df = pd.read_csv(temp_path)
                required_columns = ['student_name', 'course_name', 'teacher_name',
                                    'issue_date', 'serial_number']

                if not all(col in df.columns for col in required_columns):
                    flash('Отсутствуют обязательные колонки!', 'error')
                    os.remove(temp_path)
                    return redirect(request.url)

                # Генерируем и отправляем архив
                response = csv_generate_certs(temp_path)

                # Удаляем временный CSV после использования
                @response.call_on_close
                def cleanup():
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                return response

            except Exception as e:
                flash(f'Ошибка: {str(e)}', 'danger')
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            flash('Только CSV-файлы разрешены!', 'error')

    return render_template('generate.html')


@main_bp.route('/progress')
def progress():
    """Эмуляция прогресса (без изменения основной логики)"""
    def generate():
        for i in range(5, 101, 5):  # Увеличиваем прогресс на 5% каждые 0.3 сек
            time.sleep(0.3)
            yield f"data: {i}\n\n"
        yield "data: 100\n\n"  # Гарантируем завершение
    return Response(generate(), mimetype='text/event-stream')