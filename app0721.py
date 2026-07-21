import streamlit as st
import io
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# --- ページ基本設定 ---
st.set_page_config(
    page_title="AI履歴書メーカー (対話サポート付)",
    page_icon="📝",
    layout="wide"
)

# --- フォント準備（ReportLab組み込みの日本語CIDフォントを使用） ---
@st.cache_resource
def setup_font():
    """外部ファイルのダウンロード不要な標準日本語フォントを登録"""
    try:
        font_name = 'HeiseiKakuGo-W5'
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        return font_name
    except Exception as e:
        return 'Helvetica'

FONT_NAME = setup_font()

# --- Gemini チャット応対関数 ---
def get_chat_response(messages_history, field_type: str, api_key: str):
    """ユーザーとの対話を通じて履歴書文章をブラッシュアップする"""
    if not api_key:
        return "⚠️ Gemini APIキーが設定されていません。"
    
    try:
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            f"あなたは親身でプロフェッショナルなキャリアコンサルタントです。"
            f"ユーザーと一緒に「{field_type}」の文章を作り上げます。\n\n"
            f"【対話ルール】\n"
            f"1. 最初ややり取りの途中で、必要に応じてユーザーのエピソードや数字、強みを引き出す質問を1つ程度投げかけてください。\n"
            f"2. 会話の中で文章が固まってきたら、日本の履歴書に適した丁寧な文体（です・ます調、200〜300文字程度）の【提案文章】を提示してください。\n"
            f"3. ユーザーから修正指示（「もっと簡潔に」「○○を強調したい」など）があれば、柔軟に修正案を出してください。\n"
            f"4. 【提案文章】を作成・更新した際は、返答の最後に必ず `---提案文章---` という区切り線の後に本文のみを記述してください。"
        )

        formatted_contents = [system_instruction]
        for msg in messages_history:
            role_label = "ユーザー" if msg["role"] == "user" else "キャリアアドバイザー"
            formatted_contents.append(f"{role_label}: {msg['content']}")
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents="\n\n".join(formatted_contents)
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ エラーが発生しました: {e}"

