# -*- coding: utf-8 -*-
import base64
import os

import aircv
import fitz
import requests
from PIL import Image, ImageEnhance


def convert_pdf_to_jpg(file_path):
    doc = fitz.open(file_path)
    page = doc[0]
    zoom = int(100)
    rotate = int(0)
    trans = fitz.Matrix(zoom / 100.0, zoom / 100.0).preRotate(rotate)
    pm = page.getPixmap(matrix=trans, alpha=False)

    pm.writePNG('./files/pdf_png/pdf.png')


def matchImg(imgsrc, imgobj, confidence=0.2):  # imgsrc=原始图像，imgobj=待查找的图片
    imsrc = aircv.imread(imgsrc)
    imobj = aircv.imread(imgobj)

    match_result = aircv.find_template(imsrc, imobj, confidence)
    # {'confidence': 0.5435812473297119, 'rectangle': ((394, 384), (394, 416), (450, 384), (450, 416)), 'result': (422.0, 400.0)}
    if match_result is not None:
        match_result['shape'] = (imsrc.shape[1], imsrc.shape[0])  # 0为高，1为宽

    return match_result


def cut_img(imgsrc, out_img_name, coordinate):
    image = Image.open(imgsrc)
    region = image.crop(coordinate)
    region = ImageEnhance.Contrast(region).enhance(1.5)
    region.save(out_img_name)


def ocr_look_result(image_path, language_type='ENG'):
    with open(image_path, 'rb') as f:
        image_data = f.read()
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
        base_name = os.path.basename(image_path)[:-4]
        if 'words_result' in result:
            data = (base_name, result['words_result'][0]['words'])
            return data

