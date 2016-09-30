from setuptools import setup
import os

version = '1.0.0'

tests_require = [
    'freezegun',
    'unittest2',
]

setup(name='supervisor-haproxy',
      version=version,
      description='supervisor eventlistener for notifying haproxy',
      long_description=open("README.rst").read() + "\n" + open(
          os.path.join("docs", "HISTORY.txt")).read(),

      author='4teamwork AG',
      author_email='mailto:info@4teamwork.ch',
      url='https://github.com/4teamwork/supervisor-haproxy',
      license='GPL2',

      packages=['supervisor_haproxy'],
      include_package_data=True,
      zip_safe=False,

      install_requires=[
          'supervisor',

      ],
      tests_require=tests_require,
      test_suite='supervisor_haproxy.tests',

      entry_points = """\
      [console_scripts]
      supervisor-haproxy = supervisor_haproxy.command:main
      """,
)
