# coding=utf-8

from django.conf.urls import url

from api import views

urlpatterns = [
    url(r'^files_ocr/$', views.files_ocr),
]
