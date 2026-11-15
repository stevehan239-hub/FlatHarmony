import streamlit as st
import io
import csv
import os

# ==========================================
# 1. Page Config & Session State Initialization
# ==========================================
st.set_page_config(page_title="FlatHarmony V1", page_icon="💸", layout="wide")

if 'users' not in st.session_state:
    st.session_state.users = ["Alice", "Bob", "Charlie"]
if 'current_user' not in st.session_state:
    st.session_state.current_user = "Alice"
if 'draft_items' not in st.session_state:
    st.session_state.draft_items = []
if 'receipts' not in st.session_state:
    st.session_state.receipts = []
if 'settlements' not in st.session_state:
    st.session_state.settlements = []  # 记录已经手动 Check Mark 为 Paid 的还款操作

# ==========================================
# 2. Sidebar: User Switcher
# ==========================================
st.sidebar.title("👥 Switch User")
current_idx = st.session_state.users.index(st.session_state.current_user)
selected_user = st.sidebar.radio("Active User:", st.session_state.users, index=current_idx)

if selected_user != st.session_state.current_user:
    st.session_state.current_user = selected_user
    st.rerun()

st.title(f"FlatHarmony V1 - Welcome, {st.session_state.current_user}")
st.divider()

col1, col2 = st.columns([1, 1.2], gap="large")

