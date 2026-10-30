# AGENTS.md

ISUCON の競技用リポジトリ。競技サーバーの webapp と設定ファイルをこのリポジトリで管理し、手元から Ansible で全サーバーにデプロイする。

## ディレクトリ

- `app/`: 競技サーバーの `~/webapp` を取り込んだもの。サーバーの `~/webapp` はサーバー上の clone の `app/` へのシンボリックリンク
- `common/`: 全サーバーに配る設定ファイル。`common/etc/nginx/nginx.conf` は `/etc/nginx/nginx.conf` に置かれる
- `s1/` 〜 `s5/`: そのホストだけに配る設定ファイル。`common/` と同じパスなら、こちらを優先する
- `ansible/`: セットアップとデプロイの playbook。ホストとサービスの配置は `ansible/inventory.yml`
- `docs/tuning/`: nginx, MySQL, sysctl の設定例。使うときは `common/` にコピーする
- `survey/`: `make survey` で集めた各サーバーの状態 (サービス、listen しているポート、unit ファイル、環境変数のファイル、テーブルのサイズなど)。サーバーの構成を調べるときは、まずここを読む

`app/` と `common/` は初回の `make setup` で primary (既定は s1) から取り込まれる。

## 作業の流れ

1. 手元で `app/` や `common/` を編集してコミットする
2. push する
3. `make deploy` (main) か `make deploy BRANCH=<branch>` で全サーバーにデプロイする
4. ベンチマークはポータルから人が実行する

- サーバー上で直接ファイルを編集しない。デプロイでサーバー上の変更は捨てられる
- `make deploy` は全サーバーのサービスを再起動する。ベンチマークの実行中に打たないよう、実行前にユーザーに確認する

## コマンド

Ansible などは Nix の devShell にあり、direnv で読み込まれる。読み込まれていなければ `nix develop -c` を付ける。

- `make deploy [BRANCH=...]`: デプロイ
- `make survey`: サーバーの状態を `survey/` に書き出し、ansible の前提と合わない点を表示する。サーバーは変更しない
- `make setup`: 初回セットアップ。何度実行しても同じ状態になる
- `make test`: `ansible/` のスクリプトとフィルターのテスト
- `make lint`: ansible-lint

サーバーには `ssh s1` のように入れる。

## デプロイが行うこと

- アプリ: `app/go` で `make` を実行し、WorkingDirectory が `~/webapp/go` のサービスを毎回再起動する。サービス名は自動で見つける。見つからないときは `ansible/group_vars/all.yml` の `app_service` に書く
- 設定ファイル: `common/` とホスト名のディレクトリを配り、変わったファイルに対応するサービスだけを再起動する。unit ファイルが変わったら daemon-reload、`/etc/sysctl*` が変わったら `sysctl --system` を実行する
- 配布はファイルの上書きだけで、`common/` から消したファイルはサーバーに残る。消すときはサーバー上でも消す
- `/var/log/nginx/access.log` と `/var/log/mysql/mysql-slow.log` を空にする

## 複数台構成

- サービスの配置は `ansible/inventory.yml` のホストごとの `host_services` で変える。他のホストに割り当てたサービスは、デプロイで停止して自動起動を無効にする
- `/etc/hosts` に全ホストが登録されているので、`common/` の設定ファイルでは他のホストを `s2` のように名前で書く。IP を書くためだけにホスト別のファイルを作らない
- MySQL を別ホストに移すときは、`bind-address` と、接続元のホストからのユーザーの権限も変える

## 計測

- pprotein: s1 の `localhost:9000`。手元からは ssh の LocalForward で開く
- アクセスログは nginx の LTSV、スロークエリログは MySQL の slow log。alp と slp が全サーバーに入っている
- alp の matching_groups は `/alp-matching-groups` skill で作る
- 計測結果からボトルネックを判断するときは、推測ではなく pprotein、alp、slp の結果を根拠にする

## `ansible/` を変更するとき

- 振る舞いを変えたら `make test` と `make lint` を通す。テストは `ansible/tests/`
- 判断のロジックは `ansible/filter_plugins/` の Python の関数に書き、テストする。filter plugin は Ansible の制約で Python。それ以外のスクリプトとテストは Ruby で書く
- `flake.nix` を変えたら `nix flake check` を通す
