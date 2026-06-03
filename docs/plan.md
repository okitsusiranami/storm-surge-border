## Plan: Storm Surge 第1段階計画（人手整形対応）

フォートナイトのデュオ2視点リプレイ動画から、0.1秒粒度でストームサージ境界値を推定する。第1段階は「自動推定の完全精度」を目標にせず、精度不足を前提に人間が後から整形・補正できる運用を中核に据える。2動画は手動オフセットで同期し、最終成果物は推定結果CSV・補正用CSV・境界値グラフPNGとする。

**Steps**
1. Phase 1: 仕様固定（人手整形前提）
2. 入力仕様を固定する（mp4 2本、0.1秒サンプリング、手動オフセット同期）。
3. ROI仕様を固定する（中央下HPバー、中央レティクル周辺、右上サージ表示）。
4. 出力を2系統に分ける。
5. 推定結果CSV: timestamp_sec, duo_damage_diff, surge_gap_value, is_above_border, estimated_border, confidence, source_flags。
6. 補正用CSV: timestamp_sec, field_name, original_value, corrected_value, reason, reviewer。
7. Phase 2: 前処理と同期基盤
8. OpenCVで2動画を読み込み、共通タイムライン（0.1秒）へ再サンプリングする。depends on Phase 1
9. --offset-sec でA/B時刻を手動同期する（自動同期は第2段階以降）。
10. 解像度比率でROIを切り出す実装を行う（特に中央下HPバーを優先）。
11. Phase 3: 特徴抽出（自動推定）
12. 右上ROIからEasyOCRで「境界値との差」を抽出し、以上/以下を判定する。depends on Phase 2
13. 中央下HPバー推移から被ダメ候補イベントを抽出する。
14. 中央レティクル周辺のダメージ数値から与ダメ候補イベントを抽出する。
15. ストーム/サージ由来など自チーム外要因を除外するヒューリスティックを適用する。
16. A/B視点イベントを時刻マージし、duo_damage_diff を更新する。
17. Phase 4: 境界値推定と根拠保持
18. 推定式を適用する。
19. is_above_border=true の場合: estimated_border = duo_damage_diff - surge_gap_value。
20. is_above_border=false の場合: estimated_border = duo_damage_diff + surge_gap_value。
21. 欠損・低信頼フレームは補間せずに根拠付きで残す（source_flags と confidence）。
22. Phase 5: 人手整形ワークフロー
23. 低信頼行を抽出したレビュー対象CSVを自動生成する（例: confidence<threshold、OCR失敗、イベント矛盾）。depends on Phase 4
24. 人間が補正用CSVに corrected_value を記入できるフォーマットを提供する。
25. 補正適用ステップを用意し、推定結果CSVへ再反映して再計算する。
26. 反映後に estimated_border を再生成し、補正履歴を残す（監査可能性）。
27. Phase 6: 可視化と受け入れ
28. matplotlibで境界値グラフPNGを生成する（補正前/補正後を切替または重ね描き）。
29. 受け入れ条件を満たすか確認する。
30. 自動推定のみでも処理が停止しない。
31. 人手補正後にCSV/PNGが再生成できる。
32. 任意時点で「元値・補正値・理由」を追跡できる。

**Relevant files**
- docs/plan.md — 第1段階の正式計画書（今回内容を反映する対象）。
- README.md — 実行方法、補正フロー、出力ファイル仕様を記載。
- docs/development-workflow.md — plan準拠での実装/レビュー運用基準。
- docs/issues.md — 仕様差異や未解決事項の記録先。

**Verification**
1. 単体検証: 境界値計算式（以上/以下）と手動オフセット同期の確認。
2. 単体検証: 中央下HPバーROI切り出しが解像度違いでも成立するか確認。
3. 結合検証: 2動画から推定結果CSV・レビュー対象CSV・PNGが生成されることを確認。
4. 手動検証: 補正用CSVに数行修正を入れ、再適用後に estimated_border と可視化が更新されることを確認。
5. 監査検証: 補正理由・補正者・補正前後値が追跡できることを確認。

**Decisions**
- 第1段階の解析粒度は0.1秒。
- 2動画同期は手動オフセット指定のみ。
- HP参照位置は「画面左」ではなく「画面中央下」に固定。
- 精度不足は許容し、人手整形可能なデータ設計を第1優先にする。
- 第1段階成果物は推定結果CSV、補正用CSV、境界値グラフPNG。

**Further Considerations**
1. 人手補正の負荷が高い場合、次段階で簡易レビューUI（時刻ジャンプ付き）を検討する。
2. ROIの個体差が大きい場合、動画ごとのROIキャリブレーション設定ファイル導入を検討する。
3. OCRの誤読が多い場合、テンプレートマッチング併用で候補を絞る方針を検討する。
