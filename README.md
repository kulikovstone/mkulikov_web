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
- `experience/index.html` — страница опыта работы на английском, доступна по `/experience/`.
- `src/style.css` — оформление.
- `src/main.js` — точка входа JavaScript и подключение CSS.
- `src/experience.js` и `src/experience.css` — подключение стилей и оформление страницы опыта.
- `vite.config.js` — сборка обеих HTML-страниц; результат включает `dist/experience/index.html`.
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

## Страница опыта

Ссылка **Work experience** на главной открывает `/experience/`; ссылки
**Back to home** вверху и внизу страницы возвращают на главную. Это отдельная
статическая HTML-страница, поэтому прямое открытие и обновление адреса работают
с существующей конфигурацией Nginx.

Опыт изложен в обратной хронологии. Проекты одного работодателя объединены,
сохранены отдельные даты проектов, их контекст, конкретный вклад и технологии.
Специализация указана над названием каждого заказчика и проекта.
Содержание Android-опыта основано на предоставленном резюме; даты IT One
сохранены как `Feb 2022 — Present`, как в исходном документе.
Текущий клиентский проект IT One — **Curator Community**, роль
**AI-Assisted Fullstack Developer** — описан по реализации и документации
соседних репозиториев `Curators` и `curator_web`. Он объединён с проектом
Gazprombank в один блок IT One с общим периодом работы.
Даты проектов уточнены владельцем сайта: Gazprombank — `Feb 2022 — Aug 2026`,
Curator Community — `Sep 2026 — Present`.

Ориентиры по структуре и изложению:
[Jake's Resume](https://github.com/jakegut/resume/blob/master/resume.tex),
[образцы MIT CAPD](https://capd.mit.edu/resources/sample-resumes/) и
[рекомендации MIT](https://capd.mit.edu/resources/resumes/).

## Публикация

После push в `master` GitHub Actions устанавливает зависимости из lock-файла,
проверяет скрипты, собирает сайт и отправляет только `dist/` на VDS по SSH.
Pull request запускает проверки и сборку. Ручная публикация доступна во вкладке
**Actions → Deploy website → Run workflow** для ветки `master`.

Сервер: `136.234.5.71`, общий с `curators.mkulikov.com`. У личного сайта собственные
конфигурация Nginx, сертификат, каталог версий и пользователь деплоя.
Настройка GitHub, сервера, HTTPS и откат описаны в [deploy/README.md](deploy/README.md).
