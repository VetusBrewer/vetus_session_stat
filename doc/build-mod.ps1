# --- НАСТРОЙКИ (ИЗМЕНИТЕ ЭТИ ПУТИ) ---
# 1. Откуда брать исходники
$SourceDir = "K:\dev\WoT\vetus_stat\src\mod"

# 2. Куда копировать для сборки (рабочая папка)
$BuildDir = "K:\dev\WoT\vetus_stat\Build\Temp"

# 3. Путь к интерпретатору Python 2.7.16
$PythonExe = "C:\Python27\python.exe"

# 4. Куда положить готовый архив
$DestinationDir = "D:\games\Tanki\mods\1.45.0.0"

# 5. Имя архива (можно добавить дату)
$ArchiveName = "vetus.test_subfolder.0.0.0.1.mtmod"
# -------------------------------------

# --- НАСТРОЙКИ ---
$SevenZipExe = "C:\Program Files\7-Zip\7z.exe" # Стандартный путь установки
# ------------------

# --- БЛОК ВЫПОЛНЕНИЯ ---

# Формируем полные пути
$TargetWorkDir = Join-Path $BuildDir "package_content"
$ArchivePath = Join-Path $DestinationDir $ArchiveName

Write-Host "=== Сборка пакета начата ==="

try {
    # 1. Очищаем старую рабочую папку, если она есть
    if (Test-Path $TargetWorkDir) {
        Remove-Item -Recurse -Force $TargetWorkDir
    }
    
    # 2. Создаем чистую рабочую папку
    New-Item -ItemType Directory -Path $TargetWorkDir | Out-Null

    # 3. Копируем ТОЛЬКО содержимое папки 'mod' в корень рабочей папки
    Write-Host "Копирование исходных файлов..."
    
    # Копируем всё, что внутри $SourceDir, в $TargetWorkDir
    # Так как $SourceDir заканчивается на \mod, внутрь $TargetWorkDir попадет папка 'res'
    Copy-Item -Path (Join-Path $SourceDir "*") -Destination $TargetWorkDir -Recurse -Container -Force

    # 4. Запускаем компилятор Python 2.7
    Write-Host "Компиляция файлов..."
    
    # Ищем файлы .py внутри рабочей папки (где теперь лежит 'res')
    $FilesToCompile = Get-ChildItem -Path $TargetWorkDir -Filter "*.py" -Recurse | Select-Object -ExpandProperty FullName
    
    if ($FilesToCompile) {
        $compileArgs = @("-m", "py_compile") + $FilesToCompile
        $process = Start-Process -FilePath $PythonExe -ArgumentList $compileArgs -Wait -NoNewWindow -PassThru
        
        if ($process.ExitCode -ne 0) {
            throw "Ошибка компиляции Python. Код выхода: $($process.ExitCode)"
        }
    } else {
        Write-Host "Файлы .py для компиляции не найдены."
    }

    # 5. Удаляем исходные .py файлы
    Write-Host "Удаление исходных .py файлов..."
    Get-ChildItem -Path $TargetWorkDir -Filter "*.py" -Recurse | Remove-Item -Force

    # 6. Проверяем, есть ли что архивировать
    $filesToArchive = Get-ChildItem -Path $TargetWorkDir -File
    if ($filesToArchive.Count -eq 0) {
        # Проверяем наличие папок (если вдруг получились только пустые директории)
        $dirsToArchive = Get-ChildItem -Path $TargetWorkDir -Directory
        if ($dirsToArchive.Count -eq 0) {
            throw "Папка для сборки пуста. Архивировать нечего."
        }
    }

    # 7. Создаем архив (7-Zip)
    Write-Host "Создание архива..."
    
    if (-not (Test-Path $SevenZipExe)) {
      throw "Ошибка: не найден 7z.exe по пути $SevenZipExe"
    }
    
    if (-not (Test-Path $DestinationDir)) {
        New-Item -ItemType Directory -Path $DestinationDir | Out-Null
    }
    
    # Упаковываем содержимое рабочей папки. 
    # Так как там лежит 'res', в архиве будет res\scripts\...
    $arguments = @("a", "-tzip", "-mx0", "`"$ArchivePath`"", "`"$TargetWorkDir\*`"")

    $process = Start-Process -FilePath $SevenZipExe -ArgumentList $arguments -Wait -NoNewWindow -PassThru
    
    if ($process.ExitCode -ne 0) {
      throw "7-Zip вернул ошибку. Код выхода: $($process.ExitCode)"
    }

    Write-Host "=== Сборка успешно завершена ==="
    Write-Host "Готовый файл: $ArchivePath"

} catch {
    Write-Host "!!! ПРОИЗОШЛА ОШИБКА !!!"
    Write-Host $_.Exception.Message
} finally {
    # 8. Гарантированная очистка
    if (Test-Path $TargetWorkDir) {
        Remove-Item -Recurse -Force $TargetWorkDir
    }
}

Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")