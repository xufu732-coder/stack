// =============================================
// main.js  ─  Step2: 仕訳選択 → 帳簿反映
// =============================================

// -----------------------------------------------
// ゲーム状態
// -----------------------------------------------
const gameState = {
  turn: 1,
  maxTurns: 12,

  // 資産
  cash: 10000000,
  receivables: [],   // { id, amount, remaining, createdTurn }
  inventory: 0,
  fixedAssets: [],   // { id, name, account, cost, bookValue, depPerMonth, bookMethod, usefulYears, createdTurn }

  // 負債
  payables: [],      // { id, amount, remaining, createdTurn }
  shortLoans: [],    // { id, principal, remaining, interestRate }
  longLoans: [],     // { id, principal, remaining, monthlyPrincipal, interestRate }
  // prepaidInterest は支払利息に変更したため削除

  // 純資産
  capitalStock: 10000000,
  retainedEarnings: 0,

  // 損益（当期累計）
  sales: 0,
  cogs: 0,
  sgaExpenses: 0,
  otherExpenses: 0,

  // 引当金
  allowanceForDoubtful: 0,

  // 有価証券
  securities: [],  // { id, name, cost, currentPrice, shares, trend, trendRemaining }

  // 固定資産の売却が解放されているか
  fixedAssetSaleUnlocked: false,

  // ゲームパラメータ
  costRate: 0.70,
  creditScore: 100,
  cardSlots: 5,
  defaultCount: 0,
  defaultTurns: [],        // 不渡り発生ターンの記録
  salesCapBonus: 0,        // 広告効果による売上上限ボーナス（翌月リセット）
  pendingSalesCapBonus: 0, // 次のターンに反映する売上上限ボーナス

  // 有効な追加効果
  activeEffects: [],

  // イベント管理
  usedEventIds: [],
  pendingGambles: [],
  pendingDelayedEffects: [],
  tempCostRateChanges: [],
  permanentSalesCapBonus: 0,
  _fraudGameOverRate: 0,
  fraudAssets: 0,   // 粉飾決算による架空資産（???資産）
  cryptoAssets: 0,  // 暗号資産投資の帳簿価額

  // 仕訳ログ
  logs: [
    { month: '開始', text: '現金 <strong>1,000万円</strong> ／ 資本金 <strong>1,000万円</strong>', auto: true }
  ],

  selectedJournalId: null,
  selectedAmount: 0,
};

// -----------------------------------------------
// ユーティリティ
// -----------------------------------------------
function fmt(n) {
  if (n === 0) return '0千円';
  const sign = n < 0 ? '-' : '';
  const thou = Math.round(Math.abs(n) / 1000);
  return sign + thou.toLocaleString() + '千円';
}

function randBetween(min, max, step) {
  const steps = Math.floor((max - min) / step);
  return min + Math.floor(Math.random() * (steps + 1)) * step;
}

function randFrom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

let idCounter = 0;
function newId() { return 'id_' + (++idCounter); }

// -----------------------------------------------
// データ読み込み
// -----------------------------------------------
let journalMaster = [];
let autoProcesses = [];

async function loadData() {
  const res = await fetch('./journals.json');
  const data = await res.json();
  journalMaster = data.journals;
  autoProcesses = data.autoProcesses;
  await loadEvents();
  init();
}

// -----------------------------------------------
// 初期化
// -----------------------------------------------
function init() {
  buildTurnDots();
  dealCards();
  renderAll();
}

// -----------------------------------------------
// ターンドット
// -----------------------------------------------
function buildTurnDots() {
  const wrap = document.getElementById('turn-steps');
  wrap.innerHTML = '';
  for (let i = 1; i <= gameState.maxTurns; i++) {
    const d = document.createElement('div');
    d.className = 'turn-dot' +
      (i < gameState.turn ? ' done' : i === gameState.turn ? ' active' : '');
    d.textContent = i;
    wrap.appendChild(d);
  }
  document.getElementById('turn-badge').textContent = gameState.turn + '月';
}

// -----------------------------------------------
// カード抽選
// -----------------------------------------------
function dealCards() {
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';
  gameState.selectedJournalId = null;
  gameState.selectedAmount = 0;
  document.getElementById('btn-confirm').disabled = true;

  // カードを枠数分抽選
  // ルール：1回の抽選で同一IDは1回まで。枠数がマスター数を超える場合は複数周する。
  const dealt = [];
  let loopPool = [...journalMaster].sort(() => Math.random() - 0.5);

  while (dealt.length < gameState.cardSlots) {
    const usedThisRound = new Set();
    let added = 0;
    for (const j of loopPool) {
      if (dealt.length >= gameState.cardSlots) break;
      if (usedThisRound.has(j.id)) continue;
      dealt.push(j);
      usedThisRound.add(j.id);
      added++;
    }
    if (added === 0) break; // 無限ループ防止
    loopPool = [...journalMaster].sort(() => Math.random() - 0.5);
  }

  for (const j of dealt) {
    grid.appendChild(buildCard(j));
  }
}

// -----------------------------------------------
// カードDOM生成
// -----------------------------------------------
function buildCard(j) {
  const card = document.createElement('div');
  card.className = 'journal-card';
  card.dataset.id = j.id;

  // 金額計算
  const growth = 1 + (j.growthRate * (gameState.turn - 1));
  let min = Math.round(j.amountMin * growth);
  let max = Math.round(j.amountMax * growth);

  // 売上上限ボーナス適用
  if (j.category === '売上') {
    max = Math.round(max * (1 + gameState.salesCapBonus));
  }

  const amount = randBetween(min, max, j.amountStep);
  card.dataset.amount = amount;

  // 耗用年数（固定資産）
  let usefulYears = null;
  if (j.depreciation) {
    usefulYears = randFrom(j.depreciation.usefulYearsOptions);
    card.dataset.usefulYears = usefulYears;
  }

  // 借入パラメータ
  let loanMonths = null, loanRate = null, loanYears = null;
  if (j.loanConfig) {
    const cfg = j.loanConfig;
    // 信用スコアによる利率上乗せ
    const penalty = gameState.creditScore < 70 ? cfg.interestRatePenalty : 0;
    loanRate = +(randBetween(
      Math.round(cfg.interestRateMin * 1000),
      Math.round(cfg.interestRateMax * 1000), 1
    ) / 1000 + penalty).toFixed(4);

    if (cfg.type === 'short') {
      loanMonths = randFrom(cfg.repayMonthsOptions);
      card.dataset.loanMonths = loanMonths;
    } else {
      loanYears = randFrom(cfg.repayYearsOptions);
      card.dataset.loanYears = loanYears;
    }
    card.dataset.loanRate = loanRate;
  }

  // グレーアウト判定
  const disabled = isDisabled(j, amount);
  if (disabled) card.classList.add('disabled');

  // カテゴリ
  const cat = document.createElement('div');
  cat.className = 'card-category';
  cat.textContent = j.category;
  card.appendChild(cat);

  // タイトル
  const title = document.createElement('div');
  title.className = 'card-title';
  title.textContent = j.name;
  card.appendChild(title);

  // 仕訳エントリ（金額を各行に表示）
  const cogsAmt   = Math.round(amount * gameState.costRate);
  // 短期借入の利息・実入金を事前計算
  const loanInterest = (j.id === '008' && loanRate && loanMonths)
    ? Math.round(amount * loanRate * loanMonths / 12) : 0;
  const loanActual   = amount - loanInterest;

  const groups = groupEntries(j.entries);
  for (const group of groups) {
    const isCogs = group[0] && group[0].role === 'cogs';
    const groupAmt = isCogs ? cogsAmt : amount;

    const el = document.createElement('div');
    el.className = 'card-entry';

    const drEntries = group.filter(e => e.side === 'debit');
    const crEntries = group.filter(e => e.side === 'credit');

    let html = '';
    for (const e of drEntries) {
      // 短期借入の借方は役割によって金額を変える
      let lineAmt = groupAmt;
      if (j.id === '008') {
        if (e.account === '現金')    lineAmt = loanActual;
        if (e.account === '支払利息') lineAmt = loanInterest;
      }
      const amtStr = Math.round(lineAmt / 1000).toLocaleString() + '千円';
      html += `<div class="entry-line"><span class="entry-dr">借）${e.account}</span><span class="entry-amt">${amtStr}</span></div>`;
    }
    for (const e of crEntries) {
      const amtStr = Math.round(groupAmt / 1000).toLocaleString() + '千円';
      html += `<div class="entry-line entry-line-cr"><span class="entry-cr">貸）${e.account}</span><span class="entry-amt">${amtStr}</span></div>`;
    }
    el.innerHTML = html;
    card.appendChild(el);
  }

  // 追加情報ラベル
  appendCardLabels(card, j, amount, usefulYears, loanMonths, loanYears, loanRate);

  // グレーアウト理由
  if (disabled) {
    const r = document.createElement('div');
    r.className = 'disabled-reason';
    r.textContent = disabledReason(j);
    card.appendChild(r);
  }

  if (!disabled) {
    card.addEventListener('click', () => selectCard(card));
  }

  return card;
}

