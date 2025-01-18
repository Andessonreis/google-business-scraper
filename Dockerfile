FROM python:3.10-slim

RUN apt-get update && apt-get install -y curl wget && apt-get clean

# Instala o Playwright
RUN pip install --no-cache-dir playwright && playwright install --with-deps

WORKDIR /app
COPY main.py .
COPY output/ ./output/

# Instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
