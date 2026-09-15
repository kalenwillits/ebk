"""Setup script for ebk package."""

from setuptools import setup, find_packages
from ebk import __version__

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ebk',
    version=__version__,
    description='E-Book CLI utility for managing EPUB projects',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='ebk contributors',
    url='https://github.com/anthropics/ebk',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'ebk': [
            'templates/*',
            'resources/*',
        ],
    },
    install_requires=[
        'markdown>=3.1',
        'Jinja2>=3.0',
        'PyYAML>=6.0',
        'weasyprint>=60.0',
        'odfpy>=1.4',
        'pypdf>=4.0',
        'pytailwindcss>=0.2.0',
    ],
    entry_points={
        'console_scripts': [
            'ebk=ebk.cli:main',
        ],
    },
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
