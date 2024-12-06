from setuptools import setup, find_packages

setup(
    name='jaalvarez2818_hotetec_sdk',
    version='0.2.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'xmltodict',
    ],
    url='https://github.com/jaalvarez2818/hotetec-sdk',
    author='José Angel Alvarez Abraira',
    author_email='jaalvarez2818development@gmail.com',
    description='SDK para la comunicación con el API de Hotetec para las reservas de hoteles.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
