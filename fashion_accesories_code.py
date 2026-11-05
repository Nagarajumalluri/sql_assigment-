# I use Python's built-in packages, so no installation is required.
import sqlite3
import random
from pathlib import Path
from datetime import date, timedelta

# I fix the seed so the same code recreates the same data.
rng = random.Random(42)
db_path = Path("fashion_accessories.db")

# I replace only this generated database when rerunning the cell.
if db_path.exists():
    db_path.unlink()

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON;")

# ----------------------------------------------------------
# 1. CREATE TABLES
# ----------------------------------------------------------
# Nominal: accessory_type and component_material.
# Ordinal: supplier_rating, ordered Poor < Fair < Good < Excellent.
# Interval: agreement_year (calendar year).
# Ratio: component_weight_g, unit_cost and quantities.
# All costs use GBP.

conn.executescript("""
CREATE TABLE suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE
        CHECK (length(trim(supplier_name)) > 0),
    country TEXT NOT NULL
        CHECK (country IN
            ('India', 'China', 'Italy', 'Turkey', 'Vietnam', 'UK')),
    supplier_rating TEXT NOT NULL
        CHECK (supplier_rating IN ('Poor', 'Fair', 'Good', 'Excellent')),
    contact_email TEXT
        CHECK (contact_email IS NULL OR
               contact_email LIKE '%@%.example')
);

CREATE TABLE components (
    component_id INTEGER PRIMARY KEY,
    component_name TEXT NOT NULL UNIQUE,
    component_material TEXT NOT NULL
        CHECK (component_material IN
            ('Leather', 'Brass', 'Steel', 'Polyester', 'Resin')),
    component_weight_g REAL NOT NULL
        CHECK (component_weight_g > 0 AND component_weight_g <= 500),
    reference_cost_gbp REAL NOT NULL
        CHECK (reference_cost_gbp > 0 AND reference_cost_gbp <= 100)
);

CREATE TABLE accessory_designs (
    design_id INTEGER PRIMARY KEY,
    design_name TEXT NOT NULL UNIQUE,
    accessory_type TEXT NOT NULL
        CHECK (accessory_type IN
            ('Handbag', 'Belt', 'Necklace', 'Bracelet', 'Hair accessory'))
);

CREATE TABLE design_components (
    design_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    quantity_required INTEGER NOT NULL
        CHECK (quantity_required BETWEEN 1 AND 30),

    PRIMARY KEY (design_id, component_id),
    FOREIGN KEY (design_id) REFERENCES accessory_designs(design_id),
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);

CREATE TABLE supply_agreements (
    supplier_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    agreement_year INTEGER NOT NULL
        CHECK (agreement_year BETWEEN 2023 AND 2025),
    unit_cost REAL NOT NULL
        CHECK (unit_cost > 0 AND unit_cost <= 100),
    minimum_order_quantity INTEGER NOT NULL
        CHECK (minimum_order_quantity BETWEEN 10 AND 5000),
    lead_time_days INTEGER NOT NULL
        CHECK (lead_time_days BETWEEN 1 AND 120),
    agreement_notes TEXT
        CHECK (agreement_notes IS NULL OR
               length(trim(agreement_notes)) > 0),

    PRIMARY KEY (supplier_id, component_id, agreement_year),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);

CREATE TABLE inspections (
    inspection_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    agreement_year INTEGER NOT NULL,
    inspection_date TEXT NOT NULL
        CHECK (
            length(inspection_date) = 10
            AND date(inspection_date, '+0 days') IS NOT NULL
            AND date(inspection_date, '+0 days') = inspection_date
            AND CAST(substr(inspection_date, 1, 4) AS INTEGER)
                = agreement_year
        ),
    quantity_checked INTEGER NOT NULL
        CHECK (quantity_checked BETWEEN 20 AND 200),
    quantity_defective INTEGER NOT NULL
        CHECK (quantity_defective BETWEEN 0 AND quantity_checked),
    inspection_result TEXT NOT NULL
        CHECK (inspection_result IN ('Pass', 'Fail')),
    inspection_notes TEXT
        CHECK (inspection_notes IS NULL OR
               length(trim(inspection_notes)) > 0),

    CHECK (
        (inspection_result = 'Pass'
         AND quantity_defective * 1.0 / quantity_checked <= 0.05)
        OR
        (inspection_result = 'Fail'
         AND quantity_defective * 1.0 / quantity_checked > 0.05)
    ),

    FOREIGN KEY (supplier_id, component_id, agreement_year)
        REFERENCES supply_agreements
            (supplier_id, component_id, agreement_year)
);
""")

