# ss_session_log.py
# -*- coding: utf-8 -*-
from collections import OrderedDict
import os
import json
import datetime
import threading
# --- НАСТРОЙКИ ПУТЕЙ ---
# Вместо того чтобы искать "mods/", используем текущее рабочее окружение клиента.
# Клиент позволяет писать файлы в любые поддиректории своего корня,
# поэтому мы строим путь прямо от текущего working directory.

# Получаем текущий рабочий каталог процесса игры
GAME_ROOT = os.getcwd()
LOGS_DIR = os.path.join(GAME_ROOT, 'mods/configs/vetus_session_stats/logs')
LOG_FILE_NAME = 'session_debug.log'
LOG_FILE_PATH = os.path.join(LOGS_DIR, LOG_FILE_NAME)
# Глобальный замок для потокобезопасности
_log_lock = threading.Lock()

def _ensure_log_dir():
    """Создает папку для логов, если её нет."""
    if not os.path.exists(LOGS_DIR):
        try:
            os.makedirs(LOGS_DIR)
        except OSError:
            pass

def _format_timestamp():
    """Возвращает текущее время в формате dd.mm.yyyy hh:mm"""
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

def _serialize(obj):
    """
    Простая сериализация без использования json.dumps().
    Работает только для простых структур данных.
    """
    try:
        # Для чисел и булевых значений
        return str(obj)
    except Exception:
        # Для словарей и списков
        if hasattr(obj, 'items'):
            # Словарь
            items = ["\"%s\": %s" % (_serialize(k), _serialize(v)) for k, v in obj.items()]
            return "{%s}" % ", ".join(items)
        elif hasattr(obj, '__iter__'):
            # Список/кортеж
            items = [_serialize(x) for x in obj]
            return "[%s]" % ", ".join(items)
        else:
            # Строки и прочие объекты
            return "\"%s\"" % obj

def vLog(data, label="DEBUG"):
    """
    Основная функция логирования.
    - data: что угодно (строка, число, dict, list, None)
    - label: метка типа сообщения
    """

    _ensure_log_dir()
    
    log_entry = OrderedDict([
        ("timestamp", _format_timestamp()),
        ("label", label),
        ("data", data)
    ])

    with _log_lock:
        try:
            with open(LOG_FILE_PATH, 'a') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, separators=(',', ':')) + '\n')
        except IOError:
            pass

# Тестовый блок (можно удалить в финальной версии)
if __name__ == "__main__":
    vLog("Тестовый запуск логгера Lesta")
    vLog({"test": u"Путь к логам: {}".format(LOGS_DIR)}, "PATH_CHECK")