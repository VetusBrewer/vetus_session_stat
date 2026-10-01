# -*- coding: utf-8 -*-
"""
ss_eff.py
=========
Расчёт РЭ (Рейтинг Эффективности, wot-news) для одного боя.

Формула:
    Dmg * (10 / (Tier + 2)) * (0.23 + 2*Tier / 100)
    + Frags * 250
    + Spot * 150
    + log(Cap + 1, 1.732) * 150
    + Def * 150

Использование:
    from ss_eff import SSEFF
    result = SSEFF.calculate(stats)
    if result:
        eff = result['eff']
"""

import math

try:
    from ss_debuglog import vLog
except ImportError:
    vLog = None


class SSEFF(object):

    @staticmethod
    def calculate(stats):
        """
        Рассчитывает РЭ для одного боя.

        stats — словарь из SSStatisticCollector.get_stats().
        Возвращает словарь:
            eff     — итоговое значение (float)
            dmg, frags, spot, cap, def, tier — исходные значения
        или None, если данных недостаточно.
        """
        combat = stats.get('combat', {})
        vehicle = stats.get('vehicle', {})

        damage = combat.get('damageDealt') or 0
        kills = combat.get('kills') or 0
        spotted = combat.get('spotted') or 0
        cap = combat.get('baseCapture') or 0
        defense = combat.get('baseDefense') or 0
        tier = vehicle.get('tankLevel')

        if tier is None or tier < 1:
            if vLog:
                vLog("EFF: не определён уровень танка", "VSS_EFF")
            return None

        tier = float(tier)

        # Формула wot-news
        dmg_part = damage * (10.0 / (tier + 2.0)) * (0.23 + 2.0 * tier / 100.0)
        frag_part = kills * 250.0
        spot_part = spotted * 150.0
        cap_part = math.log(cap + 1.0, 1.732) * 150.0
        def_part = defense * 150.0

        eff = dmg_part + frag_part + spot_part + cap_part + def_part

        if vLog:
            vLog("EFF: tier=%.0f dmg=%d frags=%d spot=%d cap=%d def=%d -> eff=%.0f" % (
                tier, damage, kills, spotted, cap, defense, eff,
            ), "VSS_EFF")

        return {
            'eff': eff,
            'dmg': damage,
            'frags': kills,
            'spot': spotted,
            'cap': cap,
            'def': defense,
            'tier': tier,
        }
