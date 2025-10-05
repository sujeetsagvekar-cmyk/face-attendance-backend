from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
from flask_cors import CORS
from datetime import date, datetime
import os

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
CORS(app)

# ✅ Use SQLite (fully compatible with Render free tier)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    roll_number = db.Column(db.String(20), unique=True)
    department = db.Column(db.String(50))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(10))
    student = db.relationship('Student', backref='attendance_records')

# ---------------- STUDENT ROUTES ----------------
@app.route('/students', methods=['POST'])
def add_student():
    data = request.get_json()
    name = data.get('name')
    roll_number = data.get('roll_number')
    department = data.get('department')

    if not name or not roll_number:
        return jsonify({"error": "Name and Roll Number are required"}), 400

    new_student = Student(name=name, roll_number=roll_number, department=department)
    db.session.add(new_student)
    db.session.commit()
    return jsonify({"message": "Student added successfully!"}), 201


@app.route('/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([
        {"id": s.id, "name": s.name, "roll_number": s.roll_number, "department": s.department}
        for s in students
    ])


@app.route('/students/<int:id>', methods=['DELETE'])
def delete_student(id):
    student = Student.query.get(id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "Student deleted successfully!"})


@app.route('/students/<int:id>', methods=['PUT'])
def update_student(id):
    student = Student.query.get(id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json()
    student.name = data.get('name', student.name)
    student.roll_number = data.get('roll_number', student.roll_number)
    student.department = data.get('department', student.department)
    db.session.commit()
    return jsonify({"message": "Student updated successfully!"}), 200


@app.route('/students/search/<string:roll_number>', methods=['GET'])
def search_student_by_roll(roll_number):
    student = Student.query.filter_by(roll_number=roll_number).first()
    if not student:
        return jsonify({"error": "Student not found"}), 200
    return jsonify({
        "id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "department": student.department
    }), 200


# ---------------- ATTENDANCE ROUTES ----------------
@app.route('/attendance/mark', methods=['POST'])
def mark_attendance_by_roll():
    data = request.get_json()
    roll_number = data.get('roll_number')
    att_date = data.get('date')
    status = data.get('status', 'Present')

    if not roll_number or not att_date:
        return jsonify({"error": "Roll number and date are required"}), 400

    student = Student.query.filter_by(roll_number=roll_number).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    try:
        att_date = datetime.strptime(att_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    record = Attendance.query.filter_by(student_id=student.id, date=att_date).first()
    if record:
        record.status = status
    else:
        record = Attendance(student_id=student.id, date=att_date, status=status)
        db.session.add(record)
    db.session.commit()

    return jsonify({"message": f"Attendance marked as {status} for {roll_number} on {att_date}."}), 200


@app.route('/attendance/summary', methods=['GET'])
@app.route('/attendance/summary/<int:year>/<int:month>', methods=['GET'])
def attendance_summary(year=None, month=None):
    if not year or not month:
        today = datetime.today()
        year, month = today.year, today.month

    total_days = db.session.query(func.count(func.distinct(Attendance.date))).filter(
        extract('year', Attendance.date) == year,
        extract('month', Attendance.date) == month
    ).scalar() or 0

    students = Student.query.all()
    summary = []
    percentages = []

    for s in students:
        present_days = db.session.query(func.count(Attendance.id)).filter(
            Attendance.student_id == s.id,
            Attendance.status == 'Present',
            extract('year', Attendance.date) == year,
            extract('month', Attendance.date) == month
        ).scalar() or 0

        percentage = round((present_days / total_days) * 100, 2) if total_days else 0
        percentages.append(percentage)
        summary.append({
            "name": s.name,
            "roll_number": s.roll_number,
            "days_present": present_days,
            "total_days": total_days,
            "attendance_percentage": percentage
        })

    above_75 = [s for s in summary if s["attendance_percentage"] >= 75]
    avg = round(sum(percentages) / len(percentages), 2) if percentages else 0

    return jsonify({
        "month": month,
        "year": year,
        "total_working_days": total_days,
        "class_average_attendance": avg,
        "students_above_75_count": len(above_75),
        "students": summary
    })


# ---------------- HOME ROUTE ----------------
@app.route('/')
def home():
    return jsonify({"message": "✅ Flask Backend is Live on Render!"})


# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
