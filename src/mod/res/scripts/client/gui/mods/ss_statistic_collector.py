# -*- coding: utf-8 -*-
"""
ss_statistic_collector.py
=========================
Коллектор статистики после боя.

Из raw data (dict из as_setDataS) извлекает все доступные данные,
очищает от HTML-тегов и иконок, складывает в единый словарь stats.

Структура stats:
{
    "battle": {
        "arenaStr": "Тундра — Полигон",
        "resultStr": "ПОБЕДА!",
        "resultShortStr": "win",
        "duration": "5 мин. 18 с",
        "finishReasonStr": "Вся техника противника уничтожена",
        "bonusType": 50,
        "startTime": "30.09.2026 0:03",
        "iconType": "xp",
        "wasInBattle": True,
    },
    "player": {
        "name": "VetusBrewer",
        "clanTag": "VEU",
        "isPremium": False,
        "isPremiumPlus": True,
        "playerRank": 0,
        "isTeamKiller": False,
        "isLegionnaire": False,
    },
    "vehicle": {
        "names": ["Об. 752"],
        "tankIcon": "R172_Object_752",
        "tankLevel": 9,
        "nation": "ussr",
        "deathReason": 0,
        "isKilled": True,
        "killerName": ":Вадим Таранов:",
    },
    "income": {
        "creditsTotal": 28672,      # creditsStr
        "xpTotal": 359,              # xpStr
        "crystalsTotal": 0,         # crystalStr
        "goldTotal": None,          # если есть
        "freeXPTotal": None,        # если есть
    },
    "credits": {
        "income": 28482,            # col3 "Начислено за бой"
        "teamBonus": 190,           # "Командный бонус от игроков с подпиской"
        "penaltyTeamDamage": 0,     # "Штраф за урон союзникам"
        "compensationTeamDamage": 0,# "Компенсация за урон от союзников"
        "subtotal": 28672,          # "Итого за бой:"
        "repair": -4000,            # "Автоматический ремонт техники"
        "shells": -5425,            # "Автопополнение боекомплекта"
        "equipment": -3000,        # "Автопополнение снаряжения"
        "net": 6753,               # финальный остаток (последняя значимая строка)
    },
    "combat": {
        # Из statValues (очищенные)
        "shots": 5,
        "directHits": 5,
        "piercings": 4,
        "heDamage": 0,
        "damageDealt": 1722,       # из efficiencyHeader
        "damageAssisted": 382,
        "armorBlocked": 490,
        "spotted": 0,
        "kills": 0,
        "crits": 0,
        "baseCapture": 0,
        "baseDefense": 0,
        "distanceKm": 2.55,
    },
    "efficiency": {
        # Из efficiencyHeader (уже чистые)
        "damage": "1 722",
        "armor": "490",
        "assist": "382",
        "assistStun": "-",
        "crits": "-",
        "kill": "-",
        "spotted": "-",
    },
    "achievements": {
        "left": [],
        "right": [],
    },
    "details": [],  # по каждому противнику
    "timeStats": [
        {"label": "Начало боя", "value": "0:03"},
        {"label": "Продолжительность боя", "value": "5 мин. 18 с"},
        {"label": "Время в бою до уничтожения", "value": "2 мин. 48 с"},
    ],
}

Методы:
    collect(data)   — извлекает всё, хранит в _stats
    get_stats()     — возвращает _stats
    get(key)        — возвращает _stats[key]
"""

import re
import traceback

# --- Логгер ---
try:
    from ss_debuglog import vLog
except ImportError:
    vLog = None


