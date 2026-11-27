"""Client, household, and advisor domain facades."""
from app.services import wealth

def get_household_context(db, user):
    return wealth.household_for_user(db, user)