# ----------------------------------------------------------
# 2. GENERATE 40 FICTIONAL SUPPLIERS
# ----------------------------------------------------------
# I use fictional names and reserved .example email domains.
# I deliberately omit exactly 4 emails: 4 / 40 = 10%.
missing_email_ids = set(rng.sample(range(1, 41), 4))

prefixes = [
    "Amber", "Cedar", "Willow", "Maple", "Silver",
    "Coral", "Elm", "Orchid"
]
suffixes = [
    "Materials", "Components", "Trims", "Craft Supplies", "Findings"
]

suppliers = []
ratings = {}

for supplier_id in range(1, 41):
    prefix = prefixes[(supplier_id - 1) // 5]
    suffix = suffixes[(supplier_id - 1) % 5]
    name = f"{prefix} {suffix}"

    country = rng.choices(
        ["India", "China", "Italy", "Turkey", "Vietnam", "UK"],
        weights=[25, 25, 12, 15, 13, 10]
    )[0]

    rating = rng.choices(
        ["Poor", "Fair", "Good", "Excellent"],
        weights=[5, 20, 50, 25]
    )[0]

    email = (
        None if supplier_id in missing_email_ids
        else f"sales@{name.lower().replace(' ', '')}.example"
    )

    suppliers.append((supplier_id, name, country, rating, email))
    ratings[supplier_id] = rating

conn.executemany(
    "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)", suppliers
)

# ----------------------------------------------------------
# 3. GENERATE 150 COMPONENTS
# ----------------------------------------------------------
# I link component names, weights and costs to their materials.
specifications = {
    "Leather": {
        "names": ["Strap", "Panel", "Tab"],
        "weight": (8, 90),
        "cost": (0.80, 7.00)
    },
    "Brass": {
        "names": ["Clasp", "Buckle", "Ring"],
        "weight": (2, 35),
        "cost": (0.15, 2.50)
    },
    "Steel": {
        "names": ["Clip", "Chain", "Fastener"],
        "weight": (2, 45),
        "cost": (0.10, 1.80)
    },
    "Polyester": {
        "names": ["Ribbon", "Lining", "Cord"],
        "weight": (1, 30),
        "cost": (0.05, 1.20)
    },
    "Resin": {
        "names": ["Bead", "Charm", "Pendant"],
        "weight": (0.5, 15),
        "cost": (0.05, 1.00)
    }
}

components = []
component_materials = {}
reference_costs = {}

for component_id in range(1, 151):
    material = rng.choices(
        list(specifications), weights=[20, 25, 20, 20, 15]
    )[0]

    spec = specifications[material]
    part = rng.choice(spec["names"])

    # Triangular distributions favour typical rather than extreme values.
    low_w, high_w = spec["weight"]
    weight = round(rng.triangular(low_w, high_w, low_w * 1.8), 2)

    low_c, high_c = spec["cost"]
    position = (weight - low_w) / (high_w - low_w)
    cost = round(
        max(0.02, (low_c + position * (high_c - low_c))
            * rng.uniform(0.85, 1.15)), 2
    )

    name = f"{material} {part} {component_id:03d}"
    components.append((component_id, name, material, weight, cost))
    component_materials[component_id] = material
    reference_costs[component_id] = cost

conn.executemany(
    "INSERT INTO components VALUES (?, ?, ?, ?, ?)", components
)

# ----------------------------------------------------------
# 4. GENERATE 80 DESIGNS AND THEIR COMPONENT LISTS
# ----------------------------------------------------------
# I separate design details from component lists to avoid repeating
# a design's name and type for every component.
allowed_materials = {
    "Handbag": ["Leather", "Brass", "Steel", "Polyester"],
    "Belt": ["Leather", "Brass", "Steel", "Polyester"],
    "Necklace": ["Brass", "Steel", "Resin"],
    "Bracelet": ["Leather", "Brass", "Steel", "Resin"],
    "Hair accessory": ["Steel", "Polyester", "Resin"]
}

designs = []
design_components = []

for design_id in range(1, 81):
    accessory_type = rng.choices(
        list(allowed_materials), weights=[30, 20, 20, 15, 15]
    )[0]

    designs.append((
        design_id,
        f"{accessory_type} Collection {design_id:03d}",
        accessory_type
    ))

    candidates = [
        cid for cid, material in component_materials.items()
        if material in allowed_materials[accessory_type]
    ]

    selected = rng.sample(candidates, rng.randint(3, 6))

    for component_id in selected:
        quantity = (
            rng.randint(4, 20)
            if component_materials[component_id] == "Resin"
            else rng.randint(1, 4)
        )
        design_components.append((design_id, component_id, quantity))

conn.executemany(
    "INSERT INTO accessory_designs VALUES (?, ?, ?)", designs
)
conn.executemany(
    "INSERT INTO design_components VALUES (?, ?, ?)", design_components
)

# ----------------------------------------------------------
# 5. GENERATE 450 ANNUAL SUPPLY AGREEMENTS
# ----------------------------------------------------------
# I assign each supplier two material specialisms.
# Each component receives one agreement in each of three years.
# The composite key permits only one agreement per supplier,
# component and year.
specialisms = {
    sid: set(rng.sample(list(specifications), 2))
    for sid in range(1, 41)
}

# I ensure every material has an eligible supplier.
for sid, material in enumerate(specifications, start=1):
    specialisms[sid].add(material)

agreements = []

for component_id in range(1, 151):
    material = component_materials[component_id]
    eligible = [
        sid for sid in range(1, 41)
        if material in specialisms[sid]
    ]

    for year in [2023, 2024, 2025]:
        supplier_id = rng.choice(eligible)
        inflation_factor = 1 + 0.03 * (year - 2023)

        unit_cost = round(
            max(0.02, reference_costs[component_id]
                * inflation_factor * rng.uniform(0.90, 1.12)), 2
        )

        minimum_order = rng.choices(
            [50, 100, 250, 500, 1000],
            weights=[10, 25, 35, 20, 10]
        )[0]

        lead_time = int(rng.triangular(7, 60, 21))

        agreements.append((
            supplier_id, component_id, year, unit_cost,
            minimum_order, lead_time, "Annual supply terms"
        ))

# I deliberately omit 45 agreement notes: 45 / 450 = 10%.
for index in rng.sample(range(len(agreements)), 45):
    row = list(agreements[index])
    row[6] = None
    agreements[index] = tuple(row)

conn.executemany(
    "INSERT INTO supply_agreements VALUES (?, ?, ?, ?, ?, ?, ?)",
    agreements
)

# ----------------------------------------------------------
# 6. GENERATE 1,485 ORIGINAL INSPECTIONS
# ----------------------------------------------------------
# I vary inspection frequency between agreements.
# Ratings affect average defects but do not guarantee outcomes.
defect_rates = {
    "Poor": 0.08,
    "Fair": 0.045,
    "Good": 0.02,
    "Excellent": 0.008
}

agreement_weights = [
    rng.lognormvariate(0, 0.7) for _ in agreements
]

inspection_business_rows = []
seen_business_rows = set()

while len(inspection_business_rows) < 1485:
    agreement = rng.choices(
        agreements, weights=agreement_weights, k=1
    )[0]

    supplier_id, component_id, year = agreement[:3]

    first_day = date(year, 1, 1)
    days_in_year = (date(year + 1, 1, 1) - first_day).days
    inspected_on = first_day + timedelta(
        days=rng.randrange(days_in_year)
    )

    checked = rng.choices(
        [20, 50, 80, 100, 125, 200],
        weights=[10, 25, 20, 25, 15, 5]
    )[0]

    probability = min(
        0.25,
        defect_rates[ratings[supplier_id]] * rng.uniform(0.6, 1.5)
    )

    defective = sum(
        rng.random() < probability for _ in range(checked)
    )
    result = "Pass" if defective / checked <= 0.05 else "Fail"

    notes = (
        "Within acceptance limit"
        if result == "Pass"
        else "Defect threshold exceeded; follow-up required"
    )

    row = (
        supplier_id, component_id, year,
        inspected_on.isoformat(), checked, defective, result, notes
    )

    # I prevent accidental duplicates before inserting planned copies.
    if row not in seen_business_rows:
        seen_business_rows.add(row)
        inspection_business_rows.append(row)

# I deliberately omit notes from exactly 150 original inspections.
missing_note_indices = set(rng.sample(range(1485), 150))

for index in missing_note_indices:
    row = list(inspection_business_rows[index])
    row[7] = None
    inspection_business_rows[index] = tuple(row)

assert len(set(inspection_business_rows)) == 1485

# ----------------------------------------------------------
# 7. DELIBERATELY ADD 15 DUPLICATE BUSINESS RECORDS
# ----------------------------------------------------------
# A duplicate has identical values in EVERY inspection business
# column, excluding inspection_id. It represents repeated entry.
# I copy records with notes so missing-note counts remain exact.
eligible_indices = [
    index for index in range(1485)
    if index not in missing_note_indices
]

duplicate_indices = rng.sample(eligible_indices, 15)

all_inspections = inspection_business_rows + [
    inspection_business_rows[index] for index in duplicate_indices
]

# I shuffle rows so duplicate copies are not grouped at the end.
rng.shuffle(all_inspections)

inspection_records = [
    (inspection_id,) + row
    for inspection_id, row in enumerate(all_inspections, start=1)
]

conn.executemany(
    "INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    inspection_records
)
conn.commit()

# ----------------------------------------------------------
# 8. DISPLAY TABLE COUNTS AND STRUCTURES
# ----------------------------------------------------------
tables = [
    "suppliers",
    "components",
    "accessory_designs",
    "design_components",
    "supply_agreements",
    "inspections"
]

print("TABLE COUNTS AND STRUCTURES")
for table in tables:
    count = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"\n{table}: {count:,} rows")
    for column in conn.execute(f"PRAGMA table_info({table})"):
        _, name, storage_type, not_null, default, pk_position = column
        print(
            f"  {name}: {storage_type}, "
            f"NOT NULL={bool(not_null)}, "
            f"primary-key position={pk_position}"
        )

    print("  Foreign keys:",
          conn.execute(f"PRAGMA foreign_key_list({table})").fetchall())

