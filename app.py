from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from docxtpl import DocxTemplate
from docx import Document
import json
from io import BytesIO
import tempfile
import subprocess
import re
import sys
import os
import jinja2  

app = Flask(__name__)
CORS(app)

def validate_template(template_path):
    doc = Document(template_path)
    template_content = "\n".join([p.text for p in doc.paragraphs])

    for_loops = re.findall(r'{%\s*for\b', template_content)
    end_for_loops = re.findall(r'{%\s*endfor\b', template_content)
    if len(for_loops) != len(end_for_loops):
        raise ValueError("Template syntax error: Mismatched '{% for %}' and '{% endfor %}' tags.")

def convert_to(folder, source, timeout=None):
    args = [libreoffice_exec(), '--headless', '--convert-to', 'pdf', '--outdir', folder, source]
    process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    filename = re.search(r'-> (.*?) using filter', process.stdout.decode())
    return filename.group(1) if filename else None

def libreoffice_exec():
    if sys.platform == 'darwin':  
        return '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    elif sys.platform == 'win32': 
        return r'C:\Program Files\LibreOffice\program\soffice.exe' 
    return 'libreoffice'

def generate_document(template_file, data, doc_type):
    validate_template(template_file)  

    template = DocxTemplate(template_file)
    try:
        template.render(data)  
    except jinja2.TemplateSyntaxError as e:
        raise ValueError(f"Template syntax error: {e.message}")
    except jinja2.UndefinedError as e:
        raise ValueError(f"Template error: Undefined variable encountered - {e.message}")

    output = BytesIO()
    template.save(output)
    output.seek(0)

    if doc_type.lower() == 'pdf':
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
            temp_docx_file.write(output.getvalue())
            temp_docx_path = temp_docx_file.name

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_filename = convert_to(temp_dir, temp_docx_path)
            if pdf_filename:
                pdf_path = os.path.join(temp_dir, pdf_filename)  
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_io = BytesIO(pdf_file.read())
                pdf_io.seek(0)
                return pdf_io, 'application/pdf', 'output.pdf'
            else:
                raise Exception("PDF conversion failed.")
    else:
        return output, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'output.docx'

@app.route('/generate-docx', methods=['POST'])
def generate_docx():
    try:
        if 'template' not in request.files:
            return jsonify({"error": "Template file is required."}), 400
        template_file = request.files['template']

        if 'data' in request.files: 
            json_data_file = request.files['data']
            data = json.load(json_data_file)
        elif 'data' in request.form:  
            data = json.loads(request.form['data'])  
        else:
            return jsonify({"error": "JSON data (either as file or raw JSON in form data) is required."}), 400

        doc_type = request.form.get('doc_type')
        if not doc_type:
            return jsonify({"error": "Document type is required."}), 400

        file_io, mimetype, filename = generate_document(template_file, data, doc_type)
        return send_file(file_io, as_attachment=True, download_name=filename, mimetype=mimetype)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
