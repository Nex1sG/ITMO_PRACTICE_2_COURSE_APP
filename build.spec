# -*- mode: python ; coding: utf-8 -*-

# Анализ зависимостей и файлов
a = Analysis(
    ['main.py'],                  # Точка входа
    pathex=[],                    # Дополнительные пути для поиска модулей (если нужно)
    binaries=[],                  # Внешние .dll/.so файлы (обычно пусто)
    datas=[
        # Упаковываем папку с иконками и картинками внутрь exe
        # Путь в проекте -> Путь внутри собранной папки
        ('gui/assets', 'gui/assets'), 
        
        # config.json будет лежать рядом с .exe
    ],
    hiddenimports=[
        'pioneer_sdk2',           # PyInstaller может не увидеть эту библиотеку
        'pioneer_sdk2.cmd',       # Часто внутренние модули SDK нужно добавлять вручную
        'PySide6',                # Если используете PySide6
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Блок 2: Создание архива с Python-кодом
pyz = PYZ(a.pure, a.zipped_data)

# Блок 3: Создание самого .exe файла
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # не пакуем binaries внутрь exe
    name='PioneerInfoManager',      # Имя вашего exe-шника
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                     # Сжатие файлов
    console=False,                # False убирает черное окно консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/assets/app_icon.ico' # Иконка для самого exeшника
)

# Сборка папки (считайте исполнение флага --onedir)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PioneerTelemetry',      # Имя итоговой папки в dist/
)