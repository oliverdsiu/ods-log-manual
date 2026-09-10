#!/usr/bin/env python3
"""
init_db.py — sample database generator for the OdsLog manual.

Reads equipment_catalog.csv and generates a realistic sample SQLite
database for screenshots and the downloadable sample data. Re-running
this script resets the database completely.

Usage : python init_db.py
Output: sample.db in this directory
"""

import sqlite3
import csv
import calendar
import os
import re
import random
from datetime import date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "sample.db")
CSV_PATH   = os.path.join(SCRIPT_DIR, "equipment_catalog.csv")
TODAY      = date.today()
SIM_START  = date(2015, 1, 1)

CONSUMER_COLORS     = ["White", "Silver", "Charcoal", "Dark Blue", "Black", "Maroon", "Dark Green"]
CONSUMER_ROAD_TYPES = {"Pickup Truck", "Pickup Truck (Diesel)", "Van", "Car", "Mini Truck"}
ROAD_TYPES          = {
    "Pickup Truck", "Pickup Truck (Diesel)", "Van", "Car",
    "Flatbed Truck", "Dump Truck", "Water Truck", "Mini Truck",
}
BOUGHT_NEW = {
    "Car", "Welder", "Generator",
    "Trimmer", "Blower", "Chainsaw", "Push Mower", "Pressure Washer", "Air Compressor",
}

ANNUAL_USAGE_RATE = {
    "Tractor":               ( 300,   600),
    "Backhoe Loader":        ( 500,  1200),
    "Skid Steer":            ( 400,   900),
    "Excavator":             ( 500,  1200),
    "Backhoe":               ( 400,   900),
    "Dozer":                 ( 500,  1200),
    "Forklift":              ( 300,   600),
    "Wood Chipper":          ( 100,   300),
    "Generator":             ( 100,   300),
    "Welder":                ( 150,   400),
    "Boom Lift":             ( 200,   600),
    "Pickup Truck":          (8000, 18000),
    "Pickup Truck (Diesel)": (10000,20000),
    "Van":                   (8000, 15000),
    "Car":                   (8000, 15000),
    "Flatbed Truck":         (10000,25000),
    "Dump Truck":            (10000,25000),
    "Water Truck":           (8000, 20000),
    "Mini Truck":            (5000, 12000),
}

USED_START_USAGE = {
    "Tractor":               (  500,  4000),
    "Backhoe Loader":        ( 1000,  5000),
    "Skid Steer":            (  500,  3000),
    "Excavator":             ( 1000,  5000),
    "Backhoe":               (  500,  3000),
    "Dozer":                 ( 1000,  6000),
    "Forklift":              (  500,  3000),
    "Wood Chipper":          (  100,  1500),
    "Boom Lift":             (  500,  3000),
    "Pickup Truck":          (30000,120000),
    "Pickup Truck (Diesel)": (40000,150000),
    "Van":                   (40000,120000),
    "Flatbed Truck":         (60000,200000),
    "Dump Truck":            (80000,250000),
    "Water Truck":           (60000,200000),
    "Mini Truck":            (20000, 80000),
}

PURCHASE_PRICE_MAP = {
    "Tractor":               (15000,  80000),
    "Backhoe Loader":        (40000, 120000),
    "Skid Steer":            (25000,  60000),
    "Excavator":             (40000, 150000),
    "Backhoe":               (30000,  90000),
    "Dozer":                 (60000, 200000),
    "Forklift":              (15000,  50000),
    "Wood Chipper":          ( 3000,  15000),
    "Generator":             ( 1000,   8000),
    "Welder":                (  500,   3000),
    "Trimmer":               (  200,    600),
    "Blower":                (  150,    500),
    "Chainsaw":              (  200,    800),
    "Push Mower":            (  300,   1200),
    "Pressure Washer":       (  200,    800),
    "Air Compressor":        (  300,   1500),
    "Pickup Truck":          (15000,  45000),
    "Pickup Truck (Diesel)": (25000,  65000),
    "Van":                   (20000,  50000),
    "Car":                   (10000,  35000),
    "Flatbed Truck":         (30000,  80000),
    "Dump Truck":            (40000, 120000),
    "Water Truck":           (25000,  70000),
    "Mini Truck":            ( 3000,  12000),
    "Boom Lift":             (15000,  60000),
}

# Cost range (lo, hi) per service type id, in-house rates (USD)
# st_id: 1=Engine Oil, 2=Hydraulic Oil, 3=Fuel Filter, 4=Air Filter, 5=Tire Rotation,
#        6=Annual Inspection, 7=Grease, 8=Spark Plug, 9=Coolant Flush, 10=Transmission
SERVICE_COST = {
    1:  ( 60,  180),
    2:  (150,  350),
    3:  ( 40,  120),
    4:  ( 30,  100),
    5:  ( 40,  100),
    6:  (200,  500),
    7:  ( 25,   80),
    8:  ( 40,  120),
    9:  (100,  250),
    10: (300,  650),
}

SPECIALIST_TYPE_IDS = {2, 6, 9, 10}

# Usage type per asset type. None = no meter (time-only service, no odometer).
USAGE_TYPE_MAP = {
    "Tractor":               "Hours",
    "Backhoe Loader":        "Hours",
    "Skid Steer":            "Hours",
    "Excavator":             "Hours",
    "Backhoe":               "Hours",
    "Dozer":                 "Hours",
    "Forklift":              "Hours",
    "Wood Chipper":          "Hours",
    "Generator":             "Hours",
    "Welder":                "Hours",
    "Trimmer":               None,
    "Blower":                None,
    "Chainsaw":              None,
    "Push Mower":            None,
    "Pressure Washer":       None,
    "Air Compressor":        None,
    "Pickup Truck":          "Miles",
    "Pickup Truck (Diesel)": "Miles",
    "Van":                   "Miles",
    "Car":                   "Miles",
    "Flatbed Truck":         "Miles",
    "Dump Truck":            "Miles",
    "Water Truck":           "Miles",
    "Mini Truck":            "Kilometers",
    "Boom Lift":             "Hours",
}

