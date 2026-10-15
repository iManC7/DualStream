FROM python:3.11-slim

# تثبيت FFmpeg والتحديثات الأساسية
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# نسخ جميع ملفات المشروع
COPY . /app

# تشغيل السيرفر السحابي
EXPOSE 10000
CMD ["python", "server.py"]