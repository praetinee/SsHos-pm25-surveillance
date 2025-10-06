import streamlit as st
import streamlit.components.v1 as components

# ตั้งค่าหน้าเว็บให้แสดงผลเต็มความกว้าง
st.set_page_config(layout="wide")

# --- ส่วนหัวเรื่อง (Header) ---
st.markdown("""
    <style>
        /* ซ่อน Header และ Footer ของ Streamlit */
        header, footer {
            visibility: hidden;
        }
        /* จัดสไตล์เหมือนต้นฉบับ */
        .title-container {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .pm-indicator {
            background-color: #3b82f6;
            color: white;
            padding: 0.75rem;
            border-radius: 9999px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }
        .pm-value { font-size: 1.5rem; line-height: 2rem; font-weight: 700; }
        .pm-label { font-size: 0.75rem; line-height: 1rem; font-weight: 700; }
        .pm-date { font-size: 0.75rem; line-height: 1rem; }
        .quality-badge { 
            background-color: #4ade80; 
            color: #166534;
            border-radius: 9999px;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            margin-top: 0.25rem;
            display: inline-block;
        }
        .main-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #374151;
        }
        /* ปรับฟอนต์ Sarabun */
        body, .stApp {
            font-family: 'Sarabun', sans-serif !important;
        }
    </style>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;500;700&display=swap" rel="stylesheet">

    <div class="title-container">
        <div class="pm-indicator">
            <div class="pm-label">ฝุ่น PM2.5</div>
            <div class="pm-value">5</div>
            <div class="pm-date">3 ต.ค. 2025</div>
            <div class="pm-date">10:00:00</div>
            <div class="quality-badge">คุณภาพดี</div>
        </div>
        <h1 class="main-title">
            การเฝ้าระวังโรคที่อาจมีผลกระทบจาก PM2.5 ของผู้เข้ารับบริการในโรงพยาบาลสันทราย
        </h1>
    </div>
""", unsafe_allow_html=True)


# --- ส่วนตัวกรอง (Sidebar) ---
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    st.selectbox("เลือกช่วงวินิจฉัย", ["วันนี้", "สัปดาห์นี้", "เดือนนี้"])
    st.selectbox("กลุ่มโรค", ["4 กลุ่มโรค", "กลุ่มโรคทางเดินหายใจ", "กลุ่มโรคผิวหนังอักเสบ"])
    st.selectbox("โรค", ["Y96, Y97, Z..."])
    st.selectbox("กลุ่มผู้เข้ารับบริการ", ["ทั้งหมด", "เด็ก", "ผู้ใหญ่"])
    st.selectbox("จังหวัด", ["เชียงใหม่"])
    st.selectbox("อำเภอ", ["สันทราย"])
    st.selectbox("ตำบล", ["หนองหาร"])
    st.selectbox("หมู่", ["หมู่ 1"])

    # --- กราฟวงกลม (Pie Chart) ---
    pie_chart_html = """
        <canvas id="pieChart"></canvas>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const pieCtx = document.getElementById('pieChart').getContext('2d');
            new Chart(pieCtx, {
                type: 'pie',
                data: {
                    labels: ['เด็ก', 'ผู้ใหญ่', 'ผู้สูงอายุ'],
                    datasets: [{
                        data: [39.9, 34.9, 24.9],
                        backgroundColor: ['#2563eb', '#3b82f6', '#60a5fa'],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        </script>
    """
    st.header("สัดส่วนผู้ป่วย")
    components.html(pie_chart_html, height=300)

# --- กราฟหลัก (Main Content) ---

# --- กราฟเส้น (Line Chart) ---
st.subheader("สถานการณ์ PM2.5 และจำนวนผู้เข้ารับการรักษา")
line_chart_html = """
    <canvas id="lineChart"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const lineCtx = document.getElementById('lineChart').getContext('2d');
        new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: ['ม.ค. 2023', 'พ.ค. 2023', 'ก.ย. 2023', 'ม.ค. 2024', 'พ.ค. 2024', 'ก.ย. 2024', 'ม.ค. 2025', 'พ.ค. 2025'],
                datasets: [
                    { label: 'PM2.5', data: [100, 80, 50, 150, 120, 110, 190, 170], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.5)', fill: true, tension: 0.4 },
                    { label: 'กลุ่มโรคทางเดินหายใจ', data: [150, 160, 120, 180, 200, 160, 180, 150], borderColor: '#ef4444', tension: 0.4, fill: false },
                    { label: 'กลุ่มโรคผิวหนังอักเสบ', data: [90, 110, 130, 100, 120, 140, 130, 110], borderColor: '#f97316', tension: 0.4, fill: false },
                    { label: 'กลุ่มโรคตาอักเสบ', data: [60, 50, 70, 80, 60, 90, 70, 80], borderColor: '#10b981', tension: 0.4, fill: false },
                    { label: 'กลุ่มโรคหัวใจและหลอดเลือด', data: [130, 140, 110, 150, 170, 130, 140, 120], borderColor: '#a855f7', tension: 0.4, fill: false }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true, max: 250 } } }
        });
    </script>
"""
components.html(line_chart_html, height=400)


# --- กราฟแท่ง (Bar Chart) ---
st.subheader("จำนวนผู้ป่วยในแต่ละตำบล")
st.caption("กรุณาเลือกช่วงวันที่ เพื่อดูการกระจายข้อมูลตามพื้นที่")
bar_chart_html = """
    <div style="overflow-x: auto; position: relative; width: 100%; height: 400px;">
        <div style="width: 800px; height: 100%;">
            <canvas id="barChart"></canvas>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
    <script>
        Chart.register(ChartDataLabels);
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: ['ต.หนองหาร', 'ต.หนองจ๊อม', 'ต.แม่แฝก', 'ต.แม่แฝกใหม่', 'ต.สันทรายน้อย', 'ต.หนองแหย่ง', 'ต.เมืองเล็น', 'ต.สันทรายหลวง', 'ต.สันพระเนตร', 'ต.สันนาเม็ง', 'ต.ป่าไผ่'],
                datasets: [{
                    label: 'จำนวนผู้ป่วย',
                    data: [1160, 763, 425, 361, 350, 291, 235, 192, 182, 118, 99],
                    backgroundColor: '#4b5563',
                    borderRadius: 4
                }]
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: false },
                    datalabels: { anchor: 'end', align: 'top', formatter: (value) => value.toLocaleString(), color: '#374151', font: { weight: 'bold' } }
                },
                scales: { y: { beginAtZero: true, max: 1200, ticks: { stepSize: 250 } } }
            }
        });
    </script>
"""
components.html(bar_chart_html, height=420)
