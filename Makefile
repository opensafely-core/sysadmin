ENV = env

$(ENV)/done: requirements.txt
	virtualenv $(ENV)
	$(ENV)/bin/pip install -r requirements.txt
	touch $@


# test allows for bootstrapping env before pip-tools installed
requirements.txt: requirements.in
	test -e $(ENV)/bin/pip-compile && $(ENV)/bin/pip-compile $^ 

ORG_TOKEN ?= $(shell cat org-token)
export ORG_TOKEN
manage: $(ENV)/done
	$(ENV)/bin/python manage-github.py config.yaml $(ARGS)

