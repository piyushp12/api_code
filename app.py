from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from docxtpl import DocxTemplate
import json
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/generate-docx', methods=['POST'])
def generate_docx():
    try:
        if 'template' not in request.files or 'data' not in request.files:
            return jsonify({"error": "Template and JSON data are required."}), 400

        template_file = request.files['template']
        json_data_file = request.files['data']
        data = json.load(json_data_file)

        template = DocxTemplate(template_file)
        template.render(data)

        output = BytesIO()
        template.save(output)
        output.seek(0)

        return send_file(output, as_attachment=True, download_name="Filled_Template.docx")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
