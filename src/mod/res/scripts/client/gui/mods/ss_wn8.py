# -*- coding: utf-8 -*-
"""
ss_wn8.py
=========
Расчёт WN8 для одного боя.

Загружает ожидаемые значения из mods/configs/vetus_session_stats/wn8exp.json,
находит танк по intCD (из коллектора или через игровой кэш),
считает WN8 по стандартной формуле.

Использование:
    from ss_wn8 import SSWN8
    result = SSWN8.calculate(stats)   # stats — из SSStatisticCollector.get_stats()
    if result:
        wn8 = result['wn8']
"""

import json
import os



try:
    from ss_debuglog import vLog
except ImportError:
    vLog = None


class SSWN8(object):
    _expected = {}          # IDNum -> {expDamage, expFrag, expSpot, expDef, expWinRate}
    _loaded = False


    @staticmethod
    def _load_expected():
        """Загружает таблицу ожидаемых значений WN8."""
        if SSWN8._loaded:
            return

        config_dir = os.path.join('mods', 'configs', 'vetus_session_stats')
        table_path = os.path.join(config_dir, 'wn8exp.json')

        if not os.path.exists(table_path):
            if vLog:
                vLog("WN8: Файл таблицы не найден: %s" % table_path, "VSS_WN8")
            return

        try:
            with open(table_path, 'rb') as f:
                data = f.read()
            parsed = json.loads(data)

            # XVM-формат: {"data": [...]}
            if isinstance(parsed, dict):
                parsed = parsed.get('data', [])

            for entry in parsed:
                idnum = entry.get('IDNum')
                if idnum is not None:
                    SSWN8._expected[idnum] = {
                        'expDamage': float(entry.get('expDamage', 0)),
                        'expFrag': float(entry.get('expFrag', 0)),
                        'expSpot': float(entry.get('expSpot', 0)),
                        'expDef': float(entry.get('expDef', 0)),
                        'expWinRate': float(entry.get('expWinRate', 0)),
                    }

            SSWN8._loaded = True
            if vLog:
                vLog("WN8: Загружено %d танков из %s" % (len(SSWN8._expected), table_path), "VSS_WN8")
        except Exception as e:
            if vLog:
                vLog("WN8: Ошибка загрузки: %s" % str(e), "VSS_WN8")

    # -------------------------------------------------------------------
    #  ЗАГРУЗКА ОЖИДАЕМЫХ ЗНАЧЕНИЙ
    # -------------------------------------------------------------------

    NATION_MAP = {
        'ussr': 0, 'germany': 1, 'usa': 2, 'china': 3, 'france': 4,
        'uk': 5, 'czech': 6, 'sweden': 7, 'poland': 8, 'italy': 9,
    }

    _name_to_cd = {}     # tankIcon -> intCD (из g_cache)
    _mapping_built = False


    # -------------------------------------------------------------------
    #  СОПОСТАВЛЕНИЕ tankIcon -> IDNum
    # -------------------------------------------------------------------

    @staticmethod
    def _build_name_mapping():
        if SSWN8._mapping_built:
            return
        SSWN8._mapping_built = True
        try:
            from items import vehicles as wg_vehicles
            import nations
            for nationID in range(len(nations.NAMES)):
                try:
                    for vid in wg_vehicles.g_list.getList(nationID).keys():
                        try:
                            vtype = wg_vehicles.g_cache.vehicle(nationID, vid)
                            if vtype and hasattr(vtype, 'name') and hasattr(vtype, 'compactDescr'):
                                name = vtype.name
                                # vtype.name может быть 'usa:A67_T57_58' — отрезаем нацию
                                if ':' in name:
                                    name = name.split(':', 1)[1]
                                SSWN8._name_to_cd[name] = vtype.compactDescr
                        except Exception:
                            pass
                except Exception:
                    pass
            if vLog:
                # Диагностический дамп: 5 случайных имён + поиск конкретных танков
                sample = list(SSWN8._name_to_cd.keys())[:5]
                vLog("WN8: mapping built (%d tanks). Sample names: %s" % (
                    len(SSWN8._name_to_cd), str(sample)), "VSS_WN8")
                for t in ['A67_T57_58', 'F74_AMX_M4_1949', 'S23_Strv_81', 'R228_Duplet']:
                    if t in SSWN8._name_to_cd:
                        vLog("WN8: FOUND %s -> %d" % (t, SSWN8._name_to_cd[t]), "VSS_WN8")
                    else:
                        vLog("WN8: NOT FOUND %s" % t, "VSS_WN8")
        except Exception as e:
            if vLog:
                vLog("WN8: Failed to build name mapping: %s" % str(e), "VSS_WN8")

    @staticmethod
    def _get_idnum(stats):
        vehicle = stats.get('vehicle', {})

        # Способ 1: intCD из данных боя
        intCD = vehicle.get('intCD')
        if intCD is not None:
            return intCD

        tankIcon = vehicle.get('tankIcon', '')
        nation = vehicle.get('nation', '')

        # Способ 2: формула (nation << 12) | (index << 4) | 1
        # Работает, когда tankIcon index = innationID
        if tankIcon and nation:
            nation_num = SSWN8.NATION_MAP.get(nation)
            if nation_num is not None:
                underscore_pos = tankIcon.find('_')
                if underscore_pos > 1:
                    try:
                        tank_index = int(tankIcon[1:underscore_pos])
                        idNum = (nation_num << 12) | (tank_index << 4) | 1
                        # Проверяем — если IDNum есть в таблице, формула сработала
                        if idNum in SSWN8._expected:
                            if vLog:
                                vLog("WN8: formula hit %s -> %d" % (tankIcon, idNum), "VSS_WN8")
                            return idNum
                    except (ValueError, TypeError):
                        pass

        # Способ 3: g_cache маппинг (fallback для танков, где index != innationID)
        if tankIcon:
            SSWN8._build_name_mapping()
            idNum = SSWN8._name_to_cd.get(tankIcon)
            if idNum is not None:
                if vLog:
                    vLog("WN8: mapping hit %s -> %d" % (tankIcon, idNum), "VSS_WN8")
                return idNum
            if vLog:
                vLog("WN8: '%s' not in mapping (%d tanks)" % (
                    tankIcon, len(SSWN8._name_to_cd)), "VSS_WN8")

        return None

    # -------------------------------------------------------------------
    #  РАСЧЁТ WN8
    # -------------------------------------------------------------------

    @staticmethod
    def calculate(stats):
        """
        Рассчитывает WN8 для одного боя.

        Возвращает словарь:
            wn8       — итоговое значение
            rDAMAGE, rFRAG, rSPOT, rDEF, rWIN — отношения
            expDamage, expFrag, expSpot, expDef, expWinRate — ожидаемые
        или None, если танк не найден.
        """
        SSWN8._load_expected()
        if not SSWN8._expected:
            return None

        idNum = SSWN8._get_idnum(stats)
        if idNum is None:
            if vLog:
                vLog("WN8: Не удалось определить IDNum танка", "VSS_WN8")
            return None

        exp = SSWN8._expected.get(idNum)
        if exp is None:
            if vLog:
                vLog("WN8: Танк IDNum=%d не найден в таблице" % idNum, "VSS_WN8")
            return None

        # Боевые данные
        combat = stats.get('combat', {})
        battle = stats.get('battle', {})

        damageDealt = combat.get('damageDealt') or 0
        kills = combat.get('kills') or 0
        spotted = combat.get('spotted') or 0
        defense = combat.get('baseDefense') or 0

        # Win rate: 100 если победа, 0 если поражение
        isWin = battle.get('resultShortStr') == 'win'
        winRate = 100.0 if isWin else 0.0

        # Ожидаемые значения
        expDamage = exp.get('expDamage', 0)
        expFrag = exp.get('expFrag', 0)
        expSpot = exp.get('expSpot', 0)
        expDef = exp.get('expDef', 0)
        expWinRate = exp.get('expWinRate', 0)

        if expDamage == 0 or expFrag == 0 or expSpot == 0 or expDef == 0 or expWinRate == 0:
            if vLog:
                vLog("WN8: Нулевые ожидаемые значения для IDNum=%d" % idNum, "VSS_WN8")
            return None

        # Отношения
        rDAMAGE = float(damageDealt) / expDamage
        rFRAG = float(kills) / expFrag
        rSPOT = float(spotted) / expSpot
        rDEF = float(defense) / expDef
        rWIN = winRate / expWinRate

        # Нормализация (Step 1)
        rWINc = max(0.0, (rWIN - 0.71) / (1.0 - 0.71))
        rDAMAGEc = max(0.0, (rDAMAGE - 0.22) / (1.0 - 0.22))
        rFRAGc = min(rDAMAGEc + 0.2, max(0.0, (rFRAG - 0.12) / (1.0 - 0.12)))
        rSPOTc = max(0.0, min(rDAMAGEc + 0.1, (rSPOT - 0.38) / (1.0 - 0.38)))
        rDEFc = max(0.0, min(rDAMAGEc + 0.1, (rDEF - 0.10) / (1.0 - 0.10)))

        # WN8 (Step 2)
        wn8 = (980.0 * rDAMAGEc +
               210.0 * rDAMAGEc * rFRAGc +
               155.0 * rFRAGc * rSPOTc +
               75.0 * rDEFc * rFRAGc +
               145.0 * min(1.8, rWINc))

        if vLog:
            vLog("WN8: tank=%s idNum=%d wn8=%.0f dmg=%.0f/%.0f frag=%.0f/%.1f spot=%.0f/%.1f def=%.0f/%.1f win=%.1f/%.1f" % (
                stats.get('vehicle', {}).get('tankIcon', ''),
                idNum, wn8,
                damageDealt, expDamage,
                kills, expFrag,
                spotted, expSpot,
                defense, expDef,
                winRate, expWinRate,
            ), "VSS_WN8")

        return {
            'wn8': wn8,
            'rDAMAGE': rDAMAGE,
            'rFRAG': rFRAG,
            'rSPOT': rSPOT,
            'rDEF': rDEF,
            'rWIN': rWIN,
            'expDamage': expDamage,
            'expFrag': expFrag,
            'expSpot': expSpot,
            'expDef': expDef,
            'expWinRate': expWinRate,
        }
