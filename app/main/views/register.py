from datetime import (
    datetime,
    timedelta
)
from functools import wraps

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from flask_login import current_user, login_fresh

from app import user_api_client
from app.main import main
from app.main.forms import RegisterUserForm
from app.main.views.sign_in import (
    accept_invitation,
    has_invitation,
    is_invitee,
    redirect_to_services,
    set_next_url
)
from app.main.views.verify import two_factor_verification_enabled


def require_authenticated_user(fn):

    @wraps(fn)
    def wrapped(*args, **kwargs):

        if 'user_info' in session:
            return fn(*args, **kwargs)

        if not current_user.is_authenticated:
            set_next_url(request.full_path)
            return current_app.login_manager.unauthorized()

        if not login_fresh():
            set_next_url(request.full_path)
            return current_app.login_manager.needs_refresh()

        return fn(*args, **kwargs)

    return wrapped


@main.route('/register', methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:
        return redirect_to_services()

    if registration_form_submitted():
        user = register_user()
        add_user_to_session(user)

        if two_factor_verification_enabled():
            send_verify_code(user)

        return redirect(url_for('main.verify'))

    if 'user_info' not in session:
        set_next_url(request.full_path)
        return redirect(url_for('main.sign_in'))

    else:
        user_info = session['user_info']
        current_user.name = user_info.get('name')
        current_user.email_address = user_info.get('email')
        current_user.mobile_number = user_info.get('mobile')

    return registration_form()


def registration_form_submitted():
    form = RegisterUserForm()
    if request.method.upper() == 'POST':

        if not form.validate():
            return False

        current_user.name = form.name.data
        current_user.email_address = form.email_address.data
        current_user.mobile_number = form.mobile_number.data
        return True


def registration_form():
    form = RegisterUserForm()

    prepopulate(form.name, user_attr('name'))
    prepopulate(form.email_address, user_attr('email_address'))
    prepopulate(form.mobile_number, user_attr('mobile_number'))

    # del form.password

    return render_template('views/register.html', form=form)


def prepopulate(field, value):
    if value:
        field.data = value
        field.disabled = ''


def user_attr(attr):
    return getattr(current_user, attr, None)


@main.route('/register-from-invite', methods=['GET', 'POST'])
@require_authenticated_user
def register_from_invite():

    if not has_invitation():
        abort(404)

    if not is_invitee(current_user):
        abort(400)

    if not user_already_registered():
        register_user()
        send_verify_code()

    add_user_to_session()
    accept_invitation()

    return redirect(url_for('main.verify'))


def default_current_user(fn):

    def wrapper(user=None, *args, **kwargs):
        if user is None:
            user = current_user

        return fn(user, *args, **kwargs)

    return wrapper


@default_current_user
def user_already_registered(user):
    return user_api_client.is_email_unique(user.email_address)


@default_current_user
def add_user_to_session(user):
    session.update({
        'user_details': {"email": user.email_address, "id": user.id},
        'expiry_date': str(datetime.utcnow() + timedelta(hours=1))
    })


@default_current_user
def register_user(user):
    return user_api_client.register_user(
        user.name,
        user.email_address,
        user.mobile_number,
        'password')


@default_current_user
def send_verify_email(user):
    user_api_client.send_verify_email(user.id, user.email_address)


@default_current_user
def send_verify_code(user):
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)


@default_current_user
def send_already_registered_email(user):
    user_api_client.send_already_registered_email(user.id, user.email_address)


@main.route('/registration-continue')
def registration_continue():
    return render_template('views/registration-continue.html')