# Template rules: (st_id, asset_type_name, usage_interval, time_interval, time_type,
#                  usage_reminder, time_reminder)
# usage_interval is in the asset type's native usage unit (hr / mi / km).
# time_interval is in the unit specified by time_type (Days or Months).
TEMPLATE_RULES = [
    # ── TRACTOR (JD 5000-series PM spec) ────────────────────────────────
    (1,  "Tractor",  250.0, 12, "Months",  25,   7),
    (2,  "Tractor",  500.0, 24, "Months",  50,  14),
    (3,  "Tractor",  500.0, None, None,    50, None),
    (4,  "Tractor",  250.0, None, None,    25, None),
    (6,  "Tractor",  None,  12, "Months", None,   7),
    (7,  "Tractor",   50.0, None, None,    10, None),
    (9,  "Tractor",  None,  24, "Months", None,  14),
    (10, "Tractor",  500.0, 24, "Months",  50,  14),

    # ── BACKHOE LOADER (Cat spec) ────────────────────────────────────────
    (1,  "Backhoe Loader",  250.0, 12, "Months",  25,   7),
    (2,  "Backhoe Loader",  500.0, 24, "Months",  50,  14),
    (4,  "Backhoe Loader",  250.0, None, None,    25, None),
    (6,  "Backhoe Loader",  None,  12, "Months", None,   7),
    (7,  "Backhoe Loader",   50.0, None, None,    10, None),
    (9,  "Backhoe Loader",  None,  24, "Months", None,  14),

    # ── SKID STEER ───────────────────────────────────────────────────────
    (1,  "Skid Steer",  250.0, 12, "Months",  25,   7),
    (2,  "Skid Steer",  500.0, 24, "Months",  50,  14),
    (4,  "Skid Steer",  250.0, None, None,    25, None),
    (6,  "Skid Steer",  None,  12, "Months", None,   7),
    (7,  "Skid Steer",   50.0, None, None,    10, None),
    (9,  "Skid Steer",  None,  24, "Months", None,  14),

    # ── EXCAVATOR ────────────────────────────────────────────────────────
    (1,  "Excavator",  250.0, 12, "Months",  25,   7),
    (2,  "Excavator",  500.0, 24, "Months",  50,  14),
    (4,  "Excavator",  250.0, None, None,    25, None),
    (6,  "Excavator",  None,  12, "Months", None,   7),
    (7,  "Excavator",   50.0, None, None,    10, None),
    (9,  "Excavator",  None,  24, "Months", None,  14),

    # ── BACKHOE ──────────────────────────────────────────────────────────
    (1,  "Backhoe",  250.0, 12, "Months",  25,   7),
    (2,  "Backhoe",  500.0, 24, "Months",  50,  14),
    (4,  "Backhoe",  250.0, None, None,    25, None),
    (6,  "Backhoe",  None,  12, "Months", None,   7),
    (7,  "Backhoe",   50.0, None, None,    10, None),
    (9,  "Backhoe",  None,  24, "Months", None,  14),

    # ── DOZER (Cat D4/D6 PM schedule) ───────────────────────────────────
    (1,  "Dozer",  250.0, 12, "Months",  25,   7),
    (2,  "Dozer",  500.0, 24, "Months",  50,  14),
    (4,  "Dozer",  250.0, None, None,    25, None),
    (6,  "Dozer",  None,  12, "Months", None,   7),
    (7,  "Dozer",   50.0, None, None,    10, None),
    (9,  "Dozer",  None,  24, "Months", None,  14),

    # ── FORKLIFT ─────────────────────────────────────────────────────────
    (1,  "Forklift",  250.0, 12, "Months",  25,   7),
    (2,  "Forklift",  500.0, 24, "Months",  50,  14),
    (4,  "Forklift",  250.0, None, None,    25, None),
    (6,  "Forklift",  None,  12, "Months", None,   7),
    (7,  "Forklift",   50.0, None, None,    10, None),
    (9,  "Forklift",  None,  24, "Months", None,  14),

    # ── GENERATOR (air-cooled — Honda EM5000/Multiquip) ─────────────────
    (1,  "Generator",  100.0,  6, "Months",  15,   7),
    (3,  "Generator",  200.0, None, None,    25, None),
    (4,  "Generator",  100.0,  6, "Months",  15,   7),
    (6,  "Generator",  None,  12, "Months", None,   7),
    (8,  "Generator",  300.0, 12, "Months",  25,   7),

    # ── WOOD CHIPPER ─────────────────────────────────────────────────────
    (1,  "Wood Chipper",  100.0, 12, "Months",  15,   7),
    (4,  "Wood Chipper",  200.0, None, None,    25, None),
    (6,  "Wood Chipper",  None,  12, "Months", None,   7),
    (7,  "Wood Chipper",  100.0, None, None,    10, None),

    # ── WELDER (engine-driven) ───────────────────────────────────────────
    (1,  "Welder",  100.0, 12, "Months",  15,   7),
    (4,  "Welder",  200.0, None, None,    25, None),
    (6,  "Welder",  None,  12, "Months", None,   7),
    (8,  "Welder",  200.0, 12, "Months",  25,   7),

    # ── NO-METER TYPES (time-only) ───────────────────────────────────────
    (4,  "Trimmer",  None, 12, "Months", None, 7),
    (6,  "Trimmer",  None, 12, "Months", None, 7),
    (8,  "Trimmer",  None, 12, "Months", None, 7),

    (6,  "Blower",  None, 12, "Months", None, 7),
    (8,  "Blower",  None, 12, "Months", None, 7),

    (6,  "Chainsaw",  None, 12, "Months", None, 7),
    (8,  "Chainsaw",  None, 12, "Months", None, 7),

    (1,  "Push Mower",  None, 12, "Months", None, 7),
    (6,  "Push Mower",  None, 12, "Months", None, 7),
    (8,  "Push Mower",  None, 12, "Months", None, 7),

    (1,  "Pressure Washer",  None, 12, "Months", None, 7),
    (6,  "Pressure Washer",  None, 12, "Months", None, 7),
    (8,  "Pressure Washer",  None, 12, "Months", None, 7),

    (4,  "Air Compressor",  None, 12, "Months", None, 7),
    (6,  "Air Compressor",  None, 12, "Months", None, 7),

    # ── PICKUP TRUCK (gasoline) ──────────────────────────────────────────
    (1,  "Pickup Truck",   5000.0,  6, "Months",  300,  14),
    (4,  "Pickup Truck",  30000.0, None, None,   1000, None),
    (5,  "Pickup Truck",   7500.0,  6, "Months",  300,  14),
    (6,  "Pickup Truck",   None,   12, "Months", None,   7),
    (8,  "Pickup Truck",  30000.0, None, None,   1000, None),
    (9,  "Pickup Truck",   None,   60, "Months", None,  14),
    (10, "Pickup Truck",  40000.0, 24, "Months", 1000,  30),

    # ── PICKUP TRUCK (diesel) — no spark plugs ───────────────────────────
    (1,  "Pickup Truck (Diesel)",   7500.0, 12, "Months",  500,  14),
    (3,  "Pickup Truck (Diesel)",  15000.0, None, None,   1000, None),
    (4,  "Pickup Truck (Diesel)",  30000.0, 12, "Months", 2000,  14),
    (5,  "Pickup Truck (Diesel)",   7500.0,  6, "Months",  500,  14),
    (6,  "Pickup Truck (Diesel)",   None,   12, "Months", None,   7),
    (9,  "Pickup Truck (Diesel)",   None,   60, "Months", None,  14),
    (10, "Pickup Truck (Diesel)",  60000.0, 24, "Months", 5000,  30),

    # ── VAN ──────────────────────────────────────────────────────────────
    (1,  "Van",   5000.0,  6, "Months",  300,  14),
    (4,  "Van",  30000.0, None, None,   1000, None),
    (5,  "Van",   7500.0,  6, "Months",  300,  14),
    (6,  "Van",   None,   12, "Months", None,   7),
    (8,  "Van",  30000.0, None, None,   1000, None),
    (9,  "Van",   None,   60, "Months", None,  14),

    # ── CAR ──────────────────────────────────────────────────────────────
    (1,  "Car",   5000.0,  6, "Months",  300,  14),
    (4,  "Car",  30000.0, None, None,   1000, None),
    (5,  "Car",   7500.0,  6, "Months",  300,  14),
    (6,  "Car",   None,   12, "Months", None,   7),
    (8,  "Car",  30000.0, None, None,   1000, None),
    (9,  "Car",   None,   60, "Months", None,  14),

    # ── HEAVY TRUCKS (diesel) ────────────────────────────────────────────
    (1,  "Flatbed Truck",   7500.0, 12, "Months",  500,  14),
    (3,  "Flatbed Truck",  15000.0, None, None,   1000, None),
    (4,  "Flatbed Truck",  30000.0, 12, "Months", 2000,  14),
    (5,  "Flatbed Truck",  10000.0,  6, "Months",  500,  14),
    (6,  "Flatbed Truck",   None,   12, "Months", None,   7),
    (9,  "Flatbed Truck",   None,   24, "Months", None,  14),
    (10, "Flatbed Truck",  50000.0, 24, "Months", 3000,  30),

    (1,  "Dump Truck",   7500.0, 12, "Months",  500,  14),
    (3,  "Dump Truck",  15000.0, None, None,   1000, None),
    (4,  "Dump Truck",  30000.0, 12, "Months", 2000,  14),
    (5,  "Dump Truck",  10000.0,  6, "Months",  500,  14),
    (6,  "Dump Truck",   None,   12, "Months", None,   7),
    (9,  "Dump Truck",   None,   24, "Months", None,  14),
    (10, "Dump Truck",  50000.0, 24, "Months", 3000,  30),

    (1,  "Water Truck",   7500.0, 12, "Months",  500,  14),
    (3,  "Water Truck",  15000.0, None, None,   1000, None),
    (4,  "Water Truck",  30000.0, 12, "Months", 2000,  14),
    (5,  "Water Truck",  10000.0,  6, "Months",  500,  14),
    (6,  "Water Truck",   None,   12, "Months", None,   7),
    (9,  "Water Truck",   None,   24, "Months", None,  14),

    # ── MINI TRUCK (kei — km odometer) ──────────────────────────────────
    (1,  "Mini Truck",   5000.0,  6, "Months",  200,  14),
    (4,  "Mini Truck",  15000.0, None, None,    500, None),
    (5,  "Mini Truck",   8000.0, None, None,    200, None),
    (6,  "Mini Truck",   None,   12, "Months", None,   7),
    (9,  "Mini Truck",   None,   24, "Months", None,  14),

    # ── BOOM LIFT (Genie Z-34/22 — diesel/propane dual fuel) ────────────
    (1,  "Boom Lift",  250.0, 12, "Months",  25,   7),
    (2,  "Boom Lift",  500.0, 24, "Months",  50,  14),
    (4,  "Boom Lift",  250.0, None, None,    25, None),
    (6,  "Boom Lift",  None,  12, "Months", None,   7),
    (7,  "Boom Lift",   50.0, None, None,    10, None),
    (9,  "Boom Lift",  None,  24, "Months", None,  14),
]

