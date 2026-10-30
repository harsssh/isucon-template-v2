.PHONY: survey setup deploy deploy-history lint test

BRANCH ?= main
export BRANCH

# サーバーの状態を survey/ に書き出し、ansible の前提と合わない点を表示する。サーバーは変更しない
survey:
	ansible-playbook ansible/survey.yml

# 競技サーバーの初回セットアップ
setup:
	ansible-playbook ansible/setup.yml

# origin の $(BRANCH) を全サーバーにデプロイする
deploy:
	ruby ansible/deploy_history.rb deploy

deploy-history:
	ruby ansible/deploy_history.rb list

lint:
	ansible-lint ansible/

# filter_plugins は Ansible の制約で Python なので、そのテストも Python で書く
test:
	PYTHONPATH=ansible/filter_plugins python3 -m unittest discover -s ansible/tests
	ruby -e 'ARGV.each { |f| require_relative f }' ansible/tests/test_*.rb
