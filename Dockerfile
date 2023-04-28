FROM python:slim-bullseye

WORKDIR /app

RUN 

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt 

COPY . .

EXPOSE 1444

CMD ["streamlit", "run", "--server.enableCORS=false", "--server.port=1444", "app.py"]