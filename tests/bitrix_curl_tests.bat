@echo off
echo ============================================================
echo BITRIX24 SMART PROCESS - cURL TESTS
echo ============================================================
echo.

set WEBHOOK_URL=https://docsinbox.bitrix24.ru/rest/100398/cu1jtnas2sy621t3/

echo [1/5] Получение типа смарт-процесса (ID=1070)
echo ------------------------------------------------------------
curl -X POST "%WEBHOOK_URL%crm.type.get.json" ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": 1070}"
echo.
echo.

echo [2/5] Получение стадии 3150
echo ------------------------------------------------------------
curl -X POST "%WEBHOOK_URL%crm.status.get.json" ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"3150\"}"
echo.
echo.

echo [3/5] Список торговых точек на стадии 3150
echo ------------------------------------------------------------
curl -X POST "%WEBHOOK_URL%crm.item.list.json" ^
  -H "Content-Type: application/json" ^
  -d "{\"entityTypeId\": 1070, \"select\": [\"ID\", \"TITLE\", \"STAGE_ID\"], \"filter\": {\"STAGE_ID\": \"3150\"}, \"limit\": 5}"
echo.
echo.

echo [4/5] Поля смарт-процесса (Type=1070)
echo ------------------------------------------------------------
curl -X POST "%WEBHOOK_URL%crm.item.fields.json" ^
  -H "Content-Type: application/json" ^
  -d "{\"entityTypeId\": 1070}"
echo.
echo.

echo [5/5] Категория 38
echo ------------------------------------------------------------
curl -X POST "%WEBHOOK_URL%crm.category.get.json" ^
  -H "Content-Type: application/json" ^
  -d "{\"id\": \"38\"}"
echo.
echo.

echo ============================================================
echo TESTS COMPLETE
echo ============================================================
pause
