# Supervisor 自 2026.04.0 起不再自动注入 BUILD_FROM，因此这里必须自带默认值。
ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.14-alpine3.24
FROM ${BUILD_FROM}

RUN apk add --no-cache \
      git \
      openssh-client \
      rsync

COPY rootfs /

RUN chmod +x /opt/hacgb/askpass.sh

# 不用 ENV PYTHONPATH：s6-overlay 把容器环境变量存进
# /run/s6/container_environment/，只有 with-contenv 服务读得到，而 CMD 是作为
# legacy service 拉起的，ENV 在那里一律为空（实测 PYTHONPATH 与
# PYTHONUNBUFFERED 双双丢失，导致 `python3 -m hacgb` 报 No module named hacgb）。
#
# 改用绝对路径脚本入口：Python 会把脚本所在目录放进 sys.path[0]，无需环境变量。
# -u 取代被剥离的 PYTHONUNBUFFERED，否则日志会卡在缓冲区里，
# add-on 日志页面看着像"什么都没发生"，排障时极具误导性。
CMD [ "python3", "-u", "/opt/hacgb/run.py" ]
