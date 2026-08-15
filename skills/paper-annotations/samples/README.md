# 樣本卡

故意壞掉的疑問卡，用來確認警告訊息真的會出現、而且看得懂該怎麼修。

```bash
cp <skill>/samples/*.md <paper_root>/notes/cards/
python <scripts>/build_annotated.py <paper_root>
```

三張卡應該各觸發一種不同的原因：

| 卡片 | 預期警告 |
|---|---|
| `9001-broken-quote.md` | 引文在此檔中找不到 |
| `9002-ambiguous-quote.md` | 引文在此檔出現 N 次，不唯一 |
| `9003-wrong-file.md` | anchor.file 不在來源清單中 |

看完刪掉再重建即可：

```bash
rm <paper_root>/notes/cards/900*.md
python <scripts>/build_annotated.py <paper_root>
```

使用前先把 `9001` 與 `9002` 的 `anchor.file` 改成**你那份論文裡實際存在的一個檔案**
（`9003` 刻意保持指向不存在的檔案，那正是它要測的情況）。
