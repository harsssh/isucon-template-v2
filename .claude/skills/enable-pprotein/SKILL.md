---
name: enable-pprotein
description: アプリに pprof のエンドポイントと、/initialize から pprotein の計測を始める処理を入れる。「pprotein を有効にして」「計測できるようにして」「pprotein に何も記録されない」と言われたとき、または setup の後で最初のチューニングを始める前に使う。
---

# enable-pprotein

pprotein はベンチマークの開始に合わせて、全ホストの pprof、アクセスログ、スロークエリログを同時に取る。取得先は ansible が inventory から作るが、次の 2 つはアプリのコードに入れる必要がある。

- 計測の開始: `/initialize` から pprotein の `/api/group/collect` を呼ぶ。ベンチマーカーは負荷をかける直前に `/initialize` を呼ぶので、計測の開始が負荷の開始と揃う
- pprof: アプリが listen しているポートの `/debug/pprof/` で profile を返す。pprotein は `http://<host>:<app_port>/debug/pprof/profile` から取る

## 手順

1. 入っているか調べる。`app/` で `api/group/collect` と `pprof` を検索し、両方あれば何もしない
2. pprotein を動かすホストを `ansible/inventory.yml` の `pprotein_server` グループのホストで調べる (既定は s1)
3. `/initialize` のハンドラーに、collect を呼ぶ処理を入れる
   - 非同期で呼び、結果を待たない。collect は全ての取得が終わるまで (60 秒) 返らないので、待つと `/initialize` がタイムアウトする
   - 失敗してもエラーにしない。計測できないだけで、ベンチマークは続ける
   - URL は `http://<pprotein_server>:9000/api/group/collect`。全ホストの `/etc/hosts` に登録されているので、ホスト名で書ける。アプリが pprotein と別のホストで動いても届く
   ```go
   go func() {
   	res, err := http.Get("http://s1:9000/api/group/collect")
   	if err != nil {
   		log.Printf("failed to start pprotein: %v", err)
   		return
   	}
   	res.Body.Close()
   }()
   ```
4. pprof のハンドラーを、アプリのルーターに `/debug/pprof/` で登録する。標準の `net/http/pprof` を使い、`github.com/kaz/pprotein/integration` は使わない。依存が増えるのと、`echov4.Integrate` はリクエストごとのログを有効にして遅くなるため
   - chi: `mux.Mount("/debug", middleware.Profiler())` (`github.com/go-chi/chi/v5/middleware`)
   - echo: `import _ "net/http/pprof"` と `e.Any("/debug/pprof/*", echo.WrapHandler(http.DefaultServeMux))`
   - net/http の ServeMux: `import _ "net/http/pprof"` で `http.DefaultServeMux` に登録される。アプリが別の ServeMux を使っていれば `mux.Handle("/debug/pprof/", http.DefaultServeMux)`
   - 認証などのミドルウェアが先に適用されるルーターなら、その外側に登録する
5. 手元でビルドが通ることを確かめる (`app/` の Go のディレクトリで `go build -o /dev/null .`)
6. コミットして push し、`make deploy` してよいかユーザーに確認する
7. deploy の後、pprotein のホストで確かめる
   - `ssh <pprotein_server> curl -s -o /dev/null -w '%{http_code}\n' http://<アプリのホスト>:<app_port>/debug/pprof/` が 200
   - 次のベンチマークの後、`ssh <pprotein_server> curl -s localhost:9000/api/httplog` が空の配列でない

## 注意

- 取得の時間は `ansible/roles/pprotein/templates/targets.json.j2` の `Duration` (60 秒)。負荷走行がそれより長い回は、その値を負荷走行の時間に合わせる
- 計測は CPU を使うので、最後の提出の前に collect の呼び出しを消す。pprof のハンドラーは呼ばれなければ負荷にならないので残してよい
