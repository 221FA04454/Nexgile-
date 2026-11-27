FROM python:3.12-slim
WORKDIR /workspace
RUN useradd --create-home --uid 10001 appuser
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend /workspace/backend
COPY worker /workspace/worker
RUN chown -R appuser:appuser /workspace
USER appuser
ENV PYTHONPATH=/workspace/backend
ENV WORKER_INTERVAL_SECONDS=60
ENTRYPOINT ["python", "/workspace/worker/docker_entrypoint.py"]
