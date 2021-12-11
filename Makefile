# run developer scripts and helpers via Makefile targets

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
# declare all targets in this variable
ALL_TARGETS:=fmt lint type vermin cclean unit_test integration_test bench_test test coverage_html
# declare all target as PHONY
.PHONY: $(ALL_TARGETS)

# This small chunk of code allows us to pass arbitrary argument to our make targets
# see the solution on SO:
# https://stackoverflow.com/a/14061796/3017219
# If the first argument is contained in ALL_TARGETS
ifneq ($(filter $(firstword $(MAKECMDGOALS)), $(ALL_TARGETS)),)
  # use the rest as arguments to create a new variable ADD_ARGS
  EXTRA_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(EXTRA_ARGS):;@:)
endif

fmt:
	# code formatting
	black $(ROOT_DIR) $(EXTRA_ARGS)

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


unit_test:
	# run unit tests
	coverage run -m pytest -v tests/unit $(EXTRA_ARGS)
	coverage report

integration_test:
	# run integration tests
	coverage run -m pytest -v tests/integration $(EXTRA_ARGS)
	coverage report

bench_test:
	# run benchmarks
	# durations=0 shows execution time for each test
	coverage run -m pytest -v --durations=0 tests/bench $(EXTRA_ARGS)

test:
	# run the test specified by EXTRA_ARGS, or all tests if no args
	coverage run -m pytest -v $(EXTRA_ARGS)

coverage_html:
	# create html coverage report and display it in system browser
	coverage html --dir .coverage_html
	xdg-open .coverage_html/index.html


shutdown_dbs:
	# shutdown Neo4j and MinIOD DBs, if they are running
	# useful after integration test session with --persistdb
	docker stop neogit_neo4j_testdb
	docker stop neogit_minio_testdb
