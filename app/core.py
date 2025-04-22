import os
import zipfile
from io import BytesIO
from typing import Union

import pandas as pd
from flask import render_template
from xhtml2pdf import pisa
import logging

xhtml2pdf_logger = logging.getLogger('xhtml2pdf')
xhtml2pdf_logger.setLevel(logging.ERROR)

class CSVCertificateGenerator:
    """Генератор сертификатов из CSV с использованием xhtml2pdf"""

    def __init__(self, data_source: Union[str, pd.DataFrame], app, progress_callback=None):
        self.data = pd.read_csv(data_source) if isinstance(data_source, str) else data_source
        self.app = app
        self.progress_callback = progress_callback

    def generate_certificates(self):
        if len(self.data) < 100:
            return self._generate_in_memory()
        return self._generate_on_disk()

    def _generate_pdf(self, template_data: dict) -> bytes:
        with self.app.app_context():
            html_content = render_template('certificate.html', **template_data)
            pdf = BytesIO()

            # Добавляем дополнительные параметры для pisa
            pisa_status = pisa.CreatePDF(
                html_content,
                dest=pdf,
                encoding='UTF-8',
                default_css='''
                    @page { size: A4 landscape; margin: 0; }
                    body { font-family: "Helvetica"; margin: 0; }
                '''
            )

            if pisa_status.err:
                raise RuntimeError("PDF generation failed")

            return pdf.getvalue()

    def _get_filename(self, record: dict) -> str:
        return f"Сертификат_{record['student_name']}_{record['serial_number']}.pdf"

    def _generate_in_memory(self):
        zip_buffer = BytesIO()
        total = len(self.data)
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for i, (_, record) in enumerate(self.data.iterrows()):
                pdf_data = self._generate_pdf(record.to_dict())
                zipf.writestr(self._get_filename(record), pdf_data)
                if self.progress_callback:
                    self.progress_callback((i + 1) / total * 100)
        zip_buffer.seek(0)
        return {'type': 'memory', 'data': zip_buffer}

    def _generate_on_disk(self):
        zip_path = f'temp_certs_{os.urandom(4).hex()}.zip'
        with zipfile.ZipFile(zip_path, 'w') as archive:
            for _, record in self.data.iterrows():
                pdf_data = self._generate_pdf(record.to_dict())
                archive.writestr(self._get_filename(record), pdf_data)
        return {'type': 'disk', 'path': zip_path}
