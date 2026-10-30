---
name: alp-matching-groups
description: アプリのルーティング定義から、alp (pprotein の httplog) で URI を集約するための matching_groups を作る。「matching_groups を作って」「alp の集約設定」「pprotein の httplog がばらける」と言われたとき、またはアプリのルーティングを変えた後に使う。
---

# alp-matching-groups

pprotein の httplog は alp で集計する。`/api/users/123` と `/api/users/456` のようにパラメータ違いの URI は別の行になるので、`matching_groups` の正規表現で 1 行にまとめる。

## 手順

1. `app/` の中で、ベンチマーカーが叩く実装のルーティング定義を探す
   - 使う言語は `ansible/group_vars/all.yml` の `app_dir` で分かる (既定は `go`)
   - Go の echo なら `e.GET(`、`e.Group(` など。ほかのフレームワーク (chi, gin, net/http の `GET /path/{id}` など) も同じ考え方で読む
   - Group やサブルーターの prefix は、子のルートのパスに連結する
2. ルートごとに正規表現を作る
   - パスパラメータ (`:id`, `{id}`) は `[^/]+` にする
   - ワイルドカード (`*`, `{path...}`) は `.+` にする
   - 固定部分の正規表現の特殊文字 (`.` など) はエスケープする
   - `^` と `$` で囲む。alp は既定でクエリ文字列を除いて照合するので、クエリは考えなくてよい
   - メソッド違いで同じパスのルートは 1 つにまとめる
3. 並べる順序を決める
   - alp は上から順に照合し、最初にマッチしたグループに入れる
   - パラメータを含むパターンにマッチしてしまう固定パス (`/api/users/me` と `/api/users/[^/]+` など) は、そのパターンより前に置く
4. nginx が直接返す静的ファイルも、パスの種類ごとにまとめる (`^/assets/.+$`, `^/image/.+$` など)。nginx の設定 (`config/common/etc/nginx/`) の `location` を見て決める
5. 結果を YAML で出力する

```yaml
matching_groups:
  - ^/api/users/me$
  - ^/api/users/[^/]+$
  - ^/api/users/[^/]+/posts$
  - ^/assets/.+$
```

## 確認

アクセスログがあるときは、実際のログで集約できているか確かめる。`s1` は nginx が動いているホストに読み替える。

```bash
ssh s1 "alp ltsv --file /var/log/nginx/access.log -m '<パターンをカンマ区切りで>' --sort count -r" | head -40
```

パラメータの値が入ったままの URI が残っていたら、対応するパターンが漏れているか、順序が間違っている。

## 反映

出力した `matching_groups` は `ansible/roles/pprotein/files/alp.yml` に書き、コミットして deploy する。deploy が pprotein のホストの `/etc/pprotein/data/alp.yml` を上書きする。pprotein の画面で編集しても次の deploy で消えるので、画面では編集しない。
