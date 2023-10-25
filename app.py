import hashlib
from flask import Flask, request, jsonify, send_file
import pytesseract
import os
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import cv2
import uuid
import PyPDF2
import shutil

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit


app = Flask(__name__)
scheduler = BackgroundScheduler(daemon=True)


@app.route('/')
def index():
    return jsonify({'message': 'Api is Running'}), 200


@app.route('/api/pdf', methods=['POST'])
def upload_pdf():
    lang = request.args.get('lang', 'eng')
    extract_image = request.args.get('image', 'yes')
    host_url = request.host_url
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file part'}), 400

    pdf = request.files['pdf']

    if pdf.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if pdf:
        filename = secure_filename(pdf.filename)
        random = str(uuid.uuid4().hex)
        temp = os.path.join('uploads', f'{random}_{filename}')
        pdf.save(temp)
        random = calculate_file_hash(temp, 'md5')
        pdf_location = os.path.join('uploads', f'{random}_{filename}')
        os.rename(temp, pdf_location)

        text = ''
        images = []

        pdf_document = fitz.open(pdf_location)
        pdf_extra = PyPDF2.PdfReader(pdf_location)
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            if (extract_image == 'yes'):
                image_list = page.get_images(full=True)
                for i, img in enumerate(image_list):
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_name = f'image_page{page_num + 1}_img{i + 1}.{base_image["ext"]}'
                    image_filename = os.path.join(
                        'images', random, image_name)
                    if not os.path.exists(os.path.join('images', random)):
                        os.makedirs(os.path.join('images', random))
                    if (base_image['ext'].lower() == 'png'):
                        image_data = pdf_extra.pages[page_num].images[i].data
                    else:
                        image_data = base_image['image']
                    with open(image_filename, 'wb') as image_file:
                        image_file.write(image_data)
                    images.append(host_url+image_filename)
                    if (lang == 'ben'):
                        page.delete_image(img[0])

            if (lang == 'ben'):
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                current = os.path.join(
                    'uploads', f'{random}_page_{page_num}.png')
                pix.save(current)
                custom_config = r'--psm 6'
                img = cv2.imread(current)
                ret, thresh3 = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
                text += pytesseract.image_to_string(
                    img, lang='ben+Bengali+eng', config=custom_config)
                os.remove(current)
            else:
                text += page.get_text()
        # pdf_document.save('test.pdf')
        # with open('test.txt', 'w', encoding='utf-8') as text_file:
        #     text_file.write(text)
        pdf_document.close()
        os.remove(pdf_location)
        if (extract_image == 'yes'):
            # image deletion
            current_time = datetime.now()
            run_date = current_time + timedelta(minutes=1)
            scheduler.add_job(delete_folder, 'date',
                              run_date=run_date, args=[os.path.join(
                                  'images', random)])
        response = {
            "text": text,
            "images": images
        }

        return jsonify(response), 201


@app.route('/images/<path:filename>')
def serve_image(filename):
    if not os.path.exists('images/'+filename):
        return jsonify({'error': 'Image Not Found'}), 404

    return send_file('images/'+filename, mimetype='image/png')


# Function to calculate the hash of a file using a specific hash algorithm

def calculate_file_hash(file_path, hash_algorithm):
    # Initialize the hash object for the specified algorithm
    hasher = hashlib.new(hash_algorithm)

    # Read the file in chunks and update the hash
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(8192)  # Read in 8KB chunks
            if not chunk:
                break
            hasher.update(chunk)

    # Return the hexadecimal representation of the hash
    return hasher.hexdigest()


def delete_folder(directory_path):
    shutil.rmtree(directory_path)


scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True)
