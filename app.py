from flask import Flask, render_template, request, Response
from docxtpl import DocxTemplate
from docx2pdf import convert
import json
import os
import pythoncom
from werkzeug.utils import secure_filename

app = Flask(__name__)

os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')  

def generate_document(template_file, json_data):
    template_filename = secure_filename(template_file.filename)
    template_path = os.path.join('uploads', template_filename)
    template_file.save(template_path)

    data = json.loads(json_data)

    doc = DocxTemplate(template_path)
    doc.render(data)
    
    output_docx_path = os.path.join('outputs', "output.docx")
    output_pdf_path = os.path.join('outputs', "output.pdf")
    
    doc.save(output_docx_path)

    pythoncom.CoInitialize()

    convert(output_docx_path, output_pdf_path)

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
