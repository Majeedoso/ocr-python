import os
import cv2
import easyocr
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Allowed file extensions and default upload folder
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Format dates (e.g., YYYYMMDD to YYYY/MM/DD)
def format_date(date_str):
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"
    return date_str

@app.route('/ocr', methods=['POST'])
def ocr():
    # Check if file is present in the request
    if 'file' not in request.files or not request.files['file']:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only jpg, jpeg, and png allowed.'}), 400

    # Securely save the file
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Read the image
    img = cv2.imread(file_path)
    if img is None:
        return jsonify({'error': 'Failed to read image. Please upload a valid image.'}), 400

    # Initialize EasyOCR Reader (Lazy Loading)
    try:
        reader = easyocr.Reader(['ar', 'en'], gpu=False)
    except Exception as e:
        return jsonify({'error': f'Failed to initialize OCR reader: {str(e)}'}), 500

    # Perform OCR
    try:
        text_results = reader.readtext(img)
    except Exception as e:
        return jsonify({'error': f'OCR processing failed: {str(e)}'}), 500

    # Prepare results
    lines_with_numbers = []
    lines_with_strings = []

    filter_phrases = [
        "Rh:", "بطاقة", "الديمقراطية", "الجمهورية", "سلطة", "تاررخ", "التعريف",
        "اللقب", "بلدية", "تاريخ", ":", "الجنس", "ائرية", "الإسم", "مكان"
    ]

    for t in text_results:
        line = t[1]
        # Detect numeric lines
        if any(char.isdigit() for char in line):
            numbers_in_line = ''.join(char for char in line if char.isdigit())
            if len(numbers_in_line) == 18:  # Example: ID number
                lines_with_numbers.append(numbers_in_line)
            elif len(numbers_in_line) >= 8:  # Example: Date
                lines_with_numbers.append(format_date(numbers_in_line))
        # Detect meaningful text lines
        elif len(line) >= 3 and not any(phrase in line for phrase in filter_phrases):
            if len(line) > 3 or line == "ذكر":  # Arabic-specific rule
                lines_with_strings.append(line)

    return jsonify({
        'lines_with_numbers': lines_with_numbers,
        'lines_with_strings': lines_with_strings
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=port, debug=True)
