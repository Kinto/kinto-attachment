TEMPDIR := $(shell mktemp -d)

.IGNORE: clean
.PHONY: all install lint format test tests tests-once clean run-kinto need-kinto-running run-moto need-moto-running functional

all: install

install:
	uv sync --all-extras

lint: install
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

tests: test
tests-once: test
test: install
	uv run pytest --cov-report term-missing --cov-fail-under 100 --cov kinto_attachment

clean:
	find src/ -name '*.pyc' -delete
	find src/ -name '__pycache__' -type d -exec rm -fr {} \;
	rm -rf .coverage *.egg-info .pytest_cache .ruff_cache build dist

run-kinto:
	uv run python -m http.server -d $(TEMPDIR) 8000 &
	uv run kinto migrate --ini tests/config/functional.ini
	uv run kinto start --ini tests/config/functional.ini

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make run-kinto' before starting tests." && exit 1)

need-moto-running:
	@curl http://localhost:6000 2>/dev/null 1>&2 || (echo "Run 'make run-moto' before starting tests." && exit 1)

functional: need-kinto-running
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image1.png 3000
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image2.png 3000
	/usr/bin/openssl rand -base64 -out $(TEMPDIR)/image3.png 3000
	uv run python scripts/create_account.py --server=http://localhost:8888/v1 --auth=my-user:my-secret
	uv run python scripts/upload.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	uv run python scripts/download.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret -f $(TEMPDIR)
	uv run python scripts/delete.py --server=http://localhost:8888/v1 --bucket=services --collection=logs --auth=my-user:my-secret
	uv run python scripts/upload.py --server=http://localhost:8888/v1 --bucket=services --collection=app --auth=my-user:my-secret $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	uv run python scripts/download.py --server=http://localhost:8888/v1 --bucket=services --collection=app --auth=my-user:my-secret -f $(TEMPDIR)/kintoapp
	/bin/rm $(TEMPDIR)/image1.png $(TEMPDIR)/image2.png $(TEMPDIR)/image3.png
	/bin/rm -rf $(TEMPDIR)/kinto*
