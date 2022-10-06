#app.py
from traceback import print_list
from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify
import psycopg2 #pip install psycopg2 
import psycopg2.extras
import re 
from werkzeug.security import generate_password_hash, check_password_hash
from elasticsearch import Elasticsearch, helpers 
import os
from subprocess import Popen, PIPE, STDOUT
#import es_core_news_md
#nlp = es_core_news_md.load()
from collections import Counter
#import spacy
#from spacy import displacy
import pandas as pd
#from txtai.pipeline import Similarity
from txtai.embeddings import Embeddings
import json
#import pickle


#get secret key
es = Elasticsearch([{'host': '5.161.145.1', 'port': 9200, 'scheme': 'http'}], request_timeout=6000, retry_on_timeout=True)
SECRET_KEY = 'karpify123'
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

df = pd.read_json('tarjetas_revolving.json')
df = df.rename(columns={0: "x", "jurisprudencias": "texto"})
dataset = df["texto"]
buffer = []
rows = 0

for x, text in enumerate(dataset):
  # Article record
  article = {"_id": x, "_index": "articles", "title": text}

  # Buffer article
  buffer.append(article)

  # Increment number of articles processed
  rows += 1

  # Bulk load every 1000 records
  if rows % 1000 == 0:
    helpers.bulk(es, buffer)
    buffer = []

    print("Inserted {} articles".format(rows), end="\r")

if buffer:
  helpers.bulk(es, buffer)
#dataset = dataset.apply(lambda x: re.sub(r'\n', ' ', x))
#txtai_data = []
#i=0
#for text in dataset:
#    txtai_data.append((i, text, None))
#    i=i+1

#embeddings = Embeddings({
    
#    "path": "sentence-transformers/all-MiniLM-L6-v2"
#})
#embeddings.index(txtai_data)


conn = psycopg2.connect(database="d66kt3el70imqq", user="skjrhrkmxmldey", password="64a8e238f3a08a513de91dce3b4559df285c294ed23225d14463c914ffc96d07", host="ec2-3-216-167-65.compute-1.amazonaws.com", port=5432)

@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
    
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route("/ajaxlivesearch",methods=["POST","GET"])
def ajaxlivesearch():
    if request.method == "POST":
        search_word = request.form['query']
        print(search_word)
        if search_word == "":
            query = print(index="articles", body={"query": {"match_all": {}}})
            employee = query
        else:
            query_ = {
                        "size": 5,
                        "query": {
                            "query_string": {"query": search_word}
                        }
                    }   

            results = []
            for result in es.search(index="articles", body=query_)["hits"]["hits"]:
                source = result["_source"]
                results.append((min(result["_score"], 18) / 18, source["title"]))

            data = []
            for item in results:
                row={}
                row['_score'] = item[0]
                row['_source'] = item[1]
                data.append(row)
                print(data)
                

    return jsonify({'htmlresponse': render_template('response.html', txtai_data=data)})

@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(password)
 
        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()
 
        if account:
            password_rs = account['password']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')
 
    return render_template('login.html')
  
@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
 
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
    
        _hashed_password = generate_password_hash(password)
 
        #Check if account exists using MySQL
        cursor.execute('SELECT * FROM userss WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO users (fullname, username, password, email) VALUES (%s,%s,%s,%s)", (fullname, username, _hashed_password, email))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('register.html')
   
   
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))
  
@app.route('/profile')
def profile(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/response')
def response():
    # Check if user is loggedin
    if 'loggedin' in session:
    
        # User is loggedin show them the home page
        return render_template('response.html')
    # User is not loggedin redirect to login page
    return redirect(url_for('response'))
 
if __name__ == "__main__":

    app.run(host='0.0.0.0')
