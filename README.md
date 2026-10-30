# isucon-template-v2

ISUCON 本番で使う、競技サーバーのセットアップと計測の手順。

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

1. `ansible/inventory.yml` の `hosts` を使うサーバーに合わせる
2. 全サーバーをセットアップする
   ```bash
   make setup
   ```
3. 手元で `git pull` する (primary の webapp と設定ファイルが push されている)

`setup.yml` が行うこと:

- 全サーバー: hostname の設定 (再起動後も保持)、ツール (bottom, alp, slp, pprotein-agent) と alias のインストール、リポジトリの clone、`~/webapp` をリポジトリの `app/` へのシンボリックリンクに置き換え (git で管理していない大きいファイルなどは既存の `~/webapp` からコピー)
- primary (`inventory.yml` の `primary`): `~/webapp` と `/etc` の設定ファイルのリポジトリへの取り込みと push、nginx の LTSV ログと MySQL の slow log の設定、pprotein の起動

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
    // 計測開始
    http.Get("http://localhost:9000/api/group/collect")
}
```

```bash
go mod tidy
```

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
3. `common/` とホスト名のディレクトリ (`s1/` など) の設定ファイルを配布する。同じパスのファイルはホスト名のディレクトリを優先する
4. サービスを再起動する。アプリ (WorkingDirectory が `~/webapp/go` のサービス) は毎回、nginx や MySQL は設定ファイルか unit ファイルが変わったときだけ再起動する
5. access.log と slow log を空にする

サービスの配置は `ansible/inventory.yml` の `services` で変える。他のホストに割り当てたサービスは、デプロイ時に停止して自動起動を無効にする。

```yaml
s1:
  services: [nginx, "{{ app_service }}"]
s2:
  services: [mysql]
```

Go 以外の実装を使うときやアプリのサービスが見つからないときは、`ansible/group_vars/all.yml` の `app_dir` と `app_service` を変える。

## Makefile

| コマンド | 内容 |
|---|---|
| `make setup` | 競技サーバーの初回セットアップ |
| `make deploy [BRANCH=...]` | 全サーバーへのデプロイ |
| `make lint` | ansible-lint |
| `make test` | スクリプトとフィルターのテスト |

サーバー上では alias (`sc`, `scs`, `jcfu` など) で systemctl と journalctl を操作する。

nginx, MySQL, sysctl のチューニング用の設定例は [docs/tuning](docs/tuning) にある。使うときは `common/` に手でコピーする。

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
