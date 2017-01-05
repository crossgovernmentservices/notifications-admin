import pytest

from flask import (
    url_for,
    session
)

from bs4 import BeautifulSoup


def test_render_register_returns_template_with_form(app_):
    response = app_.test_client().get('/register')

    assert response.status_code == 200
    assert 'Create an account' in response.get_data(as_text=True)


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    api_user_active,
                                                    mock_get_user_by_email,
                                                    mock_send_verify_code,
                                                    mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.register'))
            assert response.status_code == 302

            response = client.get(
                url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for(
                'main.choose_service', _external=True)


def test_register_creates_new_user_and_redirects_to_continue_page(app_,
                                                                  mock_send_verify_code,
                                                                  mock_register_user,
                                                                  mock_get_user_by_email_not_found,
                                                                  mock_is_email_unique,
                                                                  mock_send_verify_email,
                                                                  mock_login):

    user_data = {'name': 'Some One Valid',
                 'email_address': 'notfound@example.gov.uk',
                 'mobile_number': '+4407700900460',
                 'password': 'validPassword!'
                 }

    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.register'), data=user_data)
        assert response.status_code == 302
        assert response.location == url_for(
            'main.registration_continue', _external=True)

        from unittest.mock import ANY
        mock_send_verify_email.assert_called_with(
            ANY, user_data['email_address'])
        mock_register_user.assert_called_with(user_data['name'],
                                              user_data['email_address'],
                                              user_data['mobile_number'],
                                              user_data['password'])


def test_process_register_returns_200_when_mobile_number_is_invalid(app_,
                                                                    mock_send_verify_code,
                                                                    mock_get_user_by_email_not_found,
                                                                    mock_login):
    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.register'),
                                           data={'name': 'Bad Mobile',
                                                 'email_address': 'bad_mobile@example.gov.uk',
                                                 'mobile_number': 'not good',
                                                 'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Must not contain letters or symbols' in response.get_data(
        as_text=True)


def test_should_return_200_when_email_is_not_gov_uk(app_,
                                                    mock_send_verify_code,
                                                    mock_get_user_by_email,
                                                    mock_login):
    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.register'),
                                           data={'name': 'Bad Mobile',
                                                 'email_address': 'bad_mobile@example.not.right',
                                                 'mobile_number': '+44123412345',
                                                 'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Enter a central government email address' in response.get_data(
        as_text=True)


def test_should_add_user_details_to_session(app_,
                                            mock_send_verify_code,
                                            mock_register_user,
                                            mock_get_user,
                                            mock_get_user_by_email_not_found,
                                            mock_is_email_unique,
                                            mock_send_verify_email,
                                            mock_login):
    user_data = {
        'name': 'Test Codes',
        'email_address': 'notfound@example.gov.uk',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!'
    }

    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.post(url_for('main.register'),
                                   data=user_data)

            assert response.status_code == 302
            assert session['user_details'][
                'email'] == user_data['email_address']


def test_should_return_200_if_password_is_blacklisted(app_,
                                                      mock_get_user_by_email,
                                                      mock_login):
    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.register'),
                                           data={'name': 'Bad Mobile',
                                                 'email_address': 'bad_mobile@example.not.right',
                                                 'mobile_number': '+44123412345',
                                                 'password': 'password'})

    response.status_code == 200
    assert 'Choose a password that’s harder to guess' in response.get_data(
        as_text=True)


def test_register_with_existing_email_sends_emails(app_,
                                                   api_user_active,
                                                   mock_get_user_by_email,
                                                   mock_send_already_registered_email):
    user_data = {
        'name': 'Already Hasaccount',
        'email_address': api_user_active.email_address,
        'mobile_number': '+4407700900460',
        'password': 'validPassword!'
    }

    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.register'),
                                           data=user_data)
        assert response.status_code == 302
        assert response.location == url_for(
            'main.registration_continue', _external=True)


email_ids = ['some.one@cabinetoffice.gov.uk',
             'some.one@sso.civilservice.digital']


@pytest.mark.parametrize("email_id", email_ids)
def test_ags_register_creates_new_user_and_redirects_to_add_service_page(
        app_,
        mock_send_verify_code,
        mock_register_user,
        mock_get_user_by_email_not_found,
        mock_is_email_unique,
        mock_send_verify_email,
        mock_login,
        email_id):

    user_data = {'name': 'Some One Valid',
                 'email_address': email_id,
                 'mobile_number': '+4407700900460',
                 'password': 'validPassword!'
                 }

    with app_.test_request_context():
        response = app_.test_client().post(url_for('main.ags_register'), data=user_data)
        assert response.status_code == 302
        assert response.location == url_for(
            'main.add_service', first='first', _external=True)

        from app.main.views.ags_register import DEFAULT_PASSWORD
        mock_register_user.assert_called_with(user_data['name'],
                                              user_data['email_address'],
                                              user_data['mobile_number'],
                                              DEFAULT_PASSWORD)
