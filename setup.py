import sys

if sys.version_info[:2] < (3, 6):
    raise RuntimeError("stg requires python >= 3.6")

from setuptools import find_packages, setup

REQUIRES = [
    'pyqtgraph',
    'PyOpenGL',
]

setup(
    # basic package metadata
    name='solar_travel_gui',
    version= 0.10,
    description='solar_travel_gui',
    long_description="solar_travel_gui",
    license='GPL3',
    author='CHEN Kian Wee',
    author_email='chenkianwee@gmail.com',
    url='https://github.com/chenkianwee/solar_travel_gui',
    classifiers="test",

    # details needed by setup
    install_requires=REQUIRES,
    python_requires=">=3.6",
    packages=find_packages(),
    package_data={},
    entry_points={'gui_scripts': ['solar_travel_gui = solar_travel_gui.__main__:main']},
)