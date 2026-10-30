---
name: register-ssh-hosts
description: 練習用に起動した EC2 インスタンスを ~/.ssh/config.local に s1, s2, ..., bench として登録する。「ssh の設定を書いて」「config.local に登録して」「s1 に入れるようにして」と言われたとき、またはインスタンスを起動、作り直して IP が変わったときに使う。
---

# register-ssh-hosts

`~/.ssh/config` は Nix (home-manager) で管理されていて書き換えられない。`~/.ssh/config.local` が `Include` されているので、そこに書く。

Host 名は `ansible/inventory.yml` のホスト名 (`s1` 〜 `s5`) と揃える。ベンチマーク用のインスタンスは `bench` にする。`bench` は inventory に入れない。

## 手順

1. 対象のインスタンスと Public IP を調べる。ユーザーに指定がなければ Name タグ (`isucon14-practice`, `isucon14-bench` など) で絞る
   ```bash
   aws ec2 describe-instances \
     --filters Name=instance-state-name,Values=running \
     --query 'Reservations[].Instances[].[InstanceId,PublicIpAddress,Tags[?Key==`Name`]|[0].Value]' \
     --output text
   ```
2. どのインスタンスを `s1`, `s2`, ..., `bench` にするか決める
   - 台数とベンチ用の指定があればそれに従う。なければ起動順に `s1` から振り、ベンチ用は最後の 1 台にする
   - 決められないときはユーザーに聞く
3. `~/.ssh/config.local` を読み、`s1` 〜 `s5` と `bench` の既存の `Host` ブロックを確認する
   - 無関係な `Host` (`vm` など) は変更しない
   - 既存のブロックがあれば IP だけ書き換える。同じ `Host` を重複して追記しない
4. 以下の形で追記または更新する
   ```
   Host s1 s2 bench
     User isucon
     ForwardAgent yes

   Host s1
     HostName <s1 の Public IP>
     # For pprotein
     LocalForward 9000 localhost:9000

   Host s2
     HostName <s2 の Public IP>

   Host bench
     HostName <bench の Public IP>
   ```
   - 1 行目の Host 名は登録するものに合わせる
   - `LocalForward 9000` は pprotein が動く primary (既定は `s1`) だけに付ける
5. 接続を確かめる。初回は host key の確認で止まるので `accept-new` を付ける
   ```bash
   for h in s1 s2 bench; do ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 $h hostname; done
   ```

## 注意

- 起動直後は user data (GitHub の公開鍵の登録) が終わっておらず、`Permission denied` になることがある。1〜2 分待って再実行する
- インスタンスを停止、起動し直すと Public IP が変わる。変わったらこの手順で IP を更新する
- `known_hosts` に古い IP の行が残っていても害はないので、消さない
