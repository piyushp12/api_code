from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from docxtpl import DocxTemplate
import json
from io import BytesIO
import tempfile
from docx2pdf import convert
from docx import Document

app = Flask(__name__)
CORS(app)

def generate_document(template_file, data, doc_type):
    template = DocxTemplate(template_file)
    template.render(data)

    output = BytesIO()
    template.save(output)
    output.seek(0)

    if doc_type.lower() == 'pdf':
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
            temp_docx_file.write(output.getvalue())
            temp_docx_path = temp_docx_file.name
        
        pdf_io = BytesIO()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf_file:
            temp_pdf_path = temp_pdf_file.name

        convert(temp_docx_path, temp_pdf_path)
        
        with open(temp_pdf_path, 'rb') as pdf_file:
            pdf_io.write(pdf_file.read())
        pdf_io.seek(0)

        return pdf_io, 'application/pdf', 'output.pdf'
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
