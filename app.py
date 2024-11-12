from flask import Flask, render_template, request, Response
from docxtpl import DocxTemplate
import json
import os
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Ensure necessary directories exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')  

def generate_document(template_file, json_data):
    # Save uploaded template file to 'uploads' folder
    template_filename = secure_filename(template_file.filename)
    template_path = os.path.join('uploads', template_filename)
    template_file.save(template_path)

    # Parse the incoming JSON data
    data = json.loads(json_data)

    # Initialize the template and render it with the data
    doc = DocxTemplate(template_path)
    doc.render(data)

    # Paths for the saved docx and PDF output
    output_docx_path = os.path.join('outputs', "output.docx")
    output_pdf_path = os.path.join('outputs', "output.pdf")

    # Save the rendered docx document
    doc.save(output_docx_path)

    # Use subprocess to call pandoc for converting docx to PDF (cross-platform)
    subprocess.run(['pandoc', output_docx_path, '-o', output_pdf_path])

    # Read the generated PDF file
    with open(output_pdf_path, 'rb') as f:
        file_data = f.read()

    # Clean up temporary files
    os.remove(output_pdf_path)
    os.remove(output_docx_path)
    os.remove(template_path)

    # Return the PDF as a response for download
    response = Response(file_data, mimetype="application/pdf")
    response.headers.set("Content-Disposition", "attachment", filename="output.pdf")
    
    return response

@app.route('/generate-doc', methods=['POST'])
def generate_doc_route():
    # Ensure both template and data are provided
    if 'template' not in request.files or 'data' not in request.form:
        return {"error": "Please provide both 'template' and 'data' in form-data."}, 400
    
    template_file = request.files['template']
    json_data = request.form['data']
    
    return generate_document(template_file, json_data)

if __name__ == '__main__':
    app.run(debug=True)
