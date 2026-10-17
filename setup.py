from setuptools import find_packages, setup

setup(
    name="modtools",
    version="2.0.0",
    description="Read, convert, check and edit Civilization V mod files (.modinfo, .civ5proj, .civ5sln)",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.9",
    install_requires=[],  # standard library only; the GUI uses Tkinter, which ships with Python
    extras_require={"dev": ["pytest>=8.3.0"]},
    entry_points={"console_scripts": ["modtools=modtools.__main__:main"]},
)
