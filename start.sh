#!/usr/bin/env bash
# اجرای کامل سامانه: بیلد فرانت + سرو توسط Flask
# (سازگار با ویندوز/Git Bash — اگر python3 نبود از python استفاده می‌شود)
set -e
cd "$(dirname "$0")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

if [ ! -f backend/data/nikookari.db ]; then
  echo "ساخت پایگاه داده نمونه…"
  (cd backend && "$PY" generator.py)
fi

# بیلد فرانت‌اند: اگر dist وجود ندارد یا سورس جدیدتر از بیلد قبلی است، دوباره بیلد شود
NEED_BUILD=0
if [ ! -f frontend/dist/index.html ]; then
  NEED_BUILD=1
elif [ -n "$(find frontend/src frontend/index.html frontend/vite.config.js -newer frontend/dist/index.html -print -quit 2>/dev/null)" ]; then
  NEED_BUILD=1
fi
if [ "$NEED_BUILD" = "1" ]; then
  echo "بیلد فرانت‌اند…"
  (cd frontend && npm install && npm run build)
else
  echo "بیلد فرانت‌اند به‌روز است."
fi

echo "اجرای سرور روی پورت ${PORT:-8000} — برای اعمال تغییرات، هر بار سرور را با این اسکریپت ری‌استارت کنید."
cd backend && exec "$PY" app.py
