#!/usr/bin/env bash
# اجرای کامل سامانه: بیلد فرانت + سرو توسط Flask
set -e
cd "$(dirname "$0")"
if [ ! -f backend/data/nikookari.db ]; then
  echo "ساخت پایگاه داده نمونه…"
  (cd backend && python3 generator.py)
fi
if [ ! -f frontend/dist/index.html ]; then
  echo "بیلد فرانت‌اند…"
  (cd frontend && npm install && npm run build)
fi
cd backend && exec python3 app.py
