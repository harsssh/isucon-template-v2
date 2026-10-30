# isucon-template-v2

## 練習環境の準備
https://github.com/matsuu/aws-isucon

上記リポジトリに記載の AMI からインスタンスを起動。
以下のユーザーデータを設定すると便利。
```bash
#!/bin/bash -ex

# スペース区切り
USERS="harsssh"

for user in $USERS; do
    sudo -u isucon mkdir -p /home/isucon/.ssh
    sudo -u isucon chmod 700 /home/isucon/.ssh
    curl "https://github.com/${user}.keys" | sudo -u isucon tee -a /home/isucon/.ssh/authorized_keys
    sudo -u isucon chmod 600 /home/isucon/.ssh/authorized_keys
done
```

ローカルの `~/.ssh/config` に以下を設定。
Host 名は `ansible/inventory.yml` のホスト名と揃える (最大 5 台を想定して s1 〜 s5)。
```
Host s1 s2 s3 s4 s5 bench
    User isucon
    ForwardAgent yes

Host s1
    Hostname xxx.xxx.xxx.xxx
    # For pprotein
    LocalForward 9000 localhost:9000

Host s2
    Hostname yyy.yyy.yyy.yyy

Host bench
    Hostname zzz.zzz.zzz.zzz
```

## 初回計測までの手順

### セットアップ

手元のリポジトリで実行する。Ansible は Nix の devShell に入っていて、`direnv allow` しておくとリポジトリに入ったときに自動で読み込まれる。
direnv を使わない場合は、各コマンドの前に `nix develop -c` を付ける。

1. `ansible/inventory.yml` の `hosts` を使うサーバーに合わせる
2. `ansible/group_vars/all.yml` と `Taskfile.yml` の "Frequently changed" を編集して push する
3. 全サーバーをセットアップする
   ```bash
   ansible-playbook ansible/setup.yml
   ```
4. 手元で `git pull` する (primary の webapp と設定ファイルが push されている)

`setup.yml` が行うこと:

- 全サーバー: hostname の設定 (再起動後も保持)、ツール (go-task, bottom, alp, slp, pprotein-agent) と alias のインストール、リポジトリの clone、`~/webapp` をリポジトリの `app/` へのシンボリックリンクに置き換え (git で管理していない大きいファイルなどは既存の `~/webapp` からコピー)
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
```bash
# この結果を pprotein の設定にペースト
task generate-matching-groups
```

### 計測

デプロイすれば準備完了
```bash
task deploy
```

## Taskfile の補足
基本的な説明は表示される help を見てください
```bash
task
```

分かりにくそう or 便利なものを補足します

```bash
# origin/my-branch が反映されます
# 何も指定しない場合は origin/main が反映されます
task deploy -- my-branch

# common/ に加えて, hostname と同じ名前のディレクトリ (s1/ など) の設定ファイルも配布されます
task deploy

# service の起動 & 自動起動を有効化
task enable -- nginx mysql

# service の停止 & 自動起動を無効化
task disable -- nginx mysql

# 変数に設定したすべての service を再起動
task restart-all

# 変数に設定したすべての service の状態を表示
task status-all
```

`Taskfile.yml` は `~` にシンボリックリンクを置いていて, `alias task="task -g"` を設定しているので, どこからでも利用できます.

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