# --- PDF生成関数 ---
def create_pdf(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    elements = []
    font_name = FONT_NAME
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], fontName=font_name, fontSize=18, leading=22, alignment=1)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Normal'], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor("#1A365D"))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=13)

    # タイトル
    elements.append(Paragraph("履 歴 書", title_style))
    elements.append(Spacer(1, 15))
    
    # 基本情報
    info_data = [
        [Paragraph(f"<b>氏名:</b> {data.get('name', '')}", body_style), Paragraph(f"<b>日付:</b> {data.get('date', '')}", body_style)],
        [Paragraph(f"<b>生年月日:</b> {data.get('birthday', '')}", body_style), Paragraph(f"<b>性別:</b> {data.get('gender', '')}", body_style)],
        [Paragraph(f"<b>住所:</b> {data.get('address', '')}", body_style), Paragraph(f"<b>電話:</b> {data.get('phone', '')}", body_style)],
        [Paragraph(f"<b>Email:</b> {data.get('email', '')}", body_style), ""]
    ]
    info_table = Table(info_data, colWidths=[300, 230])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    
    # 学歴・職歴
    elements.append(Paragraph("<b>【学歴・職歴】</b>", section_style))
    elements.append(Spacer(1, 5))
    history_data = [["年月", "内容"]]
    for item in data.get('history', []):
        history_data.append([item.get('year_month', ''), item.get('content', '')])
    hist_table = Table(history_data, colWidths=[100, 430])
    hist_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), font_name),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(hist_table)
    elements.append(Spacer(1, 15))
    
    # 免許・資格
    elements.append(Paragraph("<b>【免許・資格】</b>", section_style))
    elements.append(Spacer(1, 5))
    cert_data = [["年月", "資格名称"]]
    for item in data.get('certs', []):
        cert_data.append([item.get('year_month', ''), item.get('content', '')])
    cert_table = Table(cert_data, colWidths=[100, 430])
    cert_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), font_name),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(cert_table)
    elements.append(Spacer(1, 15))

    # 自己PR・志望動機
    elements.append(Paragraph("<b>【自己PR・自分の強み】</b>", section_style))
    elements.append(Spacer(1, 3))
    pr_p = Paragraph(data.get('pr', '').replace('\n', '<br/>'), body_style)
    pr_table = Table([[pr_p]], colWidths=[530])
    pr_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('PADDING', (0,0), (-1,-1), 8)]))
    elements.append(pr_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>【志望動機・特記事項】</b>", section_style))
    elements.append(Spacer(1, 3))
    motive_p = Paragraph(data.get('motive', '').replace('\n', '<br/>'), body_style)
    motive_table = Table([[motive_p]], colWidths=[530])
    motive_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('PADDING', (0,0), (-1,-1), 8)]))
    elements.append(motive_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- メインアプリ ---
def main():
    st.title("📝 対話型AIサポート付き 履歴書作成アプリ")
    st.caption("AIアドバイザーと対話（チャット）しながら、あなたに最適な自己PR・志望動機を練り上げます。")

    # APIキー取得
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        with st.sidebar:
            st.subheader("🔑 設定")
            api_key = st.text_input("Gemini API Key", type="password")

    # セッション状態初期化
    if 'history_list' not in st.session_state:
        st.session_state.history_list = [{'year_month': '2020年3月', 'content': '〇〇高等学校 卒業'}]
    if 'cert_list' not in st.session_state:
        st.session_state.cert_list = [{'year_month': '2022年10月', 'content': '普通自動車第一種運転免許 取得'}]
    if 'pr_latest_proposal' not in st.session_state:
        st.session_state.pr_latest_proposal = ""
    if 'motive_latest_proposal' not in st.session_state:
        st.session_state.motive_latest_proposal = ""
        
    # テキストエリア用 key セッションの初期化
    if 'pr_final_area' not in st.session_state:
        st.session_state.pr_final_area = ""
    if 'motive_final_area' not in st.session_state:
        st.session_state.motive_final_area = ""

    # チャット履歴初期化
    if 'pr_messages' not in st.session_state:
        st.session_state.pr_messages = [
            {"role": "assistant", "content": "こんにちは！「自己PR」の作成を担当します。まず、あなたの強みや過去に力を入れた経験（仕事・部活・アルバイトなど）について、箇条書きや短文で教えていただけますか？"}
        ]
    if 'motive_messages' not in st.session_state:
        st.session_state.motive_messages = [
            {"role": "assistant", "content": "こんにちは！「志望動機」の作成をお手伝いします。応募したい企業の業界や職種、なぜその企業に興味を持ったかについて、思いつく理由を教えてください！"}
        ]

    tab1, tab2, tab3, tab4 = st.tabs(["1. 基本情報", "2. 学歴・職歴・資格", "3. AI対話（自己PR・志望動機）", "4. プレビュー＆ダウンロード"])

    with tab1:
        st.subheader("基本情報")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("氏名", "山田 太郎")
            birthday = st.text_input("生年月日", "1998年5月15日")
            gender = st.selectbox("性別", ["男", "女", "回答しない"])
        with col2:
            doc_date = st.text_input("作成日", "2026年7月21日")
            phone = st.text_input("電話番号", "090-1234-5678")
            email = st.text_input("メールアドレス", "taro.yamada@example.com")
        address = st.text_input("住所", "東京都千代田区麹町1-2-3")

    with tab2:
        st.subheader("学歴・職歴")
        edited_history = st.data_editor(
            st.session_state.history_list, num_rows="dynamic", key="history_editor",
            column_config={
                "year_month": st.column_config.TextColumn("年月", width="medium"),
                "content": st.column_config.TextColumn("学歴・職歴内容", width="large")
            }
        )
        st.subheader("免許・資格")
        edited_certs = st.data_editor(
            st.session_state.cert_list, num_rows="dynamic", key="cert_editor",
            column_config={
                "year_month": st.column_config.TextColumn("年月", width="medium"),
                "content": st.column_config.TextColumn("資格名称", width="large")
            }
        )

    with tab3:
        sub_tab1, sub_tab2 = st.tabs(["💬 自己PRの対話作成", "💬 志望動機の対話作成"])

        # --- サブタブ1: 自己PR ---
        with sub_tab1:
            col_chat, col_final = st.columns([1.2, 1.0])

            with col_chat:
                st.markdown("#### AIキャリアコンサルタントとの会話")
                chat_container = st.container(height=400)
                
                for msg in st.session_state.pr_messages:
                    with chat_container.chat_message(msg["role"]):
                        st.write(msg["content"])

                if user_input_pr := st.chat_input("自己PRに関するメモや返答を入力...", key="input_pr"):
                    st.session_state.pr_messages.append({"role": "user", "content": user_input_pr})
                    
                    with st.spinner("AIが思考中..."):
                        bot_response = get_chat_response(st.session_state.pr_messages, "自己PR", api_key)
                        
                        if "---提案文章---" in bot_response:
                            parts = bot_response.split("---提案文章---")
                            display_text = parts[0].strip()
                            proposal = parts[1].strip()
                            st.session_state.pr_latest_proposal = proposal
                        else:
                            display_text = bot_response
                        
                        st.session_state.pr_messages.append({"role": "assistant", "content": display_text})
                    st.rerun()

            with col_final:
                st.markdown("#### 📌 確定・採用文面（履歴書に反映）")
                if st.session_state.pr_latest_proposal:
                    st.success("✨ AIから新しい修正案が届いています！")
                    st.info(st.session_state.pr_latest_proposal)
                    if st.button("⬆️ この提案文章を確定欄に反映する", key="apply_pr_btn"):
                        st.session_state.pr_final_area = st.session_state.pr_latest_proposal
                        st.toast("自己PRに反映しました！")

                pr_text = st.text_area(
                    "履歴書に印字される最終テキスト（直接微調整も可能です）",
                    height=250,
                    key="pr_final_area"
                )

        # --- サブタブ2: 志望動機 ---
        with sub_tab2:
            col_chat_m, col_final_m = st.columns([1.2, 1.0])

            with col_chat_m:
                st.markdown("#### AIキャリアコンサルタントとの会話")
                chat_container_m = st.container(height=400)

                for msg in st.session_state.motive_messages:
                    with chat_container_m.chat_message(msg["role"]):
                        st.write(msg["content"])

                if user_input_motive := st.chat_input("志望動機に関するメモや返答を入力...", key="input_motive"):
                    st.session_state.motive_messages.append({"role": "user", "content": user_input_motive})

                    with st.spinner("AIが思考中..."):
                        bot_response_m = get_chat_response(st.session_state.motive_messages, "志望動機", api_key)

                        if "---提案文章---" in bot_response_m:
                            parts = bot_response_m.split("---提案文章---")
                            display_text_m = parts[0].strip()
                            proposal_m = parts[1].strip()
                            st.session_state.motive_latest_proposal = proposal_m
                        else:
                            display_text_m = bot_response_m

                        st.session_state.motive_messages.append({"role": "assistant", "content": display_text_m})
                    st.rerun()

            with col_final_m:
                st.markdown("#### 📌 確定・採用文面（履歴書に反映）")
                if st.session_state.motive_latest_proposal:
                    st.success("✨ AIから新しい修正案が届いています！")
                    st.info(st.session_state.motive_latest_proposal)
                    if st.button("⬆️ この提案文章を確定欄に反映する", key="apply_motive_btn"):
                        st.session_state.motive_final_area = st.session_state.motive_latest_proposal
                        st.toast("志望動機に反映しました！")

                motive_text = st.text_area(
                    "履歴書に印字される最終テキスト（直接微調整も可能です）",
                    height=250,
                    key="motive_final_area"
                )

    with tab4:
        st.subheader("📄 履歴書プレビュー & PDFダウンロード")
        resume_data = {
            'name': name, 'date': doc_date, 'birthday': birthday, 'gender': gender,
            'address': address, 'phone': phone, 'email': email,
            'history': edited_history, 'certs': edited_certs,
            'pr': st.session_state.get('pr_final_area', ''),
            'motive': st.session_state.get('motive_final_area', '')
        }

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### ■ 自己PR")
            st.info(resume_data['pr'] if resume_data['pr'] else "未入力")
        with col_p2:
            st.markdown("#### ■ 志望動機")
            st.info(resume_data['motive'] if resume_data['motive'] else "未入力")

        st.divider()

        if st.button("📥 PDFを作成・準備する", type="primary"):
            with st.spinner("PDFファイルを生成しています..."):
                pdf_bytes = create_pdf(resume_data)
                st.download_button(
                    label="📄 履歴書PDFをダウンロード",
                    data=pdf_bytes,
                    file_name=f"履歴書_{name.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main()