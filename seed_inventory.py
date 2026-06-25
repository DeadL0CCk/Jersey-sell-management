"""One-time seed script for current jersey inventory."""

from database import get_connection, init_db
from models import price_for_size

INVENTORY = [
    ("Argentina", "Home", [("2XL", 2), ("XL", 1)]),
    ("Argentina", "Away", [("XL", 5), ("L", 2), ("2XL", 1)]),
    ("Argentina", "Terrace", [("XL", 4), ("L", 2), ("4XL", 2)]),
    ("Brazil", "Home", [("L", 3), ("2XL", 2), ("XL", 2)]),
    ("Brazil", "Away", [("M", 3), ("S", 2), ("XL", 1), ("L", 1)]),
    ("Brazil", "Terrace", [("2XL", 3), ("L", 1)]),
    ("England", "Away", [("3XL", 1)]),
    ("England", "Home", [("3XL", 1)]),
    ("Germany", "Home", [("2XL", 3), ("XL", 1), ("L", 1), ("M", 1)]),
    ("Germany", "Away", [("XL", 1)]),
    ("Japan", "Home", [("2XL", 2), ("XL", 2), ("L", 2)]),
    ("Korea", "Home", [("XL", 1), ("2XL", 1)]),
    ("Portugal", "Home", [("3XL", 2), ("S", 1)]),
    ("Portugal", "Away", [("XL", 3), ("2XL", 2), ("L", 1), ("M", 1)]),
    ("Spain", "Home", [("3XL", 2), ("L", 1)]),
    ("Spain", "Away", [("XL", 5), ("L", 2), ("2XL", 1)]),
    ("USA", "Home", [("2XL", 1), ("XL", 1)]),
    ("USA", "Away", [("L", 1)]),
]

OUT_OF_STOCK = [
    ("Brazil", "White Concept"),
    ("France", "Home"),
    ("Morocco", "Home"),
]


def clear_inventory():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sales")
        conn.execute("DELETE FROM jerseys")
        conn.commit()
    finally:
        conn.close()


def seed():
    init_db()
    clear_inventory()

    conn = get_connection()
    inserted = 0
    total_units = 0

    try:
        for team, variant, sizes in INVENTORY:
            for size, qty in sizes:
                conn.execute(
                    """
                    INSERT INTO jerseys (team, player_name, size, initial_stock, current_stock, unit_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (team, variant, size, qty, qty, price_for_size(size)),
                )
                inserted += 1
                total_units += qty

        for team, variant in OUT_OF_STOCK:
            conn.execute(
                """
                INSERT INTO jerseys (team, player_name, size, initial_stock, current_stock, unit_price)
                VALUES (?, ?, ?, 0, 0, ?)
                """,
                (team, variant, "—", price_for_size("L")),
            )
            inserted += 1

        conn.commit()
    finally:
        conn.close()

    return inserted, total_units


if __name__ == "__main__":
    count, units = seed()
    print(f"Seeded {count} jersey rows ({units} units in stock).")
