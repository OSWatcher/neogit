import nox

nox.options.sessions = ["fmt", "lint", "type", "vermin", "unit_test"]


@nox.session
def fmt(session):
    session.install("black==20.8b1")
    # note: black doesn't support setup.cfg
    # so we hardcode the config here
    session.run("black", "--line-length", "120", ".")


@nox.session
def lint(session):
    session.install("flake8", "flake8-bugbear", "isort")
    session.run("flake8", "--show-source", "--statistics")
    session.run("isort", "--line-length", "120", ".")


@nox.session
def type(session):
    session.install("-r", "requirements.txt")
    session.install("mypy")
    session.run("mypy", "-p", "neogit")


@nox.session
def vermin(session):
    """Check for a maximum Python version"""
    session.install("-r", "dev-requirements.txt")
    # we want to be compatible with PyPy, so 3.7 max
    session.run("vermin", "--no-tips", "--target=3.7-", "neogit")


@nox.session
def unit_test(session):
    # run unit tests
    args = session.posargs
    install_test_req(session)
    session.run("coverage", "run", "-m", "pytest", "--pdb", "-m", "not dev", "-k", "unit", "-v", *args)
    session.run("coverage", "report")


@nox.session
def test(session):
    # run unit tests
    args = session.posargs
    install_test_req(session)
    session.run("coverage", "run", "-m", "pytest", "--pdb", "-m", "not dev", "-v", *args)
    session.run("coverage", "report")


@nox.session
def coverage_html(session):
    session.install("-r", "dev-requirements.txt")
    session.run("coverage", "html", "--dir", ".coverage_html")
    session.run("xdg-open", ".coverage_html/index.html")


@nox.session
def dev(session):
    args = session.posargs
    install_test_req(session)
    session.run("python", "-m", "pytest", "-k", "dev", "--pdb", *args)


def install_test_req(session):
    session.install("-r", "requirements.txt")
    session.install("-r", "dev-requirements.txt")


@nox.session
def run(session):
    """install neogit and run it"""
    args = session.posargs
    session.install(".")
    session.run("neogit", *args)
