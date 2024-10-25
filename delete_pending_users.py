from app import app, db, User
from datetime import datetime

def delete_pending_users():
    """Deletes users with onboarding_status 'pending'."""
    pending_users = User.query.filter_by(onboarding_status="pending").all()
    deleted_count = len(pending_users)

    for user in pending_users:
        db.session.delete(user)

    db.session.commit()

    print(f"Deleted {deleted_count} users with pending onboarding status at {datetime.now()}.")

if __name__ == '__main__':
    with app.app_context():
        delete_pending_users()
#