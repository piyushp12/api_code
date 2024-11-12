from flask import Flask, render_template, request, Response
from docxtpl import DocxTemplate
import json
import os
import subprocess
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)

os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')  

def convert_docx_to_pdf(docx_file, pdf_output):
    """Converts a .docx file to .pdf using unoconv"""
    try:
        subprocess.run(['unoconv', '-f', 'pdf', '-o', pdf_output, docx_file], check=True)
        logging.info(f"Successfully converted {docx_file} to {pdf_output}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error converting DOCX to PDF: {e}")
        raise ValueError("Error converting DOCX to PDF.")


def generate_document(template_file, json_data):
    template_filename = secure_filename(template_file.filename)
    template_path = os.path.join('uploads', template_filename)
    template_file.save(template_path)

    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error: {e}")
        return {"error": "Invalid JSON data."}, 400

    try:
        doc = DocxTemplate(template_path)
        doc.render(data)
    except Exception as e:
        logging.error(f"Error rendering DOCX template: {e}")
        return {"error": "Error rendering DOCX template."}, 500

    output_docx_path = os.path.join('outputs', "output.docx")
    output_pdf_path = os.path.join('outputs', "output.pdf")
    
    try:
        doc.save(output_docx_path)
    except Exception as e:
        logging.error(f"Error saving DOCX file: {e}")
        return {"error": "Error saving generated DOCX file."}, 500

    # Convert the generated .docx to .pdf
    try:
        convert_docx_to_pdf(output_docx_path, output_pdf_path)
    except ValueError as e:
        return {"error": str(e)}, 500

    with open(output_pdf_path, 'rb') as f:
        file_data = f.read()
    
    os.remove(output_pdf_path) 
    os.remove(output_docx_path)  
    os.remove(template_path)    

    response = Response(file_data, mimetype="application/pdf")
    response.headers.set("Content-Disposition", "attachment", filename="output.pdf")
    
    return response

@app.route('/generate-doc', methods=['POST'])
def generate_doc_route():
    if 'template' not in request.files or 'data' not in request.form:
        return {"error": "Please provide both 'template' and 'data' in form-data."}, 400
    
    template_file = request.files['template']
    json_data = request.form['data']
    
    return generate_document(template_file, json_data)

if __name__ == '__main__':
    app.run(debug=True)