function groupEntries(entries) {
  const sales  = entries.filter(e => e.role === 'sales');
  const cogs   = entries.filter(e => e.role === 'cogs');
  const others = entries.filter(e => e.role !== 'sales' && e.role !== 'cogs');
  const groups = [];
  if (sales.length)  groups.push(sales);
  if (cogs.length)   groups.push(cogs);
  if (others.length) groups.push(others);
  return groups.length ? groups : [entries];
}

function appendCardLabels(card, j, amount, usefulYears, loanMonths, loanYears, loanRate) {
  const e = j.effect;
  if (!e && !j.depreciation && !j.loanConfig) return;

  if (e && e.type === 'autoSettle') {
    const months = randBetween(e.monthsMin, e.monthsMax, 1);
    card.dataset.settleMo = months;
    addLabel(card, 'auto', `⏳ ${months}ヶ月後に自動${e.target === 'receivable' ? '回収' : '決済'}`);
  }

  if (e && e.type === 'salesCapUp') {
    const pct = Math.round(amount / 1000000 * e.coefficient * 100);
    addLabel(card, 'effect', `✨ 翌月の売上上限 +${pct}%`);
    card.dataset.salesCapPct = pct;
  }

  if (e && e.type === 'costRateDown') {
    const down = (amount * e.coefficient).toFixed(2);
    addLabel(card, 'effect', `✨ 原価率 −${down}%（翌月から）`);
    card.dataset.costDown = down;
  }

  if (e && e.type === 'addSlot') {
    addLabel(card, 'effect', `✨ 選択肢 +${e.value}枠（翌月から）`);
  }

  if (j.depreciation) {
    const monthly = Math.round(amount / usefulYears / 12);
    addLabel(card, 'auto', `📉 耗用${usefulYears}年 ／ 月次償却 ${fmt(monthly)}`);
    card.dataset.depMonthly = monthly;
  }

  if (j.loanConfig) {
    if (j.loanConfig.type === 'short') {
      const interest = Math.round(amount * loanRate * loanMonths / 12);
      const actual = amount - interest;
      addLabel(card, 'auto', `💴 実入金 ${fmt(actual)}（利息 ${fmt(interest)}）`);
      addLabel(card, 'auto', `⏳ ${loanMonths}ヶ月後に元金自動返済`);
    } else {
      const monthly = Math.round(amount / (loanYears * 12));
      addLabel(card, 'auto', `⏳ 毎月 ${fmt(monthly)} + 利息 自動返済（${loanYears}年）`);
    }
    addLabel(card, 'auto', `利率 ${(loanRate * 100).toFixed(2)}%`);
  }

  if (j.creditScoreEffect) {
    addLabel(card, 'effect', '✨ 信用スコアで調達額が変動');
  }
}

function addLabel(card, type, text) {
  const el = document.createElement('div');
  el.className = type === 'effect' ? 'card-effect' : 'card-auto';
  el.textContent = text;
  card.appendChild(el);
}

// -----------------------------------------------
// グレーアウト判定
// -----------------------------------------------
function isDisabled(j, amount) {
  // 在庫チェック：在庫ゼロ、または売上原価が在庫残高を超える場合
  if (j.requiresStock) {
    const cogsAmt = Math.round(amount * gameState.costRate);
    if (gameState.inventory <= 0 || gameState.inventory < cogsAmt) return true;
  }
  if (j.id === '008' && gameState.defaultCount >= 2 &&
      gameState.defaultTurns.some(t => gameState.turn - t <= 6)) return true;
  if (j.id === '009' && gameState.creditScore < 40) return true;
  // 借入・増資は現金不足でも選べる
  if (['008', '009', '010'].includes(j.id)) return false;
  // 現金支払いが必要な仕訳は現金残高チェック
  const needsCash = j.entries.some(e => e.side === 'credit' && e.account === '現金');
  if (needsCash && gameState.cash < amount) return true;
  return false;
}

function disabledReason(j) {
  if (j.requiresStock) return '🚫 在庫不足のため選択不可';
  if (j.id === '008') return '🚫 信用スコア不足（不渡り2回）';
  if (j.id === '009') return '🚫 信用スコア不足';
  const needsCash = j.entries.some(e => e.side === 'credit' && e.account === '現金');
  if (needsCash) return '🚫 現金不足のため選択不可';
  return '🚫 選択不可';
}