FUEL_ECONOMY = {
    "Tractor":               ( 35, 15, "Diesel"),
    "Backhoe Loader":        ( 45, 18, "Diesel"),
    "Skid Steer":            ( 45, 10, "Diesel"),
    "Excavator":             ( 35, 18, "Diesel"),
    "Backhoe":               ( 45, 16, "Diesel"),
    "Dozer":                 ( 30, 20, "Diesel"),
    "Forklift":              ( 75, 12, "Propane"),
    "Wood Chipper":          ( 55, 12, "Gasoline"),
    "Generator":             (100,  8, "Gasoline"),
    "Welder":                ( 80,  8, "Gasoline"),
    "Boom Lift":             ( 90, 10, "Diesel"),
    "Pickup Truck":          (210, 15, "Gasoline"),
    "Pickup Truck (Diesel)": (270, 15, "Diesel"),
    "Van":                   (240, 16, "Gasoline"),
    "Car":                   (250, 11, "Gasoline"),
    "Flatbed Truck":         (280, 35, "Diesel"),
    "Dump Truck":            (245, 35, "Diesel"),
    "Water Truck":           (245, 35, "Diesel"),
    "Mini Truck":            (480, 28, "Gasoline"),
}


# ─── Schema ───────────────────────────────────────────────────────────────────

