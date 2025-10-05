import random
from datetime import datetime, timedelta
from app import db, Attendance, Student, app

def seed_attendance():
    print("Seeding attendance data for 30 days...")
    students = Student.query.all()

    start_date = datetime(2025, 9, 1)  # start date
    days_to_seed = 30

    for i in range(days_to_seed):
        current_date = start_date + timedelta(days=i)
        for student in students:
            # 70% chance Present, 30% chance Absent
            status = random.choices(["Present", "Absent"], weights=[7, 3], k=1)[0]

            record = Attendance(
                student_id=student.id,
                date=current_date.date(),
                status=status
            )
            db.session.add(record)

    db.session.commit()
    print("✅ Random attendance data for 30 days inserted successfully!")

# ensure Flask app context
if __name__ == "__main__":
    with app.app_context():
        seed_attendance()
