# Для Славяночки 🦇

Маленький сайт для любимой.

## Структура

- `site/` сам сайт (html, css, js, картинки, музыка)
- `site/js/config.js` песни, карточки love is и текст письма, всё меняется тут
- `site/music/` сюда кидать mp3
- `deploy/` конфиг nginx и скрипт установки

## Как добавить песни

1. Закинуть mp3 в `site/music/`, лучше латиницей без пробелов, например `song1.mp3`
2. Прописать название и исполнителя в `site/js/config.js` в `PLAYLIST`

## Посмотреть у себя на компе

```bash
cd site
python3 -m http.server 8000
```

И открыть http://localhost:8000

## Запуск на сервере по IP

Нужен любой VPS с Ubuntu или Debian. Заходим по ssh и делаем:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/dalmatinec/Downloader.git
cd Downloader
sudo bash deploy/setup.sh
```

Скрипт в конце напишет адрес вида `http://123.45.67.89`, его и кидаешь ей.

## Включить https

```bash
cd ~/Downloader && bash deploy/https.sh
```

Сертификат бесплатный от Let's Encrypt, выдаётся прямо на IP. Живёт 6 дней и продлевается сам.

## Обновить сайт после изменений

```bash
cd ~/Downloader && sudo bash deploy/update.sh
```

Кэш настроен так, что браузер каждый раз сверяется с сервером, поэтому после обновления все сразу видят новую версию.
