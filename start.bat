@echo off
rem ---------------------------------------------------------------
rem  اجرای کامل سامانه نیکوکاری روی ویندوز (PowerShell / CMD)
rem  استفاده:  .\start.bat     یا دابل‌کلیک روی همین فایل
rem ---------------------------------------------------------------
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set PY=python
where python3 >nul 2>nul && set PY=python3

if not exist "backend\data\nikookari.db" (
  echo ساخت پایگاه داده نمونه...
  pushd backend && %PY% generator.py && popd
)

rem بیلد فرانت‌اند: اگر dist نباشد یا سورس جدیدتر از بیلد قبلی باشد
set NEED_BUILD=0
if not exist "frontend\dist\index.html" set NEED_BUILD=1
if "%NEED_BUILD%"=="0" (
  for /f %%i in ('powershell -NoProfile -Command "(Get-ChildItem -Recurse 'frontend\src','frontend\index.html','frontend\vite.config.js' -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Item 'frontend\dist\index.html').LastWriteTime } | Measure-Object).Count"') do set NEWER=%%i
  if not "%NEWER%"=="0" set NEED_BUILD=1
)
if "%NEED_BUILD%"=="1" (
  echo بیلد فرانت‌اند... (بار اول چند دقیقه طول می‌کشد)
  pushd frontend
  call npm install || (popd & echo خطا: npm در دسترس نیست & goto :run)
  call npm run build
  popd
) else (
  echo بیلد فرانت‌اند به‌روز است.
)

:run
if not defined PORT set PORT=8000
echo اجرای سرور روی پورت %PORT% — مرورگر: http://localhost:%PORT%
cd backend
%PY% app.py
