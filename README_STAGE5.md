# Этап 5 — визуализация Graphviz (вариант 16)

Этот архив содержит только файлы, добавленные или изменённые для этапа 5. Он рассчитан на применение поверх проекта после этапа 4.

## Что входит

- `src/dependency_visualizer/visualization.py` — генерация DOT, экспорт SVG через Graphviz и ASCII-дерево.
- `src/dependency_visualizer/cli.py` — обновлённый CLI, подключающий визуализацию к построенному графу.
- `tests/test_visualization.py` — тесты визуализации.
- `config.test.A.toml`, `config.test.B.toml`, `config.test.C.toml` — три конфигурации для демонстрации.
- `examples/` — DOT-описания и готовые SVG для пакетов A, B и C.

## Установка и запуск (Windows)

1. Установите Graphviz: https://graphviz.org/download/.
2. Добавьте каталог `bin` Graphviz в `PATH`.
3. Проверьте установку: `dot -V`.
4. В корне полного проекта выполните:

```bat
set PYTHONPATH=src
python -m dependency_visualizer --config config.test.A.toml
python -m dependency_visualizer --config config.test.B.toml
python -m dependency_visualizer --config config.test.C.toml
```

Команды формируют SVG-файлы. DOT-описание графа выводится в консоль. ASCII-дерево выводится, если в TOML включён параметр `ascii_tree = true`.

## Сравнение с NuGet

Для сравнения состава прямых и транзитивных пакетов в реальном проекте используйте:

```bat
dotnet list package --include-transitive
```

Команда .NET SDK показывает список зависимостей, но не строит ориентированный граф и не экспортирует SVG. Сравнивать следует состав и версии пакетов. Возможные различия связаны с тем, что SDK учитывает целевые платформы, runtime и результат восстановления проекта, а визуализатор строит граф по метаданным выбранной версии пакета NuGet.

## Интеграция

Распакуйте содержимое папки `dependency_visualizer` поверх проекта этапа 4 с заменой `src/dependency_visualizer/cli.py`, затем запустите тесты проекта. Этот архив не является самостоятельной полной копией приложения: базовые модули конфигурации, NuGet и графа берутся из этапа 4.
