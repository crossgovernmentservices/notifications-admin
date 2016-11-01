from datetime import datetime, timedelta
from functools import wraps

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for)
from flask_login import current_user, login_fresh

from app import user_api_client
from app.main import main
from app.main.forms import RegisterUserForm
from app.main.views.ags_sign_in import (
    accept_invitation,
    has_invitation,
    is_invitee,
    redirect_to_services,
    set_next_url)


DEFAULT_PASSWORD = 'ags_default_password'


@main.route('/ags-register', methods=['GET', 'POST'])
def ags_register():

    if current_user.is_authenticated:
        return redirect_to_services()

    if registration_form_submitted():
        user = register_user()
        add_user_to_session(user)

        return redirect(url_for('main.verify'))

    if not ags_authenticated():
        set_next_url(request.full_path)
        return redirect(url_for('main.sign_in'))

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
    return user_api_client.register_url(
        user.name,
        user.email_address,
        user.mobile_number,
        DEFAULT_PASSWORD)


def registration_form():
    form = RegisterUserForm()
    auth_data = session.get('auth_data', request.environ.get('auth_data', {}))

    prepopulate(form.name, auth_data.get('name'))
    prepopulate(form.email_address, auth_data.get('email'))
    prepopulate(form.mobile_number, auth_data.get('mobile'))

    return render_template('views/register_completion.html', form=form)


def registration_form_submitted():
    form = RegisterUserForm()

    if request.method.upper() == 'POST':

        if not form.validate():
            return False

        current_user.name = form.name.data
        current_user.email_address = form.email_address.data
        current_user.mobile_number = form.mobile_number.data
        return True


@default_current_user
def user_already_registered(user):
    return user_api_client.is_email_unique(user.email_address)
