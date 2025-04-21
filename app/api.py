import os
import uuid

import pandas as pd
from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import login_required

from app.core import CSVCertificateGenerator
from app.models import User

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/generate', methods=['POST'])
@login_required
def api_generate_certificates():
    # Проверка наличия файла
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed'}), 400

    try:
        # Сохраняем временный файл
        temp_path = f"temp_api_{uuid.uuid4().hex}.csv"
        file.save(temp_path)

        # Проверяем CSV
        df = pd.read_csv(temp_path)
        required_columns = ['student_name', 'course_name', 'teacher_name',
                            'issue_date', 'serial_number']
        if not all(col in df.columns for col in required_columns):
            os.remove(temp_path)
            return jsonify({'error': 'Missing required columns'}), 400

        # Генерируем сертификаты
        generator = CSVCertificateGenerator(temp_path, current_app._get_current_object())
        result = generator.generate_certificates()

        # Удаляем временный файл
        os.remove(temp_path)

        if result['type'] == 'memory':
            return send_file(
                result['data'],
                as_attachment=True,
                download_name='certificates.zip',
                mimetype='application/zip'
            )
        else:
            return send_file(
                result['path'],
                as_attachment=True,
                download_name='certificates.zip'
            )

    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username} for u in users])


@api_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'username': user.username})


@api_bp.route('/api/token', methods=['POST'])
def get_token():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = user.generate_auth_token()
    return jsonify({'token': token, 'expires_in': 3600})
