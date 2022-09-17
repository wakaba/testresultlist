all:

WGET = wget
CURL = curl
GIT = git

updatenightly: local/bin/pmbp.pl
	$(CURL) -s -S -L https://gist.githubusercontent.com/wakaba/34a71d3137a52abb562d/raw/gistfile1.txt | sh
	$(GIT) add modules
	perl local/bin/pmbp.pl --update
	$(GIT) add config
	$(CURL) -sSLf https://raw.githubusercontent.com/wakaba/ciconfig/master/ciconfig | RUN_GIT=1 REMOVE_UNUSED=1 perl

## ------ Setup ------

deps: always
	true # dummy for make -q
ifdef PMBP_HEROKU_BUILDPACK
else
	$(MAKE) git-submodules
endif
	$(MAKE) pmbp-install

deps-circleci: deps

deps-docker: pmbp-install

git-submodules:
	$(GIT) submodule update --init

PMBP_OPTIONS=

local/bin/pmbp.pl:
	mkdir -p local/bin
	$(CURL) -s -S -L https://raw.githubusercontent.com/wakaba/perl-setupenv/master/bin/pmbp.pl > $@
pmbp-upgrade: local/bin/pmbp.pl
	perl local/bin/pmbp.pl $(PMBP_OPTIONS) --update-pmbp-pl
pmbp-update: git-submodules pmbp-upgrade
	perl local/bin/pmbp.pl $(PMBP_OPTIONS) --update
pmbp-install: pmbp-upgrade
	perl local/bin/pmbp.pl $(PMBP_OPTIONS) --install \
            --create-perl-command-shortcut @perl \
            --create-perl-command-shortcut @prove \
            --create-perl-command-shortcut @plackup=perl\ modules/twiggy-packed/script/plackup

deps-data: local/data1/cvs/pub/testresults/data

local/data1/cvs/pub/testresults/data:
	mkdir -p local
	#$(WGET) -O local/cvs-pub.tar.gz https://www.dropbox.com/s/5oujy6bzvm176ih/cvs-pub.tar.gz?dl=1
	$(WGET) -O local/cvs-pub.tar.gz https://bitbucket.org/wakabatan/suikaweb-pubdata/raw/6eb536c8fc93100df6ab131f2aaef0c230b4268a/cvs-pub.tar.gz
	cd local && tar zxf cvs-pub.tar.gz
	cd local/data1/cvs/pub/testresults/data && co *,v

create-commit-for-heroku:
	git remote rm origin
	rm -fr deps/pmtar/.git deps/pmpp/.git modules/*/.git
	git add -f deps/pmtar/* #deps/pmpp/*
	#rm -fr ./t_deps/modules
	#git rm -r t_deps/modules
	git rm .gitmodules
	git rm modules/* --cached
	rm -fr local/data1/cvs/pub/testresults/data/*,v
	git add -f modules/*/* local/data1/cvs/pub/testresults/data
	git commit -m "for heroku"

## ------ Tests ------

PROVE = ./prove

test: test-deps test-main

test-deps: deps

test-main:
	#$(PROVE) t/*.t

## ------ Deployment ------

deploy-master:
	$(CURL) -sSf $$DEPLOY_KICK_URL

always:

## License: Public Domain.
