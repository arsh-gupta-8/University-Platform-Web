from flask import Flask, render_template
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask("__main__")

load_dotenv()

DB_URI = os.getenv("DB_URI") 
if not DB_URI:
    print("Database environment not set")

try:
    client = MongoClient(os.getenv("DB_URI"), server_api=ServerApi('1'))
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected!")
except Exception as e:
    client = None
    print(e)

if client:
    db = client.datastore
    user_collection = db.user_collection
else:
    db = None
    user_collection = None 

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html')

@app.route('/accounts')
def accounts():
    return render_template('accounts.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if not user_collection:
        return redirect(url_for('accounts'))
    
    if not username or not password:
        return redirect(url_for('accounts'))
        
    try:
        user_collection.insert_one({
            "username": username,
            "password": password
        })

        return render_template('posts.html')

    except Exception as e:
        print(f"Database operation failed: {e}")
        return render_template('posts.html')

if __name__ == '__main__':
    app.run(debug=True)