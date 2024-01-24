VENV := $(shell echo $${VIRTUAL_ENV-$$PWD/.venv})
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.IGNORE: clean
.PHONY: all install virtualenv tests tests-once

OBJECTS = .venv .coverage

all: install

$(VENV)/bin/python:
	python -m venv $(VENV)

install: $(INSTALL_STAMP) pyproject.toml requirements.txt
$(INSTALL_STAMP): $(VENV)/bin/python pyproject.toml requirements.txt
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -e ".[dev]"
	touch $(INSTALL_STAMP)

lint: install
	$(VENV)/bin/ruff check src tests
	$(VENV)/bin/ruff format --check src tests

format: install
	$(VENV)/bin/ruff check --fix src tests
	$(VENV)/bin/ruff format src tests

requirements.txt: requirements.in
	pip-compile requirements.in

tests: test
tests-once: test
test: install
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto_attachment

clean:
	find src/ -name '*.pyc' -delete
	find src/ -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf $(OBJECTS) *.egg-info .pytest_cache .ruff_cache build dist

run-kinto: install
	python -m http.server -d $(TEMPDIR) 8000 &
	$(VENV)/bin/kinto migrate --ini tests/config/functional.ini
	$(VENV)/bin/kinto start --ini tests/config/functional.ini

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make run-kinto' before starting tests." && exit 1)

run-moto: install
	$(VENV)/bin/moto_server s3bucket_path -H 0.0.0.0 -p 6000

need-moto-running:
	@curl http://localhost:6000 2>/dev/null 1>&2 || (echo "Run 'make run-moto' before starting tests." && exit 1)

functional: install need-kinto-running need-moto-running
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image1.png 3000
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image2.png 3000
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image3.png 3000
	$(VENV)/bin/python scripts/create_account.py --server=http://localhost:8888/v1 --auth=my-user:my-secret
	$(VENV)/bin/python scripts/upload.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	$(VENV)/bin/python scripts/download.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret -f $(TEMPDIR)
	$(VENV)/bin/python scripts/delete.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret
	$(VENV)/bin/python scripts/upload.py --server=http://localhost:8888/v1 --bucket=services --collection=app --auth=my-user:my-secret $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	$(VENV)/bin/python scripts/download.py --server=http://localhost:8888/v1 --bucket=services --collection=app --auth=my-user:my-secret -f $(TEMPDIR)/kintoapp
	/bin/rm $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	/bin/rm -rf $(TEMPDIR)/kinto*
