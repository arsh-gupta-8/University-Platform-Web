from flask import Flask, render_template
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask("__main__")

load_dotenv()
client = MongoClient(os.getenv("DB_URI"), server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected!")
except Exception as e:
    print(e)

db = client.datastore
user_collection = db.user_collection

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html')

if __name__ == '__main__':
    app.run(debug=True)