def create_schema(conn):
    conn.executescript("""
        CREATE TABLE metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE asset_types (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            usage_type TEXT,
            status     TEXT NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE assets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT    NOT NULL,
            make           TEXT,
            model          TEXT,
            year           INTEGER,
            asset_type_id  INTEGER NOT NULL REFERENCES asset_types(id),
            fuel_type      TEXT,
            color          TEXT,
            current_usage  REAL    NOT NULL DEFAULT 0,
            status         TEXT    NOT NULL DEFAULT 'Active',
            notes          TEXT,
            created_at     DATE    NOT NULL,
            serial_number  TEXT,
            license_plate  TEXT,
            purchase_date  DATE,
            purchase_price REAL
        );

        CREATE TABLE asset_retirements (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id      INTEGER NOT NULL REFERENCES assets(id),
            retire_date   DATE    NOT NULL,
            retire_price  REAL,
            retire_reason TEXT,
            retire_notes  TEXT,
            status        TEXT    NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE service_types (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE asset_type_templates (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type_id       INTEGER NOT NULL REFERENCES asset_types(id),
            service_type_id INTEGER NOT NULL REFERENCES service_types(id),
            usage_interval      REAL,
            time_interval       REAL,
            time_type           TEXT,
            usage_reminder      REAL,
            time_reminder       INTEGER,
            notes               TEXT,
            status              TEXT NOT NULL DEFAULT 'Active',
            UNIQUE (asset_type_id, service_type_id)
        );

        CREATE TABLE asset_schedule (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id            INTEGER NOT NULL REFERENCES assets(id),
            service_type_id INTEGER NOT NULL REFERENCES service_types(id),
            usage_interval      REAL,
            time_interval       REAL,
            time_type           TEXT,
            usage_reminder      REAL,
            time_reminder       INTEGER,
            last_done_date      DATE,
            last_done_usage     REAL,
            next_due_date       DATE,
            next_due_usage      REAL,
            notes               TEXT,
            status              TEXT NOT NULL DEFAULT 'Active',
            UNIQUE (asset_id, service_type_id)
        );

        CREATE TABLE companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            is_internal INTEGER NOT NULL DEFAULT 0,
            status      TEXT    NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE technicians (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT,
            middle_name TEXT,
            last_name   TEXT,
            company_id  INTEGER REFERENCES companies(id),
            status      TEXT    NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE service_logs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id            INTEGER NOT NULL REFERENCES assets(id),
            service_type_id INTEGER NOT NULL REFERENCES service_types(id),
            date                DATE    NOT NULL,
            usage_at_service    REAL,
            cost                REAL,
            currency            TEXT    NOT NULL DEFAULT 'USD',
            company_id          INTEGER NOT NULL REFERENCES companies(id),
            technician_id       INTEGER          REFERENCES technicians(id),
            notes               TEXT,
            status              TEXT    NOT NULL DEFAULT 'Active'
        );

        CREATE TABLE usage_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id    INTEGER NOT NULL REFERENCES assets(id),
            date        DATE    NOT NULL,
            odometer    REAL,
            fuel_amount REAL,
            fuel_unit   TEXT,
            fuel_type   TEXT,
            fuel_cost   REAL,
            currency    TEXT    NOT NULL DEFAULT 'USD',
            notes       TEXT,
            status      TEXT    NOT NULL DEFAULT 'Active'
        );

        CREATE INDEX idx_logs_asset      ON service_logs(asset_id);
        CREATE INDEX idx_logs_service_type      ON service_logs(service_type_id);
        CREATE INDEX idx_logs_company    ON service_logs(company_id);
        CREATE INDEX idx_logs_technician ON service_logs(technician_id);
        CREATE INDEX idx_logs_date       ON service_logs(date);
        CREATE INDEX idx_sched_asset     ON asset_schedule(asset_id);
    """)
    conn.commit()


# ─── Seed: metadata ───────────────────────────────────────────────────────────

def seed_metadata(conn):
    conn.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("company_name",                 "Sample Farm LLC"),
        ("schema_version",               "1.0"),
        ("app_version",                  "1.0"),
        ("created_at",                   str(TODAY)),
        ("due_soon_threshold_pct",       "10"),
        ("default_currency",             "USD"),
        ("default_fuel_unit",            "Gallons"),
        ("clear_archived_logs_on_close", "false"),
        ("fiscal_year_start",            "01-01"),
    ])
    conn.commit()


# ─── Seed: companies ──────────────────────────────────────────────────────────

def seed_companies(conn):
    conn.executemany(
        "INSERT INTO companies (name, is_internal) VALUES (?,?)",
        [
            ("In-House",                   1),
            ("Northside Auto",             0),
            ("Hilltop Repair",             0),
            ("Eastside Equipment Service", 0),
            ("Route 9 Shop",               0),
        ],
    )
    conn.commit()


# ─── Seed: technicians ────────────────────────────────────────────────────────

