from database import get_connection

LARGE_SIZES = {"3XL", "4XL", "5XL"}
PRICE_LARGE = 1200.0
PRICE_STANDARD = 1100.0


def price_for_size(size):
    normalized = size.strip().upper()
    if normalized in LARGE_SIZES:
        return PRICE_LARGE
    return PRICE_STANDARD


def apply_size_pricing():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, size FROM jerseys").fetchall()
        for row in rows:
            conn.execute(
                "UPDATE jerseys SET unit_price = ? WHERE id = ?",
                (price_for_size(row["size"]), row["id"]),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def add_jersey(team, player_name, size, initial_stock, unit_price):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO jerseys (team, player_name, size, initial_stock, current_stock, unit_price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (team.strip(), player_name.strip(), size.strip(), initial_stock, initial_stock, unit_price),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_jersey(jersey_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM jerseys WHERE id = ?", (jersey_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_jerseys_in_stock():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM jerseys
            WHERE current_stock > 0
            ORDER BY team, player_name, size
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_jerseys_with_stats(search="", size_filter=""):
    conn = get_connection()
    try:
        query = """
            SELECT
                j.*,
                (j.initial_stock - j.current_stock) AS sold_count,
                (
                    SELECT MAX(s.sold_at)
                    FROM sales s
                    WHERE s.jersey_id = j.id
                ) AS last_sale_at
            FROM jerseys j
            WHERE 1=1
        """
        params = []

        if search.strip():
            query += " AND (j.team LIKE ? OR j.player_name LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        if size_filter.strip():
            query += " AND j.size = ?"
            params.append(size_filter.strip())

        query += " ORDER BY j.team, j.player_name, j.size"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def record_sale(jersey_id, quantity, note=""):
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        jersey = conn.execute(
            "SELECT * FROM jerseys WHERE id = ?",
            (jersey_id,),
        ).fetchone()

        if jersey is None:
            raise ValueError("Jersey not found")

        if quantity <= 0:
            raise ValueError("Quantity must be at least 1")

        if jersey["current_stock"] < quantity:
            raise ValueError(
                f"Not enough stock. Only {jersey['current_stock']} left for "
                f"{jersey['team']} {jersey['player_name']} ({jersey['size']})."
            )

        total_amount = jersey["unit_price"] * quantity
        conn.execute(
            """
            INSERT INTO sales (jersey_id, quantity, total_amount, note)
            VALUES (?, ?, ?, ?)
            """,
            (jersey_id, quantity, total_amount, note.strip()),
        )
        new_stock = jersey["current_stock"] - quantity
        conn.execute(
            "UPDATE jerseys SET current_stock = ? WHERE id = ?",
            (new_stock, jersey_id),
        )
        conn.commit()

        return {
            "jersey": dict(jersey),
            "quantity": quantity,
            "left": new_stock,
            "total_amount": total_amount,
            "sold_today": count_sales_today(conn),
            "revenue_today": get_revenue_today(conn),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _today_clause():
    return "date(sold_at) = date('now', 'localtime')"


def count_sales_today(conn=None):
    close = False
    if conn is None:
        conn = get_connection()
        close = True
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM(quantity), 0) AS total FROM sales WHERE {_today_clause()}"
        ).fetchone()
        return int(row["total"])
    finally:
        if close:
            conn.close()


def get_revenue_today(conn=None):
    close = False
    if conn is None:
        conn = get_connection()
        close = True
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM(total_amount), 0) AS total FROM sales WHERE {_today_clause()}"
        ).fetchone()
        return float(row["total"])
    finally:
        if close:
            conn.close()


def get_today_sales():
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                s.id,
                s.quantity,
                s.total_amount,
                s.sold_at,
                s.note,
                j.team,
                j.player_name,
                j.size
            FROM sales s
            JOIN jerseys j ON j.id = s.jersey_id
            WHERE {_today_clause()}
            ORDER BY s.sold_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_out_of_stock_jerseys():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                j.*,
                (j.initial_stock - j.current_stock) AS sold_count,
                (
                    SELECT MAX(s.sold_at)
                    FROM sales s
                    WHERE s.jersey_id = j.id
                ) AS last_sale_at
            FROM jerseys j
            WHERE j.current_stock = 0
            ORDER BY j.team, j.player_name, j.size
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_out_of_stock_jersey(jersey_id):
    conn = get_connection()
    try:
        jersey = conn.execute(
            "SELECT * FROM jerseys WHERE id = ?",
            (jersey_id,),
        ).fetchone()

        if jersey is None:
            raise ValueError("Jersey not found")

        if jersey["current_stock"] > 0:
            raise ValueError(
                f"Cannot delete {jersey['team']} {jersey['player_name']} ({jersey['size']}) — "
                f"it still has {jersey['current_stock']} in stock."
            )

        conn.execute("DELETE FROM sales WHERE jersey_id = ?", (jersey_id,))
        conn.execute("DELETE FROM jerseys WHERE id = ?", (jersey_id,))
        conn.commit()
        return dict(jersey)
    finally:
        conn.close()


def get_low_stock_jerseys(threshold=2):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM jerseys
            WHERE current_stock > 0 AND current_stock <= ?
            ORDER BY current_stock ASC, team, player_name, size
            """,
            (threshold,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_dashboard_summary():
    conn = get_connection()
    try:
        sold_today = count_sales_today(conn)
        revenue_today = get_revenue_today(conn)
        total_remaining = conn.execute(
            "SELECT COALESCE(SUM(current_stock), 0) AS total FROM jerseys"
        ).fetchone()["total"]
        jersey_types = conn.execute("SELECT COUNT(*) AS total FROM jerseys").fetchone()["total"]
        return {
            "sold_today": sold_today,
            "revenue_today": revenue_today,
            "total_remaining": int(total_remaining),
            "jersey_types": int(jersey_types),
        }
    finally:
        conn.close()
