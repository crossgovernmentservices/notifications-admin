from app.main.forms import AddServiceForm
from werkzeug.datastructures import MultiDict


def test_form_should_have_errors_when_duplicate_service_is_added(client):
    def _get_form_names():
        return ['some.service', 'more.names']
    form = AddServiceForm(_get_form_names,
                          formdata=MultiDict([('name', 'some service')]))
    form.validate()
    assert {'name': ['This service name is already in use']} == form.errors
