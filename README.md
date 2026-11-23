# Dependency Visualizer

CLI-инструмент для практической работы №2, **вариант 16, этапы 1–2**.
Программа читает параметры из TOML и получает прямые зависимости конкретной
версии NuGet-пакета.

## Что реализовано

### Этап 1 — минимальный прототип с конфигурацией

- Параметры берутся из `config.toml`.
- Проверяются все шесть параметров: имя пакета, URL/путь репозитория,
  режим тестового репозитория, версия, имя SVG-файла, режим ASCII-дерева.
- Сохранён CLI-запуск через `python -m dependency_visualizer`.

### Этап 2 — сбор данных

- Используется формат пакетов .NET (NuGet).
- Получение данных выполняется для точной версии из `package_version`.
- Для реального репозитория программа запрашивает NuGet V3 service index,
  находит ресурс `PackageBaseAddress`, затем загружает `.nuspec` выбранной
  версии пакета.
- XML `.nuspec` разбирается встроенным `xml.etree.ElementTree`.
- Выводятся все прямые зависимости, их диапазоны версий и целевые framework-группы.
- Для offline-проверки оставлен тестовый режим с JSON-файлом.

**Ограничение задания соблюдено:** не вызываются `dotnet`, `nuget`, `PackageReference`
или сторонние библиотеки для разрешения/получения зависимостей. HTTP выполняется
стандартным `urllib`, XML/JSON разбираются стандартными модулями Python.

## Требования

- Windows 10/11
- Python 3.11 или новее
- Для реального режима — доступ к сети и URL NuGet V3 service index
- Git — для сохранения результата коммитом

Внешние Python-пакеты устанавливать не требуется.

## Структура проекта

```text
dependency_visualizer/
├── src/
│   └── dependency_visualizer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       └── nuget.py
├── tests/
│   ├── fixtures/
│   │   └── nuget_test_repository.json
│   ├── test_config.py
│   └── test_nuget.py
├── config.toml
├── README.md
├── .gitignore
└── run.bat
```

- `config.py` — модель настроек и проверка TOML.
- `cli.py` — точка входа CLI: загружает конфигурацию, запускает получение зависимостей и печатает результат.
- `nuget.py` — NuGet V3 HTTP-клиент, извлечение PackageBaseAddress и разбор `.nuspec`; здесь же находится чтение тестового JSON.
- `__main__.py` — запуск пакета командой `python -m`.
- `tests/test_config.py` — тесты параметров конфигурации.
- `tests/test_nuget.py` — тесты разбора `.nuspec`, HTTP-последовательности и тестового репозитория.
- `tests/fixtures/nuget_test_repository.json` — небольшой offline-набор для ручной демонстрации.
- `config.toml` — пользовательские параметры.
- `run.bat` — запуск в Windows.

## Настройка и запуск в Windows

1. Установите Python 3.11+ и включите **Add Python to PATH**.
2. Откройте `config.toml` и укажите пакет, версию и URL репозитория.
3. Для обычной работы оставьте `test_mode = false`.
4. Запустите `run.bat` двойным щелчком или из `cmd`:

```bat
run.bat
```

Пример конфигурации для публичного NuGet:

```toml
package_name = "Newtonsoft.Json"
repository = "https://api.nuget.org/v3/index.json"
test_mode = false
package_version = "13.0.3"
output_file = "dependencies.svg"
ascii_tree = true
```

В обычном режиме указывается именно URL V3 service index, а не страница пакета
на nuget.org.

## Offline-режим для демонстрации

В `config.toml` временно укажите:

```toml
package_name = "Example.Library"
repository = "tests/fixtures/nuget_test_repository.json"
test_mode = true
package_version = "1.2.0"
output_file = "dependencies.svg"
ascii_tree = true
```

Затем запустите `run.bat`. Должны появиться три прямые зависимости:

- `System.Text.Json`, диапазон `[8.0.0, 9.0.0)`, framework `net8.0`;
- `Microsoft.Extensions.Logging.Abstractions`, версия `8.0.0`, framework `net8.0`;
- `System.Text.Json`, диапазон `[7.0.0, 8.0.0)`, framework `net6.0`.

Одинаковый пакет может присутствовать в разных framework-группах с разными
ограничениями версии. Программа намеренно показывает обе записи, а не выбирает
одну без заданного целевого framework.

## Пример результата

Фактический список зависит от метаданных NuGet для выбранного пакета и версии.
Формат вывода:

```text
Прямые зависимости NuGet-пакета
Пакет: Example.Library
Версия: 1.2.0
Репозиторий: tests/fixtures/nuget_test_repository.json
Количество прямых зависимостей: 3
1. System.Text.Json (версия: [8.0.0, 9.0.0); целевой framework: net8.0)
2. Microsoft.Extensions.Logging.Abstractions (версия: 8.0.0; целевой framework: net8.0)
3. System.Text.Json (версия: [7.0.0, 8.0.0); целевой framework: net6.0)

Этап 2 завершён: прямые зависимости получены.
```

## Проверка тестами

Из корня проекта выполните:

```bat
set PYTHONPATH=src
python -m unittest discover -s tests -v
```

Тесты не обращаются к интернету: сетевые ответы для проверки клиента
подменяются локальными данными. Отдельно проверяются конфигурация, разбор XML,
несколько framework-групп, отсутствие зависимостей и тестовый JSON-репозиторий.

## Обработка ошибок

Программа сообщает понятную ошибку, если:

- конфигурация отсутствует или имеет неверный TOML-синтаксис;
- URL репозитория недоступен или возвращает HTTP-ошибку;
- service index не содержит `PackageBaseAddress`;
- пакет/версия не найдены (HTTP 404);
- ответ service index не является корректным JSON;
- файл `.nuspec` содержит некорректный XML;
- в тестовом репозитории нет указанной версии.

## Git: коммит этапа 2

Если проект уже находится под Git, откройте папку проекта в командной строке
через GitHub Desktop (**Repository → Open in Command Prompt**, название пункта
может отличаться в зависимости от версии), затем выполните:

```bat
git status
git add .
git status
git commit -m "feat(nuget): fetch direct dependencies for package version"
```

Вернитесь в GitHub Desktop и нажмите **Push origin**. Если репозиторий ещё не
опубликован, нажмите **Publish repository**.

Если Git-репозиторий ещё не создан, сначала выполните `git init` в папке проекта.
