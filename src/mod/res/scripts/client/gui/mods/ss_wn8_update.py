# -*- coding: utf-8 -*-
"""
ss_wn8_update.py
================
Фоновое автообновление таблицы ожидаемых значений WN8 с static.modxvm.com.

check_and_update() запускаетdaemon-поток и сразу возвращает управление.
Скачивание не блокирует игру.
"""

import os
import time
import json
import threading

try:
    from ss_debuglog import vLog
except ImportError:
    vLog = None

# URL таблицы Lesta (для игроков на серверах Лесты/России)
WN8_URL = "https://static.modxvm.com/wn8-data-exp/json/lesta/wn8exp.json"

# Проверять обновление не чаще, чем раз в N дней
UPDATE_INTERVAL_DAYS = 1


def _download(url):
    """Скачивает данные по URL. Возвращает строку или None."""
    try:
        import urllib2

        req = urllib2.Request(url, headers={
            'User-Agent': 'VetusSessionStats/1.0'
        })
        resp = urllib2.urlopen(req, timeout=15)
        data = resp.read()
        if vLog:
            vLog("WN8UPD: Скачано %d байт" % len(data), "VSS_WN8UPD")
        return data
    except Exception as e:
        if vLog:
            vLog("WN8UPD: Ошибка скачивания: %s" % str(e), "VSS_WN8UPD")
        return None


def _validate(raw_data):
    """Проверяет, что скачанные данные — корректная таблица WN8."""
    try:
        parsed = json.loads(raw_data)
    except Exception:
        return None

    # XVM-формат: {"data": [...]}
    if isinstance(parsed, dict):
        data = parsed.get('data')
        if isinstance(data, list) and len(data) > 0:
            required = ['IDNum', 'expDamage', 'expFrag', 'expSpot', 'expDef', 'expWinRate']
            if all(k in data[0] for k in required):
                return data

    # Fallback: плоский массив [...]
    if isinstance(parsed, list) and len(parsed) > 0:
        required = ['IDNum', 'expDamage', 'expFrag', 'expSpot', 'expDef', 'expWinRate']
        if all(k in parsed[0] for k in required):
            return parsed

    return None


def _do_update(table_path, url):
    """Фоновое скачивание и сохранение таблицы. Работает в потоке."""
    try:
        if vLog:
            vLog("WN8UPD: Запрос обновления таблицы с %s" % url, "VSS_WN8UPD")

        raw = _download(url)
        if raw is None:
            if vLog:
                vLog("WN8UPD: Не удалось скачать таблицу", "VSS_WN8UPD")
            return

        parsed = _validate(raw)
        if parsed is None:
            if vLog:
                vLog("WN8UPD: Скачанный файл невалиден или неверный формат", "VSS_WN8UPD")
            return

        # Бэкап старого файла
        if os.path.exists(table_path):
            backup = table_path + '.bak'
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(table_path, backup)
            except Exception:
                pass

        # Сохраняем новый
        with open(table_path, 'wb') as f:
            f.write(raw)

        if vLog:
            vLog("WN8UPD: Таблица обновлена (%d танков)" % len(parsed), "VSS_WN8UPD")

    except Exception as e:
        if vLog:
            vLog("WN8UPD: Ошибка обновления таблицы: %s" % str(e), "VSS_WN8UPD")


def check_and_update(table_path, url=None):
    """Запускает обновление в фоновом потоке. Не блокирует игру.

    Возвращает False немедленно (обновление идёт в фоне).
    """
    if url is None:
        url = WN8_URL

    # Проверяем возраст — если свежая, поток не запускаем
    if os.path.exists(table_path):
        file_age_days = (time.time() - os.path.getmtime(table_path)) / 86400
        if file_age_days < UPDATE_INTERVAL_DAYS:
            if vLog:
                vLog("WN8UPD: Таблица свежая (%.0f дней), обновление не требуется" % file_age_days, "VSS_WN8UPD")
            return

    t = threading.Thread(target=_do_update, args=(table_path, url))
    t.daemon = True
    t.start()

    if vLog:
        vLog("WN8UPD: Фоновый поток обновления запущен", "VSS_WN8UPD")
