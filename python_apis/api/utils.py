# -*- coding: utf-8 -*-
import base64
import os

import aircv
import cv2
import fitz
import numpy
import requests
from io import BytesIO
from PIL import Image, ImageEnhance


def convert_pdf_to_jpg(pdf_stream):
    doc = fitz.open('type', pdf_stream)
    page = doc[0]
    zoom = int(100)
    rotate = int(0)
    trans = fitz.Matrix(zoom / 100.0, zoom / 100.0).preRotate(rotate)
    pm = page.getPixmap(matrix=trans, alpha=False)

    png_io = BytesIO(pm.getPNGData())
    return png_io


def matchImg(src, img_obj, confidence=0.2):  # imgsrc=原始图像，imgobj=待查找的图片
    img_obj = aircv.imread(img_obj)
    imgsrcNPArray = numpy.fromstring(src, numpy.uint8)
    img_src = cv2.imdecode(imgsrcNPArray, cv2.IMREAD_COLOR)

    match_result = aircv.find_template(img_src, img_obj, confidence)
    # {'confidence': 0.5435812473297119, 'rectangle': ((394, 384), (394, 416), (450, 384), (450, 416)), 'result': (422.0, 400.0)}
    if match_result is not None:
        match_result['shape'] = (img_src.shape[1], img_src.shape[0])  # 0为高，1为宽

    return match_result


def cut_img(img_src, coordinate):
    image = Image.open(img_src)
    region = image.crop(coordinate)
    region = ImageEnhance.Contrast(region).enhance(1.5)
    img_io = BytesIO()
    region.save(img_io, format='png')
    return img_io


def ocr_look_result(image, language_type='ENG'):
    image_name, image_io = image['name'], image['file']
    image_data = image_io.getvalue()
    base64_ima = str(base64.b64encode(image_data)).replace("b'", "").replace("'", "")
    data = {
        'image': base64_ima,
        "language_type": language_type
    }
    headers = {
        'Authorization': 'APPCODE aa27272bbda7484f8593b9d6e44bba18',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'detect_direction': 'false',
        'detect_language': 'false',
        'probability': 'false'
    }
    url = "http://wenzi.market.alicloudapi.com/do"
    result = requests.post(url, data=data, headers=headers, verify=False, timeout=15).json()
    if 'words_result' in result:
        data = (image_name, result['words_result'][0]['words'])
        return data

