# apt-get install graphviz
DOT=dot
XDG_OPEN=xdg-open
# pip install snakefood
SFOOD=sfood
SFOOD_GRAPH=sfood-graph
# pip install coverage
COVERAGE=coverage

MODULES=checklist.py config.py db_util.py hcard_mock.py heron_policy.py medcenter.py redcap_connect.py

view: ,deps.ps
	$(XDG_OPEN) ,deps.ps

,deps.ps: ,deps.dot
	$(DOT) -Tps ,deps.dot >$@

,deps.dot: ,deps.txt
	$(SFOOD_GRAPH) ,deps.txt >$@

,deps.txt: $(MODULES)
	$(SFOOD) --internal-only $(MODULES) >$@

coverage: htmlcov/index.html
	$(XDG_OPEN) htmlcov/index.html

htmlcov/index.html: .coverage
	$(COVERAGE) html --omit ldaplib.py,db_util.py,hcard_mock.py

.coverage: tests.py $(MODULES)
	$(COVERAGE) run --source . --branch tests.py

clean:
	$(RM) -rf .coverage htmlcov ,deps.*
