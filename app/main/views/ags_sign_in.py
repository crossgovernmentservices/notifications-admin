import datetime
import json

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for)
from flask.ext.login import current_user, login_user

from app import invite_api_client, service_api_client, user_api_client
from app.main import main
from app.main.views.two_factor import _is_safe_redirect_url


@main.route('/ags-sign-in')
def ags_sign_in():

    if not feature_switch_active():
        current_app.logger.info('Feature switch not active')
        return redirect(url_for('main.sign_in'))

    auth_data = request.environ.get('auth_data')

    if auth_data is None:
        flash('Not authenticated')
        abort(403)

    user = get_user(auth_data['userinfo']['email'])

    if not user:
        session['auth_data'] = serialize_auth_data(auth_data)
        return redirect(url_for('main.ags_register'))

    if has_invitation():

        if not is_invitee(user):
            reject_invitation()

        else:
            accept_invitation()

    login_user(user, remember=True)

    _next = next_url()
    if _next:
        return redirect(_next)

    return redirect_to_services()


def accept_invitation():
    invite_api_client.accept_invite(
        session['invited_user']['service'],
        session['invited_user']['id'])


def feature_switch_active():
    cookie = request.cookies.get('ags_client_active')
    return cookie is None or cookie == '1'


def get_services(user):
    return service_api_client.get_services(
        {'user_id': str(user.id)}).get('data', [])


def get_user(email):
    return user_api_client.get_user_by_email_or_none(email)


def has_invitation():
    return session.get('invited_user') is not None


def is_invitee(user):
    return user.email_address == session['invited_user']['email_address']


def is_platform_admin(user):
    return getattr(user, 'platform_admin', False)


def next_url():
    for url in [request.args.get('next'), session.get('next_url')]:
        if url and _is_safe_redirect_url(url):
            return url


def redirect_to_services(user=None):
    if user is None:
        user = current_user

    if is_platform_admin(user):
        return redirect_to_all_services_list()

    services = get_services(user)

    if len(services) == 1:
        return redirect_to_service_dashboard(services[0])

    return redirect_to_service_selection()


def redirect_to_all_services_list():
    return redirect(url_for('main.show_all_services'))


def redirect_to_service_dashboard(service):
    return redirect(
        url_for('main.service_dashboard', service_id=service['id']))


def redirect_to_service_selection():
    return redirect(url_for('main.choose_service'))


def reject_invitation():
    flash("You can't accept an invite for another person.")
    session.pop('invited_user', None)
    abort(403)


def serialize_auth_data(auth_data):

    def dt_json_serializer(obj):

        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        raise TypeError('Type not serializable')

    return json.dumps(auth_data, default=dt_json_serializer)
