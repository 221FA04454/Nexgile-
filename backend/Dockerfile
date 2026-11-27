FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app
EXPOSE 8000
ENTRYPOINT ["python", "/app/docker_entrypoint.py"]