class SSStatisticCollector(object):
    """
    Сбор статистики из data окна ПБО.
    Все методы — статические, инстанс не нужен.
    """

    _stats = None

    # ---------------------------------------------------------------
    #  ОЧИСТКА HTML
    # ---------------------------------------------------------------

    _TAG_RE = re.compile(r'<[^>]+>')

    @staticmethod
    def _strip_html(value):
        """
        Удаляет HTML-теги, иконки, неразрывные пробелы.
        Возвращает чистую строку.
        """
        if value is None:
            return ""
        if not isinstance(value, (str, unicode)):
            value = str(value)
        # Удаляем все теги
        result = SSStatisticCollector._TAG_RE.sub('', value)
        # \n -> ""
        result = result.replace('\n', '')
        # &nbsp; и неразрывные пробелы
        result = result.replace('&nbsp;', ' ').replace(u'\xa0', ' ')
        # Лишние пробелы
        result = result.strip()
        return result

    @staticmethod
    def _parse_int(value):
        """
        Пробует извлечь целое число из строки.
        "18 988" -> 18988
        "-4 000" -> -4000
        "<FONT color=\"#bc0000\">-5 425</FONT>" -> -5425
        "0" -> 0
        "-" -> None
        """
        if value is None:
            return None
        s = SSStatisticCollector._strip_html(str(value))
        if not s or s == '-':
            return None
        # Удаляем всё кроме цифр, минуса и точки
        cleaned = re.sub(r'[^\d\-.]', '', s)
        if not cleaned or cleaned == '-':
            return None
        try:
            if '.' in cleaned:
                return int(float(cleaned))
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_float(value):
        """
        Пробует извлечь float из строки.
        "2,55" -> 2.55
        "382" -> 382.0
        "-" -> None
        """
        if value is None:
            return None
        s = SSStatisticCollector._strip_html(str(value))
        if not s or s == '-':
            return None
        cleaned = re.sub(r'[^\d,.-]', '', s)
        cleaned = cleaned.replace(',', '.')
        if not cleaned or cleaned == '-':
            return None
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_pair(value):
        """
        Разбирает строку вида "5/4" -> (5, 4).
        "<FONT ...>0</FONT>/<FONT ...>0</FONT>" -> (0, 0)
        """
        if value is None:
            return (None, None)
        s = SSStatisticCollector._strip_html(str(value))
        if '/' in s:
            parts = s.split('/', 1)
            return (SSStatisticCollector._parse_int(parts[0]),
                    SSStatisticCollector._parse_int(parts[1]))
        return (SSStatisticCollector._parse_int(s), None)

    # ---------------------------------------------------------------
    #  СБОР
    # ---------------------------------------------------------------

    @staticmethod
    def collect(data):
        """
        Главный метод: извлекает всё из data, складывает в _stats.
        """
        if data is None:
            return

        stats = {}

        # --- common ---
        common = data.get('common', {})
        stats['battle'] = {
            'arenaStr': common.get('arenaStr', ''),
            'resultStr': common.get('resultStr', ''),
            'resultShortStr': common.get('resultShortStr', ''),
            'duration': common.get('duration', ''),
            'finishReasonStr': common.get('finishReasonStr', ''),
            'bonusType': common.get('bonusType'),
            'startTime': common.get('arenaCreateTimeStr', ''),
            'iconType': common.get('iconType', ''),
            'wasInBattle': common.get('wasInBattle', False),
            'epicMode': common.get('epicMode', False),
            'isFreeForAll': data.get('isFreeForAll', False),
        }

        # --- timeStats ---
        time_stats = common.get('timeStats', [])
        stats['timeStats'] = [
            {'label': ts.get('label', ''), 'value': ts.get('value', '')}
            for ts in time_stats if isinstance(ts, dict)
        ]

        # --- vehicle ---
        player_vehicles = common.get('playerVehicles', [])
        pv = player_vehicles[0] if player_vehicles else {}

        stats['vehicle'] = {
            'names': common.get('playerVehicleNames', []),
            'tankIcon': pv.get('tankIcon', ''),
            'intCD': pv.get('intCD') or pv.get('vehTypeCompDescr'),
            'tankLevel': pv.get('tankLevel'),
            'nation': pv.get('flag', ''),
            'deathReason': pv.get('deathReason'),
            'isKilled': pv.get('deathReason', -1) >= 0,
            'killerName': pv.get('killerFakeNameStr', ''),
            'vehicleStateStr': pv.get('vehicleStateStr', ''),
        }
        if vLog:
            vLog("PV keys: %s" % str(pv.keys()), "VSS_STAT")

        # --- personal ---
        personal = data.get('personal', {})

        # --- player info ---
        stats['player'] = {
            'name': common.get('playerRealNameStr', ''),
            'fakeName': common.get('playerFakeNameStr', ''),
            'fullName': common.get('playerFullNameStr', ''),
            'clanTag': common.get('clanNameStr', ''),
            'isPremium': personal.get('isPremium', False),
            'isPremiumPlus': personal.get('isPremiumPlus', False),
            'playerRank': personal.get('playerRank', 0),
            'isTeamKiller': personal.get('isTeamKiller', False),
            'isLegionnaire': personal.get('isLegionnaire', False),
        }

        # --- income (итоговые строки) ---
        stats['income'] = {
            'creditsTotal': SSStatisticCollector._parse_int(personal.get('creditsStr')),
            'xpTotal': SSStatisticCollector._parse_int(personal.get('xpStr')),
            'crystalsTotal': SSStatisticCollector._parse_int(personal.get('crystalStr')),
            'goldTotal': SSStatisticCollector._parse_int(personal.get('goldStr')),
            'freeXPTotal': SSStatisticCollector._parse_int(personal.get('freeXPStr')),
        }

        # --- credits breakdown ---
        stats['credits'] = SSStatisticCollector._extract_credits(personal)

        # --- xp breakdown ---
        stats['xp'] = SSStatisticCollector._extract_xp(personal)

        # --- combat stats (из statValues) ---
        stats['combat'] = SSStatisticCollector._extract_combat_stats(personal)

        # --- efficiency header ---
        eff = personal.get('efficiencyHeader', {})
        stats['efficiency'] = {
            'damage': SSStatisticCollector._parse_int(eff.get('damage')),
            'armor': SSStatisticCollector._parse_int(eff.get('armor')),
            'assist': SSStatisticCollector._parse_int(eff.get('assist')),
            'assistStun': SSStatisticCollector._strip_html(eff.get('assistStun', '')),
            'crits': SSStatisticCollector._strip_html(eff.get('crits', '')),
            'kill': SSStatisticCollector._strip_html(eff.get('kill', '')),
            'spotted': SSStatisticCollector._strip_html(eff.get('spotted', '')),
            'hasEfficiency': eff.get('hasEfficencyStats', False),
        }

        # --- achievements ---
        stats['achievements'] = {
            'left': personal.get('achievementsLeft', []),
            'right': personal.get('achievementsRight', []),
        }

        # --- details (по каждому противнику) ---
        stats['details'] = SSStatisticCollector._extract_details(personal)

        # --- battlePass ---
        stats['battlePass'] = SSStatisticCollector._extract_battlepass(data.get('battlePass', []))

        # --- quests ---
        stats['quests'] = data.get('quests', [])

        # Сохраняем
        SSStatisticCollector._stats = stats

        if vLog:
            vLog("Статистика собрана. Ключи: %s" % str(stats.keys()), "VSS_STAT")

        if vLog:
            for k, v in stats.items():
                vLog("%s: %s" % (k, str(v)[:30000]), "VSS_STAT")


        # --- WN8 ---
        try:
            from ss_wn8 import SSWN8
            wn8_result = SSWN8.calculate(stats)
            if vLog:
                if wn8_result:
                    vLog("WN8 result: %.0f" % wn8_result['wn8'], "VSS_WN8")
                else:
                    vLog("WN8 result: None", "VSS_WN8")
        except Exception as e:
            if vLog:
                vLog("WN8 error: %s" % str(e), "VSS_WN8")

            

        return stats

    # ---------------------------------------------------------------
    #  ЭКСТРАКТОРЫ
    # ---------------------------------------------------------------

    @staticmethod
    def _extract_credits(personal):
        """
        Разбирает creditsData -> словарь с чистыми числами.
        creditsData — list of list of dicts, каждый dict:
        {col1, col2, col3, col4, label, labelStripped, lineType, tooltip}

        col1 — без према, col3 — с премом.
        Берём col3 (с прем-аккаунтом).
        """
        result = {
            'income': None, 'teamBonus': None,
            'penaltyTeamDamage': None, 'compensationTeamDamage': None,
            'subtotal': None,
            'repair': None, 'shells': None, 'equipment': None,
            'net': None,
            'storageCredits': None,
            'storageGold': None,
            'raw': [],  # все строки для отладки
        }

        credits_data = personal.get('creditsData', [])
        if not credits_data or not isinstance(credits_data, list):
            return result

        # Берём первый блок (без према) и второй (с премом)
        # col1 — без према, col3 — с премом
        block = credits_data[0] if len(credits_data) > 0 else []
        if not isinstance(block, list):
            return result

        for entry in block:
            if not isinstance(entry, dict):
                continue
            label = entry.get('labelStripped', entry.get('label', ''))
            line_type = entry.get('lineType')

            # Пропускаем пустые разделители
            if line_type is None:
                continue

            col3 = entry.get('col3', '')  # с прем-аккаунтом
            val = SSStatisticCollector._parse_int(col3)

            raw_entry = {'label': label, 'value': val}
            result['raw'].append(raw_entry)

            # Маппинг по label
            if label is None:
                continue
            label_lower = label.strip()

            if label_lower == u'Начислено за бой':
                result['income'] = val
            elif label_lower == u'Командный бонус от игроков с подпиской':
                result['teamBonus'] = val
            elif label_lower == u'Штраф за урон союзникам':
                result['penaltyTeamDamage'] = val
            elif label_lower == u'Компенсация за урон от союзников':
                result['compensationTeamDamage'] = val
            elif label_lower == u'Итого за бой:':
                result['subtotal'] = val
            elif label_lower == u'Автоматический ремонт техники':
                result['repair'] = val
            elif label_lower == u'Автопополнение боекомплекта':
                result['shells'] = val
            elif label_lower == u'Автопополнение снаряжения':
                result['equipment'] = val
            elif label_lower == u'Итого:':
                result['net'] = val
            elif label_lower == u'Добавлено в хранилище ресурсов':
                result['storageCredits'] = val
                result['storageGold'] = SSStatisticCollector._parse_int(entry.get('col4', ''))

        # net — fallback, если "Итого:" не найдено
        if result['net'] is None:
            for entry in reversed(result['raw']):
                if entry['value'] is not None and entry['label']:
                    result['net'] = entry['value']
                    break

        return result

    @staticmethod
    def _extract_xp(personal):
        """
        Разбирает xpData -> словарь с чистыми числами.
        Структура аналогична creditsData.
        col1 — без према, col3 — с премом (опыт), col4 — с премом (элит-опыт).
        """
        result = {
            'base': None, 'teamBonus': None,
            'penaltyTeamDamage': None,
            'premiumVehicleBonus': None,
            'subtotal': None,
            'elite': None,  # элитный опыт
            'raw': [],
        }

        xp_data = personal.get('xpData', [])
        if not xp_data or not isinstance(xp_data, list):
            return result

        block = xp_data[0] if len(xp_data) > 0 else []
        if not isinstance(block, list):
            return result

        for entry in block:
            if not isinstance(entry, dict):
                continue
            label = entry.get('labelStripped', entry.get('label', ''))
            line_type = entry.get('lineType')

            if line_type is None:
                continue

            col3 = entry.get('col3', '')
            col4 = entry.get('col4', '')
            val = SSStatisticCollector._parse_int(col3)
            val_elite = SSStatisticCollector._parse_int(col4)

            raw_entry = {'label': label, 'value': val, 'elite': val_elite}
            result['raw'].append(raw_entry)

            if label is None:
                continue
            label_lower = label.strip()

            if label_lower == u'Начислено за бой':
                result['base'] = val
            elif label_lower == u'Командный бонус от игроков с подпиской':
                result['teamBonus'] = val
            elif label_lower == u'Штраф за урон союзникам':
                result['penaltyTeamDamage'] = val
            elif label_lower == u'Надбавка за уровень премиум машины':
                result['premiumVehicleBonus'] = val
            elif label_lower == u'Итого:':
                result['subtotal'] = val
                result['elite'] = val_elite

        return result

    @staticmethod
    def _extract_combat_stats(personal):
        """
        Разбирает statValues -> словарь боевой статистики.
        statValues — list of list of {label, value, infoTooltip}.
        Значения — строки, иногда с HTML.
        """
        result = {
            'shots': None,
            'directHits': None, 'piercings': None,
            'heDamage': None,
            'damageDealt': None,
            'damageAssisted': None,
            'spotted': None,
            'kills': None,
            'crits': None,
            'baseCapture': None, 'baseDefense': None,
            'distanceKm': None,
            'raw': [],
        }

        stat_values = personal.get('statValues', [])
        if not stat_values or not isinstance(stat_values, list):
            return result

        block = stat_values[0] if len(stat_values) > 0 else []
        if not isinstance(block, list):
            return result

        for entry in block:
            if not isinstance(entry, dict):
                continue
            label = entry.get('label', '')
            value = entry.get('value', '')

            stripped_label = SSStatisticCollector._strip_html(label)
            result['raw'].append({'label': stripped_label, 'value': SSStatisticCollector._strip_html(value)})

            if not stripped_label:
                continue

            # Маппинг
            if stripped_label == u'Произведено выстрелов':
                result['shots'] = SSStatisticCollector._parse_int(value)
            elif u'прямых попаданий/пробитий' in stripped_label:
                hits, piercings = SSStatisticCollector._parse_pair(value)
                result['directHits'] = hits
                result['piercings'] = piercings
            elif u'осколочно-фугасных' in stripped_label:
                result['heDamage'] = SSStatisticCollector._parse_int(value)
            elif u'помощью' in stripped_label:
                if result['damageAssisted'] is None:
                    result['damageAssisted'] = SSStatisticCollector._parse_int(value)
            elif u'Нанесено урона' in stripped_label or u'Всего нанесено' in stripped_label:
                if result['damageDealt'] is None:
                    result['damageDealt'] = SSStatisticCollector._parse_int(value)
            elif u'Обнаружено' in stripped_label:
                result['spotted'] = SSStatisticCollector._parse_int(value)
            elif u'уничтожено' in stripped_label.lower():
                # "Повреждено/уничтожено машин противника" -> value "2/0"
                # Второе число — уничтожено
                _, kills = SSStatisticCollector._parse_pair(value)
                result['kills'] = kills
            elif u'критических' in stripped_label or u'Криты' in stripped_label:
                result['crits'] = SSStatisticCollector._parse_int(value)
            elif u'захвата/защиты' in stripped_label or u'Захват' in stripped_label:
                cap, defn = SSStatisticCollector._parse_pair(value)
                result['baseCapture'] = cap
                result['baseDefense'] = defn
            elif u'километров' in stripped_label or u'Пройдено' in stripped_label:
                result['distanceKm'] = SSStatisticCollector._parse_float(value)

        return result

    @staticmethod
    def _extract_details(personal):
        """
        Разбирает details -> список словарей по каждому игроку-противнику.
        Берём только боевые поля (урон, броня, помощь, обнаружение, убийства).
        """
        results = []
        details = personal.get('details', [])
        if not details or not isinstance(details, list):
            return results

        block = details[0] if len(details) > 0 else []
        if not isinstance(block, list):
            return results

        for entry in block:
            if not isinstance(entry, dict):
                continue
            # Пропускаем groupLabel-записи
            if 'groupLabel' in entry and 'playerFakeName' not in entry:
                continue
            if 'playerFakeName' not in entry:
                continue

            results.append({
                'name': entry.get('playerFakeName', ''),
                'vehicle': entry.get('vehicleName', ''),
                'damageDealt': entry.get('damageDealt', 0),
                'damageAssisted': entry.get('damageAssisted', 0),
                'spotted': entry.get('spotted', 0),
                'killCount': entry.get('killCount', 0),
                'piercings': entry.get('piercings', 0),
                'deathReason': entry.get('deathReason', -1),
                'armorBlocked': SSStatisticCollector._parse_int(
                    entry.get('armorVals', [None, None, None])[2]
                    if entry.get('armorVals') and len(entry['armorVals']) > 2
                    else None
                ),
            })

        return results

    @staticmethod
    def _extract_battlepass(battlepass_list):
        """
        Разбирает battlePass -> краткая сводка прогресса.
        """
        results = []
        if not battlepass_list or not isinstance(battlepass_list, list):
            return results

        for bp in battlepass_list:
            if not isinstance(bp, dict):
                continue
            quest_info = bp.get('questInfo', {})
            progress_list = bp.get('progressList', [])
            results.append({
                'description': quest_info.get('description', ''),
                'status': bp.get('questState', {}).get('statusState', ''),
                'progress': [
                    {
                        'description': p.get('description', ''),
                        'current': p.get('currentProgrVal', 0),
                        'max': p.get('maxProgrVal', 0),
                        'diff': p.get('progressDiff', ''),
                    }
                    for p in progress_list if isinstance(p, dict)
                ],
            })

        return results

    # ---------------------------------------------------------------
    #  ДОСТУП
    # ---------------------------------------------------------------

    @staticmethod
    def get_stats():
        return SSStatisticCollector._stats

    @staticmethod
    def get(key, default=None):
        if SSStatisticCollector._stats is None:
            return default
        return SSStatisticCollector._stats.get(key, default)

    @staticmethod
    def reset():
        SSStatisticCollector._stats = None
