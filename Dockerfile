FROM python:3.13-slim
RUN pip install aiohttp beautifulsoup4
WORKDIR /app
COPY . .
RUN python -c "\
from stagehand.toolbox import xmlconfig; \
xmlconfig.convert('stagehand/config.cxml', 'stagehand/config.py', 'stagehand', 'stagehand.toolbox.config'); \
xmlconfig.convert('stagehand/searchers/easynews_config.cxml', 'stagehand/searchers/easynews_config.py', 'stagehand.searchers', 'stagehand.toolbox.config'); \
xmlconfig.convert('stagehand/notifiers/email_config.cxml', 'stagehand/notifiers/email_config.py', 'stagehand.notifiers', 'stagehand.toolbox.config'); \
xmlconfig.convert('stagehand/notifiers/xbmc_config.cxml', 'stagehand/notifiers/xbmc_config.py', 'stagehand.notifiers', 'stagehand.toolbox.config'); \
"
CMD ["python", "-m", "stagehand.bootstrap"]
