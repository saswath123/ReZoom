from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import traceback
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
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


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
        print("\n" + "=" * 60)
        print("UPLOAD REQUEST RECEIVED")
        print("=" * 60)

        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["resume"]

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({
                "error": "Invalid file type. Use PDF or DOCX"
            }), 400

        # Save uploaded file
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        saved_filename = (
            f"{timestamp}_{unique_id}_{secure_filename(file.filename)}"
        )

        file_path = os.path.join(
            UPLOAD_FOLDER,
            saved_filename
        )

        print(f"Saving file: {file_path}")
        file.save(file_path)

        # STEP 1 - Text Extraction
        print("\nSTEP 1: Text extraction started")
        extracted_text = extract_resume_text(file_path)

        if not extracted_text:
            raise Exception("No text extracted from resume")

        print(
            f"STEP 1: Text extraction completed "
            f"({len(extracted_text)} characters)"
        )

        # STEP 2 - LLM Analysis
        print("\nSTEP 2: LLM analysis started")
        structured_data = analyze_resume(extracted_text)

        print("STEP 2: LLM analysis completed")
        print(f"Returned type: {type(structured_data)}")

        if structured_data is None:
            raise Exception(
                "analyze_resume() returned None"
            )

        if not isinstance(structured_data, dict):
            raise Exception(
                f"Expected dict but got {type(structured_data)}"
            )

        # STEP 3 - Gap Analysis
        print("\nSTEP 3: Gap analysis started")

        gap_analyzer = GapAnalyzer()

        education_raw = structured_data.get(
            "education_raw",
            []
        )

        experience_raw = structured_data.get(
            "experience_raw",
            []
        )

        gap_analysis = gap_analyzer.analyze_complete_gaps(
            education_raw,
            experience_raw
        )

        print("STEP 3: Gap analysis completed")

        # STEP 4 - Image Generation
        print("\nSTEP 4: Image generation started")

        candidate_name = structured_data.get(
            "name",
            "Candidate"
        )

        png_filename = (
            f"Resume_{candidate_name}_{unique_id}.png"
        )

        png_output_path = os.path.join(
            OUTPUT_FOLDER,
            png_filename
        )

        png_path = generate_resume_image(
            structured_data,
            png_output_path
        )

        print("STEP 4: Image generation completed")
        print(f"Generated image: {png_path}")

        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

        print("\nPROCESS COMPLETED SUCCESSFULLY")
        print("=" * 60)

        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_download_url": f"/download/{png_filename}",
            "fit_score": structured_data.get(
                "fit_score",
                85
            ),
            "gap_analysis": gap_analysis
        }), 200

    except Exception as e:
        print("\n" + "=" * 60)
        print("ERROR OCCURRED")
        print("=" * 60)

        traceback.print_exc()

        print("\nERROR TYPE:", type(e).__name__)
        print("ERROR MESSAGE:", str(e))

        print("=" * 60 + "\n")

        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route("/download/<filename>")
def download_image(filename):
    try:
        image_path = os.path.join(
            OUTPUT_FOLDER,
            filename
        )

        if os.path.exists(image_path):
            return send_file(
                image_path,
                as_attachment=True,
                download_name=filename,
                mimetype="image/png"
            )

        return jsonify({
            "error": "File not found"
        }), 404

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )