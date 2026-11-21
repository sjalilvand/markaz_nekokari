# -*- coding: utf-8 -*-
"""لایه دیتابیس SQLite - طرح جداول و شاخص‌ها"""
import os
import sqlite3

# جدول‌هایی که ستون src_file دارند (برای ورود مجدد idempotent هر فایل)
SRC_TABLES = ['members', 'hamyaran', 'needy', 'requests', 'transactions', 'networks',
              'legal_donors', 'finance_province', 'compensation_province', 'anomalies', 'agg_reports']

# نگاشت اسکیما → جدول‌هایی که با ورود مجدد همان فایل باید پاک شوند
SCHEMA_TABLES = {
    'centers_new': [],            # مراکز با get_or_create تکرار نمی‌شوند
    'hamyaran': ['hamyaran'],
    'needy': ['needy'],
    'requests_report': ['requests'],
    'payments_cash': ['transactions'],
    'payments_group': ['transactions'],
    'receipts_cash': ['transactions'],
    'receipts_inkind': ['transactions'],
    'activity_center': ['transactions'],
    'members_kartex': ['members'],
    'centers_kartex': [],         # فقط UPDATE
    'networks': ['networks'],
    'packs': [],                  # خود handler کل جدول را بازسازی می‌کند
    'legal_donors': ['legal_donors'],
    'finance_province': [],       # خود handler کل جدول را بازسازی می‌کند
    'compensation': [],           # خود handler کل جدول را بازسازی می‌کند
    'general_report': ['members'],
    'agg': ['agg_reports'],
}

# نگاشت اسکیما → جدول اصلی برای backfill رکوردهای قدیمی از import_log
SCHEMA_BACKFILL = {
    'needy': 'needy', 'requests_report': 'requests', 'payments_cash': 'transactions',
    'payments_group': 'transactions', 'receipts_cash': 'transactions',
    'receipts_inkind': 'transactions', 'activity_center': 'transactions',
    'members_kartex': 'members', 'general_report': 'members', 'networks': 'networks',
    'legal_donors': 'legal_donors', 'finance_province': 'finance_province',
    'compensation': 'compensation_province', 'anomalies': 'anomalies', 'hamyaran': 'hamyaran',
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'nikookari.db')

DDL = """
CREATE TABLE IF NOT EXISTS provinces(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS offices(
  id INTEGER PRIMARY KEY, province_id INT, name TEXT);
CREATE TABLE IF NOT EXISTS centers(
  id INTEGER PRIMARY KEY, license_no TEXT UNIQUE, name TEXT,
  province_id INT, office_id INT, status TEXT DEFAULT 'فعال',
  chair INT DEFAULT 0, vice INT DEFAULT 0, exec_mgr INT DEFAULT 0,
  finance INT DEFAULT 0, members INT DEFAULT 0, inspector INT DEFAULT 0,
  alt_inspector INT DEFAULT 0, total_active INT DEFAULT 0, total_inactive INT DEFAULT 0,
  center_type TEXT, urban_rural TEXT, ownership TEXT, area INT,
  score REAL, medal TEXT, created_year INT);
CREATE TABLE IF NOT EXISTS members(
  id INTEGER PRIMARY KEY, center_id INT, national_id TEXT, name TEXT, family TEXT,
  gender TEXT, birth TEXT, age INT, education TEXT, job TEXT, role TEXT,
  status TEXT DEFAULT 'فعال',
  bank_debt TEXT, tax_debt TEXT, welfare TEXT, bounced_cheque TEXT,
  military TEXT, gov_emp TEXT, alive TEXT, criminal TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS hamyaran(
  id INTEGER PRIMARY KEY, national_id TEXT, mobile TEXT, name TEXT, family TEXT,
  father TEXT, gender TEXT, birth TEXT, age INT,
  province_id INT, office TEXT, center_id INT, status TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS needy(
  id INTEGER PRIMARY KEY, national_id TEXT, name TEXT, family TEXT, gender TEXT,
  birth TEXT, age INT, province_id INT, office TEXT, center_id INT,
  need_group TEXT, need_type TEXT, vital TEXT, decile INT, mobile TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS requests(
  id INTEGER PRIMARY KEY, tracking_no TEXT, center_id INT, province_id INT,
  request_type TEXT, category TEXT, national_id TEXT, creator TEXT,
  date_j TEXT, year INT, month INT,
  status TEXT, process_status TEXT, amount REAL, flow TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY, tracking_no TEXT, center_id INT, province_id INT,
  date_j TEXT, year INT, month INT, flow TEXT, method TEXT, category TEXT,
  source TEXT, amount REAL, beneficiaries INT, coverage TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS networks(
  id INTEGER PRIMARY KEY, center_id INT, network TEXT, people INT, src_file TEXT);
CREATE TABLE IF NOT EXISTS packs(
  id INTEGER PRIMARY KEY, pack_type TEXT, activity TEXT, source TEXT, items TEXT);
CREATE TABLE IF NOT EXISTS legal_donors(
  id INTEGER PRIMARY KEY, province_id INT, center_id INT, name TEXT,
  national_id TEXT, amount REAL, year INT, src_file TEXT);
CREATE TABLE IF NOT EXISTS finance_province(
  id INTEGER PRIMARY KEY, province_id INT, category TEXT, amount REAL, src_file TEXT);
CREATE TABLE IF NOT EXISTS compensation_province(
  id INTEGER PRIMARY KEY, province_id INT, year INT, month INT,
  centers_ok INT, centers_not_ok INT, centers_review INT,
  amount_ok REAL, amount_not_ok REAL, src_file TEXT);
CREATE TABLE IF NOT EXISTS anomalies(
  id INTEGER PRIMARY KEY, province_id INT, center_id INT, doc_no TEXT,
  date_j TEXT, descr TEXT, flow TEXT, amount REAL, title TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS import_log(
  id INTEGER PRIMARY KEY, filename TEXT, schema_name TEXT, encoding TEXT,
  rows_read INT, rows_inserted INT, duplicates INT, nulls_pct REAL,
  warnings TEXT, imported_at TEXT);
CREATE TABLE IF NOT EXISTS agg_reports(
  id INTEGER PRIMARY KEY, source TEXT, province TEXT, city TEXT, center TEXT,
  flow TEXT, method TEXT, category TEXT, amount REAL, extra TEXT, src_file TEXT);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS ix_tx_prov_year ON transactions(province_id, year, month, flow, method);
CREATE INDEX IF NOT EXISTS ix_tx_cat ON transactions(category);
CREATE INDEX IF NOT EXISTS ix_tx_center ON transactions(center_id);
CREATE INDEX IF NOT EXISTS ix_req_prov_year ON requests(province_id, year, month);
CREATE INDEX IF NOT EXISTS ix_req_center ON requests(center_id);
CREATE INDEX IF NOT EXISTS ix_needy_prov ON needy(province_id, decile);
CREATE INDEX IF NOT EXISTS ix_needy_center ON needy(center_id);
CREATE INDEX IF NOT EXISTS ix_centers_prov ON centers(province_id, status);
CREATE INDEX IF NOT EXISTS ix_members_center ON members(center_id);
CREATE INDEX IF NOT EXISTS ix_tx_src ON transactions(src_file);
CREATE INDEX IF NOT EXISTS ix_needy_src ON needy(src_file);
CREATE INDEX IF NOT EXISTS ix_req_src ON requests(src_file);
CREATE INDEX IF NOT EXISTS ix_mem_src ON members(src_file);
"""


def connect(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _migrate_src_file(conn):
    """مهاجرت: افزودن ستون src_file به پایگاه داده موجود و برچسب‌گذاری رکوردهای قدیمی
    بر اساس import_log تا ورود مجدد هر فایل، رکوردهای همان فایل را جایگزین کند."""
    if get_meta(conn, 'srcfile_v1') == '1':
        return
    for t in SRC_TABLES:
        cols = [r['name'] for r in conn.execute(f'PRAGMA table_info("{t}")')]
        if cols and 'src_file' not in cols:
            try:
                conn.execute(f'ALTER TABLE "{t}" ADD COLUMN src_file TEXT')
            except sqlite3.OperationalError:
                pass
    try:
        logs = conn.execute('SELECT * FROM import_log ORDER BY id').fetchall()
        for lg in logs:
            t = SCHEMA_BACKFILL.get(lg['schema_name'])
            n = lg['rows_inserted'] or lg['rows_read'] or 0
            if not t or not n:
                continue
            conn.execute(f'UPDATE "{t}" SET src_file=? WHERE src_file IS NULL AND rowid IN '
                         f'(SELECT rowid FROM "{t}" WHERE src_file IS NULL LIMIT ?)',
                         (lg['filename'], n))
    except sqlite3.OperationalError:
        pass
    set_meta(conn, 'srcfile_v1', '1')
    conn.commit()


def ensure_schema(conn):
    conn.executescript(DDL)
    _migrate_src_file(conn)   # ابتدا ستون src_file به جدول‌های قدیمی اضافه شود
    conn.executescript(INDEXES)
    conn.commit()


def set_meta(conn, key, value):
    conn.execute('INSERT INTO meta(key, value) VALUES(?, ?) '
                 'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))


def get_meta(conn, key, default=None):
    row = conn.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default
