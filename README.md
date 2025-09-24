# Discord Voice Reader Bot

Discord VCにて特定のテキストチャンネルのメッセージを読み上げるBotです。

## 必要環境
- Docker & Docker Compose
- Discord Bot Token

## セットアップ

1. `.env.example`を`.env`にコピー
```bash
cp .env.example .env
```

2. `.env`ファイルを編集してDiscord Bot Tokenを設定
```bash
nano .env
```

3. Dockerコンテナを起動
```bash
docker compose up -d
```

## 使い方

1. `/setchannel #チャンネル名` - 読み上げるテキストチャンネルを設定
2. VCに参加
3. `/join` - Botが参加して読み上げ開始
4. `/leave` - 読み上げ停止

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| DISCORD_TOKEN | - | Discord Bot Token（必須） |
| SPEAKER_ID | 2 | VOICEVOXの話者ID（2=四国めたん） |
| VOICE_SPEED | 1.0 | 話速（0.5〜2.0） |
| VOICE_PITCH | 0.0 | 音高（-0.15〜0.15） |
| VOICE_INTONATION | 1.0 | 抑揚（0〜2.0） |
| VOICE_VOLUME | 1.0 | 音量（0〜2.0） |
| MAX_MESSAGE_LENGTH | 100 | 最大文字数 |

## コマンド一覧

- `/join` - VCに参加
- `/leave` - VCから退出
- `/setchannel` - 読み上げチャンネル設定
- `/status` - 現在の状態表示
- `/help` - ヘルプ表示

## 利用規約・ライセンス

### VOICEVOX利用について
このBotは[VOICEVOX ENGINE](https://github.com/VOICEVOX/voicevox_engine)のDockerイメージを使用しています。

**クレジット表記**  
音声合成には「VOICEVOX:四国めたん」を使用しています。  
他のキャラクターを使用する場合も「VOICEVOX:キャラクター名」の表記が必要です。

**ライセンス**  
- VOICEVOX ENGINE: LGPL v3
- 各音声ライブラリ: キャラクターごとに異なる（詳細は[公式リポジトリ](https://github.com/VOICEVOX/voicevox_engine)参照）

### このBotのライセンス
Apache License 2.0