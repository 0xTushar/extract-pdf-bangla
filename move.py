import os
import shutil


src = 'Bengali.traineddata'
dest = '/usr/share/tesseract-ocr/4.00/tessdata/'
shutil.copy(src, dest)
filenames = os.listdir('/usr/share/tesseract-ocr/4.00/tessdata/')
print(filenames)
