import cv2
import easyocr
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# Define the path to save uploaded files
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize OCR reader
reader = easyocr.Reader(['ar', 'en'], gpu=False)

# Function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to format dates
def format_date(date_str):
    if len(date_str) == 8:
        return f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"
    return date_str

@app.route('/ocr', methods=['POST'])
def ocr():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        # Save file securely
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Read image
        img = cv2.imread(file_path)

        # Perform OCR
        text = reader.readtext(img)

        # Initialize arrays for the results
        lines_with_numbers = []
        lines_with_strings = []

        # Define the phrases to filter out for strings
        filter_phrases = [
            "Rh:", "بطاقة", "الديمقراطية", "الجمهورية", "سلطة", "تاررخ", "التعريف", 
            "اللقب", "بلدية", "تاريخ", ":", "الجنس", "ائرية", "الإسم", "مكان"
        ]

        # Iterate over detected text
        for t in text:
            line = t[1]

            # Check if the line contains any numbers
            if any(char.isdigit() for char in line):
                numbers_in_line = ''.join([char for char in line if char.isdigit()])
                if len(numbers_in_line) == 18:
                    lines_with_numbers.append(numbers_in_line)
                else:
                    if len([char for char in line if char.isdigit()]) >= 3:
                        lines_with_numbers.append(format_date(numbers_in_line))
            elif len(line) >= 3 and not any(phrase in line for phrase in filter_phrases):
                if len(line) > 3 or line == "ذكر":
                    lines_with_strings.append(line)

        # Return the results as a JSON response
        return jsonify({
            'lines_with_numbers': lines_with_numbers,
            'lines_with_strings': lines_with_strings
        })
    else:
        return jsonify({'error': 'Invalid file type. Only jpg, jpeg, and png allowed.'}), 400

if __name__ == '__main__':
    # Make sure the uploads folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Run the app
    app.run(debug=True)
