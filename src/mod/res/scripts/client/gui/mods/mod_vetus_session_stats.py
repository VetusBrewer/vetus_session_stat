# -*- coding: utf-8 -*-
"""
mod_vetus_session_stats.py - главный координатор мода сессионной статистики.
Lesta / Мир Танков, версия 1.45.0.0, Python 2.7, Scaleform AS2.

Этот файл - точка входа (entry point). Игра загружает любой .py с префиксом mod_
из папки res_mods/<версия>/scripts/client/gui/mods/.
Здесь мы инициализируем все подмодули и управляем их жизненным циклом.
"""

import os
import traceback

# --- ПОПЫТКА ИМПОРТА ЛОГГЕРА ---
# vLog(data, label) - пишет в mods/configs/vetus_session_stats/logs/session_debug.log
# Если логгер недоступен, используем print как запасной вариант (пишет в python.log)
try:
    from ss_debuglog import vLog
except ImportError:
    traceback.print_exc()
    def vLog(data, label="DEBUG"):
        print ("[{}] {}").format(label, data)

# --- ПОПЫТКА ИМПОРТА КОНФИГ-ИНСТРУМЕНТА ---
# SSConfig - синглтон для работы с config.json
try:
    from ss_config import SSConfig
except ImportError:
    traceback.print_exc()
    SSConfig = None

# --- ПОПЫТКА ИМПОРТА МОДУЛЯ ОПС (окно послебоевой статистики) ---
# SS_OPBS - класс, хукающий BattleResultsWindow.as_setDataS
try:
    from ss_opbs import SS_OPBS
except ImportError:
    traceback.print_exc()
    SS_OPBS = None

# --- ЗАГОЛУШКИ БУДУЩИХ ПОДМОДУЛЕЙ ---
# from ss_session import SS_Session
# from ss_battlestat import SS_BattleStat
# from ss_hide import SS_Hide
# from ss_buttons import SS_Buttons


def init():
    """
    Точка входа мода. Вызывается клиентом после загрузки всех модулей.
    """
    print ("[VSS_MAIN] init() start")

    # 1. Инициализация конфига
    if SSConfig is not None:
        try:
            cfg = SSConfig.instance()
            vLog("Конфиг загружен", "VSS_MAIN")
        except Exception:
            traceback.print_exc()
            vLog("Ошибка загрузки конфига", "VSS_MAIN")
    else:
        print ("[VSS_MAIN] SSConfig недоступен!")
        vLog("SSConfig не импортирован", "VSS_MAIN")

    # 2. Автообновление таблицы wn8exp с сайта XVM

    # --- Автообновление таблицы WN8 ---
    try:
        from ss_wn8_update import check_and_update
        import os
        table_path = os.path.join('mods', 'configs', 'vetus_session_stats', 'wn8exp.json')
        if vLog:
            vLog("Запуск автообновления таблицы WN8...", "VSS_WN8")
        check_and_update(table_path)
    except Exception as e:
        if vLog:
            vLog("WN8: Ошибка автообновления: %s" % str(e), "VSS_WN8")


    # 3. Запуск хука ОПС
    if SS_OPBS is not None:
        try:
            SS_OPBS.init()
            vLog("ОПС хук установлен", "VSS_MAIN")
        except Exception:
            traceback.print_exc()
            vLog("Ошибка установки хука ОПС", "VSS_MAIN")
    else:
        print( "[VSS_MAIN] SS_OPBS недоступен!")
        vLog("SS_OPBS не импортирован", "VSS_MAIN")

    print ("[VSS_MAIN] init() done")


def fini():
    """Вызывается при выгрузке мода."""
    print ("[VSS_MAIN] fini()")
    vLog("Выгрузка мода", "VSS_MAIN")

    if SS_OPBS is not None:
        try:
            SS_OPBS.fini()
        except Exception:
            traceback.print_exc()


def onConfigCheck():
    """Проверка изменения конфига (если onlineReloadConfig = true)."""
    if SSConfig is not None:
        try:
            cfg = SSConfig.instance()
            cfg.maybe_reload()
        except Exception:
            traceback.print_exc()
