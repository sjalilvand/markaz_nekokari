#!/usr/bin/env bash
# ===============================================================
# اجرای کامل سامانه نیکوکاری — سازگار با Git Bash ویندوز و لینوکس
# Python را از چند مسیر پیدا می‌کند؛ شبه‌فایل Microsoft Store رد می‌شود.
# ===============================================================
set -e
cd "$(dirname "$0")"

PY=""
PYARG=""

# ۱) محیط مجازی محلی پروژه
if [ -f .venv/bin/python ]; then PY=.venv/bin/python
elif [ -f .venv/Scripts/python.exe ]; then PY=".venv/Scripts/python.exe"
elif [ -f backend/.venv/bin/python ]; then PY=backend/.venv/bin/python
elif [ -f backend/.venv/Scripts/python.exe ]; then PY="backend/.venv/Scripts/python.exe"
fi

# ۲) دستورهای شناخته‌شده روی PATH — تست import، شبه‌فایل Store ویندوز را رد می‌کند
if [ -z "$PY" ]; then
  for c in "python3" "python" "py -3"; do
    if $c -c "import sys" >/dev/null 2>&1; then
      PY="${c%% *}"
      PYARG="${c#* }"
      [ "$PYARG" = "$c" ] && PYARG=""
      break
    fi
  done
fi

# ۳) مسیرهای نصب رایج ویندوز — حتی وقتی PATH تنظیم نشده است
if [ -z "$PY" ]; then
  for p in "$LOCALAPPDATA/Programs/Python/"Python*/python.exe \
           "$USERPROFILE/anaconda3/python.exe" \
           "$USERPROFILE/miniconda3/python.exe" \
           /c/Python*/python.exe; do
    if [ -f "$p" ] && "$p" -c "import sys" >/dev/null 2>&1; then PY="$p"; break; fi
  done
fi

if [ -z "$PY" ]; then
  cat <<'EOF'
============================================================
[خطا] Python روی این سیستم پیدا نشد.

راه‌حل‌ها:
  ۱. نصب Python از python.org و تیک‌زدن گزینهٔ Add python.exe to PATH
  ۲. یا در PowerShell:  winget install -e --id Python.Python.3.12
  ۳. اگر Python نصب است: در تنظیمات ویندوز مسیر
     Settings > Apps > Advanced app settings > App execution aliases
     دو گزینهٔ python را خاموش کنید و PowerShell را دوباره باز کنید.

سپس دوباره: bash start.sh
============================================================
EOF
  exit 1
fi

echo "Python پیدا شد: $PY ${PYARG:+$PYARG}"

# ── وابستگی‌های بک‌اند ──
if ! $PY $PYARG -c "import flask, flask_cors" >/dev/null 2>&1; then
  echo "وابستگی‌های بک‌اند نصب نیستند — در حال نصب، چند دقیقه زمان می‌برد…"
  $PY $PYARG -m pip install -r backend/requirements.txt
fi

# ── پایگاه دادهٔ نمونه ──
if [ ! -f backend/data/nikookari.db ]; then
  echo "ساخت پایگاه دادهٔ نمونه…"
  (cd backend && $PY $PYARG generator.py)
fi

# ── بیلد فرانت‌اند: اگر dist نباشد یا سورس جدیدتر باشد ──
NEED_BUILD=0
if [ ! -f frontend/dist/index.html ]; then
  NEED_BUILD=1
elif [ -n "$(find frontend/src frontend/index.html frontend/vite.config.js -newer frontend/dist/index.html -print -quit 2>/dev/null)" ]; then
  NEED_BUILD=1
fi
if [ "$NEED_BUILD" = "1" ]; then
  echo "بیلد فرانت‌اند… بار اول چند دقیقه طول می‌کشد"
  (cd frontend && npm install && npm run build)
else
  echo "بیلد فرانت‌اند به‌روز است."
fi

echo ""
echo "اجرای سرور روی پورت ${PORT:-8000} — مرورگر: http://localhost:${PORT:-8000}"
echo "برای توقف سرور: Ctrl+C"
echo ""
cd backend && exec $PY $PYARG app.py