// -----------------------------------------------
// カード選択
// -----------------------------------------------
function selectCard(el) {
  document.querySelectorAll('.journal-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  gameState.selectedJournalId = el.dataset.id;
  gameState.selectedAmount = parseInt(el.dataset.amount);
  gameState._selectedCardEl = el;
  document.getElementById('btn-confirm').disabled = false;
}

// -----------------------------------------------
// 確定ボタン → 帳簿反映
// -----------------------------------------------
function confirmSelection() {
  const id = gameState.selectedJournalId;
  const amount = gameState.selectedAmount;
  const card = gameState._selectedCardEl;
  if (!id || !amount) return;

  const j = journalMaster.find(x => x.id === id);
  if (!j) return;

  // 帳簿に反映
  applyJournal(j, amount, card);

  // イベント発火チェック
  if (checkEventTrigger()) {
    document.getElementById('event-turn-label').textContent = gameState.turn + '月';
    showEventModal();
    return;
  }

  // 次のターンへ
  advanceTurn();
}

// -----------------------------------------------
// 仕訳を帳簿に反映
// -----------------------------------------------
function applyJournal(j, amount, card) {
  const cogsAmount = Math.round(amount * gameState.costRate);

  switch (j.id) {

    // 001: 掛け売上（分記法）
    case '001': {
      if (gameState.inventory < cogsAmount) return;
      const settleMo = parseInt(card.dataset.settleMo) || 2;
      gameState.receivables.push({ id: newId(), amount, remaining: settleMo, createdTurn: gameState.turn });
      gameState.inventory -= cogsAmount;
      gameState.sales += amount;
      gameState.cogs  += cogsAmount;
      addLog(gameState.turn + '月', `掛け売上 <strong>${fmt(amount)}</strong>（${settleMo}ヶ月後回収）`, false);
      break;
    }

    // 002: 現金売上（分記法）
    case '002': {
      if (gameState.inventory < cogsAmount) return;
      gameState.cash      += amount;
      gameState.inventory -= cogsAmount;
      gameState.sales += amount;
      gameState.cogs  += cogsAmount;
      addLog(gameState.turn + '月', `現金売上 <strong>${fmt(amount)}</strong>`, false);
      break;
    }

    // 003: 広告宣伝費
    case '003': {
      if (gameState.cash < amount) { showAlert('現金が不足しています'); return; }
      gameState.cash -= amount;
      gameState.sgaExpenses += amount;
      const pct = parseFloat(card.dataset.salesCapPct) || 0;
      gameState.pendingSalesCapBonus = pct / 100;
      addLog(gameState.turn + '月', `広告宣伝費 <strong>${fmt(amount)}</strong>（翌月売上上限+${pct}%）`, false);
      break;
    }

    // 004: 掛け仕入
    case '004': {
      const settleMo = parseInt(card.dataset.settleMo) || 2;
      gameState.payables.push({ id: newId(), amount, remaining: settleMo, createdTurn: gameState.turn });
      gameState.inventory += amount;
      addLog(gameState.turn + '月', `掛け仕入 <strong>${fmt(amount)}</strong>（${settleMo}ヶ月後支払）`, false);
      break;
    }

    // 005: 機械装置
    case '005': {
      if (gameState.cash < amount) { showAlert('現金が不足しています'); return; }
      gameState.cash -= amount;
      const dep = parseInt(card.dataset.depMonthly) || 0;
      const years = parseInt(card.dataset.usefulYears) || 5;
      const costDown = parseFloat(card.dataset.costDown) || 0;
      gameState.fixedAssets.push({
        id: newId(), name: '機械装置', account: '機械装置',
        cost: amount, bookValue: amount, depPerMonth: dep,
        bookMethod: 'indirect', usefulYears: years,
        accumulatedDep: 0, createdTurn: gameState.turn,
        costDownEffect: costDown / 100,
        slotEffect: 0,
      });
      if (costDown > 0) {
        const fa = gameState.fixedAssets[gameState.fixedAssets.length - 1];
        gameState.activeEffects.push({ label: `原価率-${costDown}%`, color: 'green', costDown, _assetId: fa.id });
        // 翌月反映のため pendingCostDown に積む
        gameState._pendingCostDown = (gameState._pendingCostDown || 0) + costDown / 100;
      }
      addLog(gameState.turn + '月', `機械装置取得 <strong>${fmt(amount)}</strong>（耗用${years}年）`, false);
      break;
    }

    // 006: 建物
    case '006': {
      if (gameState.cash < amount) { showAlert('現金が不足しています'); return; }
      gameState.cash -= amount;
      const dep = parseInt(card.dataset.depMonthly) || 0;
      const years = parseInt(card.dataset.usefulYears) || 30;
      const costDown006 = parseFloat(card.dataset.costDown) || 0;
      gameState.fixedAssets.push({
        id: newId(), name: '建物', account: '建物',
        cost: amount, bookValue: amount, depPerMonth: dep,
        bookMethod: 'indirect', usefulYears: years,
        accumulatedDep: 0, createdTurn: gameState.turn,
        costDownEffect: costDown006 / 100,
        slotEffect: 0,
      });
      if (costDown006 > 0) {
        const fa = gameState.fixedAssets[gameState.fixedAssets.length - 1];
        gameState.activeEffects.push({ label: `原価率-${costDown006}%`, color: 'green', costDown: costDown006, _assetId: fa.id });
        gameState._pendingCostDown = (gameState._pendingCostDown || 0) + costDown006 / 100;
      }
      addLog(gameState.turn + '月', `建物取得 <strong>${fmt(amount)}</strong>（耗用${years}年）`, false);
      break;
    }

    // 007: ソフトウェア
    case '007': {
      if (gameState.cash < amount) { showAlert('現金が不足しています'); return; }
      gameState.cash -= amount;
      const dep = parseInt(card.dataset.depMonthly) || 0;
      const years = parseInt(card.dataset.usefulYears) || 5;
      gameState.fixedAssets.push({
        id: newId(), name: 'ソフトウェア', account: 'ソフトウェア',
        cost: amount, bookValue: amount, depPerMonth: dep,
        bookMethod: 'direct', usefulYears: years,
        accumulatedDep: 0, createdTurn: gameState.turn,
        costDownEffect: 0,
        slotEffect: 1,
      });
      gameState._pendingAddSlot = (gameState._pendingAddSlot || 0) + 1;
      const fa = gameState.fixedAssets[gameState.fixedAssets.length - 1];
      gameState.activeEffects.push({ label: '選択肢+1枠', color: 'blue', _type: 'slot', _assetId: fa.id });
      addLog(gameState.turn + '月', `ソフトウェア取得 <strong>${fmt(amount)}</strong>（耗用${years}年）`, false);
      break;
    }

    // 011: 売買目的有価証券購入
    case '011': {
      if (gameState.cash < amount) { showAlert('現金が不足しています'); return; }
      buySecurities(amount);
      break;
    }

    // 008: 短期借入
    case '008': {
      const rate = parseFloat(card.dataset.loanRate) || 0.025;
      const months = parseInt(card.dataset.loanMonths) || 3;
      const interest = Math.round(amount * rate * months / 12);
      const actualCash = amount - interest;
      gameState.cash += actualCash;
      gameState.otherExpenses += interest;  // 支払利息として即時費用計上
      gameState.shortLoans.push({
        id: newId(), principal: amount, remaining: months,
        interestRate: rate
      });
      addLog(gameState.turn + '月',
        `短期借入 <strong>${fmt(amount)}</strong>（実入金${fmt(actualCash)}、支払利息${fmt(interest)}、${months}ヶ月後返済）`, false);
      break;
    }

    // 009: 長期借入
    case '009': {
      const rate = parseFloat(card.dataset.loanRate) || 0.03;
      const years = parseInt(card.dataset.loanYears) || 10;
      const monthlyPrincipal = Math.round(amount / (years * 12));
      gameState.cash += amount;
      gameState.longLoans.push({
        id: newId(), principal: amount, remaining: amount,
        monthlyPrincipal, interestRate: rate
      });
      addLog(gameState.turn + '月',
        `長期借入 <strong>${fmt(amount)}</strong>（利率${(rate*100).toFixed(2)}%、${years}年返済）`, false);
      break;
    }

    // 010: 増資
    case '010': {
      // 信用スコアによる調達額の変動
      let actualAmount = amount;
      const cfg = j.creditScoreEffect;
      if (gameState.creditScore < 40)       actualAmount = Math.min(amount, cfg.severeMax);
      else if (gameState.creditScore < 70)  actualAmount = Math.min(amount, cfg.penaltyMax);
      else                                  actualAmount = Math.min(amount, cfg.normalMax);
      gameState.cash         += actualAmount;
      gameState.capitalStock += actualAmount;
      addLog(gameState.turn + '月', `増資 <strong>${fmt(actualAmount)}</strong>`, false);
      break;
    }
  }
}

// -----------------------------------------------
// ターン進行
// -----------------------------------------------
function advanceTurn() {
  // 自動処理通知リストを初期化
  gameState._autoNotices = [];

  // 遅延効果の処理（ギャンブル結果・遅延ボーナスなど）
  resolveDelayedEffects();

  // 翌月効果の反映
  applyPendingEffects();

  // 有価証券の時価更新
  updateSecuritiesPrices();

  // 自動処理（給料・家賃）
  runAutoProcesses();

  // 掛け取引・借入のカウントダウン＆自動決済
  processSettlements();

  // 長期借入の月次返済
  processLongLoanRepayment();

  gameState.turn++;

  if (gameState.turn > gameState.maxTurns) {
    runClosing();
    return;
  }

  // 自動処理がある場合はモーダルを表示してから次ターンへ
  if (gameState._autoNotices && gameState._autoNotices.length > 0) {
    showAutoModal(gameState.turn - 1);
  } else {
    proceedToNextTurn();
  }
}

function proceedToNextTurn() {
  buildTurnDots();
  dealCards();
  renderAll();
  hideAlert();
}

// -----------------------------------------------
// 翌月効果の反映
// -----------------------------------------------
function applyPendingEffects() {
  if (gameState._pendingCostDown) {
    gameState.costRate = Math.max(0.1, gameState.costRate - gameState._pendingCostDown);
    gameState._pendingCostDown = 0;
  }
  if (gameState._pendingAddSlot) {
    gameState.cardSlots += gameState._pendingAddSlot;
    gameState._pendingAddSlot = 0;
  }
  // 広告効果（1ターン限り）＋恒久的売上上限ボーナスを合算
  gameState.salesCapBonus = (gameState.pendingSalesCapBonus || 0)
    + (gameState.permanentSalesCapBonus || 0);
  gameState.pendingSalesCapBonus = 0;
}

// -----------------------------------------------
// 毎月の自動固定費
// -----------------------------------------------
function runAutoProcesses() {
  for (const ap of autoProcesses) {
    gameState.cash -= ap.amount;
    gameState.sgaExpenses += ap.amount;
    addLog(gameState.turn + '月', `${ap.name} <strong>${fmt(ap.amount)}</strong>（自動）`, true);
    addNotice('orange', '💴', ap.name, `${fmt(ap.amount)} を現金から支払いました`);
  }
}

// -----------------------------------------------
// 掛け取引・短期借入のカウントダウン＆決済
// -----------------------------------------------
function processSettlements() {
  // 売掛金の回収
  for (const r of gameState.receivables) {
    r.remaining--;
    if (r.remaining <= 0) {
      gameState.cash += r.amount;
      addLog(gameState.turn + '月', `売掛金 <strong>${fmt(r.amount)}</strong> を自動回収`, true);
      addNotice('green', '💰', '売掛金の回収', `${fmt(r.amount)} が現金に入金されました`);
    }
  }
  gameState.receivables = gameState.receivables.filter(r => r.remaining > 0);

  // 買掛金の支払い
  const newPayables = [];
  for (const p of gameState.payables) {
    p.remaining--;
    if (p.remaining <= 0) {
      if (gameState.cash >= p.amount) {
        gameState.cash -= p.amount;
        addLog(gameState.turn + '月', `買掛金 <strong>${fmt(p.amount)}</strong> を自動決済`, true);
        addNotice('blue', '🧾', '買掛金の支払い', `${fmt(p.amount)} を現金から支払いました`);
      } else {
        // 不渡り確定・支払い保留
        triggerDefault(p.amount);
        p.remaining = 1; // 来月再試行
        newPayables.push(p);
        continue;
      }
    } else {
      newPayables.push(p);
    }
  }
  gameState.payables = newPayables;

  // 短期借入の返済
  const newShortLoans = [];
  for (const l of gameState.shortLoans) {
    l.remaining--;
    if (l.remaining <= 0) {
      if (gameState.cash >= l.principal) {
        gameState.cash -= l.principal;
        addLog(gameState.turn + '月', `短期借入金 <strong>${fmt(l.principal)}</strong> を自動返済`, true);
        addNotice('blue', '🏦', '短期借入金の返済', `元金 ${fmt(l.principal)} を返済しました`);
      } else {
        triggerDefault(l.principal);
        l.remaining = 1;
        newShortLoans.push(l);
        continue;
      }
    } else {
      newShortLoans.push(l);
    }
  }
  gameState.shortLoans = newShortLoans;
}

// -----------------------------------------------
// 不渡り処理
// -----------------------------------------------
function triggerDefault(amount) {
  gameState.defaultCount++;
  gameState.defaultTurns.push(gameState.turn);

  // 信用スコアのペナルティ
  const recentDefaults = gameState.defaultTurns.filter(t => gameState.turn - t <= 6).length;
  if (recentDefaults >= 2) {
    gameState.creditScore = Math.max(0, gameState.creditScore - 40);
  } else {
    gameState.creditScore = Math.max(0, gameState.creditScore - 20);
  }

  showAlert(`⚠️ 不渡り発生！${fmt(amount)}の支払いができませんでした。信用スコアが低下しました。`);
  addLog(gameState.turn + '月', `<strong style="color:var(--danger)">不渡り発生</strong> ${fmt(amount)}（支払い保留）`, true);
  addNotice('red', '⚠️', '不渡り発生！', `${fmt(amount)} の支払いができませんでした。信用スコアが低下します。`);
}

// -----------------------------------------------
// 月次減価償却
// -----------------------------------------------
function processDepreciation() {
  for (const fa of gameState.fixedAssets) {
    if (fa.bookValue <= 0) continue;
    // 取得月の翌月から12月末までの月数
    const depMonths = Math.max(0, gameState.maxTurns - fa.createdTurn);
    if (depMonths <= 0) continue;
    const dep = Math.min(fa.depPerMonth * depMonths, fa.bookValue);
    fa.bookValue      -= dep;
    fa.accumulatedDep += dep;
    gameState.otherExpenses += dep;
    addLog('決算',
      `${fa.name} 減価償却費 <strong>${fmt(dep)}</strong>（${depMonths}ヶ月分・帳簿価額 ${fmt(fa.bookValue)}）`, true);
  }
}

// -----------------------------------------------
// 長期借入の月次返済
// -----------------------------------------------
function processLongLoanRepayment() {
  for (const l of gameState.longLoans) {
    if (l.remaining <= 0) continue;

    const interest = Math.round(l.remaining * l.interestRate / 12);
    const principal = Math.min(l.monthlyPrincipal, l.remaining);
    const total = principal + interest;

    if (gameState.cash >= total) {
      gameState.cash -= total;
      l.remaining -= principal;
      gameState.otherExpenses += interest;
      addLog(gameState.turn + '月',
        `長期借入返済 元金<strong>${fmt(principal)}</strong> + 利息${fmt(interest)}`, true);
      addNotice('blue', '🏦', '長期借入金の返済', `元金 ${fmt(principal)} + 利息 ${fmt(interest)} を返済しました`);
    } else {
      // 現金不足は不渡り扱い
      triggerDefault(total);
    }
  }
  gameState.longLoans = gameState.longLoans.filter(l => l.remaining > 0);
}

// processPrepaidInterest は支払利息方式に変更したため削除

// -----------------------------------------------
// 有価証券関連
// -----------------------------------------------
const SECURITY_NAMES = [
  'アルファ工業', 'ベータ商事', 'ガンマ電機',
  'デルタ食品', 'イプシロン建設', 'ゼータ製薬',
  'エータ物流', 'シータ金融'
];

function buySecurities(amount) {
  const name = SECURITY_NAMES[Math.floor(Math.random() * SECURITY_NAMES.length)];
  const shares = Math.round(amount / 1000) * 10; // 株数（表示用）
  const costPerShare = Math.round(amount / shares * 100) / 100;
  // トレンド：1=上昇、-1=下落
  const trend = Math.random() > 0.5 ? 1 : -1;
  const trendRemaining = Math.floor(Math.random() * 3) + 3; // 3〜5ターン
  gameState.securities.push({
    id: newId(),
    name,
    cost: amount,          // 取得原価
    currentPrice: amount,  // 現在の時価
    shares,
    trend,
    trendRemaining,
  });
  gameState.cash -= amount;
  addLog(gameState.turn + '月', `売買目的有価証券購入 <strong>${name}</strong> ${fmt(amount)}`, false);
  addNotice('blue', '📈', '有価証券を購入しました', `${name} ${fmt(amount)}`);
  renderSecurities();
}

// ボタンを押したとき → 確認画面を出すだけ
function sellSecurities(secId) {
  const sec = gameState.securities.find(s => s.id === secId);
  if (!sec) return;

  const gain = sec.currentPrice - sec.cost;
  const isProfit = gain >= 0;

  const body = document.getElementById('sell-confirm-body');
  body.innerHTML = `
    <div class="modal-entry">
      <div class="modal-entry-icon blue">💰</div>
      <div class="modal-entry-text">
        <div><strong>${sec.name}</strong> を売却します</div>
        <div class="sub">売却額：${fmt(sec.currentPrice)}</div>
        <div class="sub">取得原価：${fmt(sec.cost)}</div>
        <div class="sub" style="color:${isProfit ? 'var(--success)' : 'var(--danger)'}; font-weight:700;">
          ${isProfit ? '売却益' : '売却損'}：${isProfit ? '+' : ''}${fmt(gain)}
        </div>
      </div>
    </div>
  `;

  document.getElementById('sell-confirm-header').textContent = '💰 売却確認';
  gameState._pendingSell = { type: 'security', id: secId };
  document.getElementById('sell-confirm-modal').classList.remove('hidden');
}

// 「売却する」を押したとき → 実際に売る
function executeSellSecurity(secId) {
  const idx = gameState.securities.findIndex(s => s.id === secId);
  if (idx === -1) return;
  const sec = gameState.securities[idx];
  const gain = sec.currentPrice - sec.cost;
  gameState.cash += sec.currentPrice;
  if (gain >= 0) {
    gameState.sales += gain;
  } else {
    gameState.otherExpenses += Math.abs(gain);
  }

  // 仕訳エントリHTML生成
  const e = (side, account, amount) => {
    const cls = side === 'dr' ? 'entry-dr' : 'entry-cr';
    const indent = side === 'cr' ? ' entry-line-cr' : '';
    return `<div class="entry-line${indent}"><span class="${cls}">${side === 'dr' ? '借）' : '貸）'}${account}</span><span class="entry-amt">${Math.round(amount / 1000).toLocaleString()}千円</span></div>`;
  };

  let entries = '';
  if (gain > 0) {
    entries += e('dr', '現金', sec.currentPrice);
    entries += e('cr', '売買目的有価証券', sec.cost);
    entries += e('cr', '有価証券売却益', gain);
  } else if (gain < 0) {
    entries += e('dr', '現金', sec.currentPrice);
    entries += e('dr', '有価証券売却損', Math.abs(gain));
    entries += e('cr', '売買目的有価証券', sec.cost);
  } else {
    entries += e('dr', '現金', sec.currentPrice);
    entries += e('cr', '売買目的有価証券', sec.cost);
  }

  const gainLabel = gain > 0 ? `<span style="color:var(--success)">売却益 ${fmt(gain)}</span>`
                  : gain < 0 ? `<span style="color:var(--danger)">売却損 ${fmt(Math.abs(gain))}</span>`
                  : '損益なし';

  addLog(gameState.turn + '月',
    `売買目的有価証券売却 <strong>${sec.name}</strong><br><div class="card-entry" style="margin-top:4px">${entries}</div><div style="font-size:0.75rem;margin-top:2px">${gainLabel}</div>`, false);

  gameState.securities.splice(idx, 1);
  renderAll();
}

function updateSecuritiesPrices() {
  for (const sec of gameState.securities) {
    // トレンドに沿って時価変動
    const minChange = 0.05, maxChange = 0.20;
    const changeRate = minChange + Math.random() * (maxChange - minChange);
    const direction = sec.trend;
    sec.currentPrice = Math.round(sec.currentPrice * (1 + direction * changeRate));
    if (sec.currentPrice < 1000) sec.currentPrice = 1000; // 最低値

    // トレンド残ターン数を減らしてランダムで反転
    sec.trendRemaining--;
    if (sec.trendRemaining <= 0) {
      sec.trend = Math.random() > 0.4 ? -sec.trend : sec.trend; // 60%で反転
      sec.trendRemaining = Math.floor(Math.random() * 3) + 3;
    }
  }
  renderSecurities();
}

function renderSecurities() {
  const panel = document.getElementById('securities-panel');
  const list  = document.getElementById('securities-list');
  if (!panel || !list) return;

  if (gameState.securities.length === 0) {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';
  list.innerHTML = '';

  for (const sec of gameState.securities) {
    const gain = sec.currentPrice - sec.cost;
    const gainPct = (gain / sec.cost * 100).toFixed(1);
    const isUp = gain >= 0;
    const trendIcon = sec.trend === 1 ? '📈' : '📉';

    const el = document.createElement('div');
    el.className = 'sec-item';
    el.innerHTML = `
      <div class="sec-top">
        <span class="sec-name">${trendIcon} ${sec.name}</span>
        <button class="btn-sell" onclick="sellSecurities('${sec.id}')">売却</button>
      </div>
      <div class="sec-prices">
        <span class="sec-label">取得</span><span>${fmt(sec.cost)}</span>
        <span class="sec-label">時価</span><span style="font-weight:700">${fmt(sec.currentPrice)}</span>
        <span class="sec-gain ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${gainPct}%</span>
      </div>`;
    list.appendChild(el);
  }
}

// -----------------------------------------------
// 固定資産の売却
// -----------------------------------------------
function renderFixedAssetList() {
  const panel = document.getElementById('fixed-asset-sale-panel');
  const list  = document.getElementById('fixed-asset-sale-list');
  if (!panel || !list) return;

  if (gameState.fixedAssets.length === 0) {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';
  list.innerHTML = '';

  for (const fa of gameState.fixedAssets) {
    const el = document.createElement('div');
    el.className = 'sec-item';

    const icon = fa.account === 'ソフトウェア' ? '💾'
               : fa.account === '建物'         ? '🏢'
               : '⚙️';

    let effectText = '';
    if (fa.costDownEffect > 0) {
      effectText = `原価率-${(fa.costDownEffect * 100).toFixed(2)}%中`;
    } else if (fa.slotEffect > 0) {
      effectText = `選択肢+${fa.slotEffect}枠中`;
    }

    el.innerHTML = `
      <div class="sec-top">
        <span class="sec-name">${icon} ${fa.name}</span>
        ${gameState.fixedAssetSaleUnlocked
          ? `<button class="btn-sell" onclick="sellFixedAsset('${fa.id}')">売却</button>`
          : ''}
      </div>
      <div class="sec-prices">
        <span class="sec-label">帳簿価額</span>
        <span style="font-weight:700">${fmt(fa.bookValue)}</span>
        ${effectText ? `<span class="sec-gain up">${effectText}</span>` : ''}
      </div>`;
    list.appendChild(el);
  }
}

// ボタンを押したとき → 確認画面を出すだけ
function sellFixedAsset(faId) {
  const fa = gameState.fixedAssets.find(f => f.id === faId);
  if (!fa) return;

  // 売却前の減価償却を仮計算（確認画面に表示するため）
  const depMonths = Math.max(0, gameState.turn - fa.createdTurn);
  const alreadyDepMonths = fa.depPerMonth > 0
    ? Math.round(fa.accumulatedDep / fa.depPerMonth) : 0;
  const remainingMonths = Math.max(0, depMonths - alreadyDepMonths);
  const preSaleDep = fa.depPerMonth > 0
    ? Math.min(fa.depPerMonth * remainingMonths, fa.bookValue) : 0;

  // 減価償却後の帳簿価額（売却時の実際の帳簿価額）
  const bookValueAfterDep = fa.bookValue - preSaleDep;

  // 売却価格（帳簿価額の50〜150%のランダム）
  const minPrice = Math.round(bookValueAfterDep * 0.5);
  const maxPrice = Math.round(bookValueAfterDep * 1.5);
  const step = Math.round(bookValueAfterDep * 0.1) || 10000;
  const salePrice = randBetween(minPrice, maxPrice, step);

  const gain = salePrice - bookValueAfterDep;
  const isProfit = gain >= 0;

  // 消える効果の説明文を作る
  let effectWarning = '';
  if (fa.costDownEffect > 0) {
    effectWarning = `
      <div class="modal-entry" style="margin-top:8px;">
        <div class="modal-entry-icon orange">⚠️</div>
        <div class="modal-entry-text">
          <div><strong>この資産を売ると…</strong></div>
          <div class="sub" style="color:var(--danger);">
            原価率が +${(fa.costDownEffect * 100).toFixed(2)}% 上昇します
          </div>
        </div>
      </div>`;
  } else if (fa.slotEffect > 0) {
    effectWarning = `
      <div class="modal-entry" style="margin-top:8px;">
        <div class="modal-entry-icon orange">⚠️</div>
        <div class="modal-entry-text">
          <div><strong>この資産を売ると…</strong></div>
          <div class="sub" style="color:var(--danger);">
            選択肢の枠が ${fa.slotEffect}枠 減ります
          </div>
        </div>
      </div>`;
  }

  const body = document.getElementById('sell-confirm-body');
  body.innerHTML = `
    <div class="modal-entry">
      <div class="modal-entry-icon blue">🏭</div>
      <div class="modal-entry-text">
        <div><strong>${fa.name}</strong> を売却します</div>
        <div class="sub">売却額（査定額）：${fmt(salePrice)}</div>
        <div class="sub">帳簿価額：${fmt(bookValueAfterDep)}</div>
        ${preSaleDep > 0
          ? `<div class="sub">※売却前に減価償却 ${fmt(preSaleDep)} を計上します</div>`
          : ''}
        <div class="sub" style="color:${isProfit ? 'var(--success)' : 'var(--danger)'}; font-weight:700;">
          ${isProfit ? '売却益' : '売却損'}：${isProfit ? '+' : ''}${fmt(gain)}
        </div>
      </div>
    </div>
    ${effectWarning}
  `;

  document.getElementById('sell-confirm-header').textContent = '🏭 売却確認';
  gameState._pendingSell = { type: 'fixedAsset', id: faId, salePrice };
  document.getElementById('sell-confirm-modal').classList.remove('hidden');
}

// 「売却する」を押したとき → 実際に売る
function executeSellFixedAsset(faId) {
  const idx = gameState.fixedAssets.findIndex(f => f.id === faId);
  if (idx === -1) return;
  const fa = gameState.fixedAssets[idx];

  // 確認画面で計算した売却価格を使う（再計算しない）
  const salePrice = gameState._pendingSell.salePrice;

  // STEP A：売却前に未計上分の減価償却を月割りで計上する
  const depMonths = Math.max(0, gameState.turn - fa.createdTurn);
  const alreadyDepMonths = fa.depPerMonth > 0
    ? Math.round(fa.accumulatedDep / fa.depPerMonth) : 0;
  const remainingMonths = Math.max(0, depMonths - alreadyDepMonths);

  if (remainingMonths > 0 && fa.depPerMonth > 0) {
    const dep = Math.min(fa.depPerMonth * remainingMonths, fa.bookValue);

    fa.bookValue      -= dep;
    fa.accumulatedDep += dep;
    gameState.otherExpenses += dep;

    if (fa.bookMethod === 'indirect') {
      addLog(gameState.turn + '月',
        `借）減価償却費 ${fmt(dep)} ／ 貸）減価償却累計額 ${fmt(dep)}（売却前計上・${remainingMonths}ヶ月分）`, false);
    } else {
      addLog(gameState.turn + '月',
        `借）減価償却費 ${fmt(dep)} ／ 貸）${fa.account} ${fmt(dep)}（売却前計上・${remainingMonths}ヶ月分）`, false);
    }
  }

  // STEP B：売却の仕訳を記録する
  const bookValue = fa.bookValue;
  const gain = salePrice - bookValue;

  gameState.cash += salePrice;

  if (fa.bookMethod === 'indirect') {
    const accDep = fa.accumulatedDep;
    if (gain >= 0) {
      gameState.sales += gain;
      addLog(gameState.turn + '月',
        `借）現金 ${fmt(salePrice)}・減価償却累計額 ${fmt(accDep)} ／` +
        ` 貸）${fa.account} ${fmt(fa.cost)}・固定資産売却益 ${fmt(gain)}`, false);
    } else {
      gameState.otherExpenses += Math.abs(gain);
      addLog(gameState.turn + '月',
        `借）現金 ${fmt(salePrice)}・減価償却累計額 ${fmt(accDep)}・固定資産売却損 ${fmt(Math.abs(gain))} ／` +
        ` 貸）${fa.account} ${fmt(fa.cost)}`, false);
    }
  } else {
    if (gain >= 0) {
      gameState.sales += gain;
      addLog(gameState.turn + '月',
        `借）現金 ${fmt(salePrice)} ／` +
        ` 貸）${fa.account} ${fmt(bookValue)}・固定資産売却益 ${fmt(gain)}`, false);
    } else {
      gameState.otherExpenses += Math.abs(gain);
      addLog(gameState.turn + '月',
        `借）現金 ${fmt(salePrice)}・固定資産売却損 ${fmt(Math.abs(gain))} ／` +
        ` 貸）${fa.account} ${fmt(bookValue)}`, false);
    }
  }

  // STEP C：この資産が持っていた効果を消す
  if (fa.costDownEffect > 0) {
    gameState.costRate = Math.min(0.999, gameState.costRate + fa.costDownEffect);
    addLog(gameState.turn + '月',
      `【効果消滅】原価率が +${(fa.costDownEffect * 100).toFixed(2)}% 戻りました`, false);
    gameState.activeEffects = gameState.activeEffects.filter(e => e._assetId !== fa.id);
  }

  if (fa.slotEffect > 0) {
    gameState.cardSlots = Math.max(5, gameState.cardSlots - fa.slotEffect);
    addLog(gameState.turn + '月',
      `【効果消滅】選択肢の枠が ${fa.slotEffect}枠 減りました`, false);
    gameState.activeEffects = gameState.activeEffects.filter(e => e._assetId !== fa.id);
  }

  // STEP D：資産リストから削除して画面を更新
  gameState.fixedAssets.splice(idx, 1);
  renderAll();
}

// -----------------------------------------------
// 売却確認モーダルの共通処理
// -----------------------------------------------
function closeSellConfirmModal() {
  document.getElementById('sell-confirm-modal').classList.add('hidden');
  gameState._pendingSell = null;
}

function executeSell() {
  const pending = gameState._pendingSell;
  if (!pending) return;

  // 実行関数が gameState._pendingSell（査定額など）を参照するため、
  // 先に売却を実行してからモーダルを閉じる（_pendingSellをnullにする）
  if (pending.type === 'security') {
    executeSellSecurity(pending.id);
  } else if (pending.type === 'fixedAsset') {
    executeSellFixedAsset(pending.id);
  }

  closeSellConfirmModal();
}

// -----------------------------------------------
// 決算整理（12ターン終了後）
// -----------------------------------------------
function runClosing() {
  if (checkFraudGameOver()) {
    alert('【ゲームオーバー】粉飾決算が発覚しました！\n経営者責任を問われ、ゲームオーバーです。');
    return;
  }

  addLog('決算', '決算整理を開始します', true);

  // 減価償却（まとめて計上）
  processDepreciation();

  // 貸倒引当金（売掛金残高×3%）
  const arTotal = gameState.receivables.reduce((s, r) => s + r.amount, 0);
  if (arTotal > 0) {
    const allowance = Math.round(arTotal * 0.03);
    gameState.allowanceForDoubtful = allowance;
    gameState.otherExpenses += allowance;
    addLog('決算', `貸倒引当金繰入 <strong>${fmt(allowance)}</strong>（売掛金×3%）`, true);
  }

  // 有価証券の期末時価評価
  for (const sec of gameState.securities) {
    const diff = sec.currentPrice - sec.cost;
    if (diff > 0) {
      gameState.sales += diff;
      addLog('決算', `${sec.name} 有価証券評価益 <strong>${fmt(diff)}</strong>`, true);
    } else if (diff < 0) {
      gameState.otherExpenses += Math.abs(diff);
      addLog('決算', `${sec.name} 有価証券評価損 <strong>${fmt(Math.abs(diff))}</strong>`, true);
    }
    // 帳簿価額を時価に洗替え
    sec.cost = sec.currentPrice;
  }

  // 利益剰余金の確定
  const netIncome = calcNetIncome();
  gameState.retainedEarnings = netIncome;

  addLog('決算', `当期純利益 <strong>${fmt(netIncome)}</strong>`, true);

  renderAll();
  showResultScreen();
}

// -----------------------------------------------
// 純利益計算
// -----------------------------------------------
function calcNetIncome() {
  return gameState.sales - gameState.cogs - gameState.sgaExpenses - gameState.otherExpenses;
}

// -----------------------------------------------
// 評価画面（暫定）
// -----------------------------------------------
function showResultScreen() {
  const ni = calcNetIncome();
  const totalAssets = calcTotalAssets();
  const equity = gameState.capitalStock + gameState.retainedEarnings;
  const totalLiab = calcTotalLiabilities();
  const currentAssets = gameState.cash
    + gameState.receivables.reduce((s,r) => s + r.amount, 0)
    + gameState.inventory;
  const currentLiab = gameState.payables.reduce((s,p) => s + p.amount, 0)
    + gameState.shortLoans.reduce((s,l) => s + l.principal, 0);

  const currentRatio  = currentLiab > 0 ? (currentAssets / currentLiab * 100).toFixed(1) : '—';
  const equityRatio   = totalAssets > 0  ? (equity / totalAssets * 100).toFixed(1)        : '—';
  const profitMargin  = gameState.sales > 0 ? (ni / gameState.sales * 100).toFixed(1)     : '—';
  const roe           = equity > 0 ? (ni / equity * 100).toFixed(1)                       : '—';

  const msg = `
===== 決算結果 =====
売上：${fmt(gameState.sales)}
当期純利益：${fmt(ni)}

【安全性】
  流動比率：${currentRatio}%
  自己資本比率：${equityRatio}%

【収益性】
  売上高利益率：${profitMargin}%
  ROE：${roe}%

【信用スコア】${gameState.creditScore} / 100
  `;

  alert(msg + '\n（Step7で正式な評価画面を実装します）');
}

function calcTotalAssets() {
  return gameState.cash
    + gameState.receivables.reduce((s,r) => s + r.amount, 0)
    + gameState.inventory
    + gameState.securities.reduce((s,sec) => s + sec.currentPrice, 0)
    + gameState.fixedAssets.reduce((s,a) => s + a.bookValue, 0)
    + (gameState.fraudAssets || 0)
    + (gameState.cryptoAssets || 0);
}

function calcTotalLiabilities() {
  return gameState.payables.reduce((s,p) => s + p.amount, 0)
    + gameState.shortLoans.reduce((s,l) => s + l.principal, 0)
    + gameState.longLoans.reduce((s,l) => s + l.remaining, 0);
}

// -----------------------------------------------
// 画面描画
// -----------------------------------------------
function renderAll() {
  renderHeader();
  renderFinance();
  renderPending();
  renderStatus();
  renderLog();
  renderEffects();
  renderSecurities();
  renderFixedAssetList();
}

function renderHeader() {
  document.getElementById('hdr-cash').textContent = fmt(gameState.cash);
  document.getElementById('hdr-turn').textContent = gameState.turn + '月';
}

function renderFinance() {
  const arTotal  = gameState.receivables.reduce((s,r) => s + r.amount, 0);
  const apTotal  = gameState.payables.reduce((s,p) => s + p.amount, 0);
  const stlTotal = gameState.shortLoans.reduce((s,l) => s + l.principal, 0);
  const ltlTotal = gameState.longLoans.reduce((s,l) => s + l.remaining, 0);
  const faTotal  = gameState.fixedAssets.reduce((s,a) => s + a.bookValue, 0);
  const ni       = calcNetIncome();

  setKpi('fin-cash',  gameState.cash,            'neutral');
  setKpi('fin-ar',    arTotal,                   'neutral');
  setKpi('fin-inv',   gameState.inventory,        'neutral');
  setKpi('fin-fa',    faTotal,                   'neutral');

  const fraudRow = document.getElementById('fin-fraud-row');
  if (fraudRow) {
    if (gameState.fraudAssets > 0) {
      fraudRow.style.display = '';
      setKpi('fin-fraud', gameState.fraudAssets, 'negative');
    } else {
      fraudRow.style.display = 'none';
    }
  }
  const cryptoRow = document.getElementById('fin-crypto-row');
  if (cryptoRow) {
    if (gameState.cryptoAssets > 0) {
      cryptoRow.style.display = '';
      setKpi('fin-crypto', gameState.cryptoAssets, 'neutral');
    } else {
      cryptoRow.style.display = 'none';
    }
  }

  setKpi('fin-ap',    apTotal,                   'neutral');
  setKpi('fin-stl',   stlTotal,                  'neutral');
  setKpi('fin-ltl',   ltlTotal,                  'neutral');
  setKpi('fin-cap',   gameState.capitalStock,    'neutral');
  setKpi('fin-re',    gameState.retainedEarnings, ni >= 0 ? 'positive' : 'negative');
  setKpi('fin-sales', gameState.sales,            'positive');
  setKpi('fin-cogs',  gameState.cogs,             'negative');
  setKpi('fin-sga',   gameState.sgaExpenses,      'negative');
  setKpi('fin-ni',    ni,                         ni >= 0 ? 'positive' : 'negative');
}

function setKpi(id, value, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = fmt(value);
  el.className = 'kpi-value ' + cls;
}

function renderPending() {
  const list = document.getElementById('pending-list');
  list.innerHTML = '';
  const items = [
    ...gameState.receivables.map(r => ({ label: '売掛金（回収待ち）',    amount: r.amount, remaining: r.remaining })),
    ...gameState.payables.map(p   => ({ label: '買掛金（支払待ち）',     amount: p.amount, remaining: p.remaining })),
    ...gameState.shortLoans.map(l => ({ label: '短期借入金（返済待ち）', amount: l.principal, remaining: l.remaining })),
  ];
  if (items.length === 0) {
    list.innerHTML = '<div class="empty-note">未決済はありません</div>';
    return;
  }
  for (const item of items) {
    const el = document.createElement('div');
    el.className = 'pending-item';
    el.innerHTML = `
      <div class="pi-top">
        <span>${item.label}</span>
        <span class="countdown ${item.remaining <= 1 ? 'urgent' : ''}">あと${item.remaining}ヶ月</span>
      </div>
      <div class="pi-bottom">${fmt(item.amount)}</div>`;
    list.appendChild(el);
  }
}

function renderStatus() {
  const badge = document.getElementById('credit-badge');
  badge.textContent = gameState.creditScore + ' / 100';
  badge.className = 'credit-badge ' +
    (gameState.creditScore >= 70 ? 'good' : gameState.creditScore >= 40 ? 'warning' : 'danger');

  const costPct = Math.round(gameState.costRate * 1000) / 10;
  document.getElementById('stat-cost-rate').textContent = costPct.toFixed(1) + '%';
  const barCost = document.getElementById('bar-cost-rate');
  barCost.style.width = costPct + '%';
  barCost.className = 'bar-fill ' + (costPct >= 80 ? 'danger' : costPct >= 60 ? 'warning' : '');

  const totalAssets = calcTotalAssets();
  const equity = gameState.capitalStock + gameState.retainedEarnings;
  const equityRatio = totalAssets > 0 ? Math.round(equity / totalAssets * 100) : 100;
  document.getElementById('stat-equity').textContent = equityRatio + '%';
  const barEq = document.getElementById('bar-equity');
  barEq.style.width = Math.min(equityRatio, 100) + '%';
  barEq.className = 'bar-fill ' + (equityRatio < 20 ? 'danger' : equityRatio < 40 ? 'warning' : '');

  document.getElementById('stat-slots').textContent = gameState.cardSlots + '枠';
}

function renderLog() {
  const list = document.getElementById('log-list');
  list.innerHTML = '';
  for (const log of gameState.logs) {
    const item = document.createElement('div');
    item.className = 'log-item';
    item.innerHTML = `
      <span class="log-month ${log.auto ? 'auto' : ''}">${log.month}</span>
      <span class="log-text">${log.text}</span>`;
    list.appendChild(item);
  }
}

function renderEffects() {
  const wrap = document.getElementById('active-effects');
  wrap.innerHTML = '';
  if (gameState.activeEffects.length === 0) {
    wrap.innerHTML = '<div class="empty-note">効果なし</div>';
    return;
  }
  for (const ef of gameState.activeEffects) {
    const tag = document.createElement('span');
    tag.className = 'effect-tag ' + (ef.color || 'blue');
    tag.textContent = ef.label;
    wrap.appendChild(tag);
  }
}

// -----------------------------------------------
// アラート
// -----------------------------------------------
function showAlert(msg) {
  const el = document.getElementById('alert-banner');
  el.textContent = msg;
  el.classList.add('show');
}
function hideAlert() {
  document.getElementById('alert-banner').classList.remove('show');
}

// -----------------------------------------------
// 自動処理通知
// -----------------------------------------------
function addNotice(color, icon, title, sub) {
  if (!gameState._autoNotices) gameState._autoNotices = [];
  gameState._autoNotices.push({ color, icon, title, sub });
}

function showAutoModal(turn) {
  const notices = gameState._autoNotices || [];
  document.getElementById('modal-month').textContent = turn + '月の自動処理';

  const body = document.getElementById('modal-body');
  body.innerHTML = '';

  if (notices.length === 0) {
    body.innerHTML = '<div style="color:var(--text-sub);font-size:0.85rem;padding:8px 0;">自動処理はありませんでした</div>';
  } else {
    for (const n of notices) {
      const el = document.createElement('div');
      el.className = 'modal-entry';
      el.innerHTML = `
        <div class="modal-entry-icon ${n.color}">${n.icon}</div>
        <div class="modal-entry-text">
          <div><strong>${n.title}</strong></div>
          <div class="sub">${n.sub}</div>
        </div>`;
      body.appendChild(el);
    }
  }

  document.getElementById('auto-modal').classList.remove('hidden');
}

function closeAutoModal() {
  document.getElementById('auto-modal').classList.add('hidden');
  proceedToNextTurn();
}

function addLog(month, text, isAuto) {
  gameState.logs.unshift({ month, text, auto: isAuto });
  if (gameState.logs.length > 50) gameState.logs.pop();
}

// -----------------------------------------------
// 起動
// -----------------------------------------------
loadData();
