# -*- coding: utf-8 -*-
"""بازمحاسبه امتیاز و مدال مراکز روی پایگاه داده موجود + اصلاح برچسب داده
اجرای یک‌بارمصرف بعد از بارگذاری فایل‌های واقعی از طریق رابط وب:
    python recompute_scores.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import connect, ensure_schema, set_meta


def main():
    conn = connect()
    ensure_schema(conn)
    from generator import score_centers
    score_centers(conn)
    set_meta(conn, 'data_mode', 'real')
    set_meta(conn, 'imported_at', str(int(__import__('time').time())))
    conn.commit()
    n = conn.execute('SELECT COUNT(*) n FROM centers').fetchone()['n']
    medals = conn.execute('SELECT medal, COUNT(*) n FROM centers WHERE medal IS NOT NULL '
                          'GROUP BY medal ORDER BY n DESC').fetchall()
    print(f'امتیاز و مدال {n} مرکز بازمحاسبه شد.')
    for m in medals:
        print(f'   {m["medal"]}: {m["n"]}')


if __name__ == '__main__':
    main()
