# Технический отчёт по созданию мода сессионной статистики для «Мир Танков» (Lesta Games)

## Резюме

Для создания мода сессионной статистики под клиент «Мир Танков» от Lesta Games существуют два подтверждённых open-source ориентира: **WotStat-analytics** (репозиторий `wotstat/wotstat-analytics`) — современный мод, работающий и с «Миром Танков», и с World of Tanks, и **WotStat** от macrosoft — более старый, но детально документированный мод, содержащий все ключевые паттерны: хуки `NotificationListView._populate` для Центра уведомлений, хуки `Account.onBecomePlayer/onBecomeNonPlayer` для отслеживания сессии, расчёт WN8 через expected-значения и JSON-конфиг с поддержкой перечитывания при открытии Центра уведомлений [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics).

**Важные ограничения:**

1. Точная внутренняя структура классов клиента Lesta после разделения с Wargaming официально не документирована; ориентироваться нужно на декомпилированный исходный код (`github.com/izeberg/wot-src`, ветка `origin/RU`) — он актуален для клиента Lesta [![docs.wotstat.info](https://favicon.yandex.net/favicon/v2/docs.wotstat.info/?size=32&stub=1)docs.wotstat.info](https://docs.wotstat.info/guide/first-steps/environment/python/).
2. Модификация окна послебоевых результатов в клиенте Lesta надёжнее всего выполняется через перехват метода `BattleResultsWindow.as_setDataS` с использованием XVM Framework (XFW) — этот приём подтверждён для WG-клиента и, с высокой вероятностью, работает и в Lesta, но требует адаптации [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN)[![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/).
3. Формат `meta.xml` и структура пакета мода для Lesta совпадают с WG, но клиент Lesta использует собственные расширения пакетов (`.mtmod`); моды от WG напрямую не переносятся [![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics/8-development-and-deployment)[![www.offstage.ru](https://favicon.yandex.net/favicon/v2/www.offstage.ru/?size=32&stub=1)www.offstage.ru](https://www.offstage.ru/industry/articles/mody-dlya-mir-tankov-ot-lesty-luchshie-modpaki-i-kak-ih-ustanovit).

---

## 1. Архитектура мода и точка входа

### 1.1. Загрузка модов в клиенте Lesta

Клиент автоматически запускает Python-скрипты с префиксом `mod_` из папки `res/scripts/client/gui/mods/`. Это подтверждено документацией по настройке окружения для модов «Мир Танков» [![docs.wotstat.info](https://favicon.yandex.net/favicon/v2/docs.wotstat.info/?size=32&stub=1)docs.wotstat.info](https://docs.wotstat.info/guide/first-steps/environment/python/).

Рекомендуемая структура проекта:

text

ПереноситьСвернутьКопировать

```text
res/scripts/client/gui/mods/
├── mod_session_stat.py          # точка входа, загружается клиентом автоматически
└── session_stat/                # пакет с кодом мода
    ├── __init__.py
    ├── config.py
    ├── stat.py
    └── ...
```

Такую же структуру используют оба WotStat [![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics/8-development-and-deployment)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics):

- `WOTSTAT/res/scripts/client/gui/mods/wot_stat/load_mod.py` — главный файл инициализации; функция `init_mod()` координирует запуск [![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics)[![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics/7-mod-management-system).
- Точка входа — файл с префиксом `mod_`, который при импорте вызывает инициализацию мода.

В `wotstat-analytics` все события и логика вынесены в пакет `wot_stat/`, а главный файл `load_mod.py` выполняет роль оркестратора: инициализация, загрузка конфига, регистрация обработчиков событий [![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics)[![deepwiki.com](https://favicon.yandex.net/favicon/v2/deepwiki.com/?size=32&stub=1)deepwiki.com](https://deepwiki.com/wotstat/wotstat-analytics/7-mod-management-system).

### 1.2. Перехват входа в бой и выхода из боя

Подтверждённые события/хуки из реальных модов:

| Событие                     | Описание                                                                        | Источник                                                                                                                                                                                                                                                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Account.onBecomePlayer`    | Срабатывает при входе игрока в аккаунт/в ангар — используется как начало сессии | [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py)                                                                                                                                                                                                  |
| `Account.onBecomeNonPlayer` | Срабатывает при выходе игрока — конец сессии                                    | [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py)                                                                                                                                                                                                  |
| `Events.OnBattleStart`      | Начало боя — создаётся новый `BattleEventSession`                               | [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics/blob/main/WOTSTAT/res/scripts/client/gui/mods/wot_stat/logger/events.py) |
| `Events.OnBattleResult`     | Результат боя — завершается `BattleEventSession`                                | [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics/blob/main/WOTSTAT/res/scripts/client/gui/mods/wot_stat/logger/events.py) |

В `wotstat-analytics` каждый новый `BattleEventSession` создаётся на событие `Events.OnEndLoad()` и завершается на `Events.OnBattleResult()` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics).

Идентификатор арены во время боя доступен через `BigWorld.player()` → `.arena` (объект `PlayerAvatar`) и `.arenaUniqueID` [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/ZbFXWJgs). Для определения сессии в старом WotStat используется сравнение `self.startDate != stat.getWorkDate()` — сброс при наступлении нового дня [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).

### 1.3. Определение сессии

- **Новая сессия после запуска клиента:** хуки `onBecomePlayer` / `onBecomeNonPlayer` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- **Сброс через N часов/суток:** реализовано в WotStat через поля конфига `dailyAutoReset`, `dailyAutoResetHour` и функцию `getWorkDate()`, которая возвращает текущую дату как `YYYY-MM-DD`, сдвинутую на час сброса [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- **Ручной сброс:** через клик по сообщению в Центре уведомлений (`onClickAction` с action `'wotstatReset'`) [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).

---

## 2. Сбор экономических данных

### 2.1. Данные аккаунта в ангаре

В `wotstat-analytics` событие `OnAccountStats` содержит поля [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics/blob/main/WOTSTAT/res/scripts/client/gui/mods/wot_stat/logger/events.py):

python

ПереноситьСвернутьКопировать

```python
class OnAccountStats:
    def __init__(self, credits, gold, crystal, equipCoin, bpCoin, eventCoin, freeXP,                 piggyBankCredits, piggyBankGold, premiumPlusExpiryTime,                 isPremiumPlus, isWotPlus, wotPlusTier, wotPlusExpiryTime, telecom):
        ...
```

То есть `credits` (серебро), `gold` (золото) и другие валюты доступны как именованные поля события [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics/blob/main/WOTSTAT/res/scripts/client/gui/mods/wot_stat/logger/events.py). Это данные **на момент входа в ангар**, а не за отдельный бой.

### 2.2. Данные после боя

В старом WotStat `battleResultsCallback` получает `value` — словарь с полями послебоевых результатов [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

python

ПереноситьСвернутьКопировать

```python
def battleResultsCallback(self, arenaUniqueID, responseCode, value=None, revision=0):
    ...
    arenaTypeID = value['common']['arenaTypeID']
    credits = value['common']['credits']  # заработок серебра
    ...
```

Из XVM-кода (`pastebin.com/ZbFXWJgs`) подтверждается структура `value['vehicles'][vehId][0]` с полем `typeCompDescr` — это компактный идентификатор танка. Также есть `value['players'][accountDBID]['name']`, `clanAbbrev` и др. [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/ZbFXWJgs).

**Важно:** точный набор полей послебоевых результатов в клиенте Lesta может отличаться от WG. Рекомендуется сверить структуру `value` по декомпилированному коду `wot-src` (ветка `origin/RU`), а не полагаться на документацию WG [![docs.wotstat.info](https://favicon.yandex.net/favicon/v2/docs.wotstat.info/?size=32&stub=1)docs.wotstat.info](https://docs.wotstat.info/guide/first-steps/environment/python/).

### 2.3. Данные о танке

- Идентификатор танка: `typeCompDescr` из данных боя [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/ZbFXWJgs).
- Уровень и класс: через `items.vehicles.getVehicleType(newIdNum)` — этот способ использован в WotStat [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py); класс определяется как пересечение тегов танка с `VEHICLE_CLASS_TAGS` [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/ZbFXWJgs).
- Название: `tank.name` из данных о танке (в коде XVM используется `vData['vehicleType'].type.name.replace(':', '-')`).

---

## 3. Расчёт WN8

### 3.1. Формула WN8

Подтверждённая формула (источник — калькулятор wn8calc и описание на форуме мододелов) [![4cheat.org](https://favicon.yandex.net/favicon/v2/4cheat.org/?size=32&stub=1)4cheat.org](https://4cheat.org/threads/%D0%A0%D0%B5%D0%B9%D1%82%D0%B8%D0%BD%D0%B3-wn8-%D0%A4%D0%BE%D1%80%D0%BC%D1%83%D0%BB%D0%B0.99143/)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/berenzorn/wn8calc/blob/master/wot.py):

WN8=980⋅rDAMAGEc​+210⋅rDAMAGEc​⋅rFRAGc​+155⋅rFRAGc​⋅rSPOTc​+75⋅rDEFc​⋅rFRAGc​+145⋅min(1.8,rWINc​)

Нормализованные значения:

- rWINc​=max(0,1−0.71rWIN​−0.71​)
- rDAMAGEc​=max(0,1−0.22rDAMAGE​−0.22​)
- rFRAGc​=max(0,min(rDAMAGEc​+0.2,1−0.12rFRAG​−0.12​))
- rSPOTc​=max(0,1−0.28rSPOT​−0.28​)
- rDEFc​=max(0,1−0.38rDEF​−0.38​)

Значения rX​ — взвешенные соотношения: сумма фактических показателей за сессию, делённая на сумму ожидаемых (expected) показателей для сыгранных танков [![4cheat.org](https://favicon.yandex.net/favicon/v2/4cheat.org/?size=32&stub=1)4cheat.org](https://4cheat.org/threads/%D0%A0%D0%B5%D0%B9%D1%82%D0%B8%D0%BD%D0%B3-wn8-%D0%A4%D0%BE%D1%80%D0%BC%D1%83%D0%BB%D0%B0.99143/)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/berenzorn/wn8calc/blob/master/wot.py).

### 3.2. Ожидаемые значения (expected values)

- Актуальные таблицы expected-значений публикуются на ресурсах WN8; для России/СНГ после разделения клиентов таблицы пересчитываются отдельно для Lesta и для WG. **На момент исследования не удалось надёжно подтвердить, что таблица WN8 для клиента Lesta совпадает с таблицей WG.** В старом WotStat таблица поставляется в файле `expected_tank_values.json` рядом с модом [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- Формат ожидаемых значений в WotStat [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

json

ПереноситьСвернутьКопировать

```json
{"IDNum": 123, "expDamage": 800.0, "expFrag": 1.2, "expSpot": 1.0, "expDef": 0.5, "expWinRate": 0.48}
```

### 3.3. Готовая реализация на Python 2.7

В **WotStat** есть метод `calcWN8(self, battles)`, который агрегирует фактические и ожидаемые показатели по всем боям сессии и возвращает WN8 [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py). В **wn8calc** есть полный расчёт по аккаунту с загрузкой данных из БД, но он не является модом — только справочная реализация [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/berenzorn/wn8calc/blob/master/wot.py).

Рекомендуется: перенести метод `calcWN8` из WotStat [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py), заменив источник expected-таблицы на актуальный для клиента Lesta.

---

## 4. Работа с Центром Уведомлений (канал info)

### 4.1. Добавление сообщения

В WotStat перехватывается метод `NotificationListView._populate` (класс Центра уведомлений) [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

python

ПереноситьСвернутьКопировать

```python
old_nlv_populate = NotificationListView._populate

def new_nlv_populate(self):
    if stat.config.get('onlineReloadConfig', False):
        stat.readConfig()
        stat.updateMessage()
    old_nlv_populate(self)
    self.as_appendMessageS(stat.createMessage())

NotificationListView._populate = new_nlv_populate
```

- `as_appendMessageS(...)` — ADF-метод (ActionScript Data Flash) для добавления сообщения в список уведомлений [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- Сообщение создаётся через `stat.createMessage()`, оформление — через шаблоны макросов [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- Для обновления уже существующего сообщения (вместо создания нового при каждом бое) используется метод `as_setMessagesListS` с полным списком сообщений [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).

### 4.2. Позиция сообщения (первое место в канале)

В WotStat реализована фильтрация и модификация списка уведомлений через перехват `NotificationListView._populate` и методы `filterNotificationList` / `expandStatNotificationList` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

python

ПереноситьСвернутьКопировать

```python
def new_nlv_setNotificationList(self):
    formedList = map(lambda item: item.getListVO(),
                     self._model.collection.getListIterator())
    if len(stat.config.get('hideMessagePatterns', [])):
        formedList = filter(stat.filterNotificationList, formedList)
    if stat.config.get('showStatForBattle', True):
        formedList = map(stat.expandStatNotificationList, formedList)
    self.as_setMessagesListS(formedList)
```

Точный механизм закрепления на первом месте в исходном коде не раскрыт, но `as_setMessagesListS` позволяет переписать весь список уведомлений, что даёт возможность вставить своё сообщение в начало.

### 4.3. HTML-форматирование

Центр уведомлений поддерживает HTML-теги. В WotStat форматирование реализовано в `formatString(self, text, values, gradient, palette)` — подстановка значений по ключам `{key}` с цветами градиента и палитры [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py). Используются цвета вида `#RRGGBB` (например, `#FFFFFF`). Полный список поддерживаемых тегов в исходниках не зафиксирован; к сожалению, точный перечень тегов на момент исследования не удалось подтвердить.

### 4.4. Обработка действий (кнопка сброса)

`NotificationListView.onClickAction` перехватывается для обработки пользовательских действий [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

python

ПереноситьСвернутьКопировать

```python
def new_onClickAction(self, typeID, entityID, action):
    if action == 'wotstatReset':
        stat.reset()
    elif action == 'wotstatSwitchPage':
        stat.page = 1 - stat.page
    else:
        old_nlv_onClickAction(self, typeID, entityID, action)
```

---

## 5. Модификация интерфейса клиента

### 5.1. Окно послебоевых результатов

Окно результатов боя в клиенте представлено классом `gui.Scaleform.daapi.view.battle_results_window.BattleResultsWindow` [![koreanrandom.com](https://favicon.yandex.net/favicon/v2/koreanrandom.com/?size=32&stub=1)koreanrandom.com](https://koreanrandom.com/forum/topic/35299-%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80-%D1%8D%D1%84%D1%84%D0%B5%D0%BA%D1%82%D0%B8%D0%B2%D0%BD%D0%BE%D1%81%D1%82%D0%B8-%D1%81%D1%80%D0%B5%D0%B4%D1%81%D1%82%D0%B2%D0%B0%D0%BC%D0%B8-xvm/page/19/)[![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN). Класс определён в клиенте (WG — подтверждено; для Lesta следует проверить в `wot-src`).

**Подход через XVM Framework (XFW):** использование `@overrideMethod` для перехвата `as_setDataS` перед отрисовкой [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN):

python

ПереноситьСвернутьКопировать

```python
from gui.Scaleform.daapi.view.battle_results_window import BattleResultsWindow

@overrideMethod(BattleResultsWindow, 'as_setDataS')
def as_setDataS(base, self, data):
    # модификация data — добавление своих полей (WN8, урон, ...)
    return base(self, data)
```

Это подтверждённый способ для WG-клиента [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN)[![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/). Для Lesta-клиента метод `BattleResultsWindow.as_setDataS` с высокой вероятностью работает так же, но требует проверки по декомпилированному коду `wot-src` (ветка `origin/RU`).

Без XFW можно использовать прямой монки-патчинг (как в WotStat для `NotificationListView`), но для окна результатов это сложнее — исторически окно результатов переделывалось в патче 1.4.1 (WG-клиент), что сломало ряд аддонов [![koreanrandom.com](https://favicon.yandex.net/favicon/v2/koreanrandom.com/?size=32&stub=1)koreanrandom.com](https://koreanrandom.com/forum/topic/35299-%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80-%D1%8D%D1%84%D1%84%D0%B5%D0%BA%D1%82%D0%B8%D0%B2%D0%BD%D0%BE%D1%81%D1%82%D0%B8-%D1%81%D1%80%D0%B5%D0%B4%D1%81%D1%82%D0%B2%D0%B0%D0%BC%D0%B8-xvm/page/19/).

### 5.2. Карточка боя в канале info

Карточка боя в канале `info` формируется после боя. Старый WotStat перехватывает метод `BattleResultsFormatter._format`:

python

ПереноситьСвернутьКопировать

```python
old_brf_format = BattleResultsFormatter.format

def new_brf_format(self, message, *args):
    result = old_brf_format(self, message, *args)
    arenaUniqueID = message.data.get('arenaUniqueID', 0)
    stat.queue.put(arenaUniqueID)
    ...
    return result
```

Это перехватывает создание карточки после боя, позволяя модифицировать её содержимое [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py). Для Lesta-клиента имена классов следует сверить с `wot-src`.

### 5.3. SWF/Flash-интерфейс

- **Через Python** можно модифицировать данные, передаваемые во Flash-интерфейс (хуки `as_setDataS`, `as_appendMessageS`, `as_setMessagesListS`), но **нельзя добавить новые визуальные элементы** (текстовые поля, кнопки) без правки SWF.
- **Для добавления новых элементов** требуется редактирование SWF-файла (например, `battle_results.swf` или `lobby.swf`) через JPEXS Free Flash Decompiler с последующей публикацией ADF-методов [![koreanrandom.com](https://favicon.yandex.net/favicon/v2/koreanrandom.com/?size=32&stub=1)koreanrandom.com](https://koreanrandom.com/forum/topic/35299-%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80-%D1%8D%D1%84%D1%84%D0%B5%D0%BA%D1%82%D0%B8%D0%B2%D0%BD%D0%BE%D1%81%D1%82%D0%B8-%D1%81%D1%80%D0%B5%D0%B4%D1%81%D1%82%D0%B2%D0%B0%D0%BC%D0%B8-xvm/page/19/)[![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/).
- XVM Framework включает модифицированный `lobby.swf` и предоставляет инструменты для работы со SWF-частью модов [![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/).

---

## 6. Конфигурация и отладка

### 6.1. Формат конфига

В WotStat конфиг — JSON-файл `wotstat/config.json`. Загрузка: сканирование путей из `../paths.xml` через `ResMgr.openSection`, поиск `scripts/client/mods/` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).

Подтверждённые поля конфига [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

| Поле                 | Тип  | Назначение                                                           |
| -------------------- | ---- | -------------------------------------------------------------------- |
| `dailyAutoReset`     | bool | Автосброс при наступлении нового дня                                 |
| `dailyAutoResetHour` | int  | Час, с которого наступает новый день для сброса                      |
| `clientReloadReset`  | bool | Сброс при перезапуске клиента                                        |
| `onlineReloadConfig` | bool | Перечитывание конфига при открытии Центра уведомлений                |
| `battleStatPatterns` | list | Паттерны для форматирования сообщений (поля `if`, `pattern`, `repl`) |
| `gradient`           | dict | Цвета для градиентной подсветки значений                             |
| `showStatForBattle`  | bool | Показывать статистику в карточке боя                                 |
| `ignoreBattleType`   | list | Типы боёв, которые не учитываются                                    |

Пример структуры:

json

ПереноситьСвернутьКопировать

```json
{
    "dailyAutoReset": true,
    "dailyAutoResetHour": 4,
    "onlineReloadConfig": true,
    "battleStatPatterns": [],
    "gradient": {"wn8": ["#FF0000", "#00FF00"]},
    "showStatForBattle": true,
    "ignoreBattleType": []
}
```

### 6.2. Перечитывание конфига при открытии Центра уведомлений

В `new_nlv_populate` (хук `NotificationListView._populate`) проверяется `stat.config.get('onlineReloadConfig', False)` и вызывается `stat.readConfig()` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py). После перечитывания обновляется сообщение через `stat.updateMessage()`.

### 6.3. Кэш и хранение сессии

WotStat сохраняет сессию в `wotstat/cache.json` через `json.dumps(...)`. Формат [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py):

json

ПереноситьСвернутьКопировать

```json
{
    "version": 1,
    "date": "2026-09-28",
    "players": {"simpleName": {"battles": [...]}}
}
```

Поля боёв включают урон, засвет, фраги, очки защиты, победу и WN8.

---

## 7. Поиск аналогичных модов

### 7.1. Моды, работающие с клиентом Lesta

**WotStat-analytics** (`github.com/wotstat/wotstat-analytics`):

- Собирает сессионную статистику во время игры: начало боя, выстрелы, попадания, результаты боя [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics).
- Работает и с «Миром Танков», и с World of Tanks (явно указано в README) [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics)[![ru.wotstat.info](https://favicon.yandex.net/favicon/v2/ru.wotstat.info/?size=32&stub=1)ru.wotstat.info](https://ru.wotstat.info/).
- Отправляет собранные события на сервер `wotstat.info` для анализа; локальная обработка — только сбор и отправка [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics)[![ru.wotstat.info](https://favicon.yandex.net/favicon/v2/ru.wotstat.info/?size=32&stub=1)ru.wotstat.info](https://ru.wotstat.info/).
- Сборка: `./build.sh -v 1.0.0.0-a.1 -d` в папке `WOTSTAT` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/wotstat/wotstat-analytics).

**WotStat** (`github.com/macrosoft/wotstat`) — устаревший, последний порт 2016 года, но содержит референсные реализации:

- Расчёт WN8/WN6/EFF [![macrosoft.github.io](https://favicon.yandex.net/favicon/v2/macrosoft.github.io/?size=32&stub=1)macrosoft.github.io](https://macrosoft.github.io/wotstat/).
- Вывод статистики в Центр уведомлений [![macrosoft.github.io](https://favicon.yandex.net/favicon/v2/macrosoft.github.io/?size=32&stub=1)macrosoft.github.io](https://macrosoft.github.io/wotstat/).
- Конфиг с автосбросом [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat)[![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/README.md).

### 7.2. Модификации интерфейса

**XVM Framework (XFW)** (`gitlab.com/xvm/xvm`, документация `xfw.readthedocs.io`):

- Предоставляет `overrideMethod`, `registerEvent` для хуков [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN)[![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/).
- Работает и с WG, и с Lesta-клиентом (XVM официально поддерживает оба [![forblitz.ru](https://favicon.yandex.net/favicon/v2/forblitz.ru/?size=32&stub=1)forblitz.ru](https://forblitz.ru/modifications/other/olenemer-xvm-extended-visualization-mod/23398)[![www.offstage.ru](https://favicon.yandex.net/favicon/v2/www.offstage.ru/?size=32&stub=1)www.offstage.ru](https://www.offstage.ru/industry/articles/mody-dlya-mir-tankov-ot-lesty-luchshie-modpaki-i-kak-ih-ustanovit)), но для Lesta требуются отдельные сборки.

### 7.3. Отсутствующие моды под конкретные требования

Мода, который **одновременно** выводил бы статистику и в Центр уведомлений, и в окно послебоевых результатов, и в карточку боя, — в найденных источниках нет. Подтверждены отдельные компоненты:

- Центр уведомлений и карточка боя — WotStat [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
- Окно результатов — XVM-аддоны (пример — `battleEfficiency.py`) [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN).

---

## 8. Рекомендации по реализации

1. **Использовать WotStat как основу** для архитектуры: его подход к хукам `NotificationListView`, конфигу и расчёту WN8 проверен и подтверждён исходным кодом [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
2. **Для окна результатов** использовать XVM Framework (XFW) и перехват `BattleResultsWindow.as_setDataS` — это сократит объём работы и избавит от необходимости править SWF [![pastebin.com](https://favicon.yandex.net/favicon/v2/pastebin.com/?size=32&stub=1)pastebin.com](https://pastebin.com/EqewizVN)[![xfw.readthedocs.io](https://favicon.yandex.net/favicon/v2/xfw.readthedocs.io/?size=32&stub=1)xfw.readthedocs.io](https://xfw.readthedocs.io/ru/latest/2.getting_started/).
3. **Сверить классы и методы с декомпилированным кодом Lesta** из `github.com/izeberg/wot-src` (ветка `origin/RU`), так как после разделения клиентов возможны отличия от WG [![docs.wotstat.info](https://favicon.yandex.net/favicon/v2/docs.wotstat.info/?size=32&stub=1)docs.wotstat.info](https://docs.wotstat.info/guide/first-steps/environment/python/).
4. **Expected-значения WN8** брать из актуальной таблицы, поддерживаемой для клиента Lesta; в старом WotStat таблица поставляется файлом `expected_tank_values.json` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
5. **Перечитывание конфига в отладочном режиме** — через `onlineReloadConfig` + хук `NotificationListView._populate` [![github.com](https://favicon.yandex.net/favicon/v2/github.com/?size=32&stub=1)github.com](https://github.com/macrosoft/wotstat/blob/master/src/stat.py).
