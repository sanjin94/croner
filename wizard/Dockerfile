FROM alpine/k8s:1.24.13

RUN apk update && \
    apk add python3 py3-pip

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 1404

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "1404"]