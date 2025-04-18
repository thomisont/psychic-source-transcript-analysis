from flask import Blueprint, request, render_template, redirect, url_for, make_response, current_app, g, flash
from functools import wraps
from tools.supabase_client import SupabaseClient
import logging
import os

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

COOKIE_NAME = 'access_token'


def get_supabase():
    # helper to fetch supabase client from app context
    if hasattr(current_app, 'supabase_client'):
        return current_app.supabase_client
    raise RuntimeError('Supabase client not attached to app.')


def set_current_user_from_cookie():
    """Populate g.user if valid JWT cookie found."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        g.user = None
        return
    supabase = get_supabase().client
    try:
        resp = supabase.auth.get_user(token)  # returns dict or raises
        g.user = resp.user if hasattr(resp, 'user') else resp
    except Exception as e:
        logging.warning(f"Invalid access token: {e}")
        g.user = None

    # Dev auto‑login helper
    if g.user is None and os.getenv('FLASK_ENV') == 'development':
        dev_email = os.getenv('DEV_AUTO_LOGIN_EMAIL')
        if dev_email:
            try:
                sb = get_supabase().client
                res = sb.auth.admin.get_user_by_email(dev_email)
                if res and res.user:
                    g.user = {"email": dev_email, "id": res.user.id}
                    logging.info(f"DEV_AUTO_LOGIN: Auto‑logged as {dev_email}")
            except Exception as dev_err:
                logging.warning(f"DEV_AUTO_LOGIN failed: {dev_err}")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, 'user', None) is None:
            return redirect(url_for('auth.login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.before_app_request
def _load_user():
    set_current_user_from_cookie()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        supabase = get_supabase().client
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session = res.session if hasattr(res, 'session') else res
            # Retrieve token depending on object type
            token = session['access_token'] if isinstance(session, dict) else getattr(session, 'access_token', None)
            if not token:
                flash('Invalid credentials', 'danger')
                return render_template('login.html')
            # Use extracted token
            resp = make_response(redirect(request.args.get('next') or url_for('main.index')))
            resp.set_cookie(COOKIE_NAME, token, httponly=True, secure=False)  # secure=True in prod
            return resp
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('Login failed', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    resp = make_response(redirect(url_for('auth.login')))
    resp.delete_cookie(COOKIE_NAME)
    return resp 