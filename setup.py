from setuptools import setup

setup(
    name='CUSTIPEN workshop',
    packages=['workshop'],
    include_package_data=True,
    install_requires=[
        'flask',
        'captcha', 
        'gunicorn'
    ],
)
