import streamlit as st

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
    
    # Item entry form
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

    # Display drafted items
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

        # Tax & Tip setup
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

        # Submit receipt
        if st.button("🚀 Submit Receipt as Current User", type="primary", use_container_width=True):
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
# 4. Right Column: Pending Claims & Settlement
# ==========================================
with col2:
    st.header("⏳ Pending Receipts")
    pending_receipts = [r for r in st.session_state.receipts if r['status'] == 'pending']
    
    if not pending_receipts:
        st.info("🎉 No pending receipts to claim.")
    else:
        for r in pending_receipts:
            with st.container(border=True):
                st.write(f"**{r['payer']}** paid **${r['total']:.2f}**")
                
                # Iterate through items for the current user to claim
                for item in r['items']:
                    is_claimed = st.session_state.current_user in r['claims'][item['id']]
                    claimed_by_others = [u for u in r['claims'][item['id']] if u != st.session_state.current_user]
                    
                    label = f"{item['name']} (${item['price']:.2f})"
                    if claimed_by_others:
                        label += f" — Claimed by {', '.join(claimed_by_others)}"
                        
                    # Checkbox for claiming
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
        # P2P debt matrix
        peer_owes = {u: {v: 0.0 for v in st.session_state.users} for u in st.session_state.users}
        
        for r in settled_receipts:
            user_subtotals = {u: 0.0 for u in st.session_state.users}
            
            # 1. Calculate each person's subtotal share
            for item in r['items']:
                claimers = r['claims'][item['id']]
                if claimers:
                    split_price = item['price'] / len(claimers)
                    for u in claimers:
                        user_subtotals[u] += split_price
                        
            claimed_subtotal = sum(user_subtotals.values())
            
            # 2. Distribute tax and tip proportionally
            if claimed_subtotal > 0:
                for u in st.session_state.users:
                    if user_subtotals[u] > 0:
                        proportion = user_subtotals[u] / claimed_subtotal
                        user_tax = r['tax'] * proportion
                        user_tip = r['tip'] * proportion
                        user_total = user_subtotals[u] + user_tax + user_tip
                        
                        # Record debt to the payer
                        if u != r['payer']:
                            peer_owes[u][r['payer']] += user_total
                            
        # Display transfer recommendations
        has_debt = False
        with st.container(border=True):
            for debtor in st.session_state.users:
                for creditor in st.session_state.users:
                    amount = peer_owes[debtor][creditor]
                    if amount > 0.01:
                        has_debt = True
                        st.error(f"💸 **{debtor}** owes **{creditor}**: ${amount:.2f}")
                        
            if not has_debt:
                st.success("All balances are settled!")