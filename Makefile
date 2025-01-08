.PHONY: help
help:
	@echo "Make targets for RSP reaper"
	@echo "make init - Set up dev environment"
	@echo "make run - Run dev instance of service locally"
	@echo "make update - Update pinned dependencies and run make init"
	@echo "make update-deps - Update pinned dependencies"

.PHONY: init
init:
	pip install --upgrade pip uv
	uv pip install --editable .
	uv pip install --upgrade -r requirements/main.txt \
            -r requirements/dev.txt
	rm -rf .tox
	uv pip install --upgrade pre-commit tox
	pre-commit install

.PHONY: update
update: update-deps init

# The dependencies need --allow-unsafe because kubernetes-asyncio and
# (transitively) pre-commit depends on setuptools, which is normally not
# allowed to appear in a hashed dependency file.
.PHONY: update-deps
update-deps:
	uv pip install --upgrade pip-tools pip setuptools
	uv pip compile --upgrade --build-isolation --generate-hashes \
	    --output-file requirements/main.txt requirements/main.in
	uv pip compile --upgrade --build-isolation --generate-hashes \
	    --output-file requirements/dev.txt requirements/dev.in