def seed_technicians(conn):
    def co(name):
        return conn.execute("SELECT id FROM companies WHERE name=?", (name,)).fetchone()[0]

    conn.executemany(
        "INSERT INTO technicians (first_name, middle_name, last_name, company_id) VALUES (?,?,?,?)",
        [
            ("John",   "D",    "Mechanic",   co("In-House")),
            ("Jack",   "Hass", "Wrench",     co("In-House")),
            ("Phil",   "Ter",  "Pak",        co("In-House")),
            ("Al",     "T",    "Nator",      co("In-House")),
            ("Otto",   None,   "Fix",        co("In-House")),
            ("Tyrese", "D",    "Grease",     co("In-House")),
            ("John",   None,   "Smith",      co("Northside Auto")),
            ("Jane",   None,   "Doe",        co("Northside Auto")),
            ("Bob",    None,   "Tech",       co("Hilltop Repair")),
            ("Amy",    None,   "Repair",     co("Hilltop Repair")),
            ("Joe",    None,   "Technician", co("Eastside Equipment Service")),
            ("Lisa",   None,   "Technician", co("Eastside Equipment Service")),
            ("Tom",    None,   "Fix",        co("Route 9 Shop")),
            ("Sue",    None,   "Wrench",     co("Route 9 Shop")),
        ],
    )
    conn.commit()


# ─── Seed: asset types ────────────────────────────────────────────────────────

def seed_asset_types(conn):
    """Populate asset_types from USAGE_TYPE_MAP. None = no meter (stored as NULL)."""
    conn.executemany(
        "INSERT INTO asset_types (name, usage_type, status) VALUES (?,?,?)",
        [(name, utype, "Active") for name, utype in USAGE_TYPE_MAP.items()],
    )
    conn.commit()


# ─── Seed: assets (from CSV) ──────────────────────────────────────────────────

def _short_model(model):
    return re.sub(r'\s+Gen\s+\d+$', '', model).strip()


def seed_assets(conn, rng):
    type_ids = dict(conn.execute("SELECT name, id FROM asset_types").fetchall())

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    model_totals = {}
    for row in rows:
        if row["equipment_type"].strip() in CONSUMER_ROAD_TYPES:
            short = _short_model(row["model"].strip())
            model_totals[short] = model_totals.get(short, 0) + int(row["quantity"])

    model_counters = {}

    for row in rows:
        make       = row["make"].strip()
        model      = row["model"].strip()
        asset_type = row["equipment_type"].strip()
        quantity   = int(row["quantity"])
        yr_start   = int(row["year_start"])
        yr_end     = int(row["year_end"])
        color_csv  = row["color"].strip()
        fuel_type  = row["fuel_type"].strip()
        usage_type = USAGE_TYPE_MAP.get(asset_type)
        is_new     = asset_type in BOUGHT_NEW

        for i in range(1, quantity + 1):
            year  = rng.randint(yr_start, yr_end)
            color = color_csv if color_csv else rng.choice(CONSUMER_COLORS)

            if asset_type in CONSUMER_ROAD_TYPES:
                short = _short_model(model)
                model_counters[short] = model_counters.get(short, 0) + 1
                n = model_counters[short]
                name = (f"{color} {short} {n}"
                        if model_totals[short] > 1 else f"{color} {short}")
            else:
                name = f"{model} #{i}" if quantity > 1 else f"{make} {model}"

            if is_new:
                purchase_date = date(year, 1, 1) + timedelta(days=rng.randint(0, 240))
            else:
                buy_year  = min(year + rng.randint(1, 6), TODAY.year - 1)
                buy_month = rng.randint(1, 12)
                buy_day   = rng.randint(1, 28)
                purchase_date = date(buy_year, buy_month, buy_day)
                purchase_date = min(purchase_date, TODAY - timedelta(days=365))

            created_at = max(purchase_date, SIM_START)

            if usage_type is None:  # no meter
                purchase_usage = 0.0
            elif is_new:
                if usage_type == "Miles":
                    purchase_usage = float(rng.randint(5, 20))
                elif usage_type == "Kilometers":
                    purchase_usage = float(rng.randint(8, 30))
                else:
                    purchase_usage = round(rng.uniform(0.0, 2.0), 1)
            else:
                lo, hi = USED_START_USAGE.get(asset_type, (100, 1000))
                purchase_usage = round(rng.uniform(lo, hi), 1)

            if usage_type is None:
                current_usage = 0.0
            else:
                days_owned    = max(1, (TODAY - purchase_date).days)
                lo_r, hi_r   = ANNUAL_USAGE_RATE.get(asset_type, (200, 800))
                accumulated   = rng.uniform(lo_r, hi_r) * (days_owned / 365)
                raw           = purchase_usage + accumulated
                current_usage = (round(raw, 1) if usage_type == "Hours" else round(raw))

            lo, hi = PURCHASE_PRICE_MAP.get(asset_type, (500, 5000))
            purchase_price = int(rng.uniform(lo, hi) / 100) * 100

            hex_chars     = "0123456789ABCDEF"
            serial_number = "SIM-" + "".join(rng.choice(hex_chars) for _ in range(6))
            license_plate = f"SIM-{rng.randint(1000, 9999)}" if asset_type in ROAD_TYPES else None

            conn.execute(
                "INSERT INTO assets "
                "(name, make, model, year, asset_type_id, fuel_type, color, "
                " current_usage, status, notes, created_at, "
                " serial_number, license_plate, purchase_date, purchase_price) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (name, make, model, year, type_ids[asset_type], fuel_type, color,
                 current_usage, "Active", None, str(created_at),
                 serial_number, license_plate, str(purchase_date), purchase_price),
            )

    conn.commit()


# ─── Seed: service types ──────────────────────────────────────────────────────

def seed_service_types(conn):
    conn.executemany(
        "INSERT INTO service_types (name) VALUES (?)",
        [
            ("Engine Oil & Filter",),     # id=1
            ("Hydraulic Oil & Filter",),  # id=2
            ("Fuel Filter",),             # id=3
            ("Air Filter - Primary",),    # id=4
            ("Tire Rotation",),           # id=5
            ("Annual Inspection",),       # id=6
            ("Grease All Fittings",),     # id=7
            ("Spark Plug",),              # id=8
            ("Coolant Flush",),           # id=9
            ("Transmission Service",),    # id=10
        ],
    )
    conn.commit()


# ─── Seed: asset type templates ───────────────────────────────────────────────

