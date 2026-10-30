.PHONY: setup deploy lint test

BRANCH ?= main

# 競技サーバーの初回セットアップ
setup:
	ansible-playbook ansible/setup.yml

# origin の $(BRANCH) を全サーバーにデプロイする
deploy:
	ansible-playbook ansible/deploy.yml -e branch=$(BRANCH)

lint:
	ansible-lint ansible/

test:
	PYTHONPATH=ansible/filter_plugins python3 -m unittest discover -s ansible/tests
