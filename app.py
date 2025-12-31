from flask import Flask, render_template, url_for, request, redirect, session, jsonify
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import uuid
from bson.objectid import ObjectId

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

app = Flask("__main__")
FLASK_KEY = os.getenv("FLASK_KEY") 
app.secret_key = FLASK_KEY

DB_URI = os.getenv("DB_URI") 
if not DB_URI:
    print("Database environment not set")

try:
    client = MongoClient(os.getenv("DB_URI"), server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected!")
except Exception as e:
    client = None
    print(e)

if client:
    db = client.datastore
    user_collection = db.user_collection
    post_storage = db.post_storage
else:
    db = None
    user_collection = None 



CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") 
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 

oauth = OAuth(app)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile',
        'issuer': 'https://accounts.google.com'
    }
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/posts')
def posts():
    all_posts = post_storage.find().sort("_id", -1)
    return render_template('posts.html', posts=all_posts)

@app.route('/account')
def account():
    return render_template('accounts.html')



# POST CREATION

@app.route('/create-post')
def create():
    return render_template('create-post.html')

@app.route('/submit-post', methods=['POST'])
def storePost():
    tag = request.form.get('tag')
    privacy = request.form.get('privacy')
    title = request.form.get('title')
    description = request.form.get('description')

    if post_storage is None:
        return redirect(url_for('create-post'))

    if not tag or not privacy or not title or not description:
        return redirect(url_for('create-post'))
    
    try:
        post_storage.insert_one({
            "creator": session.get('username'),
            "title" : title,
            "tag": tag,
            "privacy": privacy,
            "description": description,
            "likes": 0,
            "comments": 0
        })

        return redirect(url_for('posts'))

    except Exception as e:
        print(f"Database operation failed: {e}")
        return redirect(url_for('posts'))



# GOOGLE / LOGIN

@app.route('/login')
def login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.userinfo()
    session['useremail'] = user_info.get('email')
    session['userprofile'] = user_info.get('picture')
    session['usergivenname'] = user_info.get('given_name')
    session['userID'] = str(uuid.uuid4())
    if user_collection is None:
        return redirect(url_for('home'))

    user = user_collection.find_one({"email": session['useremail']})
    if user:
        session['usergivenname'] = user.get('given_name')
        session['username'] = user.get('username')
        session['userID'] = user.get("user_id")

        if user.get('picture') != session.get('userprofile'):
            updatedprofile = { "$set": {"userprofile" : session.get('userprofile')}}
            update_result = user_collection.update_one( {"email": session.get('useremail')} , updatedprofile)
        
        return redirect(url_for('home'))

    return redirect(url_for('account_setup'))

@app.route('/account_setup')
def account_setup():
    return render_template('account_setup.html')

@app.route('/account_confirmation', methods=['POST'])
def account_confirmation():
    session['usergivenname'] = request.form.get('givenname')
    session['username'] = request.form.get('name')
    try:
        user_collection.insert_one({
            "user_id": session.get('userID'),
            "email": session.get('useremail'),
            "picture": session.get('userprofile'),
            "given_name": session.get('usergivenname'),
            "username": session.get('username'),
        })

        return redirect(url_for('posts'))

    except Exception as e:
        print(f"Database operation failed: {e}")
        return redirect(url_for('posts'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('useremail', None)
    session.pop('usergivenname', None)
    session.pop('userprofile', None)
    return redirect('/')



# LOAD POST

@app.route('/post/<post_id>')
def view_post(post_id):
    try:
        query = {"_id": ObjectId(post_id)}
    except:
        return "Invalid Post ID", 400

    post = post_storage.find_one(query)

    if post:
        return render_template('post_detail.html', post=post)
    else:
        return "Post not found", 404



# RUN

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)