// =============================================
// evaluation.js  ─  最終評価画面
// =============================================

// -----------------------------------------------
// スコア計算
// -----------------------------------------------
// 資産・負債・純資産のリストから科目名で金額を探す
function findAmount(list, name) {
  const item = list.find(i => i.name === name);
  return item ? item.amount : 0;
}

function computeFinalEvaluation() {
  // 勘定科目マスターに基づく総額方式の財務諸表データ
  const bsData = buildBalanceSheet();
  const plData = buildIncomeStatement();

  const cash = findAmount(bsData.assets, '現金');
  const ar = findAmount(bsData.assets, '売掛金');
  const inv = findAmount(bsData.assets, '商品');
  const secValue = findAmount(bsData.assets, '売買目的有価証券');
  // 固定資産（純額）＝固定資産区分の合計（減価償却累計額のマイナスも含めて合算済み）
  const faValue = bsData.assets
    .filter(a => a.subCategory === '固定資産')
    .reduce((s, a) => s + a.amount, 0);
  const fraudAssets = findAmount(bsData.assets, '???資産');
  const cryptoAssets = findAmount(bsData.assets, '暗号資産');
  const totalAssets = bsData.totalAssets;

  const ap = findAmount(bsData.liabilities, '買掛金');
  const stl = findAmount(bsData.liabilities, '短期借入金');
  const ltl = findAmount(bsData.liabilities, '長期借入金');
  // 貸倒引当金は勘定科目マスター上「資産のマイナス」科目のため資産の部から拾う
  const allowance = Math.abs(findAmount(bsData.assets, '貸倒引当金'));
  const totalLiab = bsData.totalLiabilities;

  const capitalStock = findAmount(bsData.equity, '資本金');
  const retainedEarnings = findAmount(bsData.equity, '利益剰余金');
  const equity = bsData.totalEquity;
  const totalLiabEquity = bsData.totalLiabilities + bsData.totalEquity;

  // ---- P/L 内訳 ----
  const securityGains = gameState.securityGains || 0;
  const assetGains = gameState.assetGains || 0;

  const salesLine = plData.sales;
  const cogs = plData.cogs;
  const grossProfit = plData.grossProfit;
  const sga = plData.sgaTotal;
  const operatingProfit = plData.operatingProfit;
  const nonOpIncome = plData.otherIncomeTotal;
  const nonOpExpense = plData.otherExpenseTotal;
  const netIncome = plData.netIncome;

  // ---- 安全性（30点） ----
  const currentAssets = cash + ar + inv + secValue;
  const currentLiab = ap + stl;
  const currentRatio = currentLiab > 0 ? (currentAssets / currentLiab * 100) : null;
  let currentRatioScore;
  if (currentLiab <= 0) currentRatioScore = 15;
  else if (currentRatio >= 200) currentRatioScore = 15;
  else if (currentRatio >= 150) currentRatioScore = 12;
  else if (currentRatio >= 100) currentRatioScore = 8;
  else if (currentRatio >= 50) currentRatioScore = 3;
  else currentRatioScore = 0;

  const equityRatio = totalAssets > 0 ? (equity / totalAssets * 100) : 0;
  let equityRatioScore;
  if (equityRatio < 0) equityRatioScore = 0;
  else if (equityRatio >= 50) equityRatioScore = 15;
  else if (equityRatio >= 30) equityRatioScore = 12;
  else if (equityRatio >= 10) equityRatioScore = 7;
  else equityRatioScore = 2;

  const safetyScore = currentRatioScore + equityRatioScore;

  // ---- 収益性（30点） ----
  const profitMargin = gameState.sales > 0 ? (netIncome / gameState.sales * 100) : null;
  let profitMarginScore;
  if (gameState.sales <= 0 || profitMargin < 0) profitMarginScore = 0;
  else if (profitMargin >= 10) profitMarginScore = 15;
  else if (profitMargin >= 5) profitMarginScore = 12;
  else profitMarginScore = 7;

  const roe = equity > 0 ? (netIncome / equity * 100) : null;
  let roeScore;
  if (equity <= 0 || roe < 0) roeScore = 0;
  else if (roe >= 20) roeScore = 15;
  else if (roe >= 10) roeScore = 12;
  else roeScore = 6;

  const profitabilityScore = profitMarginScore + roeScore;

  // ---- 成長性（40点） ----
  const initialEquity = 10000000;
  const netWorthGrowth = (equity - initialEquity) / initialEquity * 100;
  let netWorthGrowthScore;
  if (netWorthGrowth < 0) netWorthGrowthScore = 0;
  else if (netWorthGrowth >= 50) netWorthGrowthScore = 20;
  else if (netWorthGrowth >= 30) netWorthGrowthScore = 16;
  else if (netWorthGrowth >= 10) netWorthGrowthScore = 10;
  else netWorthGrowthScore = 5;

  const monthly = gameState.monthlySales || [];
  const firstHalf = monthly.slice(0, 6).reduce((s, v) => s + (v || 0), 0) / 6;
  const secondHalf = monthly.slice(6, 12).reduce((s, v) => s + (v || 0), 0) / 6;
  const salesGrowthRatio = firstHalf > 0 ? (secondHalf / firstHalf) : null;
  let salesGrowthScore;
  if (firstHalf <= 0) salesGrowthScore = 0;
  else if (salesGrowthRatio >= 1.5) salesGrowthScore = 20;
  else if (salesGrowthRatio >= 1.2) salesGrowthScore = 15;
  else if (salesGrowthRatio >= 1.0) salesGrowthScore = 8;
  else salesGrowthScore = 0;

  const growthScore = netWorthGrowthScore + salesGrowthScore;

  const rawTotal = safetyScore + profitabilityScore + growthScore;

  // ---- ペナルティ ----
  const penalties = [];
  if (gameState.defaultCount >= 2) {
    penalties.push({ label: `不渡り${gameState.defaultCount}回発生`, points: 25 });
  } else if (gameState.defaultCount === 1) {
    penalties.push({ label: '不渡り1回発生', points: 10 });
  }
  if (gameState._fraudGameOverRate > 0) {
    penalties.push({ label: '粉飾決算に手を染めた', points: 40 });
  }
  const totalPenalty = penalties.reduce((s, p) => s + p.points, 0);
  const totalScore = Math.max(0, Math.min(100, rawTotal - totalPenalty));

  // ---- ランク ----
  let rank;
  if (totalScore >= 90) rank = 'S';
  else if (totalScore >= 75) rank = 'A';
  else if (totalScore >= 60) rank = 'B';
  else if (totalScore >= 40) rank = 'C';
  else rank = 'D';

  // ---- 経営スタイル判定 ----
  const style = judgeManagementStyle({
    rank, netIncome, equity, equityRatio, securityGains, assetGains,
    longLoanTotal: ltl, cash
  });

  return {
    bs: {
      assetsList: bsData.assets,
      liabilitiesList: bsData.liabilities,
      equityList: bsData.equity,
      totalAssets, totalLiab, totalEquity: equity, totalLiabEquity,
    },
    pl: {
      salesLine, cogs, grossProfit, sga, sgaItems: plData.sgaItems,
      operatingProfit, nonOpIncome, otherIncomeItems: plData.otherIncomeItems,
      nonOpExpense, otherExpenseItems: plData.otherExpenseItems,
      netIncome
    },
    scores: {
      currentRatio, currentRatioScore,
      equityRatio, equityRatioScore,
      safetyScore,
      profitMargin, profitMarginScore,
      roe, roeScore,
      profitabilityScore,
      netWorthGrowth, netWorthGrowthScore,
      salesGrowthRatio, salesGrowthScore,
      growthScore,
      rawTotal
    },
    penalties,
    totalScore,
    rank,
    style
  };
}

