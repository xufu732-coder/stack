// =============================================
// eventManager.js  ─  イベントシステム
// =============================================

let eventMaster = [];

async function loadEvents() {
  const res = await fetch('./events.json');
  const data = await res.json();
  eventMaster = data.events;
}

// -----------------------------------------------
// イベント発動チェック（3の倍数ターンに発動）
// -----------------------------------------------
function checkEventTrigger() {
  if (gameState.turn % 3 !== 0) return false;
  return true;
}

// -----------------------------------------------
// イベント抽選（3枚）
// -----------------------------------------------
function drawEventCards() {
  const usedIds = gameState.usedEventIds || [];
  const pool = eventMaster.filter(e => {
    if (e.oneTime && usedIds.includes(e.id)) return false;
    return true;
  });
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

// -----------------------------------------------
// イベントモーダルを表示
// -----------------------------------------------
function showEventModal() {
  const cards = drawEventCards();
  if (cards.length === 0) return;

  gameState._pendingEventCards = cards;

  const grid = document.getElementById('event-cards-grid');
  grid.innerHTML = '';

  cards.forEach(ev => {
    const el = buildEventCard(ev);
    grid.appendChild(el);
  });

  document.getElementById('event-modal').classList.remove('hidden');
}

// -----------------------------------------------
// イベントカードのDOM生成
// -----------------------------------------------
function buildEventCard(ev) {
  const el = document.createElement('div');
  el.className = 'event-card';
  el.dataset.eventId = ev.id;

  const colorMap = {
    unlock: 'blue',
    gamble: 'red',
    plus: 'green',
    minus: 'orange',
    tradeoff: 'purple'
  };
  el.classList.add('event-card-' + (colorMap[ev.type] || 'blue'));

  el.innerHTML = `
    <div class="ev-icon">${ev.icon}</div>
    <div class="ev-name">${ev.name}</div>
    <div class="ev-desc">${ev.description}</div>
    <div class="ev-choices">
      ${ev.choices.map(c => `
        <button class="ev-choice-btn" onclick="selectEventChoice('${ev.id}', '${c.id}')">
          <div class="ev-choice-label">${c.label}</div>
          <div class="ev-choice-desc">${c.description}</div>
        </button>
      `).join('')}
    </div>
  `;
  return el;
}

// -----------------------------------------------
// 選択肢を選んだとき
// -----------------------------------------------
function selectEventChoice(eventId, choiceId) {
  const ev = eventMaster.find(e => e.id === eventId);
  if (!ev) return;
  const choice = ev.choices.find(c => c.id === choiceId);
  if (!choice) return;

  if (ev.oneTime) {
    if (!gameState.usedEventIds) gameState.usedEventIds = [];
    gameState.usedEventIds.push(eventId);
  }

  applyEventEffect(ev, choice);
}

// -----------------------------------------------
// イベント効果の適用
// -----------------------------------------------
function applyEventEffect(ev, choice) {
  const effect = choice.effect;
  const result = { message: effect.message || '' };

  switch (effect.type) {

    case 'none':
      break;

    case 'unlockJournal':
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      // お金を払う
      gameState.cash -= effect.cost;
      gameState.sgaExpenses += effect.cost;

      // 固定資産の売却を解放する
      gameState.fixedAssetSaleUnlocked = true;

      // 仕訳ログに記録（お金が動いたので借方・貸方両方書く）
      addLog(gameState.turn + '月',
        `借）支払手数料 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}`, false);
      addLog(gameState.turn + '月',
        `【解放】固定資産の売却が可能になりました`, false);

      showEventResult(effect.message || '不動産鑑定士との契約が完了しました。固定資産を売却できるようになりました！');
      break;

    case 'cashIn':
      gameState.cash += effect.amount;
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）現金 ${fmt(effect.amount)} ／ 貸）雑収入 ${fmt(effect.amount)}`, false);
      break;

    case 'permanentSalesCapUp':
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.sgaExpenses += effect.cost;
      gameState.permanentSalesCapBonus = (gameState.permanentSalesCapBonus || 0) + effect.value;
      gameState.activeEffects.push({ label: `売上上限+${Math.round(effect.value*100)}%（恒久）`, color: 'green' });
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）業務委託費 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}（売上上限+${Math.round(effect.value*100)}%・恒久）`, false);
      break;

    case 'fraud':
      gameState.sales += effect.salesBonus;
      gameState.fraudAssets = (gameState.fraudAssets || 0) + effect.salesBonus;
      gameState._fraudGameOverRate = Math.max(
        gameState._fraudGameOverRate || 0,
        effect.gameOverRate
      );
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）???資産 ${fmt(effect.salesBonus)} ／ 貸）売上 ${fmt(effect.salesBonus)}`, false);
      break;

    case 'gambling':
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.cryptoAssets = (gameState.cryptoAssets || 0) + effect.cost;
      if (!gameState.pendingGambles) gameState.pendingGambles = [];
      gameState.pendingGambles.push({
        resolveTurn: gameState.turn + effect.delayTurns,
        amount: effect.cost,
        winRate: effect.winRate,
        winMultiplier: effect.winMultiplier,
        name: ev.name
      });
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）暗号資産 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}`, false);
      break;

    case 'badDebt': {
      const arTotal = gameState.receivables.reduce((s, r) => s + r.amount, 0);
      const badDebtAmt = Math.round(arTotal * effect.rate);
      let remaining = badDebtAmt;
      for (const r of gameState.receivables) {
        const reduce = Math.min(r.amount, remaining);
        r.amount -= reduce;
        remaining -= reduce;
        if (remaining <= 0) break;
      }
      gameState.receivables = gameState.receivables.filter(r => r.amount > 0);
      gameState.otherExpenses += badDebtAmt;
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）貸倒損失 ${fmt(badDebtAmt)} ／ 貸）売掛金 ${fmt(badDebtAmt)}`, false);
      break;
    }

    case 'badDebtWithLawyer': {
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.sgaExpenses += effect.cost;
      const arTotal2 = gameState.receivables.reduce((s, r) => s + r.amount, 0);
      const lossRate = 1 - effect.recoveryRate;
      const lossAmt = Math.round(arTotal2 * lossRate);
      let rem2 = lossAmt;
      for (const r of gameState.receivables) {
        const reduce = Math.min(r.amount, rem2);
        r.amount -= reduce;
        rem2 -= reduce;
        if (rem2 <= 0) break;
      }
      gameState.receivables = gameState.receivables.filter(r => r.amount > 0);
      gameState.otherExpenses += lossAmt;
      addLog(gameState.turn + '月',
        `【イベント】${ev.name}：借）顧問料 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}<br>借）貸倒損失 ${fmt(lossAmt)} ／ 貸）売掛金 ${fmt(lossAmt)}`, false);
      break;
    }

    case 'repair':
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.otherExpenses += effect.cost;
      if (!gameState.tempCostRateChanges) gameState.tempCostRateChanges = [];
      gameState.tempCostRateChanges.push({
        amount: effect.costRateUp,
        remainingTurns: effect.duration,
        direction: 'up'
      });
      gameState.costRate += effect.costRateUp;
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）修繕費 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}（原価率一時+${Math.round(effect.costRateUp*100)}%）`, false);
      break;

    case 'temporaryCostRateUp':
      gameState.costRate += effect.costRateUp;
      if (!effect.permanent) {
        if (!gameState.tempCostRateChanges) gameState.tempCostRateChanges = [];
        gameState.tempCostRateChanges.push({
          amount: effect.costRateUp,
          remainingTurns: effect.duration,
          direction: 'up'
        });
        addLog(gameState.turn + '月', `【イベント】${ev.name}：原価率+${Math.round(effect.costRateUp*100)}%（${effect.duration}ターン・仕訳なし）`, false);
      } else {
        addLog(gameState.turn + '月', `【イベント】${ev.name}：原価率+${Math.round(effect.costRateUp*100)}%（恒久・仕訳なし）`, false);
      }
      break;

    case 'newEquipment': {
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;

      // 旧機械装置の帳簿価額がある場合は除却損を計上
      const oldMachines = gameState.fixedAssets.filter(fa => fa.account === '機械装置' && fa.bookValue > 0);
      let disposalLoss = 0;
      for (const fa of oldMachines) {
        disposalLoss += fa.bookValue;
        fa.bookValue = 0;
      }
      if (disposalLoss > 0) {
        gameState.otherExpenses += disposalLoss;
      }

      const years = 5;
      const dep = Math.round(effect.cost / years / 12);
      gameState.fixedAssets.push({
        id: newId(), name: '機械装置（新）', account: '機械装置',
        cost: effect.cost, bookValue: effect.cost, depPerMonth: dep,
        bookMethod: 'indirect', usefulYears: years,
        accumulatedDep: 0, createdTurn: gameState.turn
      });

      gameState._pendingCostDown = (gameState._pendingCostDown || 0) + effect.costRateDown;
      gameState.activeEffects.push({ label: `原価率-${Math.round(effect.costRateDown*100)}%`, color: 'green' });

      let logText = `【イベント】${ev.name}：借）機械装置 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}（原価率-${Math.round(effect.costRateDown*100)}%）`;
      if (disposalLoss > 0) {
        logText += `<br>借）固定資産除却損 ${fmt(disposalLoss)} ／ 貸）機械装置（旧） ${fmt(disposalLoss)}`;
      }
      addLog(gameState.turn + '月', logText, false);
      break;
    }

    case 'subsidy':
      gameState.cash += effect.amount;
      gameState._pendingCostDown = (gameState._pendingCostDown || 0) + effect.costRateDown;
      gameState.activeEffects.push({ label: `原価率-${Math.round(effect.costRateDown*100)}%`, color: 'green' });
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）現金 ${fmt(effect.amount)} ／ 貸）補助金収入 ${fmt(effect.amount)}（原価率-${Math.round(effect.costRateDown*100)}%）`, false);
      break;

    case 'delayedSalesCapUp':
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.sgaExpenses += effect.cost;
      if (!gameState.pendingDelayedEffects) gameState.pendingDelayedEffects = [];
      gameState.pendingDelayedEffects.push({
        resolveTurn: gameState.turn + effect.delayTurns,
        type: 'salesCapUp',
        value: effect.value
      });
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）教育研修費 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}（${effect.delayTurns}ターン後に売上上限+${Math.round(effect.value*100)}%）`, false);
      break;

    case 'bigOrder': {
      if (gameState.cash < effect.cost) {
        showEventResult('現金が不足しています。');
        return;
      }
      gameState.cash -= effect.cost;
      gameState.inventory += effect.cost;
      const cogsAmt = Math.round(effect.sales * gameState.costRate);
      if (gameState.inventory >= cogsAmt) {
        gameState.cash += effect.sales;
        gameState.sales += effect.sales;
        gameState.cogs += cogsAmt;
        gameState.inventory -= cogsAmt;
        addLog(gameState.turn + '月',
          `【イベント】${ev.name}：借）仕入 ${fmt(effect.cost)} ／ 貸）現金 ${fmt(effect.cost)}<br>借）現金 ${fmt(effect.sales)} ／ 貸）商品売上 ${fmt(effect.sales)}`, false);
      }
      break;
    }

    case 'bigOrderFromStock': {
      const cogsFromStock = Math.round(effect.sales * gameState.costRate);
      if (gameState.inventory >= cogsFromStock) {
        gameState.cash += effect.sales;
        gameState.sales += effect.sales;
        gameState.cogs += cogsFromStock;
        gameState.inventory -= cogsFromStock;
        addLog(gameState.turn + '月', `【イベント】${ev.name}：借）現金 ${fmt(effect.sales)} ／ 貸）商品売上 ${fmt(effect.sales)}`, false);
      } else {
        result.message = '在庫が不足していたため、失注しました。';
        addLog(gameState.turn + '月', `【イベント】${ev.name}：在庫不足により失注（仕訳なし）`, false);
      }
      break;
    }

    case 'reduceSalary':
    case 'increaseSalary': {
      const salaryProc = autoProcesses.find(p => p.id === 'auto_salary');
      if (salaryProc) {
        salaryProc.amount += effect.salaryChange;
      }
      if (effect.creditChange) {
        gameState.creditScore = Math.max(0, Math.min(100, gameState.creditScore + effect.creditChange));
      }
      if (effect.salesCapUp) {
        gameState.permanentSalesCapBonus = (gameState.permanentSalesCapBonus || 0) + effect.salesCapUp;
        gameState.activeEffects.push({ label: `売上上限+${Math.round(effect.salesCapUp*100)}%（恒久）`, color: 'green' });
      }
      addLog(gameState.turn + '月', `【イベント】${ev.name}：給料${effect.salaryChange > 0 ? '+' : ''}${fmt(effect.salaryChange)}/月`, false);
      break;
    }

    case 'refinance':
      for (const loan of gameState.longLoans) {
        loan.interestRate = Math.max(0, loan.interestRate + effect.interestRateChange);
      }
      addLog(gameState.turn + '月', `【イベント】${ev.name}：長期借入金利率-1%`, false);
      break;

    case 'additionalLoan':
      gameState.cash += effect.amount;
      gameState.longLoans.push({
        id: newId(),
        principal: effect.amount,
        remaining: effect.amount,
        monthlyPrincipal: Math.round(effect.amount / 120),
        interestRate: 0.03 + effect.interestRatePenalty
      });
      addLog(gameState.turn + '月', `【イベント】${ev.name}：借）現金 ${fmt(effect.amount)} ／ 貸）長期借入金 ${fmt(effect.amount)}`, false);
      break;

    case 'creditUp':
      gameState.creditScore = Math.min(100, gameState.creditScore + effect.value);
      addLog(gameState.turn + '月', `【イベント】${ev.name}：信用スコア+${effect.value}`, false);
      break;
  }

  showEventResult(result.message || effect.message || '対応しました。');
}

