from datetime import (
    datetime,
    timedelta
)

from flask import (
    render_template,
    redirect,
    request,
    session,
    abort,
    url_for
)

from flask_login import current_user

from app.main import main

from app.main.forms import (
    RegisterUserForm,
    RegisterUserFromInviteForm
)

from app import (
    user_api_client,
    invite_api_client
)


@main.route('/pre-register')
def pre_register():
    return render_template('views/pre_register.html')


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user and current_user.is_authenticated:
        return redirect(url_for('main.choose_service'))

    form = RegisterUserForm()
    if form.validate_on_submit():
        _do_registration(form, send_sms=False)
        return redirect(url_for('main.registration_continue'))

    return render_template('views/register.html', form=form)


@main.route('/register-from-invite', methods=['GET', 'POST'])
def register_from_invite():
    form = RegisterUserFromInviteForm()
    invited_user = session.get('invited_user')
    if not invited_user:
        abort(404)

    if form.validate_on_submit():
        if form.service.data != invited_user['service'] or form.email_address.data != invited_user['email_address']:
            abort(400)
        _do_registration(form, send_email=False)
        invite_api_client.accept_invite(invited_user['service'], invited_user['id'])
        return redirect(url_for('main.verify'))

    form.service.data = invited_user['service']
    form.email_address.data = invited_user['email_address']

    return render_template('views/register-from-invite.html', email_address=invited_user['email_address'], form=form)


def _do_registration(form, service=None, send_sms=True, send_email=True):
    if user_api_client.is_email_unique(form.email_address.data):
        user = user_api_client.register_user(form.name.data,
                                             form.email_address.data,
                                             form.mobile_number.data,
                                             form.password.data)

        # TODO possibly there should be some exception handling
        # for sending sms and email codes.
        # How do we report to the user there is a problem with
        # sending codes apart from service unavailable?
        # at the moment i believe http 500 is fine.

        if send_email:
            user_api_client.send_verify_email(user.id, user.email_address)

        if send_sms:
            user_api_client.send_verify_code(user.id, 'sms', user.mobile_number)
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
    else:
        if send_email:
            user = user_api_client.get_user_by_email(form.email_address.data)
            user_api_client.send_already_registered_email(user.id, user.email_address)
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}


@main.route('/registration-continue')
def registration_continue():
    return render_template('views/registration-continue.html')