# ----------------------------------------------------------
# 9. CHECK MISSING VALUES AND DUPLICATES
# ----------------------------------------------------------
print("\nDELIBERATE MISSING VALUES")

missing_checks = [
    ("suppliers", "contact_email", 4),
    ("supply_agreements", "agreement_notes", 45),
    ("inspections", "inspection_notes", 150)
]

for table, column, expected in missing_checks:
    total, missing = conn.execute(
        f"SELECT COUNT(*), "
        f"SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END) "
        f"FROM {table}"
    ).fetchone()

    assert missing == expected
    print(
        f"{table}.{column}: {missing}/{total} "
        f"({missing / total:.2%})"
    )

duplicate_groups, extra_copies = conn.execute("""
    SELECT COUNT(*), COALESCE(SUM(record_count - 1), 0)
    FROM (
        SELECT COUNT(*) AS record_count
        FROM inspections
        GROUP BY supplier_id, component_id, agreement_year,
                 inspection_date, quantity_checked,
                 quantity_defective, inspection_result,
                 inspection_notes
        HAVING COUNT(*) > 1
    )
""").fetchone()

assert duplicate_groups == 15
assert extra_copies == 15

print("\nDELIBERATE DUPLICATES")
print("Duplicate business-record groups:", duplicate_groups)
print(
    f"Extra duplicate copies: {extra_copies}/1500 "
    f"({extra_copies / 1500:.2%})"
)