// -----------------------------------------------
// 結果表示
// -----------------------------------------------
function showEventResult(message) {
  document.getElementById('event-result-text').textContent = message;
  document.getElementById('event-cards-grid').style.display = 'none';
  document.getElementById('event-result').style.display = 'block';
}

// -----------------------------------------------
// イベントモーダルを閉じる
// -----------------------------------------------
function closeEventModal() {
  document.getElementById('event-modal').classList.add('hidden');
  document.getElementById('event-cards-grid').style.display = 'grid';
  document.getElementById('event-result').style.display = 'none';

  // advanceTurn runs auto-processes, settlements, increments the turn, then shows the auto modal or proceeds
  advanceTurn();
}

// -----------------------------------------------
// ギャンブル・遅延効果の解決（毎ターン呼ぶ）
// -----------------------------------------------
function resolveDelayedEffects() {
  if (gameState.pendingGambles) {
    const remaining = [];
    for (const g of gameState.pendingGambles) {
      if (gameState.turn >= g.resolveTurn) {
        const win = Math.random() < g.winRate;
        if (win) {
          const prize = Math.round(g.amount * g.winMultiplier);
          const gain = prize - g.amount;
          gameState.cash += prize;
          gameState.cryptoAssets = (gameState.cryptoAssets || 0) - g.amount;
          gameState.sales += gain;
          addLog(gameState.turn + '月', `【ギャンブル結果】${g.name}：借）現金 ${fmt(prize)} ／ 貸）暗号資産 ${fmt(g.amount)}・暗号資産売却益 ${fmt(gain)}`, false);
          addNotice('green', '🎉', 'ギャンブル当選！', `${fmt(prize)}が入金されました`);
        } else {
          gameState.cryptoAssets = (gameState.cryptoAssets || 0) - g.amount;
          gameState.otherExpenses += g.amount;
          addLog(gameState.turn + '月', `【ギャンブル結果】${g.name}：借）暗号資産売却損 ${fmt(g.amount)} ／ 貸）暗号資産 ${fmt(g.amount)}`, false);
          addNotice('red', '💸', 'ギャンブル失敗', '投資額が消滅しました');
        }
      } else {
        remaining.push(g);
      }
    }
    gameState.pendingGambles = remaining;
  }

  if (gameState.pendingDelayedEffects) {
    const remaining = [];
    for (const ef of gameState.pendingDelayedEffects) {
      if (gameState.turn >= ef.resolveTurn) {
        if (ef.type === 'salesCapUp') {
          gameState.permanentSalesCapBonus = (gameState.permanentSalesCapBonus || 0) + ef.value;
          gameState.activeEffects.push({ label: `売上上限+${Math.round(ef.value*100)}%（恒久）`, color: 'green' });
          addNotice('green', '📈', '効果発動！', `売上上限が+${Math.round(ef.value*100)}%になりました`);
        }
      } else {
        remaining.push(ef);
      }
    }
    gameState.pendingDelayedEffects = remaining;
  }

  if (gameState.tempCostRateChanges) {
    const remaining = [];
    for (const t of gameState.tempCostRateChanges) {
      t.remainingTurns--;
      if (t.remainingTurns <= 0) {
        gameState.costRate -= t.amount;
        addNotice('blue', '✅', '一時効果終了', '原価率が元に戻りました');
      } else {
        remaining.push(t);
      }
    }
    gameState.tempCostRateChanges = remaining;
  }
}

// -----------------------------------------------
// 粉飾決算のゲームオーバー判定（決算時に呼ぶ）
// -----------------------------------------------
function checkFraudGameOver() {
  if (!gameState._fraudGameOverRate) return false;
  return Math.random() < gameState._fraudGameOverRate;
}
