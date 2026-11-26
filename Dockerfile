FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN find /etc/apt -type f \( -name "*.list" -o -name "*.sources" \) -exec sed -i \
      -e 's|http://deb.debian.org|https://deb.debian.org|g' \
      -e 's|http://security.debian.org|https://security.debian.org|g' {} + \
    && apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 douassess
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && pip check \
    && python -m pip freeze --all > /tmp/DOU-ASSESS-RUNTIME-DEPENDENCIES.txt
COPY alembic.ini ./
COPY RELEASE.env ./
COPY SBOM-6.70.cdx.json ./SBOM.cdx.json
RUN cp /tmp/DOU-ASSESS-RUNTIME-DEPENDENCIES.txt ./RUNTIME-DEPENDENCIES.txt
COPY migrations ./migrations
COPY app ./app
RUN mkdir -p /app/data/evidence /app/data/scans /app/data/ops && chown -R douassess:douassess /app
USER douassess
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
