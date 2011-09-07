# apt-get install graphviz
DOT=dot
XDG_OPEN=xdg-open
# pip install snakefood
SFOOD=sfood
SFOOD_GRAPH=sfood-graph
# pip install coverage
COVERAGE=coverage

MODULES=admin_lib/checklist.py admin_lib/config.py admin_lib/db_util.py \
        admin_lib/hcard_mock.py admin_lib/heron_policy.py \
        admin_lib/medcenter.py admin_lib/redcap_connect.py \
        heron_srv.py cas_auth.py usrv.py

view: ,deps.svg
	$(XDG_OPEN) ,deps.svg

,deps.svg: ,deps.dot
	$(DOT) -Tsvg ,deps.dot >$@

,deps.ps: ,deps.dot
	$(DOT) -Tps ,deps.dot >$@

,deps.dot: ,deps.txt
	$(SFOOD_GRAPH) ,deps.txt >$@

,deps.txt: $(MODULES)
	$(SFOOD) --internal-only $(MODULES) >$@

coverage: htmlcov/index.html
	$(XDG_OPEN) htmlcov/index.html

htmlcov/index.html: .coverage
	$(COVERAGE) html \
		--omit admin_lib/ldaplib.py,admin_lib/db_util.py,admin_lib/hcard_mock.py,tests.py,admin_lib/tests.py

.coverage: tests.py $(MODULES)
	$(COVERAGE) run --source . --branch tests.py

clean:
	$(RM) -rf .coverage htmlcov ,deps.*