// -----------------------------------------------
// 経営スタイル判定
// -----------------------------------------------
function judgeManagementStyle(d) {
  if (gameState._fraudGameOverRate > 0 || gameState._hadGamblingLoss) {
    return { icon: '🎰', name: 'ギャンブラー型経営者', comment: 'リスクを取りすぎた経営でした。実務では監査法人が飛んできます。' };
  }
  if (gameState.defaultCount >= 2 || d.cash < 1000000) {
    return { icon: '😰', name: '自転車操業型経営者', comment: '常に資金繰りと戦った1年。実務では銀行との関係が命綱になります。' };
  }
  if (d.netIncome > 0 && d.securityGains >= d.netIncome * 0.5) {
    return { icon: '📈', name: 'トレーダー型経営者', comment: '本業より市場で稼いだ経営。CFOより証券マンが向いているかも。' };
  }
  if (d.netIncome > 0 && d.assetGains >= d.netIncome * 0.3) {
    return { icon: '🏠', name: '資産運用型経営者', comment: '資産の売買で利益を出す経営。資産管理会社として優秀です。' };
  }
  if (d.netIncome > 0 && d.longLoanTotal >= d.equity * 0.5) {
    return { icon: '⚔️', name: '攻めの投資家型経営者', comment: 'レバレッジを効かせた積極経営。リスクと背中合わせですが結果を出しました。' };
  }
  if (d.netIncome > 0 && d.equityRatio >= 40) {
    return { icon: '🛡️', name: '堅実経営型経営者', comment: '借金に頼らない堅実な経営。実務でも融資審査はほぼ通ります。' };
  }
  if (d.rank === 'S' && d.equityRatio >= 30) {
    return { icon: '🏆', name: '優良経営型経営者', comment: '教科書通りの優等生経営。実務でもこんな会社は稀です。' };
  }
  if (d.netIncome < 0) {
    return { icon: '💸', name: '再建が必要型経営者', comment: '売上より費用が多い1年でした。固定費の見直しが急務です。' };
  }
  return { icon: '📚', name: '堅実型経営者', comment: '可もなく不可もない1年。次はもう少し攻めてみましょう。' };
}

