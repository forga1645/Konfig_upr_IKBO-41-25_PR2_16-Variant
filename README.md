# Dependency Visualizer

Минимальный CLI-прототип для практической работы №2, **вариант 16,
этап 1** (дисциплина «Конфигурационное управление»).

## Что реализовано

Параметры читаются из TOML-файла. При запуске приложение проверяет
конфигурацию и печатает все параметры в формате `ключ = значение`.

- `package_name` — имя анализируемого NuGet-пакета.
- `repository` — URL репозитория NuGet либо путь к файлу тестового репозитория.
- `test_mode` — `true` для тестового файла, `false` для URL.
- `package_version` — версия пакета.
- `output_file` — имя будущего SVG-файла (на этапе 1 файл ещё не создаётся).
- `ascii_tree` — включение режима ASCII-дерева (само дерево реализуется
  на последующих этапах).

Этап 1 не получает зависимости из NuGet и не строит граф. Это соответствует
разделению требований по этапам в задании.

## Требования

- Windows 10/11
- Python 3.11 или новее (для встроенного модуля `tomllib`)
- Git (для отправки проекта на GitHub)

Внешние Python-библиотеки не нужны.

## Структура проекта

```text
dependency_visualizer/
├── src/
│   └── dependency_visualizer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       └── config.py
├── tests/
│   └── test_config.py
├── config.toml
├── README.md
├── .gitignore
└── run.bat
```

- `src/dependency_visualizer/config.py` — модель параметров и чтение/валидация TOML.
- `src/dependency_visualizer/cli.py` — аргументы запуска и вывод параметров.
- `src/dependency_visualizer/__main__.py` — запуск через `python -m`.
- `tests/` — автоматические тесты проверки конфигурации.
- `config.toml` — пользовательские настройки.
- `run.bat` — запуск на Windows.

## Настройка и запуск

1. Установите Python 3.11+ и отметьте опцию **Add Python to PATH**.
2. Откройте папку проекта в проводнике.
3. Отредактируйте `config.toml`.
4. Запустите `run.bat` двойным щелчком либо из терминала:

```bat
run.bat
```

Можно указать другой конфигурационный файл:

```bat
.venv\Scripts\python.exe -m dependency_visualizer --config my-config.toml
```

Без виртуального окружения:

```bat
python -m dependency_visualizer --config config.toml
```

## Пример вывода

```text
Параметры приложения:
package_name = Newtonsoft.Json
repository = https://api.nuget.org/v3/index.json
test_mode = false
package_version = 13.0.3
output_file = dependencies.svg
ascii_tree = true

Этап 1 завершён: конфигурация успешно загружена.
```

## Проверка тестами

Из корня проекта:

```bat
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

Тесты проверяют корректную конфигурацию и ошибки каждого параметра:
имя пакета, URL/путь тестового репозитория, тип `test_mode`, версию,
имя SVG-файла, тип `ascii_tree`, а также отсутствие конфигурационного файла.

## Обработка ошибок вручную

Попробуйте по очереди изменить в `config.toml`:

- `package_name = "bad name"` — недопустимое имя.
- `repository = "not-a-url"` при `test_mode = false` — неверный URL.
- `test_mode = "no"` — вместо логического значения передана строка.
- `test_mode = true` и несуществующий путь в `repository` — файл не найден.
- `package_version = "??"` — неверная версия.
- `output_file = "graph.png"` — требуется расширение `.svg`.
- `ascii_tree = "yes"` — требуется `true` или `false`.

После каждого изменения запустите `run.bat`. Для успешного запуска
верните исходные корректные значения.

## Git и коммиты

Используйте Conventional/Scoped Commits. Пример сообщения для этапа 1:

```text
feat(config): add TOML configuration and CLI prototype
```

Подробная инструкция по публикации проекта через GitHub Desktop приведена
ниже.

### Публикация через GitHub Desktop

1. Создайте пустой репозиторий на GitHub (можно без README и `.gitignore`).
2. Откройте GitHub Desktop.
3. Выберите **File → Add local repository...** и укажите папку проекта.
   Если GitHub Desktop сообщает, что это ещё не Git-репозиторий, выберите
   **create a repository** или сначала выполните `git init` в терминале.
4. В GitHub Desktop проверьте список изменений, введите сообщение коммита
   `feat(config): add TOML configuration and CLI prototype`.
5. Нажмите **Commit to main**.
6. Нажмите **Publish repository** (или **Push origin**, если remote уже создан).

### Если удобнее открыть проект через командную строку

В GitHub Desktop откройте **File → Options → Integrations** и проверьте,
что выбран терминал (например, Git Bash). Затем откройте папку проекта
в Проводнике, в адресной строке введите `cmd` и нажмите Enter.

В открывшемся окне выполните:

```bat
git init
git add .
git commit -m "feat(config): add TOML configuration and CLI prototype"
```

После этого вернитесь в GitHub Desktop: добавьте локальный репозиторий
через **File → Add local repository...**, затем нажмите **Publish repository**.

Если репозиторий на GitHub уже создан и подключён как `origin`, можно
отправить коммит командой:

```bat
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/ИМЯ_РЕПОЗИТОРИЯ.git
git push -u origin main
```

Не выполняйте `git remote add`, если `origin` уже существует. Проверить
его можно командой `git remote -v`.
