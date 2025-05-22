import os
import datetime
import uuid
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()  # Load .env if not in production

app = Flask(__name__)
client = MongoClient(os.getenv("MONGODB_URI"))
app.db = client.DailyDrill


@app.context_processor
def add_calc_date_range():
    def date_range(start: datetime.date):
        dates = [start + datetime.timedelta(days=diff) for diff in range(-3, 4)]
        return dates
    return {"date_range": date_range}


def today_at_midnight():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day)


@app.route("/")
def index():
    date_str = request.args.get("date")
    try:
        selected_date = (
            datetime.datetime.fromisoformat(date_str)
            if date_str
            else today_at_midnight()
        )
        selected_date = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        selected_date = today_at_midnight()

    drills_on_date = list(app.db.drills.find({"added": {"$lte": selected_date}}))
    
    # Use selected_date (datetime) directly, NOT selected_date.date()
    completions = [
        drill["drill"]
        for drill in app.db.completions.find({"date": selected_date})
    ]

    return render_template(
        "index.html",
        drills=drills_on_date,
        selected_date=selected_date,
        completions=completions,
        title="Daily Drill - Home"
    )


@app.route("/add", methods=["GET", "POST"])
def add_drill():
    today = today_at_midnight()

    if request.method == "POST":
        drill_name = request.form.get("drill").strip()
        if drill_name:  # Only insert non-empty drills
            app.db.drills.insert_one({
                "_id": uuid.uuid4().hex,
                "added": today,
                "name": drill_name
            })
            return redirect(url_for("index"))

    return render_template(
        "add_drill.html",
        title="Daily Drill - Add Drill",
        selected_date=today,
    )


@app.route("/complete", methods=["POST"])
def complete():
    date_string = request.form.get("date")
    drill_id = request.form.get("drillid")

    try:
        # Convert input date string to datetime at midnight
        date_obj = datetime.datetime.fromisoformat(date_string)
        date_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

        if drill_id:
            app.db.completions.insert_one({
                "date": date_dt,
                "drill": drill_id
            })
    except (ValueError, AttributeError):
        pass

    return redirect(url_for("index", date=date_string))


if __name__ == "__main__":
    app.run(debug=True)
