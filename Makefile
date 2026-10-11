SH_SRCFILES = $(shell git ls-files "bin/*")
SHFMT_BASE_FLAGS = -s -i 2 -ci
TEST_FILES = $(wildcard tests/*.bats)

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
	@if command -v bats >/dev/null 2>&1; then \
		bats --tap $(TEST_FILES); \
	else \
		echo "Error: bats is not installed. Please install bats-core."; \
		exit 1; \
	fi
.PHONY: test-verbose

check: fmt-check lint test
.PHONY: check
