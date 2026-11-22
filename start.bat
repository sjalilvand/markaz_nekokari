@echo off
rem ===============================================================
rem  اجرای کامل سامانه نیکوکاری روی ویندوز (PowerShell / CMD)
rem  استفاده:  .\start.bat    یا دابل‌کلیک روی همین فایل
rem  این اسکریپت Python را از چند مسیر مختلف پیدا می‌کند؛
rem  شبه‌فایل Microsoft Store به‌طور خودکار رد می‌شود.
rem ===============================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

rem ═══════════════ یافتن Python ═══════════════
set "PY="
set "PYARG="

rem ۱) محیط مجازی محلی پروژه — اگر وجود داشته باشد در اولویت است
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "backend\.venv\Scripts\python.exe" set "PY=backend\.venv\Scripts\python.exe"

rem ۲) اجراکنندهٔ py ویندوز (نصب python.org همیشه آن را ثبت می‌کند)
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PY=py"
            set "PYARG=-3"
        )
    )
)

rem ۳) python3 و python روی PATH — تست import شبه‌فایل Store را حذف می‌کند
if not defined PY (
    where python3 >nul 2>nul
    if not errorlevel 1 (
        python3 -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY=python3"
    )
)
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY=python"
    )
)

rem ۴) مسیرهای نصب رایج — حتی وقتی PATH تنظیم نشده است
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
if not defined PY for /d %%D in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%ProgramFiles%\Python*" "C:\Python*") do if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"

if not defined PY goto :no_python
echo Python پیدا شد: "%PY%" %PYARG%

rem ═══════════════ وابستگی‌های بک‌اند ═══════════════
"%PY%" %PYARG% -c "import flask, flask_cors" >nul 2>nul
if errorlevel 1 (
    echo وابستگی‌های بک‌اند نصب نیستند — در حال نصب، چند دقیقه زمان می‌برد...
    "%PY%" %PYARG% -m pip install -r backend\requirements.txt
    "%PY%" %PYARG% -c "import flask, flask_cors" >nul 2>nul
    if errorlevel 1 goto :pip_fail
)
echo وابستگی‌های بک‌اند آماده است.

rem ═══════════════ پایگاه دادهٔ نمونه ═══════════════
if exist "backend\data\nikookari.db" goto :have_db
echo ساخت پایگاه دادهٔ نمونه...
pushd backend
"%PY%" %PYARG% generator.py
popd
:have_db

rem ═══════════════ بیلد فرانت‌اند ═══════════════
set "NEED_BUILD=0"
if not exist "frontend\dist\index.html" set "NEED_BUILD=1"
if "%NEED_BUILD%"=="1" goto :do_build
rem سورس جدیدتر از بیلد قبلی؟ شمارش فایل‌های تغییرکرده با PowerShell
for /f "usebackq" %%i in (`powershell -NoProfile -Command "(Get-ChildItem -Recurse 'frontend\src','frontend\index.html','frontend\vite.config.js' -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Item 'frontend\dist\index.html').LastWriteTime } | Measure-Object).Count"`) do set "NEWER=%%i"
if not "!NEWER!"=="0" set "NEED_BUILD=1"
:do_build
if "%NEED_BUILD%"=="0" (
    echo بیلد فرانت‌اند به‌روز است.
    goto :after_build
)
echo بیلد فرانت‌اند... بار اول چند دقیقه طول می‌کشد
where npm >nul 2>nul
if errorlevel 1 (
    echo [خطا] npm پیدا نشد — Node.js را از nodejs.org نصب کنید و دوباره تلاش کنید.
    pause
    exit /b 1
)
pushd frontend
call npm install
call npm run build
popd
if not exist "frontend\dist\index.html" (
    echo [خطا] بیلد فرانت‌اند ناموفق بود — پیام‌های بالا را بررسی کنید.
    pause
    exit /b 1
)
:after_build

rem ═══════════════ اجرای سرور ═══════════════
if not defined PORT set "PORT=8000"
echo.
echo اجرای سرور روی پورت %PORT% — مرورگر: http://localhost:%PORT%
echo برای توقف سرور: Ctrl+C
echo.
cd backend
"%PY%" %PYARG% app.py
goto :eof

:no_python
echo ────────────────────────────────────────────────────────────
echo [خطا] Python روی این سیستم پیدا نشد.
echo.
echo راه‌حل‌ها:
echo   ۱. نصب Python از python.org و تیک‌زدن گزینهٔ Add python.exe to PATH هنگام نصب
echo   ۲. یا در PowerShell این دستور را اجرا کنید:
echo        winget install -e --id Python.Python.3.12
echo   ۳. اگر Python نصب است ولی باز هم پیدا نمی‌شود:
echo      Settings ^> Apps ^> Advanced app settings ^> App execution aliases
echo      دو گزینهٔ python را خاموش کنید، سپس PowerShell را ببندید و دوباره باز کنید.
echo.
echo پس از آن دوباره دستور  .\start.bat  را اجرا کنید.
echo ────────────────────────────────────────────────────────────
pause
exit /b 1

:pip_fail
echo ────────────────────────────────────────────────────────────
echo [خطا] نصب وابستگی‌های بک‌اند ناموفق بود. این دستور را دستی اجرا کنید:
echo     "%PY%" %PYARG% -m pip install -r backend\requirements.txt
echo ────────────────────────────────────────────────────────────
pause
exit /b 1
