# -*- coding: utf-8 -*-
"""
ss_opbs.py
==========

Модуль перехвата окна "После Боевая Статистика" (ПБО / ОПС).

Перехватывает вызов as_setDataS в BattleResultsWindow,
модифицирует data['common']['arenaStr'] — дописывает HTML-блок
с макросами статистики, которые раскрываются в цвета и значения.

БЕЗОПАСНОСТЬ:
- Модифицируется ТОЛЬКО data['common']['arenaStr'] (существующее поле).
- Запись в несуществующие поля data НЕ ДОПУСКАЕТСЯ — это вешает игру.
- Если battleResultsWindow.enable = false или нет format — оригинал вызывается без изменений.
"""

import traceback
import re

print ("VSS_OPBS Начало файла")

# --- Логгер ---
try:
    from ss_debuglog import vLog
except ImportError:
    vLog = None

# --- Конфиг ---
try:
    from ss_config import _instance as SSConfig
except ImportError:
    SSConfig = None

# --- Импорт класса окна ПБО ---
try:
    from gui.Scaleform.daapi.view.battle_results_window import BattleResultsWindow
except ImportError:
    BattleResultsWindow = None
    if vLog:
        vLog("Не удалось импортировать BattleResultsWindow", "VSS_OPBS")


# ================================================================
#  ФУНКЦИЯ ХУКА (вне класса!)
#  Обычная функция, не staticmethod — Python 2 передаёт
#  instance как self, data как data.
# ================================================================

def _hooked_as_setDataS(self, data):
    """
    Перехваченный метод as_setDataS.
    self — инстанс BattleResultsWindow (передаётся игрой).
    data — словарь с данными ПБО.
    """
    # --- Отладка: хук сработал ---
    print "[VSS_OPBS] _hooked_as_setDataS ВЫЗВАН"
    if vLog:
        vLog("Хук as_setDataS сработал!", "VSS_OPBS_DATA")

    try:
        # Проверка: включена ли модификация ПБО в конфиге
        enabled = False
        fmt = None

        if SSConfig is not None:
          enabled = SSConfig.get("battleResultsWindow", "enable", False)
          fmt = SSConfig.get("battleResultsWindow", "format", None)


        print "[VSS_OPBS] enabled=%s, fmt=%s" % (enabled, repr(fmt)[:100] if fmt else "None")

        if not enabled or not fmt:
            # Модификация отключена — вызываем оригинал как есть
            if SS_OPBS._orig_as_setDataS is not None:
                return SS_OPBS._orig_as_setDataS(self, data)
            return

        # Проверка: есть ли нужное поле в data
        if data is None or 'common' not in data or 'arenaStr' not in data['common']:
            if vLog:
                vLog("data не содержит common/arenaStr, пропускаем. Ключи data: %s" % (str(data.keys()) if data else "None"), "VSS_OPBS_DATA")
            if SS_OPBS._orig_as_setDataS is not None:
                return SS_OPBS._orig_as_setDataS(self, data)
            return

        # Логируем исходные данные для отладки
        arena = data['common'].get('arenaStr', '')[:200]
        if vLog:
            vLog("arenaStr (первые 200 символов): %s" % arena, "VSS_OPBS_DATA")
        print "[VSS_OPBS] arenaStr: %s" % arena[:100]

        # Обрабатываем шаблон макросами
        processed = SS_OPBS._process_template(fmt)
        if vLog:
            vLog("processed: %s" % str(processed)[:500], "VSS_OPBS_DATA")


        # Дописываем обработанный HTML к оригинальному arenaStr
        data['common']['arenaStr'] = data['common']['arenaStr'] + " " + processed

        if vLog:
            vLog("arenaStr модифицирован, длина: %d" % len(data['common']['arenaStr']), "VSS_OPBS_DATA")
        print "[VSS_OPBS] arenaStr модифицирован, новая длина: %d" % len(data['common']['arenaStr'])

    except Exception:
        if vLog:
            vLog("Ошибка в хуке: %s" % traceback.format_exc(), "VSS_OPBS")
        print "[VSS_OPBS] ОШИБКА: %s" % traceback.format_exc()

    # Вызываем оригинальный метод с (возможно) модифицированными данными
    if SS_OPBS._orig_as_setDataS is not None:
        return SS_OPBS._orig_as_setDataS(self, data)




