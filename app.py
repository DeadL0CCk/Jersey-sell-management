from flask import Flask, flash, redirect, render_template, request, url_for

from database import init_db
import models

app = Flask(__name__)
app.secret_key = "jersey-sales-tracker-dev-key"

SIZES = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "XXL"]


@app.before_request
def ensure_db():
    init_db()


@app.route("/")
def dashboard():
    summary = models.get_dashboard_summary()
    today_sales = models.get_today_sales()
    low_stock = models.get_low_stock_jerseys()
    return render_template(
        "dashboard.html",
        summary=summary,
        today_sales=today_sales,
        low_stock=low_stock,
    )


@app.route("/stock/setup", methods=["GET", "POST"])
def setup_stock():
    if request.method == "POST":
        team = request.form.get("team", "")
        player_name = request.form.get("player_name", "")
        size = request.form.get("size", "")
        initial_stock = request.form.get("initial_stock", "")
        unit_price_str = request.form.get("unit_price", "")

        if not team.strip() or not size:
            flash("Team and size are required.", "error")
            return redirect(url_for("setup_stock"))

        try:
            qty = int(initial_stock)
            if qty <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid quantity (1+).", "error")
            return redirect(url_for("setup_stock"))

        try:
            unit_price = float(unit_price_str)
            if unit_price <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid unit price.", "error")
            return redirect(url_for("setup_stock"))

        models.add_jersey(team, player_name, size, qty, unit_price)
        flash(
            f"Added {team} {player_name} ({size}) — {qty} in stock at {unit_price:.0f} each.",
            "success",
        )
        return redirect(url_for("setup_stock"))

    jerseys = models.get_all_jerseys_with_stats()
    return render_template("setup_stock.html", jerseys=jerseys, sizes=SIZES)


@app.route("/sales/new", methods=["GET", "POST"])
def record_sale():
    if request.method == "POST":
        jersey_id = request.form.get("jersey_id", "")
        quantity = request.form.get("quantity", "")
        note = request.form.get("note", "")

        try:
            jersey_id = int(jersey_id)
            quantity = int(quantity)
        except ValueError:
            flash("Select a jersey and enter a valid quantity.", "error")
            return redirect(url_for("record_sale"))

        try:
            result = models.record_sale(jersey_id, quantity, note)
            jersey = result["jersey"]
            label = f"{jersey['team']} {jersey['player_name']} ({jersey['size']})".strip()
            flash(
                f"Sold {result['quantity']} × {label}. "
                f"Left: {result['left']}. "
                f"Today total sold: {result['sold_today']} jerseys.",
                "success",
            )
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("record_sale"))

    jerseys = models.get_jerseys_in_stock()
    return render_template("record_sale.html", jerseys=jerseys)


@app.route("/stock/delete", methods=["GET", "POST"])
def delete_stock():
    if request.method == "POST":
        jersey_id = request.form.get("jersey_id", "")
        redirect_to = request.form.get("redirect_to", "delete_stock")

        try:
            jersey_id = int(jersey_id)
        except ValueError:
            flash("Invalid jersey selected.", "error")
            return redirect(url_for("delete_stock"))

        try:
            jersey = models.delete_out_of_stock_jersey(jersey_id)
            label = f"{jersey['team']} {jersey['player_name']} ({jersey['size']})".strip()
            flash(f"Removed {label} from inventory.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        if redirect_to == "inventory":
            search = request.form.get("search", "")
            size_filter = request.form.get("size_filter", "")
            return redirect(url_for("inventory", search=search, size=size_filter))
        return redirect(url_for("delete_stock"))

    jerseys = models.get_out_of_stock_jerseys()
    return render_template("delete_stock.html", jerseys=jerseys)


@app.route("/inventory")
def inventory():
    search = request.args.get("search", "")
    size_filter = request.args.get("size", "")
    jerseys = models.get_all_jerseys_with_stats(search=search, size_filter=size_filter)
    return render_template(
        "inventory.html",
        jerseys=jerseys,
        search=search,
        size_filter=size_filter,
        sizes=SIZES,
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