// -----------------------------------------------
// 描画
// -----------------------------------------------
function showResultScreen() {
  const data = computeFinalEvaluation();
  renderFinalEvaluation(data);
  document.getElementById('final-eval-modal').classList.remove('hidden');
  animateScoreCountUp(data.totalScore);
}

function bsRow(label, value, cls) {
  return `<div class="eval-row"><span class="eval-row-label">${label}</span><span class="eval-row-value ${cls || ''}">${fmt(value)}</span></div>`;
}

// 勘定科目マスターの{name, amount}アイテムを1行にする（マイナス科目は自動で赤色）
function accountRow(item) {
  return bsRow(item.name, item.amount, item.amount < 0 ? 'eval-negative' : '');
}

function renderFinalEvaluation(data) {
  const rankEl = document.getElementById('eval-rank-letter');
  rankEl.textContent = data.rank;
  rankEl.className = 'eval-rank eval-rank-' + data.rank.toLowerCase();

  document.getElementById('eval-score-max-label').textContent = `点 / 100点`;
  document.getElementById('eval-style-badge').textContent = `${data.style.icon} ${data.style.name}`;
  document.getElementById('eval-style-comment').textContent = data.style.comment;

  // B/S（勘定科目マスターに基づく総額方式：貸倒引当金・減価償却累計額も別建てで表示）
  const bs = data.bs;
  document.getElementById('eval-bs-body').innerHTML = `
    <div class="eval-subtitle">資産の部</div>
    ${bs.assetsList.map(accountRow).join('')}
    <div class="eval-row eval-row-total"><span class="eval-row-label">資産合計</span><span class="eval-row-value">${fmt(bs.totalAssets)}</span></div>

    <div class="eval-subtitle" style="margin-top:10px;">負債の部</div>
    ${bs.liabilitiesList.length ? bs.liabilitiesList.map(accountRow).join('') : bsRow('なし', 0)}
    <div class="eval-row eval-row-sub"><span class="eval-row-label">負債合計</span><span class="eval-row-value">${fmt(bs.totalLiab)}</span></div>

    <div class="eval-subtitle" style="margin-top:10px;">純資産の部</div>
    ${bs.equityList.map(accountRow).join('')}
    <div class="eval-row eval-row-total"><span class="eval-row-label">負債純資産合計</span><span class="eval-row-value">${fmt(bs.totalLiabEquity)}</span></div>
  `;

  // P/L（勘定科目マスターに基づく総額方式：販管費・営業外収益・営業外費用を科目ごとに表示）
  const pl = data.pl;
  document.getElementById('eval-pl-body').innerHTML = `
    ${bsRow('売上高', pl.salesLine, 'eval-positive')}
    ${bsRow('売上原価', -pl.cogs, 'eval-negative')}
    <div class="eval-row eval-row-sub"><span class="eval-row-label">売上総利益</span><span class="eval-row-value ${pl.grossProfit >= 0 ? 'eval-positive' : 'eval-negative'}">${fmt(pl.grossProfit)}</span></div>

    <div class="eval-subtitle" style="margin-top:6px;">販管費</div>
    ${pl.sgaItems.length ? pl.sgaItems.map(i => bsRow(i.name, -i.amount, 'eval-negative')).join('') : bsRow('なし', 0)}
    <div class="eval-row eval-row-sub"><span class="eval-row-label">営業利益</span><span class="eval-row-value ${pl.operatingProfit >= 0 ? 'eval-positive' : 'eval-negative'}">${fmt(pl.operatingProfit)}</span></div>

    <div class="eval-subtitle" style="margin-top:10px;">営業外収益</div>
    ${pl.otherIncomeItems.length ? pl.otherIncomeItems.map(i => bsRow(i.name, i.amount, 'eval-positive')).join('') : bsRow('なし', 0)}

    <div class="eval-subtitle" style="margin-top:10px;">営業外費用</div>
    ${pl.otherExpenseItems.length ? pl.otherExpenseItems.map(i => bsRow(i.name, -i.amount, 'eval-negative')).join('') : bsRow('なし', 0)}

    <div class="eval-row eval-row-total"><span class="eval-row-label">当期純利益</span><span class="eval-row-value ${pl.netIncome >= 0 ? 'eval-positive' : 'eval-negative'}">${fmt(pl.netIncome)}</span></div>
  `;

  // スコアバー
  const s = data.scores;
  const safetyComment = s.safetyScore >= 24 ? '支払い能力は十分です。借入も適切な水準です。'
    : s.safetyScore >= 15 ? '支払い能力はまずまずですが、注意が必要な水準です。'
    : '資金繰りに不安が残る結果でした。';
  const profitComment = s.profitabilityScore >= 24 ? '収益性の高い経営でした。効率よく利益を生み出しています。'
    : s.profitabilityScore >= 15 ? '一定の利益は確保できています。'
    : '利益率が低く、収益改善が必要です。';
  const growthComment = s.growthScore >= 32 ? '着実に会社を成長させました。'
    : s.growthScore >= 20 ? '緩やかな成長が見られました。'
    : '成長は限定的でした。次期に向けた投資が必要かもしれません。';

  document.getElementById('eval-score-bars').innerHTML = `
    ${scoreBarHtml('安全性', s.safetyScore, 30,
      `流動比率 ${s.currentRatio === null ? '—' : Math.round(s.currentRatio) + '%'}・自己資本比率 ${Math.round(s.equityRatio)}%`,
      safetyComment)}
    ${scoreBarHtml('収益性', s.profitabilityScore, 30,
      `売上高利益率 ${s.profitMargin === null ? '—' : s.profitMargin.toFixed(1) + '%'}・ROE ${s.roe === null ? '—' : s.roe.toFixed(1) + '%'}`,
      profitComment)}
    ${scoreBarHtml('成長性', s.growthScore, 40,
      `純資産増加率 ${s.netWorthGrowth.toFixed(1)}%・売上成長率 ${s.salesGrowthRatio === null ? '—' : s.salesGrowthRatio.toFixed(2) + '倍'}`,
      growthComment)}
  `;

  // ペナルティ
  const penaltyBox = document.getElementById('eval-penalty-box');
  if (data.penalties.length > 0) {
    penaltyBox.classList.remove('hidden');
    penaltyBox.innerHTML = `
      <div class="eval-penalty-title">⚠️ ペナルティ</div>
      ${data.penalties.map(p => `
        <div class="eval-penalty-row">
          <span>${p.label}</span>
          <span class="eval-negative">-${p.points}点</span>
        </div>`).join('')}
    `;
  } else {
    penaltyBox.classList.add('hidden');
    penaltyBox.innerHTML = '';
  }
}

function scoreBarHtml(label, score, maxScore, detail, comment) {
  const pct = Math.max(0, Math.min(100, Math.round(score / maxScore * 100)));
  return `
    <div class="score-bar-row">
      <div class="score-bar-head">
        <span>${label}</span>
        <span>${score}点 / ${maxScore}点</span>
      </div>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${pct}%"></div></div>
      <div class="score-bar-detail">${detail}</div>
      <div class="score-bar-comment">${comment}</div>
    </div>
  `;
}

// -----------------------------------------------
// スコアカウントアップ演出
// -----------------------------------------------
function animateScoreCountUp(target) {
  const el = document.getElementById('eval-score-num');
  const duration = 1000;
  const start = performance.now();

  function step(now) {
    const progress = Math.min(1, (now - start) / duration);
    const current = Math.round(target * progress);
    el.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      el.textContent = target;
    }
  }
  requestAnimationFrame(step);
}
