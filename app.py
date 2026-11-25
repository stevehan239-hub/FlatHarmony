import streamlit as st

# ==========================================
# 1. 页面配置与 Session State 初始化
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
# 2. 侧边栏：用户切换 (无密码一键切换)
# ==========================================
st.sidebar.title("👥 用户切换")
current_idx = st.session_state.users.index(st.session_state.current_user)
selected_user = st.sidebar.radio("当前活跃用户：", st.session_state.users, index=current_idx)

if selected_user != st.session_state.current_user:
    st.session_state.current_user = selected_user
    st.rerun()

st.title(f"FlatHarmony V1 - 欢迎, {st.session_state.current_user}")
st.divider()

col1, col2 = st.columns([1, 1.2], gap="large")

# ==========================================
# 3. 左侧：录入新小票
# ==========================================
with col1:
    st.header("🧾 录入新小票")
    
    # 逐项录入表单
    with st.form("add_item_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        i_name = c1.text_input("物品名称 (例如：鸡蛋)")
        i_price = c2.number_input("金额 ($)", min_value=0.0, step=0.01, format="%.2f")
        submitted = c3.form_submit_button("➕ 添加")
        
        if submitted and i_name and i_price > 0:
            st.session_state.draft_items.append({
                "id": str(len(st.session_state.draft_items)), 
                "name": i_name, 
                "price": i_price
            })
            st.rerun()

    # 显示已录入的物品
    subtotal = 0.0
    if st.session_state.draft_items:
        st.subheader("当前物品清单")
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

        # 税费与小费设置
        tax = st.number_input("Tax (精确金额 $)", min_value=0.0, step=0.01, format="%.2f")
        
        tip_mode = st.radio("Tip (小费) 录入方式", ["按百分比 (%)", "按具体金额 ($)"], horizontal=True)
        if tip_mode == "按百分比 (%)":
            tip_pct = st.number_input("小费比例 (%)", min_value=0.0, step=1.0, value=0.0)
            final_tip = subtotal * (tip_pct / 100)
            st.caption(f"换算金额: ${final_tip:.2f}")
        else:
            final_tip = st.number_input("小费金额 ($)", min_value=0.0, step=0.01, format="%.2f")

        total = subtotal + tax + final_tip
        st.markdown(f"### Total: **${total:.2f}**")

        # 提交小票
        if st.button("🚀 以当前用户身份提交小票", type="primary", use_container_width=True):
            new_receipt = {
                "id": f"R_{len(st.session_state.receipts)}",
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
# 4. 右侧：待认领 (Pending) 与 结算 (Settlement)
# ==========================================
with col2:
    st.header("⏳ 待认领小票 (Pending)")
    pending_receipts = [r for r in st.session_state.receipts if r['status'] == 'pending']
    
    if not pending_receipts:
        st.info("🎉 暂无需要认领的小票。")
    else:
        for r in pending_receipts:
            with st.container(border=True):
                st.write(f"**{r['payer']}** 支付了 **${r['total']:.2f}**")
                
                # 遍历小票中的物品，当前用户进行勾选
                for item in r['items']:
                    is_claimed = st.session_state.current_user in r['claims'][item['id']]
                    claimed_by_others = [u for u in r['claims'][item['id']] if u != st.session_state.current_user]
                    
                    label = f"{item['name']} (${item['price']:.2f})"
                    if claimed_by_others:
                        label += f" — 已被 {', '.join(claimed_by_others)} 认领"
                        
                    # 复选框状态绑定
                    toggled = st.checkbox(label, value=is_claimed, key=f"claim_{r['id']}_{item['id']}")
                    
                    if toggled and not is_claimed:
                        r['claims'][item['id']].append(st.session_state.current_user)
                    elif not toggled and is_claimed:
                        r['claims'][item['id']].remove(st.session_state.current_user)
                
                if st.button("✅ 所有人已认领，结算此小票", key=f"settle_{r['id']}", use_container_width=True):
                    r['status'] = 'settled'
                    st.rerun()

    st.header("🧮 最终结算结果 (Settlement)")
    settled_receipts = [r for r in st.session_state.receipts if r['status'] == 'settled']
    
    if not settled_receipts:
        st.write("暂无已结算的账单。")
    else:
        # P2P 债务矩阵
        peer_owes = {u: {v: 0.0 for v in st.session_state.users} for u in st.session_state.users}
        
        for r in settled_receipts:
            user_subtotals = {u: 0.0 for u in st.session_state.users}
            
            # 1. 计算每个人的本金份额 (Subtotal share)
            for item in r['items']:
                claimers = r['claims'][item['id']]
                if claimers:
                    split_price = item['price'] / len(claimers)
                    for u in claimers:
                        user_subtotals[u] += split_price
                        
            claimed_subtotal = sum(user_subtotals.values())
            
            # 2. 按本金比例分摊税和小费
            if claimed_subtotal > 0:
                for u in st.session_state.users:
                    if user_subtotals[u] > 0:
                        proportion = user_subtotals[u] / claimed_subtotal
                        user_tax = r['tax'] * proportion
                        user_tip = r['tip'] * proportion
                        user_total = user_subtotals[u] + user_tax + user_tip
                        
                        # 记录欠付款人的钱
                        if u != r['payer']:
                            peer_owes[u][r['payer']] += user_total
                            
        # 显示转账建议
        has_debt = False
        with st.container(border=True):
            for debtor in st.session_state.users:
                for creditor in st.session_state.users:
                    amount = peer_owes[debtor][creditor]
                    if amount > 0.01:
                        has_debt = True
                        st.error(f"💸 **{debtor}** 应付给 **{creditor}**: ${amount:.2f}")
                        
            if not has_debt:
                st.success("目前所有账单已平，互不相欠！")