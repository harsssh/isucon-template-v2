# AGENTS.md

ISUCON の競技用リポジトリ。競技サーバーの webapp と設定ファイルをこのリポジトリで管理し、手元から Ansible で全サーバーにデプロイする。

## ディレクトリ

- `app/`: 競技サーバーの `~/webapp` を取り込んだもの。サーバーの `~/webapp` はサーバー上の clone の `app/` へのシンボリックリンク
- `config/common/`: 全サーバーに配る設定ファイル。`config/common/etc/nginx/nginx.conf` は `/etc/nginx/nginx.conf` に置かれる
- `config/s1/` 〜 `config/s5/`: そのホストだけに配る設定ファイル。`config/common/` と同じパスなら、こちらを優先する
- `ansible/`: セットアップとデプロイの playbook。ホストとサービスの配置は `ansible/inventory.yml`
- `docs/tuning/`: nginx, MySQL, sysctl の設定例。使うときは `config/common/` にコピーする
- `survey/`: `make survey` で集めた各サーバーの状態 (サービス、listen しているポート、unit ファイル、環境変数のファイル、テーブルのサイズなど)。サーバーの構成を調べるときは、まずここを読む

`app/` と `config/common/` は初回の `make setup` で primary (既定は s1) から取り込まれる。

## 作業の流れ

変更は 1 つずつ PR にし、ベンチマークで確かめてから main にマージする。スコアが下がったり失敗したりした変更を main に入れないため。この流れでは、ブランチの push と PR の作成をユーザーに聞かずに行ってよい

1. main から `git switch -c <変更の内容の kebab-case>` でブランチを作る
2. `app/` や `config/common/` を編集してコミットし、push する
3. `gh pr create` で PR を作る。本文は下の形にする
4. `make deploy BRANCH=<branch>` で全サーバーにデプロイする
5. ユーザーがポータルからベンチマークを実行し、結果を貼る
6. 本文の結果の行を `gh pr edit --body` で埋める
7. ユーザーがマージを指示したら `gh pr merge --squash --delete-branch` し、`git switch main && git pull` する。スコアが下がったときは、指示に従って PR を close し、`make deploy` で main に戻す

PR のタイトルは変更の内容を 1 行で書く。本文は時間とトークンを使わないよう、次の 3 項目だけにする。diff を 1 行ずつ説明しない

```
根拠: <直す理由になった計測の数値。例: GET /api/chair/nearby が合計 42s (全体の 38%)>
方針: <どう直すかを 1、2 文。例: 椅子の最新の位置を chairs に非正規化し、chair_locations の集計をやめる>
結果: <スコア 前 → 後。前は main の最後の結果>, <エラーの有無>
```

- サーバー上で直接ファイルを編集しない。デプロイでサーバー上の変更は捨てられる
- `make deploy` は全サーバーのサービスを再起動する。ベンチマークの実行中に打たないよう、実行前にユーザーに確認する

## チューニングの方針

目的はベンチマークのスコアを上げること。レギュレーションに反しない範囲で、一般的なアプリケーションでは避ける競技特化の手段を積極的に使う。

- 手段の例
  - アプリのプロセスのメモリにキャッシュする (グローバル変数の map と mutex など)
  - 起動時や `/initialize` で、DB のデータをメモリに読み込んでおく
  - 集計結果を事前に計算しておく。テーブルに列を足して非正規化する
  - MySQL の durability の設定を緩める (`docs/tuning/mysqld.conf`)
  - nginx で静的ファイルを直接返し、キャッシュのヘッダーを付ける
  - ログの出力や、ベンチマーカーが通らない処理を削る
- 実装の品質よりスコアを優先する。production ではありえない雑な実装 (グローバル変数、コピーした処理、ハードコード) でも、スコアが上がるなら好ましい。リファクタリングやテストの追加に時間を使わない
  - ユーザーのグローバルな指示にあるコーディングの規約 (テストの追加、純粋関数への分離など) は `app/` には適用しない。`ansible/` には適用する
- 守ること
  - レギュレーションと当日マニュアルの制約。違反すると失格になる
  - 永続化: API で書き込まれたデータは DB に保存する。メモリだけに持つと、再起動後にデータが残っているかの確認で失格になる。メモリのキャッシュは DB の写しとして持ち、起動時と `/initialize` で DB から作り直す
  - 整合性: ベンチマーカーはレスポンスの内容と、書き込みの直後に読んだときの整合性を検査する。キャッシュは書き込みと同時に更新し、古い値を返さない
  - 複数台でアプリを動かすと、プロセスのメモリのキャッシュはホスト間で共有されない。書き込みのあるデータをメモリにキャッシュするなら、アプリを動かすホストを 1 台にする
- 1 つの PR には 1 つの変更だけを入れる。どの変更でスコアが変わったかを分けるため

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
- 設定ファイル: `config/common/` とホスト名のディレクトリを配り、変わったファイルに対応するサービスだけを再起動する。unit ファイルが変わったら daemon-reload、`/etc/sysctl*` が変わったら `sysctl --system` を実行する
- 配布はファイルの上書きだけで、`config/common/` から消したファイルはサーバーに残る。消すときはサーバー上でも消す
- `/var/log/nginx/access.log` と `/var/log/mysql/mysql-slow.log` を空にする

## 複数台構成

- サービスの配置は `ansible/inventory.yml` のホストごとの `host_services` で変える。他のホストに割り当てたサービスは、デプロイで停止して自動起動を無効にする
- `/etc/hosts` に全ホストが登録されているので、`config/common/` の設定ファイルでは他のホストを `s2` のように名前で書く。IP を書くためだけにホスト別のファイルを作らない
- 複数台のアプリでキャッシュを共有するときは memcached を使う。setup で全ホストに入り、`0.0.0.0:11211` で listen する。1 台の `host_services` に `memcached` を書いて他のホストでは止め、アプリからは `s2:11211` のように名前で接続する。`/initialize` で `flush_all` する
- MySQL を別ホストに移すときは、`bind-address` と、接続元のホストからのユーザーの権限も変える

## 計測

- pprotein: inventory の `pprotein_server` (既定は s1) の `localhost:9000`。手元からは ssh の LocalForward で開く
- pprotein の取得先は、inventory の `host_services` から deploy のたびに作り直す。サービスの配置を変えたら、pprotein の画面ではなく inventory を変えて deploy する
- アプリの `/initialize` からは `http://s1:9000/api/group/collect` を呼ぶ。アプリが s1 以外で動いても計測が始まるように
- アクセスログは nginx の LTSV、スロークエリログは MySQL の slow log。alp と slp が全サーバーに入っている
- アプリが pprotein に記録させる処理 (`/initialize` からの collect と pprof) は `/enable-pprotein` skill で入れる
- alp と slp の設定は `ansible/roles/pprotein/files/alp.yml` と `slp.yml` に書いて deploy する。pprotein の画面で編集しても次の deploy で上書きされる
- alp の matching_groups は `/alp-matching-groups` skill で作る
- 計測結果からボトルネックを判断するときは、推測ではなく pprotein、alp、slp の結果を根拠にする
- ベンチマークの後の分析は `/analyze-pprotein` skill で行う

## `ansible/` を変更するとき

- 振る舞いを変えたら `make test` と `make lint` を通す。テストは `ansible/tests/`
- 判断のロジックは `ansible/filter_plugins/` の Python の関数に書き、テストする。filter plugin は Ansible の制約で Python。それ以外のスクリプトとテストは Ruby で書く
- `flake.nix` を変えたら `nix flake check` を通す
