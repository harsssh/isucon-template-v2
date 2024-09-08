# isucon-template-v2

## 初回計測までの手順

### ソースコードの push まで

名前は何でもいいが、短い方が楽
```bash
git clone $REPO_URL $REPO_DIR
```

go-task をインストール
```bash
cd $REPO_DIR
assets/install_go_task.sh
```

`SetupTasks.yml` を実行.
実行前に "Frequently changed" の部分を確認してください.
```bash
task -t SetupTasks.yml all
source ~/.bashrc  # alias を読み込む
```

pprotein を起動
```bash
task enable -- pprotein
```

Go が古すぎる場合は新しくインストール
```bash
task -t SetupTasks.yml install-go
source ~/.bashrc  # PATH を読み込む
```

gitignore を設定し, pushする
```bash
cd app
cat << 'EOF' >> .gitignore
node
python
# ...
EOF

git add -A && git commit -m "init" && git push
```

### ログの設定

nginx
```nginx configuration
# /etc/nginx/nginx.conf
log_format ltsv "time:$time_local"
                "\thost:$remote_addr"
                "\tforwardedfor:$http_x_forwarded_for"
                "\treq:$request"
                "\tstatus:$status"
                "\tmethod:$request_method"
                "\turi:$request_uri"
                "\tsize:$body_bytes_sent"
                "\treferer:$http_referer"
                "\tua:$http_user_agent"
                "\treqtime:$request_time"
                "\tcache:$upstream_http_x_cache"
                "\truntime:$upstream_http_x_runtime"
                "\tapptime:$upstream_response_time"
                "\tvhost:$host";
access_log /var/log/nginx/access.log ltsv;
```

mysql
```
# /etc/mysql/mysql.conf.d/mysqld.cnf
[mysqld]
slow_query_log = 1
slow_query_log_file = /var/log/mysql/mysql-slow.log
long_query_time = 0
log-queries-not-using-indexes
```

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
task -t SetupTasks.yml generate-matching-groups
```

### 計測

デプロイすれば準備完了
```bash
task deploy
```

## リンク集

ライブラリ

- https://github.com/jmoiron/sqlx
- https://jmoiron.github.io/sqlx/
- https://github.com/samber/lo