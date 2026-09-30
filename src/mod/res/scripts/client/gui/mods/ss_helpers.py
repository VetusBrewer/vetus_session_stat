import os
import shutil

MOD_ROOT = os.path.join(os.getcwd(), 'mods', 'configs', 'vetus_session_stats')


def path_config():
    return os.path.join(MOD_ROOT, 'config.json')


def dir_img():
    return os.path.join(MOD_ROOT, 'img')


def _detect_game_version():
    """
    Автоопределение версии клиента по поддиректории в res_mods/.
    Ищет папку вида x.y.z.w (например 1.45.0.0).
    """
    res_mods = os.path.join(os.getcwd(), 'res_mods')
    if not os.path.isdir(res_mods):
        return None
    for name in os.listdir(res_mods):
        parts = name.split('.')
        if len(parts) == 4:
            try:
                int(parts[0])
                int(parts[1])
                int(parts[2])
                int(parts[3])
                return name
            except ValueError:
                continue
    return None


def img_url(filename):
    """
    Возвращает img:// URL для Scaleform.
    Копирует картинку из mods/configs/ в res_mods/<version>/gui/...
    (т.к. mods/configs/ не входит в виртуальную файловую систему игры).
    """
    src_path = os.path.join(dir_img(), filename)
    version = _detect_game_version()

    if version is None:
        # Fallback: возвращаем как есть (не будет работать, но хоть не крашит)
        rel = os.path.join('mods', 'configs', 'vetus_session_stats', 'img', filename)
        return 'img://' + rel.replace('\\', '/')

    # VFS-доступный путь: res_mods/<version>/gui/maps/icons/vetus_session_stats/
    vfs_subdir = os.path.join('gui', 'maps', 'icons', 'vetus_session_stats')
    vfs_dir = os.path.join(os.getcwd(), 'res_mods', version, vfs_subdir)

    # Копируем картинку (каждый раз — на случай замены)
    try:
        if not os.path.isdir(vfs_dir):
            os.makedirs(vfs_dir)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, os.path.join(vfs_dir, filename))
        else:
            pass  # файла нет — вернём путь всё равно, Scaleform покажет пустоту
    except Exception:
        pass  # не крашим бой из-за копирования

    # img:// ссылается на путь внутри VFS (от корня, без res_mods/<version>/)
    vfs_rel = os.path.join(vfs_subdir, filename).replace('\\', '/')
    return 'img://' + vfs_rel
