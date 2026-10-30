---
name: create-contest-repo
description: isucon-template-v2 から、練習用または本番用の private リポジトリを作って手元に clone し、make survey まで進める。「リポジトリを作って」「練習を始める」「本番の準備」「新しい回の repo」と言われたとき、または練習用のサーバーを作り直して最初からやり直すときに使う。
---

# create-contest-repo

ISUCON の練習や本番では、このテンプレートから回ごとにリポジトリを作る。`make setup` は primary の webapp と設定ファイル (`env.sh` の DB のパスワードなどを含む) を origin に push するので、テンプレート自体では setup しない。

## 練習と本番の違い

| | 練習 | 本番 |
|---|---|---|
| リポジトリ名 | `isucon<回>-practice` (例: `isucon14-practice`) | `isucon<回>` (例: `isucon15`) |
| サーバー | 自分で起動した EC2 (`docs/practice.md`) | ポータルに表示されるサーバー |
| ssh の設定 | `register-ssh-hosts` skill で登録する | ポータルの IP をユーザーから受け取って登録する |
| `make setup` の前 | 確認せず進めてよい | 実行してよいかユーザーに確認する |

どちらでも、リポジトリは必ず private にする。本番中にコードを公開することは競技のルールで禁止されている。

## 手順

1. 練習か本番か、何回目の ISUCON かを決める。ユーザーが言っていなければ聞く。練習ならサーバーの Name タグ (`isucon14-practice` など) からも分かる
2. 作るリポジトリの名前を決める
   - `gh api user -q .login` で owner を調べ、`gh repo view <owner>/<名前>` で同名のリポジトリが無いか確かめる
   - 同名のリポジトリがあれば、ユーザーに聞く。setup は `app/` が空のリポジトリにしか webapp を取り込めないので、サーバーを作り直して最初からやり直すなら、既存のリポジトリは使えない。`-2` のような連番を付けた名前を提案する
3. テンプレートを決める。このリポジトリが `gh repo view --json isTemplate` で template ならこのリポジトリ、そうでなければ `gh repo view --json templateRepository` のリポジトリ
4. テンプレートの親ディレクトリに移り、private で作って clone する
   ```bash
   gh repo create <owner>/<名前> --private --template <テンプレート> --clone
   ```
   - テンプレートのコピーは非同期なので、clone が空になることがある。`git -C <名前> log` が失敗したら、数秒待って `git -C <名前> pull origin main` をやり直す
5. 作ったリポジトリで `direnv allow` を実行する
6. サーバーの ssh の設定を登録する
   - 練習: `register-ssh-hosts` skill を使う
   - 本番: ポータルのサーバーの IP をユーザーから受け取り、`register-ssh-hosts` skill の手順 3 以降と同じ形で `~/.ssh/config.local` に書く。`bench` は無い
7. `ansible/inventory.yml` の `hosts` を、登録したサーバー (`s1` から台数分) に合わせる。変えたらコミットして push する
8. `make survey` を実行し、NG の項目と、その原因と直し方をユーザーに伝える
9. NG が無ければ `make setup` に進む。本番では実行してよいか確認してから進める

## 注意

- 作ったリポジトリでの作業は、そのリポジトリの `AGENTS.md` に従う
- 練習を終えたリポジトリは消さない。後で見返すことがある。消すのはユーザーに言われたときだけにする
- チームで出るときは、メンバーを collaborator に招待する (`gh api -X PUT repos/<owner>/<名前>/collaborators/<GitHub のユーザー名>`)
