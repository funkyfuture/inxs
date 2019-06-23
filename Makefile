.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"
VERSION = $(shell python setup.py --version)

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts


clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr docs/_build/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	find . -name '*.orig' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f tests/.coverage
	rm -fr htmlcov/

.PHONY: doctest
doctest: ## Tests docs and contained links
	$(MAKE) -C docs doctest
	$(MAKE) -C docs linkcheck

lint: ## check style with flake8
	tox -e flake8

test: ## run tests quickly with the default Python
	tox -e py37

test-all: lint test doctest ## run all tests

coverage: ## check code coverage quickly with the default Python
	coverage run --source inxs -m pytest

		coverage report -m
		coverage html
		$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

.PHONY: showdocs
showdocs:
	$(BROWSER) docs/_build/html/index.html

release: clean test-all clean ## package and upload a release
	git push
	git tag -f $(VERSION)
	git push -f origin $(VERSION)
	python setup.py sdist upload

dist: clean ## builds source and wheel package
	python setup.py sdist
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install
