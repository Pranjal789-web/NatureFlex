from flask import Flask, request, jsonify
from flask_cors import CORS

from werkzeug.security import generate_password_hash, check_password_hash

import jwt
import os

from datetime import datetime, date, timedelta

from dotenv import load_dotenv

from database import get_connection


# =========================
# CONFIGURATION
# =========================

load_dotenv()

app = Flask(__name__)

CORS(app)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)


# =========================
# CONSTANTS
# =========================

STEPS_PER_SEED = 100
TREE_COST = 10
FOREST_SIZE = 100


# =========================
# HELPER FUNCTIONS
# =========================

def create_token(user_id):

    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )


def get_user_from_token():

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    try:

        token = auth_header.split(" ")[1]

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        user_id = payload["user_id"]

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            user = cursor.fetchone()

        connection.close()

        return user

    except Exception:

        return None


def user_response(user):

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "height": float(user["height"]) if user["height"] else None,
        "weight": float(user["weight"]) if user["weight"] else None,
        "seeds": user["seeds"],
        "trees": user["trees"]
    }


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "🌱 NatureFlex Backend is running!",
        "status": "success"
    })


# =========================
# SIGNUP
# =========================

@app.route("/api/signup", methods=["POST"])
def signup():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    height = data.get("height")
    weight = data.get("weight")


    if not name or not email or not password:

        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            # Check existing account

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()


            if existing_user:

                return jsonify({
                    "success": False,
                    "message": "An account with this email already exists."
                }), 409


            # Secure password hashing

            password_hash = generate_password_hash(password)


            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    height,
                    weight
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    password_hash,
                    height,
                    weight
                )
            )


            user_id = cursor.lastrowid


        connection.commit()


        token = create_token(user_id)


        return jsonify({

            "success": True,

            "message": "Account created successfully.",

            "token": token,

            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "height": height,
                "weight": weight,
                "seeds": 0,
                "trees": 0
            }

        }), 201


    finally:

        connection.close()


# =========================
# LOGIN
# =========================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")


    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()


            if not user:

                return jsonify({
                    "success": False,
                    "message": "Invalid email or password."
                }), 401


            if not check_password_hash(
                user["password_hash"],
                password
            ):

                return jsonify({
                    "success": False,
                    "message": "Invalid email or password."
                }), 401


            token = create_token(user["id"])


            return jsonify({

                "success": True,

                "message": "Login successful.",

                "token": token,

                "user": user_response(user)

            })


    finally:

        connection.close()


# =========================
# GET PROFILE
# =========================

@app.route("/api/profile", methods=["GET"])
def profile():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    return jsonify({
        "success": True,
        "user": user_response(user)
    })


# =========================
# ADD STEPS
# =========================

@app.route("/api/steps", methods=["POST"])
def add_steps():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    data = request.get_json()

    steps_to_add = int(
        data.get("steps", 0)
    )


    if steps_to_add <= 0:

        return jsonify({
            "success": False,
            "message": "Steps must be greater than zero."
        }), 400


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            today = date.today()


            # Find today's activity

            cursor.execute(
                """
                SELECT *
                FROM activity
                WHERE user_id = %s
                AND activity_date = %s
                """,
                (
                    user["id"],
                    today
                )
            )

            activity = cursor.fetchone()


            if activity:

                old_steps = activity["steps"]

                old_seeds = activity["seeds_earned"]

                new_steps = old_steps + steps_to_add

                new_seeds = (
                    new_steps // STEPS_PER_SEED
                )

                additional_seeds = (
                    new_seeds - old_seeds
                )


                cursor.execute(
                    """
                    UPDATE activity

                    SET
                        steps = %s,
                        seeds_earned = %s

                    WHERE user_id = %s
                    AND activity_date = %s
                    """,
                    (
                        new_steps,
                        new_seeds,
                        user["id"],
                        today
                    )
                )


            else:

                new_steps = steps_to_add

                new_seeds = (
                    new_steps // STEPS_PER_SEED
                )

                additional_seeds = new_seeds


                cursor.execute(
                    """
                    INSERT INTO activity
                    (
                        user_id,
                        steps,
                        seeds_earned,
                        activity_date
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user["id"],
                        new_steps,
                        new_seeds,
                        today
                    )
                )


            # Add seeds to user's total

            cursor.execute(
                """
                UPDATE users

                SET seeds = seeds + %s

                WHERE id = %s
                """,
                (
                    additional_seeds,
                    user["id"]
                )
            )


        connection.commit()


        return jsonify({

            "success": True,

            "message": "Steps added successfully.",

            "steps_added": steps_to_add,

            "seeds_earned": additional_seeds

        })


    finally:

        connection.close()


# =========================
# GET TODAY'S ACTIVITY
# =========================

@app.route("/api/activity/today", methods=["GET"])
def today_activity():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    steps,
                    seeds_earned,
                    activity_date

                FROM activity

                WHERE user_id = %s
                AND activity_date = %s
                """,
                (
                    user["id"],
                    date.today()
                )
            )

            activity = cursor.fetchone()


            if not activity:

                return jsonify({
                    "success": True,
                    "steps": 0,
                    "seeds_earned": 0
                })


            return jsonify({
                "success": True,
                "steps": activity["steps"],
                "seeds_earned": activity["seeds_earned"]
            })


    finally:

        connection.close()


# =========================
# PLANT TREE
# =========================

@app.route("/api/tree/plant", methods=["POST"])
def plant_tree():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT seeds, trees
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (user["id"],)
            )

            current_user = cursor.fetchone()


            if current_user["seeds"] < TREE_COST:

                return jsonify({

                    "success": False,

                    "message":
                    "You need 10 seeds to plant a tree."

                }), 400


            if current_user["trees"] >= FOREST_SIZE:

                return jsonify({

                    "success": False,

                    "message":
                    "You have already completed this forest."

                }), 400


            cursor.execute(
                """
                UPDATE users

                SET
                    seeds = seeds - %s,
                    trees = trees + 1

                WHERE id = %s
                """,
                (
                    TREE_COST,
                    user["id"]
                )
            )


        connection.commit()


        return jsonify({

            "success": True,

            "message": "🌳 Tree planted successfully!",

            "seeds_remaining":
                current_user["seeds"] - TREE_COST,

            "trees":
                current_user["trees"] + 1

        })


    finally:

        connection.close()


# =========================
# FOREST STATUS
# =========================

@app.route("/api/forest", methods=["GET"])
def forest_status():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    trees = user["trees"]

    progress = min(
        (trees / FOREST_SIZE) * 100,
        100
    )


    return jsonify({

        "success": True,

        "trees": trees,

        "required_trees": FOREST_SIZE,

        "progress": progress,

        "completed":
            trees >= FOREST_SIZE

    })


# =========================
# REDEEM REWARD
# =========================

@app.route("/api/rewards/redeem", methods=["POST"])
def redeem_reward():

    user = get_user_from_token()


    if not user:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    connection = get_connection()


    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT trees
                FROM users
                WHERE id = %s
                """,
                (user["id"],)
            )

            current_user = cursor.fetchone()


            if current_user["trees"] < FOREST_SIZE:

                return jsonify({

                    "success": False,

                    "message":
                    "Complete one forest before redeeming a reward."

                }), 400


            cursor.execute(
                """
                INSERT INTO rewards
                (
                    user_id,
                    reward_name,
                    status
                )
                VALUES (%s, %s, %s)
                """,
                (
                    user["id"],
                    "NatureFlex Forest Reward",
                    "requested"
                )
            )


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "🎁 Reward redemption request created."

        })


    finally:

        connection.close()


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )