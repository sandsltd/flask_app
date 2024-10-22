import os
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

# Set the database URI directly
db_url = 'postgresql://flask_app_db_a9w1_user:5saqJ0QMkRJOnT7TaNk3DNFPrTkfZEi6@dpg-cs8isuu8ii6s73ccl88g-a.oregon-postgres.render.com/flask_app_db_a9w1'

# Set up the database engine
engine = create_engine(db_url)

# Create a base class for the models
Base = declarative_base()

# Define the User model
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    unique_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(120), nullable=False)         # First name
    last_name = Column(String(120), nullable=False)          # Last name
    phone_number = Column(String(20), nullable=False)
    business_name = Column(String(120), nullable=False)
    website_url = Column(String(200), nullable=True)         # Optional
    vat_number = Column(String(50), nullable=True)           # Optional
    stripe_connect_id = Column(String(120), nullable=False)

    # Address fields
    house_name_or_number = Column(String(255), nullable=False)  # House name/number
    street = Column(String(255), nullable=False)                 # Street
    locality = Column(String(255), nullable=True)                # Locality
    town = Column(String(100), nullable=False)                   # Town
    postcode = Column(String(20), nullable=False)                # Postcode

    # New fields for rates
    flat_rate = Column(Float, nullable=True, default=0.01)       # Flat rate
    promo_rate = Column(Float, nullable=True)                    # Promotional rate
    promo_rate_date_end = Column(Date, nullable=True)            # End date for promotional rate

# Define the Event model
class Event(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    date = Column(String(120), nullable=False)
    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(String(50), nullable=False)
    end_time = Column(String(50), nullable=False)
    ticket_quantity = Column(Integer, nullable=False)
    ticket_price = Column(Float, nullable=False)
    event_image = Column(String(300), nullable=True)  # Image URL

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

# Create a session factory
Session = sessionmaker(bind=engine)

def add_user(email, password, first_name, last_name, phone_number, business_name, stripe_connect_id, 
             website_url=None, vat_number=None, house_name_or_number=None, street=None, 
             locality=None, town=None, postcode=None, flat_rate=0.01, promo_rate=None, promo_rate_date_end=None):
    """Adds a new user to the database."""
    session = Session()
    try:
        hashed_password = generate_password_hash(password)
        new_user = User(
            unique_id=str(uuid.uuid4()),
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            business_name=business_name,
            website_url=website_url,
            vat_number=vat_number,
            stripe_connect_id=stripe_connect_id,
            house_name_or_number=house_name_or_number,
            street=street,
            locality=locality,
            town=town,
            postcode=postcode,
            flat_rate=flat_rate,
            promo_rate=promo_rate,
            promo_rate_date_end=promo_rate_date_end
        )
        session.add(new_user)
        session.commit()
        print(f"User {email} added successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error adding user: {str(e)}")
    finally:
        session.close()

def view_users():
    """Fetches all users from the database."""
    session = Session()
    users = session.query(User).all()
    
    print("\nUser List:")
    print("ID | Unique ID | Email | First Name | Last Name | Phone Number | Business Name | Website URL | VAT Number | Stripe Connect ID | Address | Flat Rate | Promo Rate | Promo Rate End Date")
    print("----------------------------------------------------------------------------------------------------------------------------------------------------------")
    
    for user in users:
        address = f"{user.house_name_or_number}, {user.street}, {user.locality or ''}, {user.town}, {user.postcode}"
        flat_rate = f"{user.flat_rate or 'N/A'}"
        promo_rate = f"{user.promo_rate or 'N/A'}"
        promo_rate_date_end = f"{user.promo_rate_date_end or 'N/A'}"
        
        print(f"{user.id} | {user.unique_id} | {user.email} | {user.first_name} | {user.last_name} | {user.phone_number} | {user.business_name} | {user.website_url or 'N/A'} | {user.vat_number or 'N/A'} | {user.stripe_connect_id} | {address} | {flat_rate} | {promo_rate} | {promo_rate_date_end}")
    
    session.close()

def update_user(email, new_data):
    """Updates a user's information based on their email."""
    session = Session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        # Update fields based on the keys present in the new_data dictionary
        for key, value in new_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        session.commit()
        print(f"User {email} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating user: {str(e)}")
    finally:
        session.close()

def delete_user(email):
    """Deletes a user based on their email."""
    session = Session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        # Confirmation prompt
        confirmation = input("Are you sure you want to delete this user? Type 'DELETE' to confirm: ")
        if confirmation != 'DELETE':
            print("Deletion cancelled.")
            return
        
        # Delete associated events before deleting the user
        session.query(Event).filter_by(user_id=user.id).delete()
        
        session.delete(user)
        session.commit()
        print(f"User {email} and their associated events deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting user: {str(e)}")
    finally:
        session.close()

def change_user_password(email, new_password):
    """Change a user's password."""
    session = Session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if user:
            # Hash the new password
            user.password = generate_password_hash(new_password)
            session.commit()
            print(f"Password for user {email} changed successfully.")
        else:
            print(f"User with email {email} not found.")
    except Exception as e:
        session.rollback()
        print(f"Error changing password: {str(e)}")
    finally:
        session.close()

# Menu for managing users
def menu():
    while True:
        print("\nUser Management Menu:")
        print("1. Add User")
        print("2. View All Users")
        print("3. Update User")
        print("4. Delete User")
        print("5. Change User Password")
        print("6. Exit")

        choice = input("Choose an option: ")

        if choice == '1':
            email = input("Email: ")
            password = input("Password: ")
            first_name = input("First Name: ")
            last_name = input("Last Name: ")
            phone_number = input("Phone Number: ")
            business_name = input("Business Name: ")
            stripe_connect_id = input("Stripe Connect ID: ")
            website_url = input("Website URL (optional): ")
            vat_number = input("VAT Number (optional): ")
            house_name_or_number = input("House Name/Number: ")
            street = input("Street: ")
            locality = input("Locality (optional): ")
            town = input("Town: ")
            postcode = input("Postcode: ")
            flat_rate = float(input("Flat Rate: "))
            promo_rate = float(input("Promo Rate (optional, press Enter to skip): ") or 0)
            promo_rate_date_end = input("Promo Rate End Date (optional, press Enter to skip): ")

            add_user(email, password, first_name, last_name, phone_number, business_name, stripe_connect_id, 
                     website_url, vat_number, house_name_or_number, street, locality, town, postcode, 
                     flat_rate, promo_rate if promo_rate != 0 else None, promo_rate_date_end if promo_rate_date_end else None)

        elif choice == '2':
            view_users()

        elif choice == '3':
            email = input("Enter the email of the user to update: ")
            field_to_update = input("Which field do you want to update? (e.g., first_name, last_name, phone_number, flat_rate, etc.): ")
            new_value = input(f"Enter the new value for {field_to_update}: ")
            update_user(email, {field_to_update: new_value})

        elif choice == '4':
            email = input("Enter the email of the user to delete: ")
            delete_user(email)

        elif choice == '5':
            email = input("Enter the email of the user whose password you want to change: ")
            new_password = input("Enter the new password: ")
            change_user_password(email, new_password)

        elif choice == '6':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    # Create the tables if they don't exist
    Base.metadata.create_all(engine)
    menu()
