FROM daocloud.io/library/ubuntu:16.04
FROM daocloud.io/library/python:2.7.8

ENV LANG C.UTF-8

WORKDIR app/

COPY sources.list /etc/apt

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 40976EAF437D05B5 3B4FE6ACC0B21F32 \
 && apt-get update && apt-get install --force-yes -y \
 python3-dev \
 python3-setuptools \
 libmysqlclient-dev \
 && apt-get --force-yes -y autoremove \
 && apt-get --force-yes -y autoclean \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple/ \
 && pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com


COPY python_apis/ .

COPY rar_need/ .

RUN cp ./default.sfx /usr/local/bin \
 && cp ./rar /usr/local/bin \
 && cp ./rarfiles.lst /usr/local/bin \
 && cp ./unrar /usr/local/bin \
 && rm ./default.sfx \
 && rm ./rar \
 && rm ./rarfiles.lst \
 && rm ./unrar

RUN apt-get update \
 && apt-get install libsm6 \
 && apt-get install libxrender1 \
 && apt-get install libxext-dev

