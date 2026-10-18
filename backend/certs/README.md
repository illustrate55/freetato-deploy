# Сертификаты для GigaChat

Для production-запуска GigaChat-API требуется сертификат
**«Russian Trusted Root CA»**.

## Где взять

1. Открой https://www.gosuslugi.ru/crt
2. Скачай **Корневой сертификат** в формате `.cer` или `.crt`
3. Положи его в эту папку с именем `russian_trusted_root_ca.crt`
4. В `.env` укажи:
   ```
   GIGACHAT_CA_BUNDLE_FILE=/app/certs/russian_trusted_root_ca.crt
   GIGACHAT_VERIFY_SSL_CERTS=true
   ```
5. Перезапусти контейнер: `docker compose restart app`

## В development

Для локальной разработки можно пропустить этот шаг —
поставь в `.env`:
```
GIGACHAT_VERIFY_SSL_CERTS=false
```

В этом режиме SDK GigaChat подключается без верификации сертификата
(это небезопасно, использовать ТОЛЬКО на dev-стенде).
