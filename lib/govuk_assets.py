# -*- coding: utf-8 -*-
"""
Manager command for installing GOV.UK assets
"""

import contextlib
import glob
import os
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
import zipfile


@contextlib.contextmanager
def pushd(path):
    old_cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_cwd)


def move_dir(src, to):
    for f in glob.glob(src):

        if not os.path.isdir(to):
            os.makedirs(to)

        shutil.move(f, to)


def rmdir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)


class GovUkFrontendToolkit(object):

    url = (
        'https://github.com/alphagov/govuk_frontend_toolkit/archive/'
        'master.zip')

    def __init__(self, app_dir):
        self.dest_dir = '{}/static/govuk_frontend_toolkit'.format(app_dir)

    def clean(self):
        rmdir(self.dest_dir)

    def is_installed(self):
        return os.path.isdir(self.dest_dir)

    def build(self, unzip_dir):
        self.clean()

        for path in ['images', 'javascripts', 'stylesheets']:
            move_dir(
                '{}/govuk_frontend_toolkit-master/{}'.format(unzip_dir, path),
                to=self.dest_dir)


class GovUkElements(object):

    url = 'https://github.com/alphagov/govuk_elements/archive/master.zip'

    def __init__(self, app_dir):
        self.dest_dir = '{}/static/govuk_elements'.format(app_dir)

    def clean(self):
        rmdir(self.dest_dir)

    def is_installed(self):
        return os.path.isdir(self.dest_dir)

    def build(self, unzip_dir):
        self.clean()

        move_dir(
            '{}/govuk_elements-master/public'.format(unzip_dir),
            to=self.dest_dir)


class GovUkTemplate(object):

    url = 'https://github.com/alphagov/govuk_template/archive/master.zip'

    def __init__(self, app_dir):
        self.dest_views = '{}/templates/govuk_template'.format(app_dir)
        self.dest_assets = '{}/static/govuk_template'.format(app_dir)

    def clean(self):
        rmdir(self.dest_views)
        rmdir(self.dest_assets)

    def is_installed(self):
        return (
            os.path.isdir(self.dest_views) and
            os.path.isdir(self.dest_assets))

    def build(self, unzip_dir):
        master_dir = '{}/govuk_template-master'.format(unzip_dir)

        with pushd(master_dir):

            os.remove('.ruby-version')

            subprocess.call(['bundle', 'install'])
            subprocess.call(['bundle', 'exec', 'rake', 'build:jinja'])

        self.clean()

        move_dir(
            '{}/pkg/jinja_govuk_template*/assets'.format(master_dir),
            to=self.dest_assets)

        move_dir(
            '{}/pkg/jinja_govuk_template*/views'.format(master_dir),
            to=self.dest_views)


def install_govuk_assets(app_dir, clean=False):
    """
    Download and install the govuk assets
    """

    packages = [
        ('frontend_toolkit', GovUkFrontendToolkit),
        ('elements', GovUkElements),
        ('template', GovUkTemplate),
    ]

    for package_name, package_class in packages:
        install(package_name, package_class(app_dir), clean=clean)


def install(package_name, package, clean=False):
    """
    Download and extract package zip file into tempdir, then build
    """

    if clean:
        package.clean()

    if package.is_installed():
        return

    print('\nInstalling GOV.UK {}'.format(package_name))

    with TemporaryDirectory() as download_dir:
        dest_zip = '{}/{}.zip'.format(download_dir, package_name)
        unzip_dir = '{}/unzipped'.format(download_dir)

        urlretrieve(package.url, dest_zip)

        with zipfile.ZipFile(dest_zip) as zf:
            zf.extractall(unzip_dir)

        package.build(unzip_dir)

    print('Done')