def seed_asset_type_templates(conn):
    """Populate asset_type_templates from TEMPLATE_RULES, resolving type names to IDs."""
    type_ids = dict(conn.execute("SELECT name, id FROM asset_types").fetchall())
    conn.executemany(
        "INSERT INTO asset_type_templates "
        "(service_type_id, asset_type_id, usage_interval, time_interval, time_type, "
        " usage_reminder, time_reminder) "
        "VALUES (?,?,?,?,?,?,?)",
        [(st_id, type_ids[atype], ui, ti, tt, ur, tr)
         for st_id, atype, ui, ti, tt, ur, tr in TEMPLATE_RULES],
    )
    conn.commit()


# ─── Seed: per-asset schedules ────────────────────────────────────────────────

def seed_asset_schedules(conn):
    """Copy asset_type_templates → asset_schedule for every active asset.
    last_done / next_due fields are NULL until seed_logs() runs."""
    assets = conn.execute(
        "SELECT id, asset_type_id FROM assets WHERE status='Active'"
    ).fetchall()
    for asset_id, asset_type_id in assets:
        templates = conn.execute(
            "SELECT service_type_id, usage_interval, time_interval, time_type, "
            "       usage_reminder, time_reminder "
            "FROM asset_type_templates "
            "WHERE asset_type_id=? AND status='Active'",
            (asset_type_id,),
        ).fetchall()
        for tmpl in templates:
            conn.execute(
                "INSERT INTO asset_schedule "
                "(asset_id, service_type_id, usage_interval, time_interval, time_type, "
                " usage_reminder, time_reminder) "
                "VALUES (?,?,?,?,?,?,?)",
                (asset_id,) + tmpl,
            )
    conn.commit()


# ─── Date helpers ─────────────────────────────────────────────────────────────

def _add_months(d, n):
    m = d.month + n
    y = d.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def _date_add(d, unit, n):
    if unit == "Months":
        return _add_months(d, int(n))
    return d + timedelta(days=int(n))


# ─── Log + schedule update ────────────────────────────────────────────────────

def _record(conn, asset_id, service_type_id, service_date,
            usage_at_service, cost, notes,
            company_id=None, technician_id=None, currency="USD"):
    """Insert a service log and update the asset_schedule row."""
    conn.execute(
        "INSERT INTO service_logs "
        "(asset_id, service_type_id, date, usage_at_service, cost, "
        " currency, company_id, technician_id, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (asset_id, service_type_id, str(service_date),
         usage_at_service, cost, currency, company_id, technician_id, notes),
    )
    sched = conn.execute(
        "SELECT usage_interval, time_interval, time_type "
        "FROM asset_schedule WHERE asset_id=? AND service_type_id=?",
        (asset_id, service_type_id),
    ).fetchone()

    if sched:
        usage_interval, time_interval, time_type = sched
    else:
        usage_interval = time_interval = time_type = None

    next_due_usage = (
        (usage_at_service + usage_interval)
        if (usage_interval is not None and usage_at_service is not None)
        else None
    )
    next_due_date = (
        str(_date_add(service_date, time_type, time_interval))
        if time_interval is not None
        else None
    )

    conn.execute(
        "UPDATE asset_schedule "
        "SET last_done_date=?, last_done_usage=?, next_due_date=?, next_due_usage=? "
        "WHERE asset_id=? AND service_type_id=?",
        (str(service_date), usage_at_service, next_due_date, next_due_usage,
         asset_id, service_type_id),
    )


# ─── Seed: usage logs ────────────────────────────────────────────────────────

def seed_usage_logs(conn, rng):
    """Generate fuel fill and odometer history for metered assets."""
    default_fuel_unit = conn.execute(
        "SELECT value FROM metadata WHERE key='default_fuel_unit'"
    ).fetchone()[0]
    default_currency = conn.execute(
        "SELECT value FROM metadata WHERE key='default_currency'"
    ).fetchone()[0]

    fleet = conn.execute(
        "SELECT a.id, at.name AS type, at.usage_type, a.current_usage, "
        "       a.purchase_date, a.fuel_type "
        "FROM assets a JOIN asset_types at ON at.id = a.asset_type_id "
        "WHERE a.status='Active'"
    ).fetchall()

    for asset_id, asset_type, usage_type, current_usage, purchase_date_str, asset_fuel_type in fleet:
        if usage_type is None:  # no meter — skip
            continue
        if current_usage == 0:
            continue

        econ = FUEL_ECONOMY.get(asset_type)
        if not econ:
            continue
        fill_interval, fill_amount, default_fill_fuel = econ

        purchase_date  = date.fromisoformat(purchase_date_str)
        first_log_date = max(purchase_date, SIM_START)
        cutoff_date    = max(first_log_date, TODAY - timedelta(days=365))

        lo_r, hi_r = ANNUAL_USAGE_RATE.get(asset_type, (200, 500))
        daily_rate  = max(0.1, rng.uniform(lo_r, hi_r) / 365)

        odo = current_usage
        while True:
            odo -= fill_interval * rng.uniform(0.80, 1.20)
            if odo <= 0:
                break
            days_back = int((current_usage - odo) / daily_rate)
            fill_date = TODAY - timedelta(days=days_back)
            if fill_date < cutoff_date:
                break

            if asset_fuel_type and '/' in asset_fuel_type:
                fill_fuel = rng.choice([f.strip() for f in asset_fuel_type.split('/')])
            else:
                fill_fuel = default_fill_fuel

            amount = round(fill_amount * rng.uniform(0.80, 1.10), 1)

            if asset_type == "Mini Truck":
                fuel_unit = "Liters"
                fuel_cost = round(amount * rng.uniform(160, 185), 0)
                currency  = "JPY"
            else:
                fuel_unit = default_fuel_unit
                price = {
                    "Diesel":   rng.uniform(3.50, 5.00),
                    "Propane":  rng.uniform(2.50, 4.00),
                    "Gasoline": rng.uniform(3.20, 4.80),
                }.get(fill_fuel, rng.uniform(3.20, 4.80))
                fuel_cost = round(amount * price, 2)
                currency  = default_currency

            entry_odo    = None if rng.random() < 0.08 else round(odo, 1)
            lost_receipt = rng.random() < 0.03
            entry_amount = None if lost_receipt else amount
            entry_cost   = None if lost_receipt else fuel_cost

            conn.execute(
                "INSERT INTO usage_logs "
                "(asset_id, date, odometer, fuel_amount, fuel_unit, fuel_type, fuel_cost, currency) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (asset_id, str(fill_date), entry_odo,
                 entry_amount, fuel_unit, fill_fuel, entry_cost, currency),
            )

    conn.commit()


