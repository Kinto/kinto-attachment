VIRTUALENV = virtualenv --python python3.5
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue .
	$(TEMPDIR)/bin/pip freeze | grep -v -- '^-e' > requirements.txt

moto:
	$(VENV)/bin/moto_server s3bucket_path -H 0.0.0.0 -p 5000

tests-once: install
	$(VENV)/bin/py.test kinto_attachment/tests --cov-report term-missing --cov-fail-under 100 --cov kinto_attachment

tests:
	$(VENV)/bin/tox

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr

distclean: clean
	rm -fr *.egg *.egg-info/

maintainer-clean: distclean
	rm -fr $(OBJECTS) .tox/ dist/ build/

run-kinto:
	cd /tmp; python -m http.server 8000 &
	$(VENV)/bin/kinto migrate --ini kinto_attachment/tests/config/functional.ini
	$(VENV)/bin/kinto start --ini kinto_attachment/tests/config/functional.ini

need-kinto-running:
	@curl http://localhost:8888/v1/ 2>/dev/null 1>&2 || (echo "Run 'make run-kinto' before starting tests." && exit 1)
