import json

from flask import (
    abort,
    after_this_request,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from flask_login import login_user
from itsdangerous import SignatureExpired
from notifications_utils.url_safe_token import check_token

from app import user_api_client
from app.main import main
from app.main.forms import TwoFactorForm
from app.utils import redirect_to_sign_in


@main.route('/toggle-2fa-enabled')
def toggle_2fa():
    after_this_request(toggle_two_factor_verification_enabled)
    return redirect(url_for('main.index'))


def toggle_two_factor_verification_enabled(response):
    response.set_cookie(
        'enable_2fa',
        '0' if two_factor_verification_enabled() else '1')
    return response


@main.route('/verify', methods=['GET', 'POST'])
@redirect_to_sign_in
def verify():
    if not two_factor_verification_enabled() or second_factor_verified():
        return continue_registration()

    return two_factor_prompt()


def two_factor_verification_enabled():
    return request.cookies.get('enable_2fa', '0') == '1'


def second_factor_verified():
    return two_factor_form().validate_on_submit()


def two_factor_form():
    return TwoFactorForm(check_form)


def check_form(code):
    return user_api_client.check_verify_code(session_user_id(), code, 'sms')


def session_user_id():
    return session['user_details']['id']


def get_user_by_id(user_id):
    return user_api_client.get_user(user_id)


def continue_registration():
    user = get_user_by_id(session_user_id())

    try:
        login_user(activated(user))
        return redirect(url_for('main.add_service', first='first'))

    finally:
        del session['user_details']


def activated(user):
    return user_api_client.activate_user(user)


def two_factor_prompt():
    return render_template('views/two-factor.html', form=two_factor_form())


@main.route('/verify-email/<token>')
def verify_email(token):
    try:
        user_id, code = parse_token(token)
        verify_second_factor, error = check_verify_code(user_id, code)
        user = get_user_or_404(user_id)

        if user.is_active:
            flash("That verification link has expired.")
            return redirect(url_for('main.sign_in'))

        add_user_to_session(user)

        if verify_second_factor:

            if two_factor_verification_enabled():
                send_verify_code(user)

            return redirect('verify')

        if code_expired(error):
            return resend_email_verification()

        flash((
            "There was a problem verifying your account. "
            "Error message: '{}'").format(error))
        return redirect(url_for('main.index'))

    except SignatureExpired:
        return resend_email_verification()


def parse_token(token):
    token_data = check_token(
        token,
        current_app.config['SECRET_KEY'],
        current_app.config['DANGEROUS_SALT'],
        current_app.config['EMAIL_EXPIRY_SECONDS'])
    decoded = json.loads(token_data)
    return decoded['user_id'], decoded['secret_code']


def check_verify_code(user_id, code):
    result = user_api_client.check_verify_code(user_id, code, 'email')
    return result[0], result[1]


def send_verify_code(user):
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)


def code_expired(error):
    return error == 'Code has expired'


def get_user_or_404(user_id):
    user = user_api_client.get_user(user_id)
    if not user:
        abort(404)
    return user


def add_user_to_session(user):
    session.update({
        'user_details': {"email": user.email_address, "id": user.id}
    })


def resend_email_verification():
    flash(
        "The link in the email we sent you has expired. "
        "We've sent you a new one.")
    return redirect(url_for('main.resend_email_verification'))
