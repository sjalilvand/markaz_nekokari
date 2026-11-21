# -*- coding: utf-8 -*-
"""نرمال‌سازی متن فارسی و تبدیل‌های عددی/تاریخی"""
import re

AR_MAP = {
    'ي': 'ی', 'ك': 'ک', 'ى': 'ی', 'ة': 'ه', 'ۀ': 'ه', 'ؤ': 'و',
    'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا', 'ﺎ': 'ا', 'ﻯ': 'ی',
}
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
ZWNJ = '\u200c'
ZWNJ_FIX = {
    'قرض‌الحسنه': 'قرض الحسنه',
}


def norm(s):
    """نرمال‌سازی: تبدیل ارقام فارسی، حروف عربی به فارسی، حذف فاصله اضافه"""
    if s is None:
        return ''
    s = str(s).translate(DIGITS)
    for a, b in AR_MAP.items():
        s = s.replace(a, b)
    s = s.replace(ZWNJ, ' ')
    s = re.sub(r'[\u200e\u200f\u202a-\u202e\ufeff]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_key(s):
    """کلید مقایسه‌ای: بدون فاصله و نیم‌فاصله؛ حروف لاتین کوچک می‌شوند تا نام فایل‌های انگلیسی مثل NK_HAMYARAN درست شناسایی شوند"""
    return norm(s).replace(' ', '').replace('_', '').lower()


def to_int(s, default=None):
    s = norm(s).replace(',', '').replace('٬', '')
    if s in ('', '-'):
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def to_float(s, default=None):
    s = norm(s).replace(',', '').replace('٬', '')
    if s in ('', '-'):
        return default
    try:
        return float(s)
    except ValueError:
        return default


DATE_RE = re.compile(r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$')
DATE_RE_COMPACT = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
DATE_RE_LOOSE = re.compile(r'(1[3-5]\d{2})[/\-.](\d{1,2})(?:[/\-.](\d{1,2}))?')


def parse_jalali(s):
    """تاریخ شمسی 'YYYY/MM/DD' → (year, month, day) یا None
    فرمت‌های پشتیبانی‌شده: 1405/08/27، 1405-8-27، 1405.08.27، 14050827 و حالت نرم (تاریخ داخل متن)"""
    t = norm(s).strip()
    if not t:
        return None
    m = DATE_RE.match(t) or DATE_RE_COMPACT.match(t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
        if 1300 <= y <= 1500 and 1 <= mo <= 12 and 1 <= d <= 31:
            return (y, mo, d)
    # حالت نرم: یافتن الگوی سال/ماه داخل رشته (مثل «تاریخ: ۱۴۰۵/۰۸/۲۷» یا متن اضافه)
    m2 = DATE_RE_LOOSE.search(t)
    if m2:
        y, mo = int(m2.group(1)), int(m2.group(2))
        d = int(m2.group(3) or 1)
        if 1300 <= y <= 1500 and 1 <= mo <= 12 and 1 <= d <= 31:
            return (y, mo, d)
    return None


def find_date_col(df):
    """اگر ستون تاریخ با نام‌های مستعار پیدا نشد، هر ستونی که «تاریخ» دارد و «تولد» نیست را برگردان"""
    for c in df.columns:
        k = norm_key(c)
        if ('تاریخ' in k or 'تاريخ' in k or 'زمان' in k or 'date' in k) \
                and 'تولد' not in k and ' births' not in k:
            return c
    return None
