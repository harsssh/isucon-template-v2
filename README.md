# isucon-template-v2

ISUCON 本番で使う、競技サーバーのセットアップと計測の手順。

練習や本番では、このテンプレートから回ごとに private リポジトリを作り、そちらで作業する。Claude Code で `/create-contest-repo` を実行すると、リポジトリの作成から `make survey` まで進む。

練習用のサーバーを用意する場合は、[練習環境の準備](docs/practice.md) を参照する。

## サーバーへの接続

ローカルの `~/.ssh/config` に以下を設定。
接続先とユーザー名は競技環境に合わせる。
Host 名は `ansible/inventory.yml` のホスト名と揃える (最大 5 台を想定して `s1` から `s5`)。
```
Host s1 s2 s3 s4 s5
    User isucon
    ForwardAgent yes

Host s1
    Hostname xxx.xxx.xxx.xxx
    # For pprotein
    LocalForward 9000 localhost:9000

Host s2
    Hostname yyy.yyy.yyy.yyy
```

## 初回計測までの手順

### セットアップ

コマンドはすべて手元のリポジトリで実行する。Ansible などは Nix の devShell に入っていて、`direnv allow` しておくとリポジトリに入ったときに自動で読み込まれる。
direnv を使わない場合は、各コマンドの前に `nix develop -c` を付ける。

サーバー上の git は、手元の ssh-agent の鍵を転送して GitHub に接続する。`ssh-add -l` で GitHub の鍵が表示されることを確かめておく。デプロイキーは使わない。

1. `ansible/inventory.yml` の `hosts` を使うサーバーに合わせる
2. サーバーの状態を調べる。ansible の前提と合わない点が表示されたら、`ansible/group_vars/all.yml` などを直す
   ```bash
   make survey
   ```
3. 全サーバーをセットアップする
   ```bash
   make setup
   ```
4. 手元で `git pull` する (primary の webapp と設定ファイルが push されている)

`survey/s1.md` などには、前提の照合結果と、サービス、listen しているポート、unit ファイル、テーブルのサイズなどを書き出す。コミットしておくと、エージェントがサーバーの構成を調べ直さずに済む。

`setup.yml` が行うこと:

- 全サーバー: hostname の設定 (再起動後も保持)、全ホストの名前の `/etc/hosts` への登録、ツール (bottom, tmux, alp, slp, pprotein-agent) と alias、tmux の設定のインストール、リポジトリの clone、`~/webapp` をリポジトリの `app/` へのシンボリックリンクに置き換え (git で管理していない大きいファイルなどは既存の `~/webapp` からコピー)
- primary (`inventory.yml` の `primary`): `~/webapp` と `/etc` の設定ファイルのリポジトリへの取り込みと push、nginx の LTSV ログと MySQL の slow log の設定
- pprotein サーバー (`inventory.yml` の `pprotein_server`): pprotein の起動

何度実行しても同じ状態になるので、途中で失敗したら原因を直して再実行すればよい。

Go が古すぎる (1.21 未満) 場合は新しくインストールする。
```bash
ansible-playbook ansible/setup.yml --tags go
```

### pprotein の設定

app (echo の場合)
```go
// main.go
import (
    pprotein "github.com/kaz/pprotein/integration/echov4"
)

func main() {
    // pprof の handler を追加
    pprotein.Integrate(e)
}

func initializeHandler(c echo.Context) error {
    // 計測開始。pprotein は inventory の pprotein_server (s1) で動くので、アプリがどのホストで動いても s1 を呼ぶ
    http.Get("http://s1:9000/api/group/collect")
}
```

```bash
go mod tidy
```

pprotein の取得先 (`targets.json`) は、setup と deploy のたびに `ansible/inventory.yml` の `host_services` から作り直す。アプリのホストから pprof、nginx のホストからアクセスログ、MySQL のホストから slow log を取る。pprotein の画面で編集しても上書きされるので、取得先は inventory で変える。

pprotein と pprotein-agent には、localhost とプライベートネットワークからしか接続できない。

pprotein http log の集約

Claude Code で `/alp-matching-groups` を実行し、出力された `matching_groups` を pprotein の httplog の設定にペーストする。

### 計測

デプロイすれば準備完了
```bash
make deploy
```

## デプロイ

```bash
# origin/main を全サーバーにデプロイする
make deploy

# origin/my-branch をデプロイする
make deploy BRANCH=my-branch
```

`deploy.yml` は各サーバーで以下を行う。

1. origin のブランチを checkout する (サーバー上の変更は捨てる)
2. アプリを割り当てたホストでアプリをビルドする (`~/webapp/go` で `make`)
3. `config/common/` とホスト名のディレクトリ (`config/s1/` など) の設定ファイルを配布する。同じパスのファイルはホスト名のディレクトリを優先する
4. サービスを再起動する。アプリ (WorkingDirectory が `~/webapp/go` のサービス) は毎回、nginx や MySQL は設定ファイルか unit ファイルが変わったときだけ再起動する
5. access.log と slow log を空にする

サービスの配置は `ansible/inventory.yml` の `host_services` で変える。他のホストに割り当てたサービスは、デプロイ時に停止して自動起動を無効にする。

```yaml
s1:
  host_services: [nginx, "{{ app_service }}"]
s2:
  host_services: ["{{ db_service }}"]  # MySQL か MariaDB のサービス名がサーバーから自動で入る
```

`config/common/` の設定ファイルでは、他のホストを `s2` のように名前で指定できる (セットアップで `/etc/hosts` に登録される)。たとえば `env.sh` の DB のホストを `s2` にすれば、ホストごとにファイルを分けなくてよい。全ホストで同じにできないファイルだけ、`config/s1/` などのホスト名のディレクトリに置く。

Go 以外の実装を使うときやアプリのサービスが見つからないときは、`ansible/group_vars/all.yml` の `app_dir` と `app_service` を変える。

## Makefile

| コマンド | 内容 |
|---|---|
| `make survey` | サーバーの状態を `survey/` に書き出し、ansible の前提と照合する。サーバーは変更しない |
| `make setup` | 競技サーバーの初回セットアップ |
| `make deploy [BRANCH=...]` | 全サーバーへのデプロイ |
| `make lint` | ansible-lint |
| `make test` | スクリプトとフィルターのテスト |

サーバー上では alias (`sc`, `scs`, `jcfu` など) で systemctl と journalctl を操作する。

nginx, MySQL, sysctl のチューニング用の設定例は [docs/tuning](docs/tuning) にある。使うときは `config/common/` に手でコピーする。

## リンク集

ライブラリ

- https://github.com/jmoiron/sqlx/
- https://jmoiron.github.io/sqlx/
- https://github.com/samber/lo/
- https://echo.labstack.com/docs/

ミドルウェア

- https://nginx.org/en/docs/

その他

- https://go.dev/play/
