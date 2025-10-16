FROM python:3.12
ADD main.py .
ADD requirements.txt .
ADD .env .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y tzdata
ENV TZ=America/New_York
CMD ["python", "./main.py"]