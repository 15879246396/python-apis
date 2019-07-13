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
    """
                     1          2         3      4
        1    德国  ：VAT、      EORI 、   报税号、 临时税号
        2    法国  ：VAT
        3    西班牙：VAT、      本地税号
        4    意大利：VAT_VIES、 VAT_temp 、 EORI
        5    英国  ：VAT

    """
    data = request.data
    site_id = str(data.get("site_id"))
    file_type = str(data.get("file_type"))
    file = request.FILES.get('file')
    if not all((file, file_type)):
        return Response({"data": 'params error', "code": 0})
    # 解压
    zip_file = None
    rar_file = None
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

    if site_id == "1":
        if file_type not in ["1", "2", "3", "4", ]:
            return Response({"data": 'file_type format error', "code": 0})
        template = "./files/templates/{}-{}.png".format(site_id, file_type)
        templates = [template]
    elif site_id == "2":
        if file_type not in ["1", ]:
            return Response({"data": 'file_type format error', "code": 0})
        template_1 = "./files/templates/{}-{}_1.png".format(site_id, file_type)
        template_2 = "./files/templates/{}-{}_2.png".format(site_id, file_type)
        templates = [template_1, template_2]
    elif site_id == "3":
        if file_type not in ["1", "2"]:
            return Response({"data": 'file_type format error', "code": 0})
        template = "./files/templates/{}-{}.png".format(site_id, file_type)
        templates = [template]
    elif site_id == "4":
        if file_type not in ["1", "2", "3"]:
            return Response({"data": 'file_type format error', "code": 0})
        template = "./files/templates/{}-{}.png".format(site_id, file_type)
        templates = [template]
    elif site_id == "5":
        if file_type not in ["1"]:
            return Response({"data": 'file_type format error', "code": 0})
        template_1 = "./files/templates/{}-{}_1.png".format(site_id, file_type)
        template_2 = "./files/templates/{}-{}_2.png".format(site_id, file_type)
        template_3 = "./files/templates/{}-{}_3.png".format(site_id, file_type)
        templates = [template_1, template_2, template_3]
    else:
        return Response({"data": 'site_id format error', "code": 0})

    png_list = []
    for pdf in compress_list:
        # 读pdf
        pdf_file = zip_file.read(pdf) if isinstance(pdf, zipfile.ZipInfo) else rar_file.read(pdf)

        # 转png
        page = 0
        if site_id == "4" and file_type == "2":
            page = 1
        png_io = convert_pdf_to_jpg(pdf_stream=pdf_file, p=page, zoom=150 if site_id in ["2", "3", "4"] else 100)
        if not png_io:
            continue
        # with open('5-1_3.png', 'wb') as f:
        #     f.write(png_io.getvalue())
        # return

        # 根据模版剪裁
        try:
            png_data = {'name': pdf.filename.decode("gbk"), "file": []}
        except UnicodeDecodeError:
            try:
                png_data = {'name': pdf.filename.decode("unicode_escape"), "file": []}
            except UnicodeDecodeError:
                png_data = {'name': pdf.filename, "file": []}

        for template in templates:
            match_result = matchImg(png_io.getvalue(), template, 0.5)
            if not match_result:
                png_data = {'name': pdf.filename, "file": []}
                break
            rectangle = match_result['rectangle']
            x, y = rectangle[0]
            w, h = rectangle[-1]
            coordinate = (x, y, w, h)
            out_img = cut_img(png_io, coordinate)
            # with open('111.png', "wb") as f:
            #     f.write(out_img.getvalue())
            # return
            png_data["file"].append(out_img)
        png_list.append(png_data)
    results = {}
    data = {}

    def callback(_, d):
        file_no = d[0]
        r = re.findall(r'([A-Z]{2}\d{5})', file_no)
        if r:
            file_no = r[0]
        tax_no = d[1].replace(' ', '').replace("/", '')
        date_1 = d[2].replace(' ', '').replace("/", '') if len(d) > 2 else ''
        date_2 = d[3].replace(' ', '').replace("/", '') if len(d) == 4 else ''
        results[file_no] = {
            "tax_no": tax_no,
            "date_1": date_1,
            "date_2": date_2,
        }

    pool = threadpool.ThreadPool(4)
    reqs = threadpool.makeRequests(ocr_look_result, png_list, callback)
    [pool.putRequest(req) for req in reqs]
    pool.wait()

    if site_id == "1":
        if file_type != "3":
            for k, v in results.items():
                r = re.findall(r'([A-Z]{2}\d+)', v["tax_no"])
                if r:
                    v["tax_no"] = r[0]
                data[k] = v
        else:
            for k, v in results.items():
                data[k] = v
    elif site_id == "2":
        for k, v in results.items():
            data[k] = v
    elif site_id == "3":
        if file_type == "1":
            for k, v in results.items():
                r = re.findall(r'(ESN\d+[A-Z])', v["tax_no"])
                if r:
                    v["tax_no"] = r[0]
                data[k] = v
        else:
            for k, v in results.items():
                data[k] = v
    elif site_id == "4":
        if file_type in ["1", "2"]:
            for k, v in results.items():
                r = re.findall(r'(\d+)', v["tax_no"])
                if r:
                    v["tax_no"] = r[0]
                data[k] = v
        else:
            for k, v in results.items():
                data[k] = v
    elif site_id == "5":
        for k, v in results.items():
            r = re.findall(r'(\d+)', v["tax_no"])
            if r:
                v["tax_no"] = r[0]
            r = re.findall(r'(\d{2}[A-Z][a-z]+\d{4})', v["date_1"])
            if r:
                v["date_1"] = r[0]
            r = re.findall(r'(\d{2}.{2,3}\d{4})', v["date_2"])
            if r:
                v["date_2"] = r[0]
            data[k] = v

    return Response({"data": data, "code": 1})
