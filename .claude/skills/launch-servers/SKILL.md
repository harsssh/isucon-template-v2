---
name: launch-servers
description: ISUCON の競技サーバーを AWS に起動する。練習では matsuu/aws-isucon の AMI から EC2 を起動し、本番では運営から配られた CloudFormation のテンプレートから stack を作る。「サーバーを立てて」「練習環境を作って」「インスタンスを起動して」「CloudFormation のテンプレートをもらった」と言われたときに使う。
---

# launch-servers

起動したら `register-ssh-hosts` skill で ssh の設定を登録し、`create-contest-repo` skill でリポジトリを作る。

起動は課金が発生するので、何を起動するか (AMI か テンプレート、インスタンスタイプ、台数) を示して、ユーザーの確認を取ってから実行する。

AWS CLI は手元の既定のプロファイルとリージョン (`ap-northeast-1`) を使う。`aws sts get-caller-identity` が失敗したら、ユーザーに `aws login` などで認証してもらう。

## 練習: AMI から起動する

1. 問題を決め、AMI を調べる。`gh api repos/matsuu/aws-isucon/readme -q .content | base64 -d` の AMI の表から、その問題の行の AMI ID を使う
2. 台数とインスタンスタイプを決める。ユーザーの指定がなければ次にして、確認のときに示す
   - webapp: その問題の本番と同じ台数 (分からなければ 3 台)
   - ベンチマーク: 1 台
   - インスタンスタイプ: `t3.medium`。本番より遅いので、スコアは本番と比べられない
3. ネットワークを決める
   - 既定の VPC の 1 つのサブネットにすべて置く。サーバー間の通信の遅延を本番に近づけるため
   - セキュリティグループは、既存の `default` (同じグループ内の全通信)、`isucon-bench` (ssh)、`isu-common` を使う。無ければ、ssh (22) と同じグループ内の全通信を許可するグループを作る
4. ssh の鍵を決める
   - キーペアは `aws ec2 describe-key-pairs` の既存のもの (`kemizuki-aws` など) を使う
   - user data で、isucon ユーザーに GitHub の公開鍵を登録する。スクリプトは `docs/practice.md` のもので、`USERS` は `gh api user -q .login` のユーザー
5. 起動する。webapp とベンチマークは別々に `aws ec2 run-instances --count <台数>` で起動する
   - Name タグは、webapp を `<問題>-practice`、ベンチマークを `<問題>-bench` にする (例: `isucon14-practice`)。`register-ssh-hosts` skill はこのタグで探す
   - `aws ec2 wait instance-running` で起動を待つ

## 本番: CloudFormation のテンプレートから起動する

運営の案内 (ポータルなど) に従うことを優先する。案内とこの手順が食い違ったら、案内に従い、食い違いをユーザーに伝える。

1. テンプレートのファイルを受け取る。リージョンなどの指定が案内にあれば、それに合わせる
2. `aws cloudformation validate-template --template-body file://<ファイル>` で、Parameters と、必要な Capabilities を調べる
3. 既定値の無いパラメーターの値をユーザーに聞く。GitHub のユーザー名を渡すものなら `gh api user -q .login`
4. stack 名は問題の名前 (`create-contest-repo` skill の命名規則。例: `isucon15`) にする
5. 確認を取ってから作る。Capabilities は validate-template が返したものだけを付ける
   ```bash
   aws cloudformation create-stack --stack-name <stack 名> --template-body file://<ファイル> \
     --parameters ParameterKey=<名前>,ParameterValue=<値> ... --capabilities <Capabilities>
   aws cloudformation wait stack-create-complete --stack-name <stack 名>
   ```
   - 失敗したら `aws cloudformation describe-stack-events --stack-name <stack 名>` の `CREATE_FAILED` の理由をユーザーに伝える。stack を消して作り直すのは、ユーザーの確認を取ってから
6. stack の Outputs と、`aws ec2 describe-instances --filters Name=tag:aws:cloudformation:stack-name,Values=<stack 名>` でインスタンスと IP を確かめる
   - 本番のベンチマーカーは運営の環境にあり、自分のアカウントには起動されない

## 片付け

インスタンスの停止や削除、stack の削除は、ユーザーに言われたときだけ行う。練習用のインスタンスは起動している間ずっと課金されるので、練習を終えたときに、停止か削除するかユーザーに聞く。本番の stack は、競技が終わり運営から削除してよいと案内されるまで消さない。
