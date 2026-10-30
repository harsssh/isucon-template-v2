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

# filter_plugins は Ansible の制約で Python なので、そのテストも Python で書く
test:
	PYTHONPATH=ansible/filter_plugins python3 -m unittest discover -s ansible/tests
	ruby -e 'ARGV.each { |f| require_relative f }' ansible/tests/test_*.rb
