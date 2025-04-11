import os
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Union

import pandas as pd
import pdfkit
from flask import render_template, send_file


class BaseCertificateGenerator(ABC):
    @abstractmethod
    def generate(self):
        pass


class CSVCertificateGenerator(BaseCertificateGenerator):
    """Генератор сертификатов из CSV"""

    def __init__(self, data_source: Union[str, pd.DataFrame]):
        self.data = pd.read_csv(data_source) if isinstance(data_source, str) else data_source
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '0mm',
            'margin-right': '0mm',
            'margin-bottom': '0mm',
            'margin-left': '0mm',
            'encoding': 'UTF-8'
        }

    def _generate_pdf(self, template_data: dict) -> bytes:
        html_content = render_template('certificate.html', **template_data)
        return pdfkit.from_string(html_content, False, options=self.pdf_options)

    def _get_filename(self, record: dict) -> str:
        return f"Сертификат_{record['student_name']}_{record['serial_number']}.pdf"


def csv_generate_on_disk(generator: CSVCertificateGenerator):
    zip_path = 'temp_certificates.zip'
    generator.create_archive(zip_path)

    response = send_file(
        zip_path,
        as_attachment=True,
        download_name='certificates.zip'
    )

    # Добавляем обработчик для удаления после отправки
    @response.call_on_close
    def cleanup():
        if os.path.exists(zip_path):
            os.remove(zip_path)

    return response


def csv_generate_in_memory(generator: CSVCertificateGenerator):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for _, record in generator.data.iterrows():
            pdf_data = generator._generate_pdf(record.to_dict())
            zipf.writestr(generator._get_filename(record), pdf_data)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name='certificates.zip',
        mimetype='application/zip'
    )


def csv_generate_certs(data_source: Union[str, pd.DataFrame]):
    generator = CSVCertificateGenerator(data_source)

    if len(generator.data) < 100:  # Если меньше 100 записей - в памяти
        return csv_generate_in_memory(generator)
    else:  # Иначе - на диск с автоматическим удалением
        return csv_generate_on_disk(generator)