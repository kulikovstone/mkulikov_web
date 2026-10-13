# mkulikov.com

Личный сайт: статические HTML, CSS и JavaScript, сборка через Vite.
На сервере готовые файлы обслуживает Nginx. Бэкенда и постоянно работающего
Node.js-приложения нет.

Репозиторий: https://github.com/kulikovstone/mkulikov_web.

## Локальная работа

Нужен Node.js 22.12 или новее; в CI используется Node.js 22.

```bash
npm ci
npm run dev
```

- `index.html` — фото, имя, специализации, краткое описание и метаданные страницы.
- `src/style.css` — оформление.
- `src/main.js` — точка входа JavaScript и подключение CSS.
- `src/assets/maksim-kulikov.jpg` — фотография для страницы; Vite добавляет хеш к имени файла в сборке.
- `public/` — файлы, копируемые в сборку без преобразования.
- `dist/` — результат `npm run build`, не хранится в Git.

Проверка перед публикацией:

```bash
python3 -m unittest discover -s tests -v
bash -n deploy/publish.sh deploy/setup-server.sh deploy/enable-https.sh
npm run build
```

`npm run preview` открывает локальный просмотр готовой сборки.
Python 3 нужен для проверок инфраструктуры; для разработки страницы достаточно Node.js.

## Публикация

После push в `master` GitHub Actions устанавливает зависимости из lock-файла,
проверяет скрипты, собирает сайт и отправляет только `dist/` на VDS по SSH.
Pull request запускает проверки и сборку. Ручная публикация доступна во вкладке
**Actions → Deploy website → Run workflow** для ветки `master`.

Сервер: `136.234.5.71`, общий с `curators.mkulikov.com`. У личного сайта собственные
конфигурация Nginx, сертификат, каталог версий и пользователь деплоя.
Настройка GitHub, сервера, HTTPS и откат описаны в [deploy/README.md](deploy/README.md).
