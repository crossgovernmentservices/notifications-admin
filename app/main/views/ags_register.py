from datetime import datetime, timedelta
from functools import wraps
import json

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for)
from flask_login import current_user, login_fresh, login_user

from app import user_api_client
from app.main import main
from app.main.forms import RegisterUserForm
from app.main.views.ags_sign_in import (
    accept_invitation,
    feature_switch_active,
    has_invitation,
    is_invitee,
    redirect_to_services)


DEFAULT_PASSWORD = 'ags_default_password'


@main.route('/ags-register', methods=['GET', 'POST'])
def ags_register():

    if not feature_switch_active():
        return redirect(url_for('main.register'))

    if current_user.is_authenticated:
        return redirect_to_services()

    if registration_form_submitted():
        user = register_user()
        add_user_to_session(user)

        try:
            login_user(activated(user))
            return redirect(url_for('main.add_service', first='first'))

        finally:
            del session['user_details']

    if not ags_authenticated():
        set_next_url(request.full_path)
        current_app.logger.debug(
            'SET NEXT_URL TO {}'.format(request.full_path))
        return redirect(url_for('main.ags_sign_in'))

    return registration_form()


def require_authenticated_user(fn):

    @wraps(fn)
    def wrapped(*args, **kwargs):

        if ags_authenticated():
            return fn(*args, **kwargs)

        if not current_user.is_authenticated:
            set_next_url(request.full_path)
            return current_app.login_manager.unauthorized()

        if not login_fresh():
            set_next_url(request.full_path)
            return current_app.login_manager.needs_refresh()

        return fn(*args, **kwargs)

    return wrapped


@main.route('/ags-register-from-invite', methods=['GET', 'POST'])
@require_authenticated_user
def ags_register_from_invite():

    if not feature_switch_active():
        return redirect(url_for('main.register_from_invite'))

    if not has_invitation():
        abort(404)

    if not is_invitee(current_user):
        abort(400)

    if not user_already_registered():
        register_user()

    add_user_to_session()
    accept_invitation()

    return redirect(url_for('main.verify'))


def default_current_user(fn):

    @wraps(fn)
    def wrapper(user=None, *args, **kwargs):
        if user is None:
            user = current_user

        return fn(user, *args, **kwargs)

    return wrapper


def activated(user):
    return user_api_client.activate_user(user)


@default_current_user
def add_user_to_session(user):
    session.update({
        'user_details': {'email': user.email_address, 'id': user.id},
        'expiry_date': str(datetime.utcnow() + timedelta(hours=1))
    })


def ags_authenticated():
    return session.get('auth_data', request.environ.get('auth_data'))


def prepopulate(field, value):
    if value:
        field.data = value
        field.disabled = ''


@default_current_user
def register_user(user):
    return user_api_client.register_user(
        user.name,
        user.email_address,
        user.mobile_number,
        DEFAULT_PASSWORD)


def registration_form():
    form = RegisterUserForm()
    del form.password

    if 'auth_data' in session:
        auth_data = json.loads(session['auth_data'])
    else:
        auth_data = request.environ.get('auth_data', {})

    prepopulate(form.name, auth_data['userinfo'].get('name'))
    prepopulate(form.email_address, auth_data['userinfo'].get('email'))
    prepopulate(form.mobile_number, auth_data['userinfo'].get('mobile'))

    return render_template('views/ags_register.html', form=form)


def registration_form_submitted():
    form = RegisterUserForm()
    del form.password

    if request.method.upper() == 'POST':

        if not form.validate():
            return False

        current_user.name = form.name.data
        current_user.email_address = form.email_address.data
        current_user.mobile_number = form.mobile_number.data
        return True


def set_next_url(url):
    session['next_url'] = url
    if session['next_url'] is None:
        del session['next_url']


@default_current_user
def user_already_registered(user):
    return user_api_client.is_email_unique(user.email_address)
