import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Запуск WSGI приложения")


# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем Flask-приложение из main.py
from main import main

application = main