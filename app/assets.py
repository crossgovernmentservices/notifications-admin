# -*- coding: utf-8 -*-

import os

from flask_assets import Bundle, Environment

from lib.sass_filter import LibSass

def static(*path):
    return os.path.join(os.path.dirname(__file__), 'static', *path)

libsass_output = LibSass(include_paths=[
    static('css'),
    static('sass'),
    static('govuk_frontend_toolkit/stylesheets'),
    static('govuk_elements/public/sass')])

# GOV.UK assets
# css_govuk = Bundle(
#  'css/govuk.scss',
#  filters='scss',
#  output='gen/css/govuk.css',
#  depends="**/*.scss"
# )

css_govuk = Bundle(
  'css/govuk.scss',
  filters=(libsass_output,),
  output='gen/css/govuk_elements.css',
  depends=[
        '/static/govuk_elements/public/sass/**/*.scss',
        '/static/govuk_frontend_toolkit/stylesheets/**/*.scss']
)

assets = Environment()

assets.register('css_govuk', css_govuk)
