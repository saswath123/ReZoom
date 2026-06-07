from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import base64
import re  # ADD THIS IMPORT
from datetime import datetime
from werkzeug.utils import secure_filename
from extractor import extract_resume_text
from llm_parser import analyze_resume
from image_generator import generate_resume_image
from gap_analyzer import GapAnalyzer

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "generated_images"
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE = 4 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return jsonify({
        "status": "active",
        "message": "Intelligent Resume Parser AI API",
        "version": "2.0"
    })

@app.route("/upload", methods=["POST"])
def upload_resume():
    try:
        print("=" * 50)
        print("New upload request received")
        
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["resume"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PDF or DOCX"}), 400
        
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)
        
        extracted_text = extract_resume_text(file_path)
        
        # Analyze with LLM
        structured_data = analyze_resume(extracted_text)
        
        # ============================================================
        # FORCE EXTRACT EMAIL AND PHONE (FALLBACK)
        # ============================================================
        if structured_data.get('email') == 'Not Provided' or not structured_data.get('email'):
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', extracted_text)
            if email_match:
                structured_data['email'] = email_match.group()
                print(f"Fallback - Found Email: {email_match.group()}")
        
        if structured_data.get('phone') == 'Not Provided' or not structured_data.get('phone'):
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', extracted_text)
            if phone_match:
                structured_data['phone'] = phone_match.group()
                print(f"Fallback - Found Phone: {phone_match.group()}")
        # ============================================================
        
        # Perform Gap Analysis
        gap_analyzer = GapAnalyzer()
        education_raw = structured_data.get('education_raw', [])
        experience_raw = structured_data.get('experience_raw', [])
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)
        
        # Generate PNG image
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename))
        
        with open(png_path, 'rb') as f:
            png_bytes = f.read()
        
        image_base64 = base64.b64encode(png_bytes).decode('utf-8')
        
        os.remove(file_path)
        
        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_base64": image_base64,
            "image_download_url": f"/download/{png_filename}",
            "fit_score": structured_data.get("fit_score", 85),
            "gap_analysis": gap_analysis
        }), 200
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route("/download/<filename>")
def download_image(filename):
    try:
        image_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(image_path):
            return send_file(image_path, as_attachment=True, download_name=filename, mimetype='image/png')
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)