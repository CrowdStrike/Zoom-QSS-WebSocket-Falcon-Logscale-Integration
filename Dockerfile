FROM python:3.9.16-bullseye
ADD requirements.txt /
RUN pip3 install -r requirements.txt
ADD logscale.py /
ADD qss2logscale.py /

CMD [ "python", "./qss2logscale.py" ]
