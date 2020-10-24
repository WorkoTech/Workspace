FROM python:3
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN pip install gunicorn

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/

CMD gunicorn -b :3002 --capture-output --enable-stdio-inheritance --log-level debug workspace.wsgi:application
