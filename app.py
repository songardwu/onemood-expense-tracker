import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

load_dotenv('.env.local')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.secret_key = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = bool(os.environ.get('VERCEL'))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(days=7)

csrf = CSRFProtect(app)


# =====================
# 安全 HTTP headers
# =====================
@app.errorhandler(400)
def handle_csrf_error(e):
    if 'CSRF' in str(e):
        return render_template('login.html', error='操作逾時，請重新操作。'), 400
    return e


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'"
    return response


# =====================
# 註冊 Blueprints
# =====================
from routes.auth import bp as auth_bp
from routes.reports import bp as reports_bp
from routes.vendors import bp as vendors_bp
from routes.users import bp as users_bp

app.register_blueprint(auth_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(vendors_bp)
app.register_blueprint(users_bp)


if __name__ == '__main__':
    app.run(debug=True)
