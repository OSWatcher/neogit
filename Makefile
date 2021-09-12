# run developer scripts and helpers via Makefile targets

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

fmt:
	# code formatting
	black $(ROOT_DIR)

lint:
	# code linting
	flake8 --show-source --statistics $(ROOT_DIR)
	isort $(ROOT_DIR)

type:
	# type checking
	mypy -p neogit

vermin:
	# minimum version check
	vermin --no-tips --target=3.7 neogit

cclean: fmt lint type vermin
	# code cleanup without unit tests