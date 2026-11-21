@echo off
rem ---------------------------------------------------------------
rem  اجرای کامل سامانه نیکوکاری روی ویندوز (PowerShell / CMD)
rem  استفاده:  .\start.bat     یا دابل‌کلیک روی همین فایل
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

set PY=python
where python3 >nul 2>nul && set PY=python3

if not exist "backend\data\nikookari.db" (
  echo ساخت پایگاه داده نمونه...
  pushd backend && %PY% generator.py && popd
)

rem بیلد فرانت‌اند اگر dist نباشد
if not exist "frontend\dist\index.html" (
  echo بیلد فرانت‌اند...
  pushd frontend && call npm install && call npm run build && popd
)

if not defined PORT set PORT=8000
echo اجرای سرور روی پورت %PORT% — مرورگر: http://localhost:%PORT%
cd backend
%PY% app.py
