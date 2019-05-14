from setuptools import setup


setup(
    name="jh_jwt",
    version="0.0.5",
    description="JSONWebToken Authenticator for JupyterHub",
    url="https://github.com/jpetrucciani/jh_jwt",
    author="mogthesprog, jpetrucciani",
    author_email="mevanj89@gmail.com, jacobi@mimirhq.com",
    license="Apache 2.0",
    tests_require=["unittest2"],
    test_suite="unittest2.collector",
    packages=["jh_jwt"],
    install_requires=["jupyterhub", "python-jose"],
)
