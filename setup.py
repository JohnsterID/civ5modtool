from setuptools import setup, find_packages

setup(
    name="modtools",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4.0",
    ],
    extras_require={
        'dev': [
            'pytest>=8.3.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'modtools=modtools.__main__:main',
        ],
    },
)