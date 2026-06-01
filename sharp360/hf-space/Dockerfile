FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR ${HOME}/app

COPY --chown=user requirements-api.txt ./requirements-api.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
       --index-url https://download.pytorch.org/whl/cpu \
       torch==2.8.0 torchvision==0.23.0 \
    && python -m pip install --no-cache-dir -r requirements-api.txt \
    && python -m pip install --no-cache-dir "git+https://github.com/apple/ml-sharp.git"

COPY --chown=user . .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