class SS_OPBS(object):
    """
    Класс перехвата ПБО.
    Все методы — статические, инстанс не создаётся.
    """

    # Ссылка на оригинальный метод (до перехвата)
    _orig_as_setDataS = None

    # Флаг: установлен ли хук
    _hooked = False

    # --- Заглушки статистики (будут заменены реальными данными) ---
    _WN8 = 3200
    _EFF = 610
    _medPlace = 3
    _avgWinRate = 52.0

    @staticmethod
    def init():
        """
        Установка хука на as_setDataS.
        Вызывается из главного модуля при загрузке.
        """
        if BattleResultsWindow is None:
            if vLog:
                vLog("BattleResultsWindow не импортирован, хук не установлен", "VSS_OPBS")
            return False

        if SS_OPBS._hooked:
            if vLog:
                vLog("Хук уже установлен, пропускаем", "VSS_OPBS")
            return True

        try:
            # Сохраняем оригинальный метод
            SS_OPBS._orig_as_setDataS = BattleResultsWindow.as_setDataS

            # Подменяем на наш обработчик
            BattleResultsWindow.as_setDataS = _hooked_as_setDataS

            SS_OPBS._hooked = True
            if vLog:
                vLog("Хук as_setDataS установлен", "VSS_OPBS")
            return True

        except Exception:
            if vLog:
                vLog("Ошибка при установке хука: %s" % traceback.format_exc(), "VSS_OPBS")
            return False

    @staticmethod
    def fini():
        """
        Снятие хука. Вызывается при выгрузке мода.
        """
        if SS_OPBS._hooked and SS_OPBS._orig_as_setDataS is not None and BattleResultsWindow is not None:
            try:
                BattleResultsWindow.as_setDataS = SS_OPBS._orig_as_setDataS
            except Exception:
                pass
        SS_OPBS._hooked = False
        SS_OPBS._orig_as_setDataS = None

    # ================================================================
    #  ДВИЖОК МАКРОСОВ
    # ================================================================

    @staticmethod
    def _process_template(template):
        """
        Заменяет макросы в шаблоне HTML на значения и цвета.

        Поддерживаемые макросы:
        - {{WN8}}            — значение WN8 (число)
        - {{EFF}}            — значение EFF (число)
        - {{medPlace}}       — среднее место (число)
        - {{avgWinRate}}     — средний % побед (число)
        - {{c:WN8}}          — цвет для WN8 из palette
        - {{c:EFF}}          — цвет для EFF из palette
        - {{c:medPlace}}     — цвет для medPlace из gradient
        - {{c:avgWinRate}}   — цвет для avgWinRate из palette
        - {{g:medPlace}}     — цвет для medPlace из gradient
        - {{medPlace:d}}     — целое значение medPlace
        - {{avgWinRate:1f}}  — float с 1 знаком после запятой
        """

        result = template

        # --- Подстановка значений ---
        result = result.replace("{{WN8}}", str(SS_OPBS._WN8))
        result = result.replace("{{EFF}}", str(SS_OPBS._EFF))
        result = result.replace("{{medPlace}}", str(SS_OPBS._medPlace))
        result = result.replace("{{avgWinRate}}", str(SS_OPBS._avgWinRate))

        # --- Форматированные значения ---
        # {{medPlace:d}} — целое
        result = result.replace("{{medPlace:d}}", str(int(SS_OPBS._medPlace)))

        # {{avgWinRate:1f}} — один знак после запятой
        result = result.replace("{{avgWinRate:1f}}", "%.1f" % SS_OPBS._avgWinRate)

        # --- Цветовые макросы ---
        # {{c:WN8}} — цвет из palette по значению WN8
        color_wn8 = SS_OPBS._resolve_color_for("WN8", SS_OPBS._WN8)
        result = result.replace("{{c:WN8}}", color_wn8)

        # {{c:EFF}} — цвет из palette по значению EFF
        color_eff = SS_OPBS._resolve_color_for("EFF", SS_OPBS._EFF)
        result = result.replace("{{c:EFF}}", color_eff)

        # {{c:medPlace}} — цвет из gradient по значению medPlace
        color_medplace = SS_OPBS._resolve_color_for("medPlace", SS_OPBS._medPlace)
        result = result.replace("{{c:medPlace}}", color_medplace)

        # {{c:avgWinRate}} — цвет из palette по значению avgWinRate
        color_winrate = SS_OPBS._resolve_color_for("avgWinRate", SS_OPBS._avgWinRate)
        result = result.replace("{{c:avgWinRate}}", color_winrate)

        # {{g:medPlace}} — цвет из gradient по значению medPlace
        grad_medplace = SS_OPBS._resolve_gradient_for("medPlace", SS_OPBS._medPlace)
        result = result.replace("{{g:medPlace}}", grad_medplace)

        return result

    # ================================================================
    #  РАЗРЕШЕНИЕ ЦВЕТОВ
    # ================================================================

    @staticmethod
    def _resolve_color_for(metric, value):
        """
        Разрешает цвет через SSConfig.resolve_palette() или SSConfig.resolve_gradient().

        Для метрик WN8, EFF, avgWinRate — используется palette.
        Для medPlace — используется gradient.

        Возвращает строку цвета (например, "#F8F400").
        """

        if SSConfig is None:
            return "#FFFFFF"

        # Для medPlace используем gradient (меньше = лучше)
        if metric == "medPlace":
            return SSConfig.resolve_gradient("medPlace", value)

        # Для остальных — palette (больше = лучше)
        return SSConfig.resolve_palette(metric, value)

    @staticmethod
    def _resolve_gradient_for(metric, value):
        """
        Разрешает цвет через SSConfig.resolve_gradient().
        """
        if SSConfig is None:
            return "#FFFFFF"
        return SSConfig.resolve_gradient(metric, value)
