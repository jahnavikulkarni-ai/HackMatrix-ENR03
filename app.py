import os
from flask import Flask, render_template, request, redirect, url_for
import cv2
import numpy as np

app = Flask(__name__)
UPLOAD_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, 'original.jpg')
        file.save(filepath)
        
        img = cv2.imread(filepath)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        cv2.imwrite(os.path.join(UPLOAD_FOLDER, 'binary.jpg'), thresh)
        cv2.imwrite(os.path.join(UPLOAD_FOLDER, 'detections.jpg'), img)
        
        return render_template('index.html', processed=True)

if __name__ == '__main__':
    app.run(debug=True)
