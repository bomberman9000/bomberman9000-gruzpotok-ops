FROM python:3.12-slim

WORKDIR /app

# Полный образ с LibreOffice. Меньший вариант без soffice: Dockerfile.slim (только fpdf).
# LibreOffice (headless) для pdf_engine=libreoffice: HTML → PDF через soffice.
# Увеличивает размер образа; без этого в контейнере доступен только fpdf.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libreoffice-writer-nogui \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV LIBREOFFICE_SOFFICE_PATH=/usr/bin/soffice

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tools ./tools
COPY tests ./tests
COPY pytest.ini .
COPY data/knowledge ./data/knowledge

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
