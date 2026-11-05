SH_SRCFILES = $(filter-out bin/install,$(wildcard bin/* lib/*.sh tests/*.bats))
SHFMT_BASE_FLAGS = -s -i 2 -ci
TEST_FILES = $(wildcard tests/*.bats)
MAX_INSTALL_LINES ?= 50

fmt:
	shfmt -w $(SHFMT_BASE_FLAGS) $(SH_SRCFILES)
.PHONY: fmt

fmt-check:
	shfmt -d $(SHFMT_BASE_FLAGS) $(SH_SRCFILES)
.PHONY: fmt-check

lint:
	shellcheck $(SH_SRCFILES)
.PHONY: lint

test:
	python3 -m unittest discover -s tests -p 'test_*.py'
	@if command -v bats >/dev/null 2>&1; then \
		bats $(TEST_FILES); \
	else \
		echo "Error: bats is not installed. Please install bats-core."; \
		echo "macOS: brew install bats-core"; \
		echo "Linux: apt-get install bats or yum install bats"; \
		exit 1; \
	fi
.PHONY: test

test-verbose:
	python3 -m unittest discover -v -s tests -p 'test_*.py'
	@if command -v bats >/dev/null 2>&1; then \
		bats --tap $(TEST_FILES); \
	else \
		echo "Error: bats is not installed. Please install bats-core."; \
		exit 1; \
	fi
.PHONY: test-verbose

linecount-check:
	@actual=$$(wc -l < bin/install); \
	if [ "$$actual" -gt "$(MAX_INSTALL_LINES)" ]; then \
		echo "bin/install is $$actual lines (limit: $(MAX_INSTALL_LINES))"; \
		exit 1; \
	fi
.PHONY: linecount-check

check: fmt-check lint test linecount-check
.PHONY: check