# ─── Seed: service logs ────────────────────────────────────────────────────────

def seed_logs(conn, rng, tech_rng):
    """
    Generate service history for every active asset.

    Log dates are derived by linearly interpolating between
    (first_log_date, min_log_usage) → (TODAY, current_usage).

    Last-service position drawn from Beta(3,5) × 1.25 — right-skewed, peaks near
    35% of interval, thin tail past 1.0. Per-item overdue rate ≈ 3%, compounding
    to ~5% of assets overdue and ~18% due-soon, ~77% healthy.

    Dual-trigger rules (usage AND time): apply Beta independently to each dimension,
    take whichever gives the more recent service (max usage wins = closer to today).
    """
    fleet = conn.execute(
        "SELECT a.id, at.name AS type, at.usage_type, a.current_usage, a.purchase_date "
        "FROM assets a JOIN asset_types at ON at.id = a.asset_type_id "
        "WHERE a.status='Active'"
    ).fetchall()

    in_house_co_id = conn.execute(
        "SELECT id FROM companies WHERE is_internal=1"
    ).fetchone()[0]
    in_house_techs = [r[0] for r in conn.execute(
        "SELECT id FROM technicians WHERE company_id=?", (in_house_co_id,)
    ).fetchall()]
    shop_entries = [(r[0], r[1]) for r in conn.execute("""
        SELECT t.company_id, t.id FROM technicians t
        JOIN companies c ON c.id = t.company_id
        WHERE c.is_internal = 0 ORDER BY t.company_id, t.id
    """).fetchall()]

    # st_ids to seed per asset type — must match TEMPLATE_RULES
    hour_based_types = {
        "Tractor":         [1, 2, 3, 4, 6, 7, 9, 10],
        "Backhoe Loader":  [1, 2, 4, 6, 7, 9],
        "Skid Steer":      [1, 2, 4, 6, 7, 9],
        "Excavator":       [1, 2, 4, 6, 7, 9],
        "Backhoe":         [1, 2, 4, 6, 7, 9],
        "Dozer":           [1, 2, 4, 6, 7, 9],
        "Forklift":        [1, 2, 4, 6, 7, 9],
        "Generator":       [1, 3, 4, 6, 8],
        "Wood Chipper":    [1, 4, 6, 7],
        "Welder":          [1, 4, 6, 8],
        "Trimmer":         [4, 6, 8],
        "Blower":          [6, 8],
        "Chainsaw":        [6, 8],
        "Push Mower":      [1, 6, 8],
        "Pressure Washer": [1, 6, 8],
        "Air Compressor":  [4, 6],
        "Boom Lift":       [1, 2, 6, 7, 9],
    }
    road_based_types = {
        "Pickup Truck":          [1, 4, 5, 6, 8, 9, 10],
        "Pickup Truck (Diesel)": [1, 3, 4, 5, 6, 9, 10],
        "Van":                   [1, 4, 5, 6, 8, 9],
        "Car":                   [1, 4, 5, 6, 8, 9],
        "Flatbed Truck":         [1, 3, 4, 5, 6, 9, 10],
        "Dump Truck":            [1, 3, 4, 5, 6, 9, 10],
        "Water Truck":           [1, 3, 4, 5, 6, 9],
        "Mini Truck":            [1, 4, 5, 6, 9],
    }

    for asset_id, asset_type, usage_type, current_usage, purchase_date_str in fleet:
        purchase_date  = date.fromisoformat(purchase_date_str)
        first_log_date = max(purchase_date, SIM_START)

        if usage_type is None or asset_type in BOUGHT_NEW:
            purchase_usage = 0.0
        else:
            lo, hi = USED_START_USAGE.get(asset_type, (0, 0))
            purchase_usage = (lo + hi) / 2.0

        total_date_span  = max(1, (TODAY - purchase_date).days)
        pct_at_log_start = max(0, (first_log_date - purchase_date).days) / total_date_span
        min_log_usage    = purchase_usage + pct_at_log_start * (current_usage - purchase_usage)
        log_usage_span   = max(0.0, current_usage - min_log_usage)
        log_date_span    = max(1, (TODAY - first_log_date).days)

        st_ids = road_based_types.get(asset_type) or hour_based_types.get(asset_type, [1, 6])

        currency     = "JPY" if asset_type == "Mini Truck" else "USD"
        primary_tech = tech_rng.choice(in_house_techs)

        for st_id in st_ids:
            sched = conn.execute(
                "SELECT usage_interval, time_interval, time_type "
                "FROM asset_schedule WHERE asset_id=? AND service_type_id=?",
                (asset_id, st_id),
            ).fetchone()
            if not sched:
                continue
            usage_interval, time_interval, time_type = sched

            if usage_interval is None:  # time-only rule
                interval_days  = time_interval * 30 if time_type == "Months" else time_interval
                available_days = log_date_span
                if available_days < 14:
                    continue

                f        = rng.betavariate(3, 5) * 1.25
                days_ago = min(max(1, int(f * interval_days)), available_days - 1)
                last_date = max(first_log_date, TODAY - timedelta(days=days_ago))
                is_shop  = st_id in SPECIALIST_TYPE_IDS and tech_rng.random() < 0.40
                lo, hi   = SERVICE_COST.get(st_id, (60, 180))
                cost     = round(tech_rng.uniform(lo, hi) * (tech_rng.uniform(1.4, 1.8) if is_shop else 1.0), 2)
                if is_shop:
                    shop_co_id, tech_id = tech_rng.choice(shop_entries)
                    _record(conn, asset_id, st_id, last_date, None, cost, None,
                            company_id=shop_co_id, technician_id=tech_id, currency=currency)
                else:
                    _record(conn, asset_id, st_id, last_date, None, cost, None,
                            company_id=in_house_co_id, technician_id=primary_tech, currency=currency)

            else:  # usage-based
                if log_usage_span < usage_interval:
                    continue

                f          = rng.betavariate(3, 5) * 1.25
                last_usage = current_usage - f * usage_interval

                if time_interval is not None:
                    time_interval_days = time_interval * 30 if time_type == "Months" else time_interval
                    f_time             = rng.betavariate(3, 5) * 1.25
                    target_date        = TODAY - timedelta(days=int(f_time * time_interval_days))
                    target_frac        = max(0.0, (target_date - first_log_date).days / log_date_span)
                    last_usage_time    = min_log_usage + target_frac * log_usage_span
                    last_usage         = max(last_usage, last_usage_time)

                last_usage = max(min_log_usage, round(last_usage, 1))

                events = [(last_usage,)]
                u = last_usage
                while u - usage_interval > min_log_usage:
                    u = round(u - usage_interval * rng.uniform(0.88, 1.00), 1)
                    u = max(min_log_usage, u)
                    events.append((u,))
                events.reverse()

                lo, hi = SERVICE_COST.get(st_id, (60, 180))
                for (svc_usage,) in events:
                    if log_usage_span <= 0:
                        continue
                    frac     = (svc_usage - min_log_usage) / log_usage_span
                    svc_date = first_log_date + timedelta(days=int(frac * log_date_span))
                    svc_date = min(svc_date, TODAY - timedelta(days=1))
                    is_shop  = st_id in SPECIALIST_TYPE_IDS and tech_rng.random() < 0.40
                    cost     = round(tech_rng.uniform(lo, hi) * (tech_rng.uniform(1.4, 1.8) if is_shop else 1.0), 2)
                    if is_shop:
                        shop_co_id, tech_id = tech_rng.choice(shop_entries)
                        _record(conn, asset_id, st_id, svc_date, svc_usage, cost, None,
                                company_id=shop_co_id, technician_id=tech_id, currency=currency)
                    else:
                        _record(conn, asset_id, st_id, svc_date, svc_usage, cost, None,
                                company_id=in_house_co_id, technician_id=primary_tech, currency=currency)

    conn.commit()


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary(conn):
    today_str     = str(TODAY)
    threshold_pct = float(
        conn.execute("SELECT value FROM metadata WHERE key='due_soon_threshold_pct'").fetchone()[0]
    ) / 100

    total   = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    active  = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Active'").fetchone()[0]
    logs_n  = conn.execute("SELECT COUNT(*) FROM service_logs").fetchone()[0]
    usage_n = conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0]
    sched_n = conn.execute("SELECT COUNT(*) FROM asset_schedule").fetchone()[0]
    tmpl_n  = conn.execute("SELECT COUNT(*) FROM asset_type_templates").fetchone()[0]

    print(f"\nAssets     : {active} active / {total} total")
    print(f"Templates  : {tmpl_n} rows  |  Schedule: {sched_n} rows")
    print(f"Service logs : {logs_n}")
    print(f"Usage logs : {usage_n}")

    rows = conn.execute("""
        SELECT s.asset_id, s.service_type_id,
               a.name, at.usage_type, a.current_usage,
               st.name AS st_name,
               s.next_due_usage, s.next_due_date,
               s.usage_reminder, s.time_reminder, s.usage_interval
        FROM asset_schedule s
        JOIN assets           a  ON a.id  = s.asset_id
        JOIN asset_types      at ON at.id = a.asset_type_id
        JOIN service_types st ON st.id = s.service_type_id
        WHERE a.status = 'Active'
        ORDER BY a.name, st.name
    """).fetchall()

    overdue = due_soon = upcoming = 0

    for (asset_id, st_id, aname, utype, current, st_name,
         next_usage, next_date, usage_rem, time_rem, usage_interval) in rows:

        is_overdue = (
            (next_usage is not None and current >= next_usage) or
            (next_date  is not None and today_str >= next_date)
        )
        if is_overdue:
            overdue += 1
            continue

        is_due_soon = False
        if next_usage is not None:
            eff_rem = usage_rem
            if eff_rem is None and usage_interval is not None:
                eff_rem = usage_interval * threshold_pct
            if eff_rem is not None and (next_usage - current) <= eff_rem:
                is_due_soon = True

        if not is_due_soon and next_date is not None:
            threshold_days = time_rem if time_rem is not None else 14
            target = date.fromisoformat(next_date) - timedelta(days=threshold_days)
            if date.fromisoformat(today_str) >= target:
                is_due_soon = True

        if is_due_soon:
            due_soon += 1
        else:
            upcoming += 1

    print(f"\nDashboard  : {overdue} overdue  |  {due_soon} due soon  |  {upcoming} upcoming")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main(seed=42):
    rng      = random.Random(seed)
    tech_rng = random.Random(seed ^ 0xA5B4C3D2)
    print(f"Building {DB_PATH} ...")
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print("ERROR: sample.db is open in another process (VS Code viewer or Jupyter).")
            print("Close that connection and re-run.")
            return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    create_schema(conn)
    seed_metadata(conn)
    seed_companies(conn)
    seed_technicians(conn)
    seed_asset_types(conn)
    seed_assets(conn, rng)
    seed_service_types(conn)
    seed_asset_type_templates(conn)
    seed_asset_schedules(conn)
    seed_usage_logs(conn, rng)
    seed_logs(conn, rng, tech_rng)
    conn.close()

    conn = sqlite3.connect(DB_PATH)
    print_summary(conn)
    conn.close()
    print(f"\nDone — {DB_PATH}")


if __name__ == "__main__":
    main()
