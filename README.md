# テスト攻略ラボ

テスト勉強の進め方や、問題の解き方、本番での時間の使い方を学べるアプリです。4つの攻略レッスンを読み、学習済みにすると進捗が保存されます。最後の実践クイズで、学んだコツを確認できます。

学習進捗はユーザーのホームディレクトリに `.test_strategy_learning.json` として保存されます。

答え合わせで間違えた写真問題は「苦手問題ノート」に自動で記録され、問題・模範解答・解き方と間違えた回数を確認できます。理解できた問題は「克服した」でノートから外せます。ノートはユーザーのホームディレクトリに `.test_strategy_weak_problems.json` として保存されます。

過去問の写真はローカルのTesseract OCRで読み取ります。読み取り後に模範解答と解き方の解説を登録すると、自分の解答を答え合わせした後に模範解答と解説が表示されます。画像は保存・外部送信されません。日本語OCRを使うには、先にTesseract本体と言語データをインストールしてください。

Ubuntu / Debian:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

## 起動方法

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

起動するとブラウザでアプリが開きます。
