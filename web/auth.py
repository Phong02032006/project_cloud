"""Authentication: Microsoft Entra ID (MSAL auth-code flow), email/password accounts, or local dev login."""
from functools import wraps

import msal
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

bp = Blueprint("auth", __name__)

ROLES = ("teacher", "student")


def _get_authority():
    authority = current_app.config.get("ENTRA_AUTHORITY", "").strip()
    if authority and not authority.startswith("http"):
        authority = f"https://login.microsoftonline.com/{authority}"
    return authority


def _msal_app():
    cfg = current_app.config
    return msal.ConfidentialClientApplication(
        cfg["ENTRA_CLIENT_ID"], authority=_get_authority(), client_credential=cfg["ENTRA_CLIENT_SECRET"]
    )


def _role_from_claims(claims):
    # App roles "Teacher"/"Student" are defined on the app registration and assigned to users in Entra.
    roles = {r.lower() for r in claims.get("roles", [])}
    if "teacher" in roles:
        return "teacher"
    if "student" in roles:
        return "student"
    return None


def _finish_session(user):
    csrf = session.get("csrf")
    session.clear()
    if csrf:
        session["csrf"] = csrf
    session["user_id"] = user.id
    return user


def _sign_in(external_id, name, email, role):
    user = User.query.filter_by(external_id=external_id).first()
    if user is None:
        user = User(external_id=external_id, name=name, email=email, role=role)
        db.session.add(user)
    else:
        # Entra is the source of truth: role changes there take effect on next login.
        user.name, user.email, user.role = name, email, role
    db.session.commit()
    return _finish_session(user)


@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = db.session.get(User, uid) if uid else None


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login", next=request.path))
            if role and g.user.role != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


@bp.route("/auth/entra")
def entra_login():
    if current_app.config["AUTH_MODE"] != "entra":
        return redirect(url_for("auth.login"))
    flow = _msal_app().initiate_auth_code_flow(scopes=[], redirect_uri=url_for("auth.callback", _external=True))
    session["auth_flow"] = flow
    return redirect(flow["auth_uri"])


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_app.config["AUTH_MODE"] == "entra":
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(external_id=f"local:{email}").first() if email else None
            if user and user.password_hash and check_password_hash(user.password_hash, password):
                _finish_session(user)
                return redirect(url_for("index"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role")
        if not name or not email or role not in ROLES:
            flash("Please enter your name, email and role.", "danger")
        else:
            _sign_in(f"dev:{email}", name, email, role)
            return redirect(url_for("index"))
    return render_template("login_dev.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "student")

        if not name or not email or "@" not in email:
            flash("Please enter a valid full name and email.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif role not in ROLES:
            flash("Please choose a valid role.", "danger")
        elif User.query.filter_by(external_id=f"local:{email}").first():
            flash("An account with this email already exists. Please sign in.", "danger")
        else:
            user = User(
                external_id=f"local:{email}",
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
            )
            db.session.add(user)
            db.session.commit()
            _finish_session(user)
            flash("Account created successfully!", "success")
            return redirect(url_for("index"))
    return render_template("register.html")


@bp.route("/auth/callback")
def callback():
    if current_app.config["AUTH_MODE"] != "entra":
        abort(404)
    try:
        result = _msal_app().acquire_token_by_auth_code_flow(session.pop("auth_flow", {}), request.args)
    except ValueError:  # state mismatch / replayed callback
        flash("Invalid sign-in session, please try again.", "danger")
        return redirect(url_for("index"))
    if "error" in result:
        flash(f"Sign-in failed: {result.get('error_description', result['error'])}", "danger")
        return redirect(url_for("index"))

    claims = result["id_token_claims"]
    role = _role_from_claims(claims)
    if role is None:
        return render_template("no_role.html"), 403
    email = claims.get("email") or claims.get("preferred_username") or ""
    _sign_in(claims["oid"], claims.get("name") or email, email, role)
    return redirect(url_for("index"))


@bp.route("/logout", methods=["POST"])
def logout():
    is_entra_user = g.user is not None and not g.user.external_id.startswith(("local:", "dev:"))
    csrf = session.get("csrf")
    session.clear()
    if csrf:
        session["csrf"] = csrf
    if current_app.config["AUTH_MODE"] == "entra" and is_entra_user:
        authority = _get_authority().rstrip("/")
        return redirect(
            f"{authority}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('index', _external=True)}"
        )
    return redirect(url_for("index"))
