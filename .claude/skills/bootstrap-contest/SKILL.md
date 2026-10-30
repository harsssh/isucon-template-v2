---
name: bootstrap-contest
description: 練習や本番の開始から、最初のベンチマークが pprotein で計測できる状態になるまでを、決まった手順と確認で進める。想定と違う結果が出たら直さずに止まる。「練習を始めて」「本番の準備をして」「計測できるところまで進めて」と言われたときに使う。
---

# bootstrap-contest

リポジトリの作成、setup、計測の組み込み、最初のベンチマークの確認までを行う。各ステップに「確認」があり、全て満たしたときだけ次に進む。

この skill は軽いモデルでも実行できるように書いてある。手順に無い判断や修正はしない。

## 止まるとき

次のどれかに当たったら、その場で作業を止め、下の形で報告して終わる。原因を推測して直そうとしない。調査は、ユーザーが賢いモデルに切り替えて行う。

- 確認の条件を 1 つでも満たさない
- コマンドが 0 以外で終わる、または ansible の `PLAY RECAP` で `failed` か `unreachable` が 0 でない
- 手順の書き方と、リポジトリやサーバーの実際の状態が合わない (ファイルが無い、フレームワークが手順に無い、など)
- ユーザーへの確認が要る操作で、ユーザーの返事が無い

報告の形:

```
止まったステップ: <番号と名前>
実行したこと: <コマンド>
期待: <確認の条件>
実際: <出力のうち関係する部分を 20 行以内で>
```

## 手順

### 1. リポジトリを作って setup する

`create-contest-repo` skill に従い、`make setup` まで進める。

確認:
- `make survey` に NG が無い (NG があれば、そこで止まる)
- `make setup` の `PLAY RECAP` で、全ホストの `failed=0` と `unreachable=0`
- `git pull` すると、`import webapp and config from s1` と `configure logs for alp and slp and add files for deploy` の 2 つのコミットが入る
- `app/` に webapp のファイルがある

### 2. サーバーの状態を確かめる

`ansible/inventory.yml` の全ホストで、次を実行する。`<app_service>` は `survey/<ホスト>.md` の「WorkingDirectory が ... のサービスが 1 つに決まる」の行の候補、`<db_service>` は同じファイルのサービスの一覧にある `mysql` か `mariadb`。

```bash
ssh -o ClearAllForwardings=yes <ホスト> 'systemctl is-active nginx <db_service> <app_service> pprotein-agent; curl -s -o /dev/null -w "%{http_code}\n" localhost/'
```

`pprotein_server` グループのホスト (既定は s1) では、さらに次を実行する。

```bash
ssh -o ClearAllForwardings=yes s1 'systemctl is-active pprotein; cat /etc/pprotein/data/targets.json'
```

確認:
- `systemctl is-active` の行が全て `active`
- `curl` が 200 か 3xx
- `targets.json` に、全ホストの `Label` がある

### 3. 計測の組み込みを PR にする

1. main から `git switch -c enable-measurement` でブランチを作る
2. `enable-pprotein` skill の手順 1 から 5 に従い、アプリに collect の呼び出しと pprof を入れる
3. `alp-matching-groups` skill に従い、`config/common/etc/pprotein/data/alp.yml` の `matching_groups` を書く
4. コミットして push し、`gh pr create` で PR を作る。本文は `AGENTS.md` の PR の形にする。結果の見出しは「未計測」と書いておく

確認:
- `app/` の Go のディレクトリで `go build -o /dev/null .` が成功する
- `gh pr diff --name-only` に、アプリのファイルと `alp.yml` だけがある

### 4. deploy する

ユーザーに「ベンチマークを実行していなければ deploy してよいか」を聞き、許可を得てから実行する。

```bash
make deploy BRANCH=enable-measurement
```

その後、`pprotein_server` のホストから、アプリが動く全ホストの pprof を確かめる。`<app_port>` は `survey/<ホスト>.md` の「アプリが listen しているポートが分かる」の行の番号。

```bash
ssh -o ClearAllForwardings=yes s1 'curl -s -o /dev/null -w "%{http_code}\n" http://<ホスト>:<app_port>/debug/pprof/'
```

確認:
- `PLAY RECAP` で、全ホストの `failed=0` と `unreachable=0`
- pprof の `curl` が全ホストで 200
- `ssh s1 sudo cat /etc/pprotein/data/alp.yml` が、手順 3 で書いた内容と同じ

### 5. 最初のベンチマークを確かめる

ユーザーにベンチマークの実行を頼み、終わったら結果のログを貼ってもらう。その後、pprotein の記録を確かめる。

```bash
for t in httplog slowlog pprof; do ssh -o ClearAllForwardings=yes s1 curl -s localhost:9000/api/$t; done
```

最新の `GroupId` の entry について、`/api/httplog/<ID>` で、nginx が動くホストの集計を見る。

確認:
- ベンチマークの結果が pass で、エラーの件数が 0。ベンチマーカーの設定の誤り (決済のサーバーの URL など) でもエラーになるので、エラーがあれば止まる
- 最新の `GroupId` に、httplog、slowlog、pprof が対象のホストの数ずつあり、全て `Status` が `ok`
- httplog の `Uri` の列に、ID のような値 (数字の列、UUID、ULID など) を含むパスが残っていない

全て満たしたら、PR の結果の見出しにスコアとエラーの有無を書き (`gh pr edit --body-file`)、ユーザーにマージしてよいか聞く。許可されたら `AGENTS.md` の作業の流れの手順 7 に従ってマージする。

## 終わったら

ユーザーに次の 3 つを伝えて終わる。

- 最初のスコア
- PR の URL
- 次は `analyze-pprotein` skill で計測を分析できること
