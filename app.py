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
    
    # 【新增】自定义小票名称
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
                "price": i_price
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
            final_tip = subtotal * (tip_pct / 100)
            st.caption(f"Calculated Amount: ${final_tip:.2f}")
        else:
            final_tip = st.number_input("Tip Amount ($)", min_value=0.0, step=0.01, format="%.2f")

        total = subtotal + tax + final_tip
        st.markdown(f"### Total: **${total:.2f}**")

        if st.button("🚀 Submit Receipt as Current User", type="primary", use_container_width=True):
            new_receipt = {
                "id": f"R_{len(st.session_state.receipts)}",
                "receipt_name": receipt_title, # 保存自定义名称
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
# 4. Right Column: Pending, Settled & Export
# ==========================================
# 债务矩阵字典，供后面计算和CSV存储使用
peer_owes = {u: {v: 0.0 for v in st.session_state.users} for u in st.session_state.users}

with col2:
    st.header("⏳ Pending Receipts")
    pending_receipts = [r for r in st.session_state.receipts if r['status'] == 'pending']
    
    if not pending_receipts:
        st.info("🎉 No pending receipts to claim.")
    else:
        for r in pending_receipts:
            with st.container(border=True):
                # UI 展示自定义的 Receipt Name
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
    
    if not settled_receipts:
        st.write("No settled receipts yet.")
    else:
        st.subheader("📜 Settled History")
        for r in settled_receipts:
            with st.container(border=True):
                st.write(f"✅ **DONE** — 🏷️ **{r['receipt_name']}** — **{r['payer']}** paid **${r['total']:.2f}**")
                for item in r['items']:
                    claimers = ", ".join(r['claims'][item['id']]) if r['claims'][item['id']] else "None"
                    st.caption(f"✔️ {item['name']} (${item['price']:.2f}) ➔ Claimed by: {claimers}")
            
            # Debt Calculation Logic
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
                        user_total = user_subtotals[u] + (r['tax'] * proportion) + (r['tip'] * proportion)
                        if u != r['payer']:
                            peer_owes[u][r['payer']] += user_total
                            
        st.subheader("💸 Who Owes Whom")
        has_debt = False
        with st.container(border=True):
            for debtor in st.session_state.users:
                for creditor in st.session_state.users:
                    amount = peer_owes[debtor][creditor]
                    if amount > 0.01:
                        has_debt = True
                        st.error(f"**{debtor}** owes **{creditor}**: ${amount:.2f}")
                        
            if not has_debt:
                st.success("All balances are settled!")

        # 将实时写入本地与手动导出结合
        st.divider()
        st.subheader("💾 Data Persistence")
        st.caption("All actions are automatically saved to local CSV files. You can also download them below.")
        
        # 为了兼容网页端下载，生成字符串流
        receipts_csv = io.StringIO()
        debts_csv = io.StringIO()
        
        # 1. 写入小票明细数据 (内存 & 本地硬盘)
        writer1 = csv.writer(receipts_csv)
        writer1.writerow(["Receipt_ID", "Receipt_Name", "Status", "Payer", "Item_Name", "Price", "Claimed_By", "Tax", "Tip", "Total_Receipt_Amount"])
        for r in st.session_state.receipts:
            for item in r['items']:
                claimers = ", ".join(r['claims'][item['id']]) if r['claims'][item['id']] else "None"
                writer1.writerow([r['id'], r['receipt_name'], r['status'].upper(), r['payer'], item['name'], f"${item['price']:.2f}", claimers, f"${r['tax']:.2f}", f"${r['tip']:.2f}", f"${r['total']:.2f}"])
                
        # 2. 写入负债清算数据 (内存 & 本地硬盘)
        writer2 = csv.writer(debts_csv)
        writer2.writerow(["Debtor", "Creditor", "Amount_Owed"])
        for debtor in st.session_state.users:
            for creditor in st.session_state.users:
                if peer_owes[debtor][creditor] > 0.01:
                    writer2.writerow([debtor, creditor, f"${peer_owes[debtor][creditor]:.2f}"])

        # 生成下载按钮
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.download_button(label="📥 Download Receipts History", data=receipts_csv.getvalue(), file_name="receipts_history.csv", mime="text/csv", use_container_width=True)
        with d_col2:
            st.download_button(label="📥 Download Final Debts", data=debts_csv.getvalue(), file_name="settlement_debts.csv", mime="text/csv", use_container_width=True)


# ==========================================
# 5. 后台实时保存到本地文件 (Real-time Save)
# ==========================================
# 只要 Streamlit 组件状态变化（重新运行脚本），此段逻辑就会执行，把最新状态硬写入本地系统 CSV 中。
try:
    with open("flatharmony_receipts.csv", "w", newline="", encoding="utf-8") as f_receipts:
        writer = csv.writer(f_receipts)
        writer.writerow(["Receipt_ID", "Receipt_Name", "Status", "Payer", "Item_Name", "Price", "Claimed_By", "Tax", "Tip", "Total_Receipt_Amount"])
        for r in st.session_state.receipts:
            for item in r['items']:
                claimers = ", ".join(r['claims'][item['id']]) if r['claims'][item['id']] else "None"
                writer.writerow([r['id'], r['receipt_name'], r['status'].upper(), r['payer'], item['name'], f"${item['price']:.2f}", claimers, f"${r['tax']:.2f}", f"${r['tip']:.2f}", f"${r['total']:.2f}"])
                
    with open("flatharmony_debts.csv", "w", newline="", encoding="utf-8") as f_debts:
        writer = csv.writer(f_debts)
        writer.writerow(["Debtor", "Creditor", "Amount_Owed"])
        for debtor in st.session_state.users:
            for creditor in st.session_state.users:
                if peer_owes[debtor][creditor] > 0.01:
                    writer.writerow([debtor, creditor, f"${peer_owes[debtor][creditor]:.2f}"])
except Exception as e:
    # 忽略只读环境下的报错（如某些云部署环境），不影响主要前端功能
    pass