# ----------------------------------------------------------
# 10. VALIDATE INTEGRITY, RELATIONSHIPS AND CONSTRAINTS
# ----------------------------------------------------------
assert conn.execute(
    "PRAGMA foreign_keys"
).fetchone()[0] == 1

assert conn.execute(
    "PRAGMA integrity_check"
).fetchall() == [("ok",)]

assert conn.execute(
    "PRAGMA foreign_key_check"
).fetchall() == []

expected_counts = {
    "suppliers": 40,
    "components": 150,
    "accessory_designs": 80,
    "design_components": len(design_components),
    "supply_agreements": 450,
    "inspections": 1500
}

for table, expected in expected_counts.items():
    actual = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]
    assert actual == expected

assert len(conn.execute(
    "PRAGMA table_info(inspections)"
).fetchall()) >= 7

# I confirm every design has components.
assert conn.execute("""
    SELECT COUNT(*)
    FROM accessory_designs AS d
    WHERE NOT EXISTS (
        SELECT 1 FROM design_components AS dc
        WHERE dc.design_id = d.design_id
    )
""").fetchone()[0] == 0

# I verify that every component has three annual agreements.
assert conn.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT component_id
        FROM supply_agreements
        GROUP BY component_id
        HAVING COUNT(*) <> 3
    )
