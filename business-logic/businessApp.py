import os
import psycopg2
import random
import string
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import jwt


app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv('POSTGRES_HOST', 'postgres-db-service')
DB_NAME = os.getenv('POSTGRES_DB', 'url_shortner_db')
DB_USER = os.getenv('POSTGRES_USER', 'admin')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'password')
SECRET_KEY = os.getenv('SECRET_KEY')

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

def get_user_from_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    try:
        token = auth_header.split(" ")[1] 
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data['user_id']
    except:
        return None


LINKS_CREATED_COUNTER = Counter('url_shortener_links_created_total', 'Total links generated')

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/getUserName', methods=['GET'])
def get_user_name():
    user_id = get_user_from_token() 
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        return jsonify({"username": user[0]})
    return jsonify({"error": "User not found"}), 404

@app.route('/createShortUrl', methods=['POST'])
def shorten_link():
    user_id = get_user_from_token() 
    

    data = request.get_json()
    long_url = data.get('url')
    
    short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        association = None
        cur.execute("SELECT * FROM short_urls WHERE long_url = %s", (long_url,))
        existing_row = cur.fetchone()
        if existing_row:
            url_id = existing_row[0]
            short_code = existing_row[1]
            cur.execute("SELECT * FROM users_urls WHERE user_id = %s AND url_id = %s", (user_id, url_id))
            association = cur.fetchone()
            print(short_code, "-------------------")
        else:
            cur.execute(
                "INSERT INTO short_urls (short_code, long_url) VALUES (%s, %s) RETURNING url_id",
                (short_code, long_url)
            )
            url_id = cur.fetchone()[0]

        if user_id and not association:
            cur.execute(
                "INSERT INTO users_urls (user_id, url_id) VALUES (%s, %s)",
                (user_id, url_id)
            )
        
        conn.commit()
        LINKS_CREATED_COUNTER.inc()
        return jsonify({"short_code": short_code, "url": f"http://localhost/{short_code}"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/getLongUrl/<short_code>', methods=['GET'])
def get_long_url(short_code):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM short_urls WHERE short_code = %s", (short_code,))
    data = cur.fetchone()
    url = data[2] if data else None
    counter = data[3] if data else None
    if url:
        cur.execute(
            "UPDATE short_urls SET click_count = click_count + 1 WHERE short_code = %s",
            (short_code,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"long_url": url})
    cur.close()
    conn.close()
    return jsonify({"error": "Short URL not found"}), 404

@app.route('/getUserUrls', methods=['GET'])
def get_user_urls():
    user_id = get_user_from_token() 
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT su.short_code, su.long_url, su.click_count, uu.created_at
        FROM short_urls su
        JOIN users_urls uu ON su.url_id = uu.url_id
        WHERE uu.user_id = %s
    """, (user_id,))
    
    urls = cur.fetchall()
    cur.close()
    conn.close()

    url_list = [{"short_code": row[0], "long_url": row[1], "click_count": row[2], "created_at": row[3]} for row in urls]
    return jsonify({"urls": url_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 

