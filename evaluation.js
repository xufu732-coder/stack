// =============================================
// evaluation.js  ─  最終評価画面
// =============================================

// -----------------------------------------------
// スコア計算
// -----------------------------------------------
function computeFinalEvaluation() {
  const cash = gameState.cash;
  const ar = gameState.receivables.reduce((s, r) => s + r.amount, 0);
  const inv = gameState.inventory;
  const secValue = gameState.securities.reduce((s, sec) => s + sec.currentPrice, 0);
  const faValue = gameState.fixedAssets.reduce((s, a) => s + a.bookValue, 0);
  const fraudAssets = gameState.fraudAssets || 0;
  const cryptoAssets = gameState.cryptoAssets || 0;
  const totalAssets = calcTotalAssets();

  const ap = gameState.payables.reduce((s, p) => s + p.amount, 0);
  const stl = gameState.shortLoans.reduce((s, l) => s + l.principal, 0);
  const ltl = gameState.longLoans.reduce((s, l) => s + l.remaining, 0);
  const allowance = gameState.allowanceForDoubtful || 0;
  const totalLiab = calcTotalLiabilities() + allowance;

  const capitalStock = gameState.capitalStock;
  const retainedEarnings = gameState.retainedEarnings;
  const equity = capitalStock + retainedEarnings;
  const totalLiabEquity = totalLiab + equity;

  // ---- P/L 内訳 ----
  const cogs = gameState.cogs;
  const sga = gameState.sgaExpenses;
  const securityGains = gameState.securityGains || 0;
  const securityLosses = gameState.securityLosses || 0;
  const assetGains = gameState.assetGains || 0;
  const assetLosses = gameState.assetLosses || 0;
  const interestExpenses = gameState.interestExpenses || 0;
  const depreciationTotal = gameState.depreciationTotal || 0;

  const salesLine = gameState.sales - securityGains - assetGains;
  const grossProfit = salesLine - cogs;
  const operatingProfit = grossProfit - sga;
  const nonOpIncome = securityGains + assetGains;
  const namedNonOpExpense = interestExpenses + depreciationTotal + securityLosses + assetLosses;
  const miscExpense = Math.max(0, gameState.otherExpenses - namedNonOpExpense);
  const nonOpExpense = namedNonOpExpense + miscExpense;
  const netIncome = calcNetIncome();

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
      cash, ar, inv, secValue, faValue, fraudAssets, cryptoAssets, totalAssets,
      ap, stl, ltl, allowance, totalLiab, capitalStock, retainedEarnings, equity, totalLiabEquity
    },
    pl: {
      salesLine, cogs, grossProfit, sga, operatingProfit,
      nonOpIncome, securityGains, assetGains,
      nonOpExpense, interestExpenses, depreciationTotal, securityLosses, assetLosses, miscExpense,
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

function renderFinalEvaluation(data) {
  const rankEl = document.getElementById('eval-rank-letter');
  rankEl.textContent = data.rank;
  rankEl.className = 'eval-rank eval-rank-' + data.rank.toLowerCase();

  document.getElementById('eval-score-max-label').textContent = `点 / 100点`;
  document.getElementById('eval-style-badge').textContent = `${data.style.icon} ${data.style.name}`;
  document.getElementById('eval-style-comment').textContent = data.style.comment;

  // B/S
  const bs = data.bs;
  document.getElementById('eval-bs-body').innerHTML = `
    <div class="eval-subtitle">資産の部</div>
    ${bsRow('現金', bs.cash)}
    ${bsRow('売掛金', bs.ar)}
    ${bsRow('在庫', bs.inv)}
    ${bsRow('有価証券（時価）', bs.secValue)}
    ${bsRow('固定資産（純額）', bs.faValue)}
    ${bs.fraudAssets > 0 ? bsRow('???資産', bs.fraudAssets, 'eval-negative') : ''}
    ${bs.cryptoAssets > 0 ? bsRow('暗号資産', bs.cryptoAssets) : ''}
    <div class="eval-row eval-row-total"><span class="eval-row-label">資産合計</span><span class="eval-row-value">${fmt(bs.totalAssets)}</span></div>

    <div class="eval-subtitle" style="margin-top:10px;">負債の部</div>
    ${bsRow('買掛金', bs.ap)}
    ${bsRow('短期借入金', bs.stl)}
    ${bsRow('長期借入金', bs.ltl)}
    ${bs.allowance > 0 ? bsRow('貸倒引当金', bs.allowance) : ''}

    <div class="eval-subtitle" style="margin-top:10px;">純資産の部</div>
    ${bsRow('資本金', bs.capitalStock)}
    ${bsRow('利益剰余金', bs.retainedEarnings, bs.retainedEarnings >= 0 ? 'eval-positive' : 'eval-negative')}
    <div class="eval-row eval-row-total"><span class="eval-row-label">負債純資産合計</span><span class="eval-row-value">${fmt(bs.totalLiabEquity)}</span></div>
  `;

  // P/L
  const pl = data.pl;
  document.getElementById('eval-pl-body').innerHTML = `
    ${bsRow('売上高', pl.salesLine, 'eval-positive')}
    ${bsRow('売上原価', -pl.cogs, 'eval-negative')}
    <div class="eval-row eval-row-sub"><span class="eval-row-label">売上総利益</span><span class="eval-row-value ${pl.grossProfit >= 0 ? 'eval-positive' : 'eval-negative'}">${fmt(pl.grossProfit)}</span></div>
    ${bsRow('販管費', -pl.sga, 'eval-negative')}
    <div class="eval-row eval-row-sub"><span class="eval-row-label">営業利益</span><span class="eval-row-value ${pl.operatingProfit >= 0 ? 'eval-positive' : 'eval-negative'}">${fmt(pl.operatingProfit)}</span></div>

    <div class="eval-subtitle" style="margin-top:10px;">営業外収益</div>
    ${pl.securityGains > 0 ? bsRow('有価証券売却益', pl.securityGains, 'eval-positive') : ''}
    ${pl.assetGains > 0 ? bsRow('固定資産売却益', pl.assetGains, 'eval-positive') : ''}
    ${pl.nonOpIncome === 0 ? bsRow('なし', 0) : ''}

    <div class="eval-subtitle" style="margin-top:10px;">営業外費用</div>
    ${pl.interestExpenses > 0 ? bsRow('支払利息', -pl.interestExpenses, 'eval-negative') : ''}
    ${pl.depreciationTotal > 0 ? bsRow('減価償却費', -pl.depreciationTotal, 'eval-negative') : ''}
    ${pl.securityLosses > 0 ? bsRow('有価証券売却損', -pl.securityLosses, 'eval-negative') : ''}
    ${pl.assetLosses > 0 ? bsRow('固定資産売却損', -pl.assetLosses, 'eval-negative') : ''}
    ${pl.miscExpense > 0 ? bsRow('その他費用', -pl.miscExpense, 'eval-negative') : ''}

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
