.PHONY: setup deploy matching-groups lint test

BRANCH ?= main

# 競技サーバーの初回セットアップ
setup:
	ansible-playbook ansible/setup.yml

# origin の $(BRANCH) を全サーバーにデプロイする
deploy:
	ansible-playbook ansible/deploy.yml -e branch=$(BRANCH)

# pprotein (alp) の matching_groups を echo のルーティングから生成する
matching-groups:
	./assets/generate_matching_groups.py < $$(git grep -l 'func main()' -- '*.go' | head -1)

lint:
	ansible-lint ansible/

test:
	python3 -m unittest discover -s assets
	PYTHONPATH=ansible/filter_plugins python3 -m unittest discover -s ansible/tests
