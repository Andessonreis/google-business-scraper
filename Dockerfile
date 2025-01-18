# Usa uma imagem base do Python
FROM python:3.10-slim

# Atualiza o sistema e instala dependências necessárias
RUN apt-get update && apt-get install -y curl wget && apt-get clean

# Instala o Playwright
RUN pip install --no-cache-dir playwright && playwright install --with-deps

# Copia os arquivos para o container
WORKDIR /app
COPY main.py .
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Cria a pasta 'output' se não existir
RUN mkdir -p output

# Define o comando padrão para rodar o script
CMD ["python", "main.py"]
