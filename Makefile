DOWNLOADS=$(HOME)/Downloads
OPT=$(HOME)/opt
WGET=wget
JAVA=java

JYTHON_HOME=$(OPT)/jython2.7.1
VENV=$(HOME)/pyenv/ha-jy
WHEELS=$(HOME)/pyenv/ha-wheels


install-deps: $(WHEELS) $(VENV)/bin/pip requirements.txt
	# ref https://pip.pypa.io/en/stable/user_guide/#installing-from-wheels
	$(VENV)/bin/pip install --no-index --find-links=$(WHEELS) -r requirements.txt



download-jython-installer: $(DOWNLOADS)/jython-installer-2.7.1.jar

$(DOWNLOADS)/jython-installer-2.7.1.jar:
	cd $(DOWNLOADS); \
	echo 392119a4c89fa1b234225d83775e38dbd149989f jython-installer-2.7.1.jar | sha1sum --check || \
	$(WGET) -O $@ http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.7.1/jython-installer-2.7.1.jar && \
	echo 392119a4c89fa1b234225d83775e38dbd149989f jython-installer-2.7.1.jar | sha1sum --check



install-jython: $(JYTHON_HOME)/bin/jython

$(JYTHON_HOME)/bin/jython:
	# TODO: headless
	echo choose standard install
	$(JAVA) -jar jython_installer-2.7.1.jar


# Then, following `jython setuptools docs`__, install `easy_install` and `virtualenv`::
# __ http://www.jython.org/jythonbook/en/1.0/appendixA.html#setuptools

download-ez_setup: $(DOWNLOADS)/ez_setup.py

$(DOWNLOADS)/ez_setup.py:
	$(WGET) -O $@ http://peak.telecommunity.com/dist/ez_setup.py

$(JYTHON_HOME)/bin/easy_install $(JYTHON_HOME)/bin/virtualenv: $(JYTHON_HOME)/bin/jython $(DOWNLOADS)/ez_setup.py
	$(JYTHON_HOME)/bin/jython $(DOWNLOADS)/ez_setup.py 
	$(JYTHON_HOME)/bin/easy_install virtualenv
	# TODO: verify checksum?
	#  Downloading https://files.pythonhosted.org/packages/b1/72/2d70c5a1de409ceb3a27ff2ec007ecdd5cc52239e7c74990e32af57affe9/virtualenv-15.2.0.tar.gz#sha256=1d7e241b431e7afce47e77f8843a276f652699d1fa4f93b9d8ce0076fd7b0b54
	# Installed .../opt/jython2.7.1/Lib/site-packages/virtualenv-15.2.0-py2.7.egg


# To work around Invalid file object: <ssl.SSLSocket object at 0x1a4> with newer pip,
# we use 9.0.1.
# TODO: verify checksum
# https://pypi.org/project/pip/9.0.1/#files
# 09f243e1a7b461f654c26a725fa373211bb7ff17a9300058b205c61658ca940d

$(VENV)/bin/python $(VENV)/bin/easy_install:
	$(JYTHON_HOME)/bin/virtualenv --no-pip $(VENV)

$(DOWNLOADS)/pip-9.0.1.tar.gz:
	$(WGET) -O $@ https://files.pythonhosted.org/packages/11/b6/abcb525026a4be042b486df43905d6893fb04f05aac21c32c638e939e447/pip-9.0.1.tar.gz

$(VENV)/bin/pip: $(DOWNLOADS)/pip-9.0.1.tar.gz $(VENV)/bin/easy_install
	$(VENV)/bin/easy_install $(DOWNLOADS)/pip-9.0.1.tar.gz 


build-wheels: $(WHEELS)

$(WHEELS): requirements.txt
	mkdir $(WHEELS)
	$(VENV)/bin/pip wheel --wheel-dir=$(WHEELS) -r requirements.txt
