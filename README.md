# コマンド一覧
* __!Result:score-score-score__ ：結果(record)を記録  
* __!Redo__ ：直近に入力したrecordを削除  
* __!List__ ：自分のrecord一覧の出力  
* __!username_1!username_2__ ：username_1とusername_2が登録したrecordのうち、timestampの差の絶対値が6時間以内のrecordを比較し、username1から見た勝敗をwin-draw-loseの順に出力

# 導入方法
* geo_2.pyを適当なフォルダに格納
* 同階層にTOKEN.textを作成し、discordのTOKENを記載
* recordはresults.jsonに格納（ファイルが存在しない場合は自動で作成）
