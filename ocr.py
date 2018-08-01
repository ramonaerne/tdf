# import the necessary packages
from PIL import Image
import pytesseract

# load the image as a PIL/Pillow image, apply OCR, and then delete
# the temporary file
#filename = "frame_text.png"
#text = pytesseract.image_to_string(Image.open(filename))

# if the image is from an array
imarray = croppedclip.get_frame(0)
im = Image.fromarray(imarray)
text = pytesseract.image_to_string(im)

print(text)

