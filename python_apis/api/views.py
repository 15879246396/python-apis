# -*- coding: utf-8 -*-
import os
import re
import time

import rarfile
import zipfile
import threadpool
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from api.utils import convert_pdf_to_jpg, matchImg, cut_img, ocr_look_result


@csrf_exempt
@api_view(['POST'])
@parser_classes((JSONParser, MultiPartParser,))
def files_ocr(request):
    data = request.data
    file_type = data.get("file_type")
    file = request.FILES.get('file')
    if not all((file, file_type)):
        return Response({"data": 'params error', "code": 0})
    if not os.path.exists('./files/'):
        os.mkdir('./files/')
    file_path = './files/' + str(time.time()) + '/'
    os.mkdir(file_path)
    # 解压
    if file.name.endswith('.rar'):
        rar_file = rarfile.RarFile(file)
        rar_file.extractall(file_path)
    elif file.name.endswith('.zip'):
        zip_file = zipfile.ZipFile(file)
        zip_file.extractall(file_path)
    else:
        return Response({"data": 'file format error', "code": 0})
    if file_type == 1:
        template = './files/templates/vat_template.png'
    elif file_type == 2:
        template = './files/templates/eori_template.png'
    elif file_type == 3:
        template = './files/templates/formal_template.png'
    else:
        return Response({"data": 'params file_type error', "code": 0})
    for file in os.listdir(file_path):
        if file.endswith('.pdf'):
            pdf_path = os.path.join(file_path, file)
            convert_pdf_to_jpg(pdf_path)
            r = matchImg('./files/pdf_png/pdf.png', template, 0.5)
            rectangle = r['rectangle']
            x, y = rectangle[0]
            w, h = rectangle[-1]
            coordinate = (x, y, w, h)
            base_name = file.replace('.pdf', '.png')
            png_path = os.path.join('./files/pdf_png/', base_name)
            cut_img('./files/pdf_png/pdf.png', png_path, coordinate)
    os.remove('./files/pdf_png/pdf.png')

    png_list = []
    results = {}

    def callback(_, d):
        results[d[0]] = d[1].replace(' ', '')

    for f in os.listdir('./files/pdf_png/'):
        f_path = os.path.join('./files/pdf_png/', f)
        png_list.append(f_path)
    pool = threadpool.ThreadPool(4)
    reqs = threadpool.makeRequests(ocr_look_result, png_list, callback)
    [pool.putRequest(req) for req in reqs]
    pool.wait()
    if file_type != 3:
        for k in results:
            value = results[k]
            r = re.findall(r'([A-Z]{2}\d{5})', k)
            if r:
                del results[k]
                k = r[0]
            r = re.findall(r'([A-Z]{2}\d+)', value)
            if r:
                results[k] = r[0]
    else:
        for k in results:
            value = results[k]
            r = re.findall(r'([A-Z]{2}\d{5})', k)
            if r:
                del results[k]
                k = r[0]
                results[k] = value

    # 删除文件夹
    for file in os.listdir(file_path):
        pdf_path = os.path.join(file_path, file)
        os.remove(pdf_path)
        os.remove(os.path.join('./files/pdf_png/', file.replace('.pdf', '.png')))
    os.rmdir(file_path)
    return Response({"data": results, "code": 1})
