# MODULE IMPORTS

# Flask modules
from flask import (
    Flask,
    render_template,
    request,
    url_for,
    request,
    redirect,
    abort,
    jsonify,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_talisman import Talisman
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

# Other modules
from urllib.parse import urlparse, urljoin
from datetime import datetime
# import configparser
import json
import sys
import os

# Local imports
from user import User, Anonymous
from note import Note

from vinted_helper import getVintedProducts

from category import Category
from email_utility import send_email, send_registration_email, send_message_email
from verification import confirm_token


# Create app
app = Flask(__name__)

# Configuration
# config = configparser.ConfigParser()
# config.read("configuration.ini")

# Create Pymongo
mongo = PyMongo(app)
# print(mongo.db, "kings only")
# Create Bcrypt
bc = Bcrypt(app)

# Create Talisman
csp = {
    "default-src": [
        "'self'",
        "https://stackpath.bootstrapcdn.com",
        "https://pro.fontawesome.com",
        "https://code.jquery.com",
        "https://cdnjs.cloudflare.com",
    ]
}
talisman = Talisman(app, content_security_policy=csp)

# Create CSRF protect
csrf = CSRFProtect()
csrf.init_app(app)

# Create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"


# ROUTES


# Index
@app.route("/")
def index():
    return render_template("index.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            # Redirect to index if already authenticated
            print("error")
            return redirect(url_for("/"))
        # Render login page
        return render_template("login.html", error=request.args.get("error"))
    # Retrieve user from database
    users = mongo.db.users
    user_data = users.find_one({"email": request.form["email"]}, {"_id": 0})
    if user_data:
        # Check password hash
        if bc.check_password_hash(user_data["password"], request.form["pass"]):
            # Create user object to login (note password hash not stored in session)
            user = User.make_from_dict(user_data)
            login_user(user)

            # Check for next argument (direct user to protected page they wanted)
            next = request.args.get("next")
            if not is_safe_url(next):
                return abort(400)

            # Go to profile page after login
            return redirect(next or url_for("profile"))

    # Redirect to login page on error
    return redirect(url_for("login", error=1))


# Register
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        # Trim input data
        email = request.form["email"].strip()
        title = request.form["title"].strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        password = request.form["pass"].strip()
        print(email, title, first_name, last_name, password)

        print(mongo.db)
        users = mongo.db.users

        # Check if email address already exists
        existing_user = users.find_one({"email": email}, {"_id": 0})

        if existing_user is None:
            logout_user()
            # Hash password ABCabc123!
            hashpass = bc.generate_password_hash(password).decode("utf-8")
            # Create user object (note password hash not stored in session)
            new_user = User(title, first_name, last_name, email)
            # Create dictionary data to save to database
            user_data_to_save = new_user.dict()
            user_data_to_save["password"] = hashpass

            # Insert user record to database
            if users.insert_one(user_data_to_save):
                login_user(new_user)
                # print("Fuplo Error")
                # send_registration_email(new_user)
                return redirect(url_for("profile"))
            else:
                # Handle database error
                print("Database Error")
                return redirect(url_for("register", error=2))

        # Handle duplicate email
        return redirect(url_for("register", error=1))

    # Return template for registration page if GET request
    return render_template("register.html", error=request.args.get("error"))


# Confirm email
@app.route("/confirm/<token>", methods=["GET"])
def confirm_email(token):
    logout_user()
    try:
        email = confirm_token(token)
        if email:
            if mongo.db.users.update_one(
                {"email": email}, {"$set": {"verified": True}}
            ):
                return render_template("confirm.html", success=True)
    except:
        return render_template("confirm.html", success=False)
    else:
        return render_template("confirm.html", success=False)


# Verification email
@app.route("/verify", methods=["POST"])
@login_required
def send_verification_email():
    if current_user.verified == False:
        send_registration_email(current_user)
        return "Verification email sent"
    else:
        return "Your email address is already verified"


# Profile
@app.route("/profile", methods=["GET"])
@login_required
def profile():
    notes = ''
    preferences = ''
    notes_count = 0
    try:
        user = mongo.db.users.find_one({"id": current_user.id})
        
        preferences = user['preferences']
        notes_count = mongo.db.notes.count_documents(
            {"user_id": current_user.id, "deleted": False}
        )        
        with open("catalog.json", "r") as f:
            data = json.load(f)
        preferences['catalog'] = [item for item in data if item['id'] in preferences['catalog']]
        print(preferences['catalog'])
    except Exception as e:
        print(e)
    return render_template(
        "profile.html", preferences=preferences, notes_count=notes_count, title=current_user.title
    )


# Logout
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Logout
@app.route("/preferences", methods=["GET"])
@login_required
def preferences():
    preferences=dict()
    with open("size.json", "r") as f:
        data = json.load(f)
    preferences['size'] = data
    # Render data to template
    # return render_template("size.html", data=data)
    # Read data from JSON file
    with open("brand.json", "r") as f:
        data = json.load(f)
    preferences['brands'] = data
    with open("catalog.json", "r") as f:
        data = json.load(f)
        preferences['catalog'] = data

    return render_template(
        "preferences.html", preferences=preferences
    )

# POST REQUEST ROUTES
# Add category
@app.route("/add_category", methods=["POST"])
@login_required
def add_category():
    title = request.form.get("title")
    id = request.form.get("id")
    if title and id:
        print("-----------------Done--------------")
        category = Category(title, id)
        if mongo.db.category.insert_one(category.dict()):
            return "Success! Note added: " + title
    else:
        print("-----------------Error--------------")
        return "Error! Could not add note"


# Delete note
@app.route("/delete_category", methods=["POST"])
@login_required
def delete_note():
    category_id = request.form.get("category_id")
    if mongo.db.category.update_one({"id": category_id}, {"$set": {"deleted": True}}):
        return "Success! Note deleted"
    else:
        return "Error! Could not delete note"


# Change Name
@app.route("/change_name", methods=["POST"])
@login_required
def change_name():
    title = request.form["title"].strip()
    first_name = request.form["first_name"].strip()
    last_name = request.form["last_name"].strip()

    if mongo.db.users.update_one(
        {"email": current_user.email},
        {"$set": {"title": title, "first_name": first_name, "last_name": last_name}},
    ):
        return "User name updated successfully"
    else:
        return "Error! Could not update user name"


# Calculate
@app.route("/calculate_feed", methods=["POST"])
@login_required
def calculate_feed():
    print("some error")
    if request.form:
        print(request.form)
        try:
            selected_catalog = request.form.getlist("catalog[]")
            user_doc = mongo.db.users.find_one({"email": current_user.email})

            # Update the preference object with the new size value
            if not user_doc:
                user_doc['preferences'] = {}
            user_doc['preferences']['catalog'] = selected_catalog

            # Save the updated document back to MongoDB
            if mongo.db.users.replace_one({'_id': user_doc['_id']}, user_doc):
                # print(selected_catalog, "this catalog")
                # print(selected_catalog, "this catalog")
                return "User feed settings updated successfully"
        except Exception as e:
            print(e)
            return "Error! Could not update user feed settings"
    # if mongo.db.users.update_one({"email": current_user.email}, {"$set": {"title": title, "first_name": first_name, "last_name": last_name}}):
    else:
        return "Error! Could not update user feed settings"

@app.route("/set_brand", methods=["POST"])
@login_required
def set_brand():
    print("some error")
    if request.form:
        print(request.form)
        try:
            selected_catalog = request.form.getlist("brand_ids[]")
            user_doc = mongo.db.users.find_one({"email": current_user.email})
            if not user_doc:
                user_doc['preferences'] = {}
            user_doc['preferences']['brands_ids'] = selected_catalog

            # Save the updated document back to MongoDB
            if mongo.db.users.replace_one({'_id': user_doc['_id']}, user_doc):
                # print(selected_catalog, "this catalog")
                return "User feed settings updated successfully"
        except Exception as e:
            print(e)
            return "Error! Could not update user feed settings"
    # if mongo.db.users.update_one({"email": current_user.email}, {"$set": {"title": title, "first_name": first_name, "last_name": last_name}}):
    else:
        return "Error! Could not update user feed settings"

@app.route("/set_size", methods=["POST"])
@login_required
def set_size():
    print("some error")
    if request.form:
        print(request.form)
        try:
            selected_catalog = request.form.getlist("size_ids[]")
            user_doc = mongo.db.users.find_one({"email": current_user.email})

            # Update the preference object with the new size value
            if not user_doc:
                user_doc['preferences'] = {}
            user_doc['preferences']['size_ids'] = selected_catalog

            # Save the updated document back to MongoDB
            if mongo.db.users.replace_one({'_id': user_doc['_id']}, user_doc):
                # print(selected_catalog, "this catalog")
                return "User feed settings updated successfully"
        except Exception as e:
            print(e)
            return "Error! Could not update user feed settings"
    # if mongo.db.users.update_one({"email": current_user.email}, {"$set": {"title": title, "first_name": first_name, "last_name": last_name}}):
    else:
        return "Error! Could not update user feed settings"


@app.route("/test", methods=["GET"])
# @login_required
def test():
    print("some error")
    if True:
        print(request.form)
        try:
            selected_catalog = [1,2,32,3]
            user_doc = mongo.db.users.find_one({"email": current_user.email})

            # Update the preference object with the new size value
            # print('user_doc',user_doc)
            if not user_doc:
                user_doc['preferences'] = {}
            user_doc['preferences']['size_ids'] = selected_catalog

            # Save the updated document back to MongoDB
            if mongo.db.users.replace_one({'_id': user_doc['_id']}, user_doc):
                # print(selected_catalog, "this catalog")
                return "User feed settings updated successfully"
        except Exception as e:
            print(e)
            return "Error! Could not update user feed settings"
    # if mongo.db.users.update_one({"email": current_user.email}, {"$set": {"title": title, "first_name": first_name, "last_name": last_name}}):
    else:
        return "Error! Could not update user feed settings"

# Delete Account
@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user_id = current_user.id

    # Deletion flags
    user_deleted = False
    notes_deleted = False
    messages_deleted = False

    # Delete user details
    if mongo.db.users.delete_one({"id": user_id}):
        user_deleted = True
        logout_user()

    # Delete notes
    if mongo.db.notes.delete_many({"user_id": user_id}):
        notes_deleted = True

    # Delete messages
    if mongo.db.messages.delete_many(
        {"$or": [{"from_id": user_id}, {"to_id": user_id}]}
    ):
        messages_deleted = True

    return {
        "user_deleted": user_deleted,
        "notes_deleted": notes_deleted,
        "messages_deleted": messages_deleted,
    }


@app.route("/catalog")
def catalog():
    # Read data from JSON file
    with open("catalog.json", "r") as f:
        data = json.load(f)

    # Render data to template
    return render_template("catalog.html", data=data)


@app.route("/brand")
def brand():
    # Read data from JSON file
    with open("brand.json", "r") as f:
        data = json.load(f)
    
    # Render data to template
    return render_template("brand.html", data=data)


@app.route("/size")
def size():
    # Read data from JSON file
    with open("size.json", "r") as f:
        data = json.load(f)
    
    # Render data to template
    return render_template("size.html", data=data)



@app.route("/feed")
def feed():
    # user_feed = all_users.
    user = mongo.db.users.find_one({"id": current_user.id})
    if user:
        catalog_preferences = user.get(
            "preferences", []
        )  # Get the 'catalog' field as a list, default to empty list
        # return jsonify({"catalog_preferences": catalog_preferences})
        data = getVintedProducts(catalog_preferences)
        output_array = []
        for key, value in data.items():
            item = value
            item["key"] = key
            output_array.append(item)
        print(output_array[0])
        return render_template('feed.html', data=output_array)
    else:
        return jsonify({"error": "User not found"}), 404

    # Render data to template


# LOGIN MANAGER REQUIREMENTS


# Load user from user ID
@login_manager.user_loader
def load_user(userid):
    # Return user object or none
    users = mongo.db.users
    user = users.find_one({"id": userid}, {"_id": 0})
    if user:
        return User.make_from_dict(user)
    return None


# Safe URL
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

if __name__ == '__main__':
# Heroku environment
    if os.environ.get("APP_LOCATION") == "heroku":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    else:
        app.run(host="localhost", port=8080, debug=True)
