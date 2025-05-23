import logging
import os
import uuid
import zipfile
from io import BytesIO
from threading import Lock, Thread
import shutil

import pandas as pd
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, \
    after_this_request, abort, current_app
from flask_login import login_required

from app.core import CSVCertificateGenerator

main_bp = Blueprint('main', __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

progress_status = {}
progress_lock = Lock()


@main_bp.route('/')
def home():
    return render_template('index.html')


def generate_certificates_background(temp_path, task_id, app):
    try:
        # Создаем специальную временную директорию
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_certs')
        os.makedirs(temp_dir, exist_ok=True)

        zip_path = os.path.join(temp_dir, f'certs_{task_id}.zip')  # Используем абсолютный путь

        # Инициализация прогресса
        with progress_lock:
            progress_status[task_id] = {
                'progress': 0,
                'status': 'processing',
                'original_csv': temp_path,
                'in_memory': False  # Временно, обновится после проверки размера
            }

        generator = CSVCertificateGenerator(temp_path, app)
        total_records = len(generator.data)
        in_memory = total_records < 100

        # Обновляем флаг in_memory
        with progress_lock:
            progress_status[task_id]['in_memory'] = in_memory

        if in_memory:
            # In-memory обработка
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for i, (_, record) in enumerate(generator.data.iterrows()):
                    pdf_data = generator._generate_pdf(record.to_dict())
                    zipf.writestr(generator._get_filename(record), pdf_data)

                    # Обновляем прогресс каждую запись
                    with progress_lock:
                        progress_status[task_id]['progress'] = int((i + 1) / total_records * 100)

            zip_buffer.seek(0)
            with progress_lock:
                progress_status[task_id].update({
                    'status': 'done',
                    'file_path': zip_path,  # Сохраняем абсолютный путь
                    'progress': 100
                })
        else:
            # On-disk обработка
            zip_path = f'temp_certs_{task_id}.zip'
            with zipfile.ZipFile(zip_path, 'w') as archive:
                for i, (_, record) in enumerate(generator.data.iterrows()):
                    pdf_data = generator._generate_pdf(record.to_dict())
                    archive.writestr(generator._get_filename(record), pdf_data)

                    # Обновляем прогресс каждые 10 записей (для больших файлов)
                    if i % 10 == 0 or i == total_records - 1:
                        with progress_lock:
                            progress_status[task_id]['progress'] = int((i + 1) / total_records * 100)

            with progress_lock:
                progress_status[task_id].update({
                    'status': 'done',
                    'file_path': zip_path,
                    'progress': 100
                })

        logger.info(f"Задача {task_id} завершена")

    except Exception as e:
        with progress_lock:
            progress_status[task_id] = {
                'status': 'error',
                'message': str(e),
                'original_csv': temp_path,
                'progress': 100
            }
        logger.error(f"Ошибка в задаче {task_id}: {str(e)}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)


@main_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'GET':
        return render_template('generate.html')

    if 'csv_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(request.url)

    file = request.files['csv_file']
    if not file.filename.endswith('.csv'):
        flash('Только CSV-файлы разрешены!', 'error')
        return redirect(request.url)

    try:
        task_id = str(uuid.uuid4())
        temp_path = f'temp_upload_{task_id}.csv'
        file.save(temp_path)
        logger.info(f"Файл сохранён как {temp_path}")

        # Проверка CSV
        df = pd.read_csv(temp_path)
        required_columns = ['student_name', 'course_name', 'teacher_name',
                            'issue_date', 'serial_number']
        if not all(col in df.columns for col in required_columns):
            os.remove(temp_path)
            flash('Отсутствуют обязательные колонки!', 'error')
            return redirect(request.url)

        # Инициализация прогресса
        with progress_lock:
            progress_status[task_id] = {
                'progress': 0,
                'status': 'processing',
                'original_csv': temp_path
            }

        # Запуск фоновой задачи с передачей app
        Thread(target=generate_certificates_background,
               args=(temp_path, task_id, current_app._get_current_object())).start()
        logger.info(f"Запущена фоновая задача {task_id}")

        return redirect(url_for('main.progress', task_id=task_id))

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}", exc_info=True)
        flash(f'Ошибка: {str(e)}', 'danger')
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return redirect(request.url)


@main_bp.route('/progress/<task_id>')
@login_required
def progress(task_id):
    return render_template('progress.html', task_id=task_id)


@main_bp.route('/progress/status/<task_id>')
def get_progress(task_id):
    with progress_lock:
        status = progress_status.get(task_id, {'status': 'not_found'})

        # Для отладки логируем весь статус
        logger.debug(f"Full status for {task_id}: {status}")

        # Подготовка безопасного ответа
        response_data = {
            'progress': status.get('progress', 0),
            'status': status.get('status', 'unknown'),
            'message': status.get('message', '')
        }

    return jsonify(response_data)


@main_bp.route('/download/<task_id>')
@login_required
def download(task_id):
    with progress_lock:
        status = progress_status.get(task_id)
        if not status or status['status'] != 'done':
            abort(404, description="Файл не найден или еще не готов")

    # Для in-memory файлов
    if status.get('in_memory'):
        try:
            return send_file(
                BytesIO(status['file_data']),
                as_attachment=True,
                download_name='certificates.zip',
                mimetype='application/zip'
            )
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки in-memory файла: {str(e)}")
            abort(500, description="Ошибка подготовки файла")

    # Для файлов на диске
    file_path = os.path.abspath(status['file_path']) if 'file_path' in status else None

    if not file_path or not os.path.exists(file_path):
        current_app.logger.error(f"Файл не найден: {file_path}")
        abort(404, description="Файл сертификатов не найден")

    try:
        # Читаем файл в память и отправляем
        with open(file_path, 'rb') as f:
            file_data = BytesIO(f.read())

        @after_this_request
        def cleanup(response):
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                if 'original_csv' in status and os.path.exists(status['original_csv']):
                    os.remove(status['original_csv'])
                with progress_lock:
                    if task_id in progress_status:
                        del progress_status[task_id]
            except Exception as e:
                current_app.logger.error(f"Ошибка очистки: {str(e)}")
            return response

        return send_file(
            file_data,
            as_attachment=True,
            download_name='certificates.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        current_app.logger.error(f"Ошибка чтения файла {file_path}: {str(e)}")
        abort(500, description="Ошибка при чтении файла")