""").fetchone()[0] == 0

# I test rejection of invalid data without retaining test records.
def expect_rejection(label, sql, parameters):
    conn.execute("SAVEPOINT validation_test")
    rejected = False

    try:
        conn.execute(sql, parameters)
    except sqlite3.IntegrityError:
        rejected = True
    finally:
        conn.execute("ROLLBACK TO validation_test")
        conn.execute("RELEASE validation_test")

    assert rejected, f"Constraint failed: {label}"
    print(f"Passed: {label}")

expect_rejection(
    "UNIQUE supplier name",
    "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)",
    (999, suppliers[0][1], "UK", "Good", None)
)

expect_rejection(
    "NOT NULL supplier name",
    "INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)",
    (999, None, "UK", "Good", None)
)

expect_rejection(
    "Positive component weight",
    "INSERT INTO components VALUES (?, ?, ?, ?, ?)",
    (999, "Validation component", "Steel", -1, 1)
)

expect_rejection(
    "Foreign-key enforcement",
    "INSERT INTO design_components VALUES (?, ?, ?)",
    (999, 1, 1)
)

expect_rejection(
    "Composite design-component primary key",
    "INSERT INTO design_components VALUES (?, ?, ?)",
    design_components[0]
)

expect_rejection(
    "Composite annual-agreement primary key",
    "INSERT INTO supply_agreements VALUES (?, ?, ?, ?, ?, ?, ?)",
    agreements[0]
)

sample = list(inspection_records[0])
sample[0] = 99999
sample[6] = sample[5] + 1

expect_rejection(
    "Defective quantity cannot exceed checked quantity",
    "INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    sample
)

sample = list(inspection_records[0])
sample[0] = 99999
sample[4] = f"{sample[3]}-02-30"

expect_rejection(
    "Invalid calendar date",
    "INSERT INTO inspections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    sample
)

conn.commit()
conn.close()

print("\nAll validation checks passed.")
print(f"Database created: {db_path.resolve()}")
print(f"File size: {db_path.stat().st_size:,} bytes")

# ----------------------------------------------------------
# 11. DOWNLOAD THE DATABASE IN GOOGLE COLAB
# ----------------------------------------------------------
try:
    from google.colab import files
except ImportError:
    print("Outside Colab: the database is saved in your working folder.")
else:
    files.download(str(db_path))