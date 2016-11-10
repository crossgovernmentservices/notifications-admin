from flask import (
    abort,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for
)
from flask.ext.login import (
    current_user,
    login_fresh,
    login_user
)

from app import (
    invite_api_client,
    oidc,
    service_api_client,
    user_api_client
)
from app.main import main
from app.main.views.two_factor import _is_safe_redirect_url


@main.route('/oidc_callback')
@oidc.callback
def oidc_callback():
    user_info = oidc.authenticate('dex', request)
    user = get_user(user_info['email'])

    if not user:
        # flash(u'You do not have an account, please register', 'error')
        # flash(u'You do not have an account, please register', 'default')
        session['user_info'] = user_info
        # return redirect(url_for('main.register_completion'))
        return redirect(url_for('main.register'))

    if has_invitation():

        if not is_invitee(user):
            reject_invitation()
        else:
            accept_invitation()

    # if require_two_factor(user):
        # return request_two_factor_auth(user)

    login_user(user, remember=True)

    if next_url():
        return redirect(next_url())

    if getattr(current_user, 'platform_admin', False):
        return redirect(url_for('main.show_all_services'))

    return redirect_to_services()


@main.route('/sign-in', methods=(['GET', 'POST']))
def sign_in():

    if current_user.is_authenticated:
        return redirect_to_services()

    set_next_url(request.args.get('next'))
    return redirect(oidc.login('dex'))


def set_next_url(url):
    session['next_url'] = url
    if session['next_url'] is None:
        del session['next_url']


def next_url():
    for url in [request.args.get('next'), session.get('next_url')]:
        if url and _is_safe_redirect_url(url):
            return url


def get_user(email):
    return user_api_client.get_user_by_email_or_none(email)


def has_invitation():
    return session.get('invited_user') is not None


def is_invitee(user):
    return user.email_address == session['invited_user']['email_address']


def reject_invitation():
    flash("You can't accept an invite for another person.")
    session.pop('invited_user', None)
    abort(403)


def accept_invitation():
    invite_api_client.accept_invite(
        session['invited_user']['service'],
        session['invited_user']['id'])


def require_two_factor(user):
    return login_fresh() or current_user.is_anonymous or \
        current_user.id != user.id or not user.is_active


def redirect_to_services(user=None):
    if user is None:
        user = current_user

    services = get_services(user)

    if len(services) == 1:
        return redirect_to_service_dashboard(services[0])

    return redirect_to_service_selection()


def get_services(user):
    return service_api_client.get_services(
        {'user_id': str(user.id)}).get('data', [])


def redirect_to_service_dashboard(service):
    return redirect(
        url_for('main.service_dashboard', service_id=service['id']))


def redirect_to_service_selection():
    return redirect(url_for('main.choose_service'))


def request_two_factor_auth(user):
    send_two_factor_code(user)
    return redirect_to_two_factor_prompt()


def send_two_factor_code(user):
    user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)


def redirect_to_two_factor_prompt():
    kwargs = {}

    if request.args.get('next'):
        kwargs['next'] = request.args['next']

    return redirect(url_for('.two_factor', **kwargs))


def authorized(user, password):
    return user and not user.is_locked() and verify_password(user, password)


def verify_password(user, password):
    return user_api_client.verify_password(user.id, password)
