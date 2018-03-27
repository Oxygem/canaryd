# canaryd
# File: setup.py
# Desc: canaryd package setup

'''
Due to the low-level nature of canaryd, this setup.py targets both setuptools
for systems that have it and the stdlib distutils for those that don't.
'''

SCRIPTS = (
    'bin/canaryctl',
    'bin/canaryd',
)

PACKAGES = (
    'canaryd',
    'canaryd.ctl',
    'canaryd.plugins',

    # Packages
    'canaryd_packages',
    'canaryd_packages.click',

    # Requests package
    'canaryd_packages.requests',
    'canaryd_packages.requests.packages',
    'canaryd_packages.requests.packages.chardet',
    'canaryd_packages.requests.packages.urllib3',
    'canaryd_packages.requests.packages.urllib3.contrib',
    'canaryd_packages.requests.packages.urllib3.packages',
    'canaryd_packages.requests.packages.urllib3.packages.backports',
    'canaryd_packages.requests.packages.urllib3.packages.ssl_match_hostname',
    'canaryd_packages.requests.packages.urllib3.util',
)

TEST_REQUIRES = (
    'nose==1.3.7',
    'jsontest==1.3',
    'coverage==4.5.1',
    'mock==1.3.0',
    'dictdiffer==0.6.1',
)

DEV_REQUIRES = TEST_REQUIRES + (
    # Releasing
    'wheel',
    'twine==1.11.0',

    # Dev debugging
    'ipdb',
    'ipdbplugin',
)


version_data = {}
with open('canaryd/version.py') as f:
    exec(f.read(), version_data)


# distutils/setuptools compatbile kwargs
setup_kwargs = {
    'name': 'canaryd',
    'version': version_data['__version__'],
    'description': 'Client for Service Canary',
    'author': 'Oxygem',
    'author_email': 'hello@oxygem.com',
    'license': 'MIT',
    'url': 'https://servicecanary.com',
    'packages': PACKAGES,
    'scripts': SCRIPTS,
    'include_package_data': True,
    # This must match the contents of MANIFEST.in, to provide full support for
    # distutil, setuptools everywhere. Annoying.
    'package_data': {
        'canaryd': [
            'init_scripts/*',
            'scripts/*',
        ],
        'canaryd_packages.requests': [
            '*.pem',
        ],
    },
}


# Attatch extras if setuptools is present
try:
    from setuptools import setup

    setup_kwargs['extras_require'] = {
        'dev': DEV_REQUIRES,
        'test': TEST_REQUIRES,
    }

# Otherwsie fallback to distutils
except ImportError:
    from distutils.core import setup

setup(**setup_kwargs)
