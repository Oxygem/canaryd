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
    'canaryd.packages',
    'canaryd.packages.click',

    # Requests package
    'canaryd.packages.requests',
    'canaryd.packages.requests.packages',
    'canaryd.packages.requests.packages.chardet',
    'canaryd.packages.requests.packages.urllib3',
    'canaryd.packages.requests.packages.urllib3.contrib',
    'canaryd.packages.requests.packages.urllib3.packages',
    'canaryd.packages.requests.packages.urllib3.packages.backports',
    'canaryd.packages.requests.packages.urllib3.packages.ssl_match_hostname',
    'canaryd.packages.requests.packages.urllib3.util',
)

TEST_REQUIRES = (
    'nose==1.3.7',
    'jsontest==1.2',
    'coverage==4.0.3',
    'mock==1.3.0',
)

DEV_REQUIRES = TEST_REQUIRES + (
    # Releasing
    'wheel',
    'twine==1.8.1',

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
        'canaryd.packages.requests': [
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
