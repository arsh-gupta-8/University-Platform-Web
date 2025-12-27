from flask import Flask, render_template, url_for, request, redirect, session
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import uuid

load_dotenv()

app = Flask("__main__")
FLASK_KEY = os.getenv("FLASK_KEY") 
app.secret_key = FLASK_KEY

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
    post_storage = db.post_storage
else:
    db = None
    user_collection = None 



CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") 
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/posts')
def posts():
    all_posts = db.posts.find().sort("_id", -1)
    return render_template('posts.html', posts=all_posts)



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

    if not post_storage:
        return redirect(url_for('create-post'))

    if not tag or not privacy or not title or not description:
        return redirect(url_for('create-post'))
    
    try:
        post_storage.insert_one({
            "creator": session["username"],
            "title" : title,
            "tag": tag,
            "privacy": privacy,
            "description": description,
            "likes": 0,
            "comments": 0
        })

        return render_template('posts.html')

    except Exception as e:
        print(f"Database operation failed: {e}")
        return render_template('posts.html')



# GOOGLE / LOGIN

@app.route('/login')
def login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)
    # return render_template('login.html')

@app.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['useremail'] = user_info.get('email')
    session['userprofile'] = user_info.get('picture')
    session['usergivenname'] = user_info.get('given_name')

    if user_collection is None:
        return redirect(url_for('home'))

    user = user_collection.find_one({"email": session['useremail']})
    if user:
        if user.get('picture') != session['userprofile']:
            updatedprofile = { "$set": {"userprofile" : session['userprofile']}}
            update_result = user_collection.update_one( {"email": session['useremail']} , updatedprofile)
        return redirect(url_for('home'))

    else:
        try:
            uniqueID = str(uuid.uuid4())
            user_collection.insert_one({
                "user_id": uniqueID,
                "email": session['useremail'],
                "userprofile": session['userprofile'],
                "usergivenname": session['usergivenname']
            })

            return render_template('posts.html')

        except Exception as e:
            print(f"Database operation failed: {e}")
            return render_template('posts.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# @app.route('/register', methods=['POST'])
# def register():
#     username = request.form.get('username')
#     password = request.form.get('password')

#     if user_collection is None:
#         return redirect(url_for('accounts'))
    
#     if not username or not password:
#         return redirect(url_for('accounts'))
        
#     try:
#         user_collection.insert_one({
#             "username": username,
#             "password": password
#         })

#         return render_template('posts.html')

#     except Exception as e:
#         print(f"Database operation failed: {e}")
#         return render_template('posts.html')

# @app.route('/enteraccount', methods=['POST'])
# def enteraccount():
#     username = request.form.get('username')
#     password = request.form.get('password')

#     if not user_collection:
#         return redirect(url_for('accounts'))
    
#     if not username or not password:
#         return redirect(url_for('accounts'))
        
#     try:
#         user = user_collection.find_one({"username": username})
#         if user and user.get('password') == password:
#             session['username'] = username
#             session['userID'] = user["_id"]
#             return redirect(url_for('home'))
#         else:
#             return redirect(url_for('accounts'))  

#     except Exception as e:
#         print(f"Login database error: {e}")
#         return redirect(url_for('accounts'))

# @app.route('/accounts')
# def accounts():
#     return render_template('accounts.html')



# RUN

if __name__ == '__main__':
    app.run(debug=True)