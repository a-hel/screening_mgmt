from distutils.core import setup

setup(
    name='screening_mgmt',
    version='0.1.1',
    author='Andreas Helfenstein',
    author_email='andreas.helfenstein@helsinki.fi',
    packages=['screening_mgmt',],
    scripts=[],
    url='https://github.com/a-hel/screening_mgmt',
    license='LICENSE.txt',
    description='Data handling interface.',
    long_description=open('README.txt').read(),
    install_requires=[
        "pandas >= 0.13.10",
        "dateutil == 0.1.4",
        "numpy >= 1.8.0",
        "matplotlib >= 1.3.0",
        "sqlalchemy >= 0.9.0"
    ],
)