# ==========================================
# 3. Left Column: Add New Receipt
# ==========================================
with col1:
    st.header("🧾 Add New Receipt")
    
    receipt_title = st.text_input("Receipt Name / Store (e.g., Costco, Target)", value="My Receipt")
    
    with st.form("add_item_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        i_name = c1.text_input("Item Name (e.g., Eggs)")
        i_price = c2.number_input("Price ($)", min_value=0.0, step=0.01, format="%.2f")
        submitted = c3.form_submit_button("➕ Add")
        
        if submitted and i_name and i_price > 0:
            st.session_state.draft_items.append({
                "id": str(len(st.session_state.draft_items)), 
                "name": i_name, 
                "price": float(i_price)
            })
            st.rerun()

    subtotal = 0.0
    if st.session_state.draft_items:
        st.subheader("Current Items")
        for idx, item in enumerate(st.session_state.draft_items):
            c_name, c_price, c_del = st.columns([3, 2, 1])
            c_name.write(item['name'])
            c_price.write(f"${item['price']:.2f}")
            if c_del.button("🗑️", key=f"del_{idx}"):
                st.session_state.draft_items.pop(idx)
                st.rerun()
                
        subtotal = sum(item['price'] for item in st.session_state.draft_items)
        st.write(f"**Subtotal: ${subtotal:.2f}**")
        st.divider()

        tax = st.number_input("Tax (Exact Amount $)", min_value=0.0, step=0.01, format="%.2f")
        
        tip_mode = st.radio("Tip Entry Mode", ["By Percentage (%)", "By Amount ($)"], horizontal=True)
        if tip_mode == "By Percentage (%)":
            tip_pct = st.number_input("Tip Percentage (%)", min_value=0.0, step=1.0, value=0.0)
            # Fix: 确保浮点数计算逻辑，精确按照 Subtotal 计算小费总额
            final_tip = float(subtotal) * (float(tip_pct) / 100.0)
            st.caption(f"Calculated Tip Amount: ${final_tip:.2f}")
        else:
            final_tip = st.number_input("Tip Amount ($)", min_value=0.0, step=0.01, format="%.2f")

        total = subtotal + tax + final_tip
        st.markdown(f"### Total: **${total:.2f}**")

        if st.button("🚀 Submit Receipt as Current User", type="primary", use_container_width=True):
            new_receipt = {
                "id": f"R_{len(st.session_state.receipts)}",
                "receipt_name": receipt_title,
                "payer": st.session_state.current_user,
                "items": st.session_state.draft_items.copy(),
                "subtotal": subtotal,
                "tax": tax,
                "tip": final_tip,
                "total": total,
                "claims": {item['id']: [] for item in st.session_state.draft_items},
                "status": "pending"
            }
            st.session_state.receipts.append(new_receipt)
            st.session_state.draft_items = []
            st.rerun()

# ==========================================
# 4. Right Column: Pending, Settled & Debts
# ==========================================

# 初始化债务矩阵
raw_owes = {u: {v: 0.0 for v in st.session_state.users} for u in st.session_state.users}
net_owes = {u: {v: 0.0 for v in st.session_state.users} for u in st.session_state.users}

with col2:
    st.header("⏳ Pending Receipts")
    pending_receipts = [r for r in st.session_state.receipts if r['status'] == 'pending']
    
    if not pending_receipts:
        st.info("🎉 No pending receipts to claim.")
    else:
        for r in pending_receipts:
            with st.container(border=True):
                st.write(f"🏷️ **{r['receipt_name']}** — **{r['payer']}** paid **${r['total']:.2f}**")
                
                for item in r['items']:
                    is_claimed = st.session_state.current_user in r['claims'][item['id']]
                    claimed_by_others = [u for u in r['claims'][item['id']] if u != st.session_state.current_user]
                    
                    label = f"{item['name']} (${item['price']:.2f})"
                    if claimed_by_others:
                        label += f" — Claimed by {', '.join(claimed_by_others)}"
                        
                    toggled = st.checkbox(label, value=is_claimed, key=f"claim_{r['id']}_{item['id']}")
                    
                    if toggled and not is_claimed:
                        r['claims'][item['id']].append(st.session_state.current_user)
                    elif not toggled and is_claimed:
                        r['claims'][item['id']].remove(st.session_state.current_user)
                
                if st.button("✅ All Claimed, Settle Receipt", key=f"settle_{r['id']}", use_container_width=True):
                    r['status'] = 'settled'
                    st.rerun()

    st.header("🧮 Settlement Results")
    settled_receipts = [r for r in st.session_state.receipts if r['status'] == 'settled']
    
    # 计算原始债务 (基于所有 settled 小票的按比例分摊)
    for r in settled_receipts:
        user_subtotals = {u: 0.0 for u in st.session_state.users}
        for item in r['items']:
            claimers = r['claims'][item['id']]
            if claimers:
                split_price = item['price'] / len(claimers)
                for u in claimers:
                    user_subtotals[u] += split_price
                    
        claimed_subtotal = sum(user_subtotals.values())
        if claimed_subtotal > 0:
            for u in st.session_state.users:
                if user_subtotals[u] > 0:
                    proportion = user_subtotals[u] / claimed_subtotal
                    # 按照各人认领的金额比例，精确分摊 Tax 和 Tip
                    user_total = user_subtotals[u] + (r['tax'] * proportion) + (r['tip'] * proportion)
                    if u != r['payer']:
                        raw_owes[u][r['payer']] += user_total

    # 计算抵消 (手动标记已付的记录将从总欠款中减去)
    for u in st.session_state.users:
        for v in st.session_state.users:
            if u != v:
                total_owed = raw_owes[u][v]
                total_paid = sum(s['amount'] for s in st.session_state.settlements if s['debtor'] == u and s['creditor'] == v)
                
                diff = total_owed - total_paid
                # 相互抵消 A欠B 和 B欠A 的债务，求净值
                if diff > 0.001:
                    net_owes[u][v] = diff

    # 简化：抵消双向债务 (如果A欠B 10，B欠A 5，简化为A欠B 5)
    for u in st.session_state.users:
        for v in st.session_state.users:
            if net_owes[u][v] > 0 and net_owes[v][u] > 0:
                if net_owes[u][v] >= net_owes[v][u]:
                    net_owes[u][v] -= net_owes[v][u]
                    net_owes[v][u] = 0
                else:
                    net_owes[v][u] -= net_owes[u][v]
                    net_owes[u][v] = 0

    # ---------------- 个人账户债务展示区 ----------------
    st.subheader("💳 Personal Accounts (Who Owes Whom)")
    
    # 为每个人创建独立的分类面板
    for user in st.session_state.users:
        with st.expander(f"👤 {user}'s Account", expanded=(user == st.session_state.current_user)):
            st.markdown(f"**Ledger for {user}:**")
            has_record = False
            
            # 1. 欠别人的钱 (Payables)
            for creditor in st.session_state.users:
                amount = net_owes[user][creditor]
                if amount > 0.01:
                    has_record = True
                    # 提供 Checkbox 一键标记已付
                    if st.checkbox(f"🔴 You owe {creditor}: **${amount:.2f}** (Check to mark as Paid)", key=f"pay_{user}_{creditor}_{amount}"):
                        # 当复选框被勾选，记录已付，重载页面
                        st.session_state.settlements.append({
                            "debtor": user,
                            "creditor": creditor,
                            "amount": amount,
                            "status": "PAID"
                        })
                        st.rerun()
            
            # 2. 别人欠你的钱 (Receivables)
            for debtor in st.session_state.users:
                amount = net_owes[debtor][user]
                if amount > 0.01:
                    has_record = True
                    st.write(f"🟢 **{debtor}** owes you: **${amount:.2f}**")
                    
            if not has_record:
                st.write("All clear! No debts or receivables.")

    # ---------------- CSV 实时写入与导出逻辑 ----------------
    st.divider()
    st.subheader("💾 Data & History")
    
    receipts_csv = io.StringIO()
    debts_csv = io.StringIO()
    
    # 生成 CSV: Receipts
    writer1 = csv.writer(receipts_csv)
    writer1.writerow(["Receipt_ID", "Receipt_Name", "Status", "Payer", "Item_Name", "Price", "Claimed_By", "Tax", "Tip", "Total_Receipt_Amount"])
    for r in st.session_state.receipts:
        for item in r['items']:
            claimers = ", ".join(r['claims'][item['id']]) if r['claims'][item['id']] else "None"
            writer1.writerow([r['id'], r['receipt_name'], r['status'].upper(), r['payer'], item['name'], f"${item['price']:.2f}", claimers, f"${r['tax']:.2f}", f"${r['tip']:.2f}", f"${r['total']:.2f}"])
            
    # 生成 CSV: Debts 包含 Pending 和 Paid 状态
    writer2 = csv.writer(debts_csv)
    writer2.writerow(["Debtor", "Creditor", "Amount", "Status"])
    # 写入尚未付清的 Pending 债务
    for debtor in st.session_state.users:
        for creditor in st.session_state.users:
            if net_owes[debtor][creditor] > 0.01:
                writer2.writerow([debtor, creditor, f"${net_owes[debtor][creditor]:.2f}", "PENDING"])
    # 写入已经打勾标记 Paid 的债务记录
    for s in st.session_state.settlements:
        writer2.writerow([s['debtor'], s['creditor'], f"${s['amount']:.2f}", "PAID"])

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(label="📥 Export Receipts History", data=receipts_csv.getvalue(), file_name="receipts_history.csv", mime="text/csv", use_container_width=True)
    with d_col2:
        st.download_button(label="📥 Export Settlement Ledger", data=debts_csv.getvalue(), file_name="settlement_debts.csv", mime="text/csv", use_container_width=True)

# ==========================================
# 5. 后台实时保存到本地文件 (Real-time Save)
# ==========================================
try:
    with open("flatharmony_receipts.csv", "w", newline="", encoding="utf-8") as f_receipts:
        f_receipts.write(receipts_csv.getvalue())
                
    with open("flatharmony_debts.csv", "w", newline="", encoding="utf-8") as f_debts:
        f_debts.write(debts_csv.getvalue())
except Exception as e:
    pass