---
name: analyze-pprotein
description: ベンチマークの後、pprotein に記録されたアクセスログ (alp)、スロークエリログ (slp)、pprof を読み、ボトルネックと直す候補を根拠の数値つきで挙げる。「計測結果を見て」「pprotein を分析して」「ボトルネックはどこ」「次に何を直す」と言われたとき、またはベンチマークの結果を貼られて次の改善を考えるときに使う。
---

# analyze-pprotein

pprotein は `/initialize` から始まる 1 回の計測で、全ホストの httplog (アクセスログ)、slowlog (スロークエリログ)、pprof を同じグループ ID で記録する。そのグループの 3 種類の結果を突き合わせて、時間を使っている処理を特定する。

## 前提

- アプリが `/initialize` から pprotein の collect を呼び、`/debug/pprof/` を返すこと。`curl` で entry が空なら `enable-pprotein` skill を先に使う
- alp の `matching_groups` が設定されていること。URI がパラメータごとにばらけていたら、`alp-matching-groups` skill で作り、`config/common/etc/pprotein/data/alp.yml` に書いて deploy する。pprotein は集計の結果を保存するので、設定を変えても記録済みの entry の結果は変わらない。記録済みの回は、生のログを alp で集計し直す
  ```bash
  ssh -o ClearAllForwardings=yes s1 'curl -s localhost:9000/api/httplog/data/<ID> | alp ltsv --config /etc/pprotein/data/alp.yml --format tsv'
  ```

## API

pprotein は `ansible/inventory.yml` の `pprotein_server` グループのホスト (既定は s1) の `localhost:9000` で動く。手元の LocalForward には頼らず、ssh 越しに叩く。`-o ClearAllForwardings=yes` を付けると、ユーザーが開いている ssh とポート転送がぶつからない。

```bash
ssh -o ClearAllForwardings=yes s1 curl -s localhost:9000/api/httplog
```

| パス | 返すもの |
|---|---|
| `/api/{httplog,slowlog,pprof}` | entry の一覧 (JSON の配列) |
| `/api/httplog/<ID>` | alp で集計した結果 (TSV) |
| `/api/slowlog/<ID>` | slp で集計した結果 (TSV) |
| `/api/{httplog,slowlog}/data/<ID>` | 集計する前の生のログ |
| `/api/pprof/data/<ID>` | pprof の profile (バイナリ) |
| `/api/httplog/config` | alp の設定 (GET で読み、POST で置き換える) |

entry は `{"Snapshot": {"ID", "Datetime", "GroupId", "Label", "Type", "URL", "Duration", ...}, "Status", "Message"}`。`Label` はホスト名、`GroupId` は 1 回の計測ごとの ID。`Status` が `ok` のものだけ使う。`fail` なら `Message` に理由がある。

## 手順

1. 一覧を取り、最新の `GroupId` の entry を種類とホストごとに選ぶ。ユーザーが別の回を指定したらそれを使う。entry の時刻がベンチマークの時刻と合うか確かめる
2. httplog を読む (nginx が動くホストごと)
   - 合計の時間 (`Sum`) の大きい順に並べ、上位 10 件を出す。件数 (`Count`)、平均 (`Avg`)、最大 (`Max`)、ステータスごとの件数も添える
   - 合計が大きいものが直す候補。平均が大きく件数が少ないものより、件数が多く合計が大きいものを優先する
   - 4xx, 5xx が多いエンドポイントは、遅さではなく失敗が原因かもしれないので別に挙げる
3. slowlog を読む (MySQL が動くホストごと)
   - 合計の時間の大きい順に上位 10 件を出す。件数、平均、`Rows Examined` と `Rows Sent` の比も添える
   - 検査した行数が返した行数より桁違いに多いクエリはインデックスが無い候補。テーブルの定義 (`app/sql/` など) とインデックスを確かめる
   - 件数が多く 1 回は速いクエリは N+1 の候補。発行しているコードを `app/` から探す
4. pprof を読む (アプリが動くホストごと)
   - `go tool pprof` を手元で使う (devShell に Go がある)。profile をスクラッチに保存して `go tool pprof -top -cum <file>` と `-top <file>`
   - `cum` の上位から、アプリのハンドラーと、その中で時間を使っている関数を挙げる
   - 時間の多くが DB の待ち (`database/sql`、`net` の read) か、アプリの CPU (JSON、暗号、ループ、GC) かを分ける
5. 3 つを突き合わせ、直す候補を効果の見込みが大きい順に 3 つ挙げる。それぞれに次を書く
   - 何が遅いか: エンドポイント、クエリ、関数
   - 根拠: 上の表の数値 (例: `GET /api/chair/nearby` は合計 42.1 秒で全体の 38%、平均 0.21 秒)
   - 直し方の案と、変えるファイルと行
   - 見込み: どの数値がどれくらい減るか
6. ユーザーがどれを直すか決めたら、AGENTS.md のチューニングの方針に従って 1 つずつ直す

## 判断の基準

- 推測で候補を挙げない。挙げる候補には、必ず上の表のどれかの数値を根拠に付ける
- 全体の合計時間に占める割合で比べる。数 % のものを直しても点数はほとんど変わらない
- ベンチマーカーのログ (エラーやタイムアウト、スコアの内訳) を貼られたら、それも根拠に使う。失敗で減点されているなら、遅さより先に直す
- 同じグループの結果だけを比べる。別の回の結果と混ぜない。前の回と比べるときは、その旨と両方の `GroupId` を書く
