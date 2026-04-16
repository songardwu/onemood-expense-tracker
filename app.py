import os
from datetime import timedelta
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, render_template
from flask.json.provider import DefaultJSONProvider
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

load_dotenv('.env.local')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Decimal → JSON（保留精度）
class DecimalJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(round(o, 2))
        return super().default(o)

app.json_provider_class = DecimalJSONProvider
app.json = DecimalJSONProvider(app)

app.secret_key = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = bool(os.environ.get('VERCEL'))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(days=7)

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["120/minute"],
                  storage_uri="memory://")


# =====================
# 安全 HTTP headers
# =====================
from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('login.html', error='操作逾時，請重新操作。'), 400


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'"
    return response


# =====================
# DB 連線自動回收
# =====================
from services.utils import close_db
app.teardown_appcontext(close_db)


# =====================
# 註冊 Blueprints
# =====================
from routes.auth import bp as auth_bp
from routes.reports import bp as reports_bp
from routes.vendors import bp as vendors_bp
from routes.users import bp as users_bp
from routes.projects import bp as projects_bp

app.register_blueprint(auth_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(vendors_bp)
app.register_blueprint(users_bp)
app.register_blueprint(projects_bp)

# 登入端點頻率限制（防暴力破解）
limiter.limit("5/minute")(app.view_functions['auth.login'])


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
