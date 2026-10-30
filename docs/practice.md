# 練習環境の準備

## インスタンスの作成

[matsuu/aws-isucon](https://github.com/matsuu/aws-isucon) に記載の AMI からインスタンスを起動する。

SSH 鍵を登録する場合は、以下のユーザーデータを設定する。
`USERS` には、鍵を登録する GitHub ユーザー名をスペース区切りで指定する。

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

## セットアップと計測

インスタンスを起動したら、[README のサーバーへの接続](../README.md#サーバーへの接続) から進める。
