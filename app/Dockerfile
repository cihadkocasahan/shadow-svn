FROM alpine:3.18

# v1.2.6 Production-Grade Hub Image
RUN apk add --no-cache \
    git \
    git-svn \
    subversion \
    bash \
    openssh-client \
    perl \
    python3 \
    py3-pip \
    py3-flask \
    curl \
    tzdata

# Install Production Engines
RUN pip install apscheduler gunicorn cryptography --break-system-packages

WORKDIR /app
COPY . .

# UX: UTF-8 and Timezone handling
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Istanbul

RUN chmod +x /app/*.sh

EXPOSE 80

# Production Entry: Running with Gunicorn (1 Worker to keep Scheduler stable)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:80", "control_panel:app"]
