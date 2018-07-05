##
## Submodules
##

branch = $(shell git rev-parse --abbrev-ref HEAD)
submodules:
	git submodule init ${submodule}
	git submodule update ${submodule}

checkout_getting_started:
	git submodule init getting_started
	git submodule update --remote getting_started

