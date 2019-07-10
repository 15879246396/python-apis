# -*- coding: utf-8 -*-
import re

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
    file_type = int(data.get("file_type"))
    file = request.FILES.get('file')
    if not all((file, file_type)):
        return Response({"data": 'params error', "code": 0})
    # 解压
    if file.name.endswith('.rar'):
        rar_file = rarfile.RarFile(file)
        rar_list = rar_file.infolist()
        compress_list = [x for x in rar_list if x.filename.endswith('.pdf')]
    elif file.name.endswith('.zip'):
        zip_file = zipfile.ZipFile(file)
        zip_list = zip_file.infolist()
        compress_list = [x for x in zip_list if x.filename.endswith('.pdf')]
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

    png_list = []
    for pdf in compress_list:
        try:
            pdf_file = rar_file.read(pdf)
        except UnboundLocalError:
            pdf_file = zip_file.read(pdf)
        png_io = convert_pdf_to_jpg(pdf_file)
        match_result = matchImg(png_io.getvalue(), template, 0.5)
        if not match_result:
            png_list.append({'name': pdf.filename, "file": 0})
            continue
        rectangle = match_result['rectangle']
        x, y = rectangle[0]
        w, h = rectangle[-1]
        coordinate = (x, y, w, h)
        out_img = cut_img(png_io, coordinate)
        png_list.append({'name': pdf.filename, "file": out_img})

    results = {}
    data = {}

    def callback(_, d):
        results[d[0]] = d[1].replace(' ', '')

    pool = threadpool.ThreadPool(4)
    reqs = threadpool.makeRequests(ocr_look_result, png_list, callback)
    [pool.putRequest(req) for req in reqs]
    pool.wait()

    if file_type != 3:
        for k in results:
            value = results[k]
            r = re.findall(r'([A-Z]{2}\d{5})', k)
            if r:
                k = r[0]
                data[k] = value
            r = re.findall(r'([A-Z]{2}\d+)', value)
            if r:
                data[k] = r[0]
    else:
        for k in results:
            value = results[k]
            data[k] = value
            r = re.findall(r'([A-Z]{2}\d{5})', k)
            if r:
                k = r[0]
                data[k] = value
    return Response({"data": data, "code": 1})
