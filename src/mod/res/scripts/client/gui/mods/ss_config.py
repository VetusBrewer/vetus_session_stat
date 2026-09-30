# -*- coding: utf-8 -*-
"""
ss_config.py - инструмент для работы с конфигом мода.
Lesta / Мир Танков, Python 2.7.

Читает config.json из mods/configs/vetus_session_stats/
Предоставляет доступ к палитрам цветов (palette, gradient) и произвольным ключам.
Реализован как синглтон: SSConfig.instance() возвращает единственный экземпляр.
"""

import os
import json
import traceback

# --- ИМПОРТ ЛОГГЕРА ---
try:
    from ss_debuglog import vLog
except ImportError:
    traceback.print_exc()
    def vLog(data, label="DEBUG"):
        print "[{}] {}".format(label, data)


class SSConfig(object):
    """
    Синглтон для работы с config.json.

    Основные методы:
        instance()                - получить единственный экземпляр
        get(section, key, default) - получить значение из вложенного ключа
        resolve_palette(metric, value)  - цвет по palette (верхняя граница, исключающая)
        resolve_gradient(metric, value) - цвет по gradient (нижняя граница, включающая)
        resolve_color(macro, value)     - универсальный: "c:WN8" -> palette, "g:medPlace" -> gradient
        maybe_reload()              - перечитать конфиг если файл изменился
    """

    _instance = None

    # Путь к конфигу: os.getcwd() = корень игры (например D:\Games\Tanki)
    CONFIG_DIR = os.path.join(os.getcwd(), "mods", "configs", "vetus_session_stats")
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

    def __init__(self):
        self._config = None
        self._mtime = 0
        self._load()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        """Читает config.json. При ошибке _config остаётся None."""
        try:
            self._mtime = os.path.getmtime(self.CONFIG_PATH)
        except OSError:
            self._mtime = 0

        try:
            with open(self.CONFIG_PATH, "r") as f:
                self._config = json.load(f)
            vLog("Конфиг загружен: %s" % self.CONFIG_PATH, "VSS_CONFIG")
        except IOError as e:
            vLog("Не удалось открыть config.json: %s" % str(e), "VSS_CONFIG")
            self._config = None
        except ValueError as e:
            vLog("Ошибка парсинга config.json: %s" % str(e), "VSS_CONFIG")
            self._config = None

    def get(self, section, key=None, default=None):
        """
        Получить значение из конфига.
        config.get("battleResultsWindow", "format")  -> строка HTML-шаблона
        config.get("onlineReloadConfig")              -> True/False
        config.get("battleResultsWindow", "enable", True) -> с дефолтом
        """
        if self._config is None:
            return default

        if key is None:
            return self._config.get(section, default)

        section_dict = self._config.get(section)
        if section_dict is None or not isinstance(section_dict, dict):
            return default
        return section_dict.get(key, default)

    def resolve_palette(self, metric, value):
        """
        Поиск цвета в секции "palette".
        value - ВЕРХНЯЯ граница (ИСКЛЮЧАЮЩАЯ).
        Берётся ПЕРВАЯ запись, где value > входного значения.
        Пример: palette.WN8, WN8=300 -> 300<471 -> красный.
        """
        if self._config is None:
            return None
        palette = self._config.get("palette")
        if palette is None:
            return None
        entries = palette.get(metric)
        if not entries or not isinstance(entries, list):
            return None

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if value < entry.get("value", 0):
                return entry.get("color")

        # Не нашлось - берём последний цвет
        last = entries[-1]
        if isinstance(last, dict):
            return last.get("color")
        return None

    def resolve_gradient(self, metric, value):
        """
        Поиск цвета в секции "gradient".
        value - НИЖНЯЯ граница (ВКЛЮЧАЮЩАЯ).
        Берётся ПОСЛЕДНЯЯ запись, где value <= входного значения.
        Пример: gradient.medPlace, medPlace=1 -> фиолетовый (1-е место).
        """
        if self._config is None:
            return None
        gradient = self._config.get("gradient")
        if gradient is None:
            return None
        entries = gradient.get(metric)
        if not entries or not isinstance(entries, list):
            return None

        result_color = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("value", 0) <= value:
                result_color = entry.get("color")
            else:
                break
        return result_color

    def resolve_color(self, macro, value):
        """
        Универсальный метод: "c:WN8" -> palette, "g:medPlace" -> gradient.
        """
        if macro is None or not isinstance(macro, str):
            return None
        parts = macro.split(":", 1)
        if len(parts) != 2:
            return None
        prefix = parts[0].strip()
        metric = parts[1].strip()
        if prefix == "c":
            return self.resolve_palette(metric, value)
        elif prefix == "g":
            return self.resolve_gradient(metric, value)
        return None

    def maybe_reload(self):
        """Перечитать конфиг если файл изменился и onlineReloadConfig=true."""
        if self._config is None:
            return
        if not self._config.get("onlineReloadConfig", False):
            return
        try:
            current_mtime = os.path.getmtime(self.CONFIG_PATH)
        except OSError:
            return
        if current_mtime != self._mtime:
            vLog("Конфиг изменился, перезагружаем...", "VSS_CONFIG")
            self._load()

_instance = SSConfig()