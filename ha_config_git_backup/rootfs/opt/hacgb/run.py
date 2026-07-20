"""容器入口。

刻意用绝对路径的脚本作为入口，而不是 `python3 -m hacgb` 配 `ENV PYTHONPATH`：
s6-overlay 把容器环境变量存进 /run/s6/container_environment/，只有走
`with-contenv` 的服务才读得到，而 Dockerfile 的 CMD 是作为 legacy service
拉起的——ENV 在那里一律为空。实测 `PYTHONPATH` 和 `PYTHONUNBUFFERED` 都会丢。

用绝对路径运行脚本时，Python 会把脚本所在目录（/opt/hacgb）放到 sys.path[0]，
于是 `import hacgb` 无需任何环境变量即可解析。
日志缓冲则由 CMD 里的 `-u` 解决，同样不依赖环境变量。
"""

from hacgb.__main__ import main

raise SystemExit(main())
