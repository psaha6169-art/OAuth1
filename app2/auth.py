from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    name="idp",  # your provider name
    client_id=os.getenv("OAUTH_CLIENT_ID"),
    client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
    server_metadata_url=f'{os.getenv("OAUTH_ISSUER")}/.well-known/openid-configuration',
    # If your provider doesn’t support discovery, comment the line above
    # and explicitly set:
    authorize_url=os.getenv("OAUTH_AUTHORIZATION_ENDPOINT"),
    access_token_url=os.getenv("OAUTH_TOKEN_ENDPOINT"),
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",  # PKCE
    },
)

@app.route("/")
def home():
    user = session.get("user")
    if not user:
        return '<a href="/login">Sign in</a>'
    return f"""
      <h3>hi {user.get('email')}</h3>
      <pre>{user}</pre>
      <a href="/logout">logout</a>
    """

@app.route("/login")
def login():
    redirect_uri = os.getenv("REDIRECT_URI")
    return oauth.idp.authorize_redirect(redirect_uri)

@app.route("/callback")
def callback():
    token = oauth.idp.authorize_access_token()  # exchanges code → tokens (uses PKCE under the hood)
    # ID token (OIDC) often contains basic profile; userinfo endpoint is cleanest:
    resp = oauth.idp.get(os.getenv("OAUTH_USERINFO_ENDPOINT"))
    userinfo = resp.json()
    # minimal session (don’t store raw tokens in cookies)
    session["user"] = {
        "sub": userinfo.get("sub"),
        "email": userinfo.get("email"),
        "name": userinfo.get("name"),
        "picture": userinfo.get("picture"),
    }
    # if you need API access later, store access/refresh tokens server-side (DB/kv), not in the session cookie
    session["has_login"] = True
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
