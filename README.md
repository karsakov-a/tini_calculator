=== Отладка ====
Отладка выпонеяется через пакет watchdog. Для запуска выполнить
```
watchmedo auto-restart --directory=. --pattern="*.py" --recursive -- venv/Scripts/python main.py
```
Будет запущена демо версия программы с текущим состоянием кода. Установлено, что при включенном режиме дебага программа запускается на экране со смещением (550, 100)


=== Сборка ====
Для сборки проекта TINI Calculator в один исполняемый файл TINI Calculator.exe на Windows с использованием PyInstaller и PySide6, выполните следующую команду в корне проекта:
```
pyinstaller --onefile --windowed --name "TINI Calculator" --clean main.py
```
`--onefile` Упаковать всё в один .exe-файл
`--windowed` Скрыть консольное окно (важно для GUI-приложений)
`--name "TINI Calculator"` Имя выходного исполняемого файла
`--clean` Очистить кэш перед сборкой (рекомендуется для стабильности)