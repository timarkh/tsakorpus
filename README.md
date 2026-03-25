# Tsakorpus Evenki 3.0
Этот репозиторий содержит инструменты для конвертации и индексации данных эвенкийского корпуса в систему **Tsakorpus**, а также для запуска самого корпуса.

## Обзор
**Tsakorpus** — это поисковая платформа для лингвистических корпусов, использующая движок **Elasticsearch** для хранения и обработки запросов. Система состоит из трех основных частей:

1. Конвертеры исходных данных: превращают тексты из различных форматов (ELAN, TXT, JSON и др.) в унифицированные JSON-документы формата Tsakorpus.
2. Индексатор: загружает эти документы в базу данных, рассчитывая частотные характеристики слов.
3. Веб-интерфейс: написан на Python (фреймворк Flask). Он позволяет пользователям строить сложные запросы через графический интерфейс и просматривать результаты.

Интерфейс легко переключается между языками благодаря библиотеке Flask-Babel.

## Документация
Вся документация по **Tsakorpus** находится [здесь](https://tsakorpus.readthedocs.io/en/latest/). [Здесь](https://tsakorpus.readthedocs.io/en/latest/overview.html) подробная инструкция по запуску.

## Требования

Tsakorpus работает на Windows and Ubuntu. Для запуска нужны следующие зависимости:

* Elasticsearch 9.x или 7.x (возможно, работает и на 8.x)
* Python >= 3.12
* Библиотеки Python: elasticsearch, flask, lxml, ijson, Flask-Babel, xlsxwriter, sqlitedict, pympler (you can use requirements.txt)
* Для конвертации мультимедийных корпусов (с привязкой к аудио или видео) необходим ffmpeg.
* Для стабильной работы рекомендуется запускать Tsakorpus через Apache2 с модулем wsgi или через nginx

**Внимание!** Номер Python-модуля elasticsearch должен совпадать с версией вашего сервера Elasticsearch. Если вы устанавливаете зависимости через `requirements.txt`, по умолчанию установится последняя версия 9.x. Если вы используете другую версию Elasticsearch (например, 7.x), отредактируйте список зависимостей вручную.

*Пример:* для Elasticsearch 7.x укажите в терминале или в файле: `elasticsearch>=7.0.0,<8.0.0`.

Ресурсы, которые используются, но их не нужно устанавливать:

* [jQuery](https://jquery.com/) library
* [jQuery-Autocomplete](https://github.com/devbridge/jQuery-Autocomplete)
* [video.js](http://videojs.com/) media player
* [videojs-youtube](https://github.com/videojs/videojs-youtube) plugin
* [bootstrap](http://getbootstrap.com/) toolkit
* [D3.js](https://d3js.org/) visualization library
* [KioskBoard](https://github.com/furcan/KioskBoard) virtual keyboard

## Установка
Для локального запуска корпуса нужно сделать следующие действия:

### Подготовка окружения
1. Запустить Docker
2. Перейти в корень проекта
3. Выполнить в терминале команды:
``` bash
docker run -d --name tsakorpus-es -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:7.17.10
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Для Windows:
``` bash
docker run -d --name tsakorpus-es -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:9.3.0
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```
### Загрузка данных
Перед этим убедитесь, что у вас есть доступ к нужному датасету на Hugging Face
``` bash
cd data_raw
python get_data.py
cd ../src_convertors
python hf2json.py
cd ../indexator
python indexator.py
```
### Запуск сервера
```bash
cd ../search
python tsakorpus.wsgi
```
Далее откройте в браузере ссылку `http://127.0.0.1:7342/search`. По этому адресу откроется корпус.
