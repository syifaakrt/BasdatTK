from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib import messages
from main.views import get_current_user, get_role
from django.db import connection


def member_nav_items():
    return [
        {"label": "Dashboard", "href": "/dashboard"},
        {"label": "Identitas Saya", "href": "/manage/identitas/"},
        {"label": "Klaim Miles", "href": "/miles/klaim/"},
        {"label": "Transfer Miles", "href": "/miles/transfer/"},
        {"label": "Redeem Hadiah", "href": "/rewards/member/redeem-hadiah/"},
        {"label": "Beli Package", "href": "/rewards/member/beli-package/"},
        {"label": "Info Tier", "href": "/rewards/member/info-tier/"},
        {"label": "Pengaturan Profil", "href": "/profile/"},
        {"label": "Logout", "href": "/logout/"},
    ]


def staff_nav_items():
    return [
        {"label": "Dashboard", "href": "/dashboard/"},
        {"label": "Kelola Member", "href": "/manage/kelola/"},
        {"label": "Kelola Klaim", "href": "/miles/staf/klaim/"},
        {"label": "Kelola Hadiah & Penyedia", "href": "/rewards/staf/kelola-hadiah"},
        {"label": "Kelola Mitra", "href": "/rewards/staf/kelola-mitra"},
        {"label": "Laporan Transaksi", "href": "/rewards/staf/laporan-transaksi/"},
        {"label": "Pengaturan Profil", "href": "/profile/"},
        {"label": "Logout", "href": "/logout/"},
    ]


def base_context(role, current_page, page_title, user_info=None):
    """
    role: "guest" | "member" | "staff"
    - "guest"  → navbar tampil tombol Masuk & Daftar (belum login)
    - "member" → navbar tampil menu member (sudah login)
    - "staff"  → navbar tampil menu staff (sudah login)
    """
    if role == "staff":
        nav_items = staff_nav_items()
    elif role == "member":
        nav_items = member_nav_items()
    else:
        nav_items = []

    user_info = user_info or {}

    return {
        "role": role,
        "current_page": current_page,
        "page_title": page_title,
        "nav_items": nav_items,
        "user_name": user_info.get("user_name", ""),
        "user_code": user_info.get("user_code", ""),
    }


# ---------------------------------------------------------------------------
# GUEST VIEWS
# ---------------------------------------------------------------------------
def guest_home(request):
    context = base_context(
        role="guest",
        current_page="Redeem Hadiah",
        page_title="Guest View",
    )
    return render(request, "member/redeem_hadiah.html", context)

# ---------------------------------------------------------------------------
# MEMBER VIEWS
# ---------------------------------------------------------------------------

def member_redeem_hadiah(request):
    email = get_logged_in_email(request)
    if not email:
        return redirect("login")

    member = get_member_info(email)
    if not member:
        return redirect("login")

    if request.method == "POST":
        kode_hadiah = request.POST.get("kode_hadiah")

        try:
            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO redeem (email_member, kode_hadiah, timestamp)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, (email, kode_hadiah))

            messages.success(request, "Redeem berhasil diproses.")
            return redirect("/rewards/member/redeem-hadiah/")

        except Exception as e:
            messages.error(request, str(e))
            return redirect("/rewards/member/redeem-hadiah/")

    hadiah_list = fetch_all_dict("""
        SELECT
            h.kode_hadiah AS kode,
            h.nama,
            COALESCE(mi.nama_mitra, ma.nama_maskapai, 'Penyedia') AS penyedia,
            h.miles,
            h.deskripsi,
            h.valid_start_date,
            h.program_end,
            false AS is_featured
        FROM hadiah h
        JOIN penyedia p ON p.id = h.id_penyedia
        LEFT JOIN mitra mi ON mi.id_penyedia = p.id
        LEFT JOIN maskapai ma ON ma.id_penyedia = p.id
        WHERE CURRENT_DATE BETWEEN h.valid_start_date AND h.program_end
        ORDER BY h.miles ASC
    """)
    for hadiah in hadiah_list:
        hadiah["sisa_award_miles"] = member["award_miles"] - hadiah["miles"]

    redeem_history = fetch_all_dict("""
        SELECT
            h.nama AS hadiah,
            h.kode_hadiah,
            r.timestamp,
            h.miles,
            'Berhasil' AS status
        FROM redeem r
        JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah
        WHERE r.email_member = %s
        ORDER BY r.timestamp DESC
    """, (email,))

    selected_hadiah = hadiah_list[0] if hadiah_list else {
        "kode": "-",
        "nama": "-",
        "penyedia": "-",
        "miles": 0,
    }

    context = base_context("member", "Redeem Hadiah", "Redeem Hadiah", member)
    context.update({
        "member_award_miles": member["award_miles"],
        "hadiah_list": hadiah_list,
        "redeem_history": redeem_history,
        "selected_hadiah": selected_hadiah,
        "remaining_miles_after_redeem": member["award_miles"] - selected_hadiah["miles"],
    })
    return render(request, "member/redeem_hadiah.html", context)


def member_beli_package(request):
    email = get_logged_in_email(request)
    if not email:
        return redirect("login")

    member = get_member_info(email)
    if not member:
        return redirect("login")

    if request.method == "POST":
        package_id = request.POST.get("package_id")

        try:
            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO member_award_miles_package
                        (id_award_miles_package, email_member, timestamp)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, (package_id, email))

            messages.success(request, "Pembelian package berhasil diproses.")
            return redirect("/rewards/member/beli-package/")

        except Exception as e:
            messages.error(request, str(e))
            return redirect("/rewards/member/beli-package/")

    packages = fetch_all_dict("""
        SELECT id, jumlah_award_miles, harga_paket
        FROM award_miles_package
        ORDER BY jumlah_award_miles ASC
    """)

    purchase_history = fetch_all_dict("""
        SELECT
            amp.id,
            mamp.timestamp,
            amp.jumlah_award_miles,
            amp.harga_paket
        FROM member_award_miles_package mamp
        JOIN award_miles_package amp ON amp.id = mamp.id_award_miles_package
        WHERE mamp.email_member = %s
        ORDER BY mamp.timestamp DESC
    """, (email,))

    selected_package = packages[0] if packages else {
        "id": "-",
        "jumlah_award_miles": 0,
        "harga_paket": 0,
    }

    context = base_context("member", "Beli Package", "Beli Award Miles Package", member)
    context.update({
        "member_award_miles": member["award_miles"],
        "packages": packages,
        "purchase_history": purchase_history,
        "selected_package": selected_package,
        "total_after_purchase": member["award_miles"] + selected_package["jumlah_award_miles"],
    })
    return render(request, "member/beli_package.html", context)


def member_info_tier(request):
    email = get_logged_in_email(request)
    if not email:
        return redirect("login")

    member = fetch_one_dict("""
        SELECT
            p.first_mid_name || ' ' || p.last_name AS user_name,
            m.nomor_member AS user_code,
            m.total_miles AS tier_miles,
            m.total_miles,
            (
                SELECT COUNT(*)
                FROM claim_missing_miles c
                WHERE c.email_member = m.email
                  AND c.status_penerimaan IN ('Disetujui', 'Diterima')
            ) AS flight_frequency,
            m.id_tier
        FROM pengguna p
        JOIN member m ON m.email = p.email
        WHERE p.email = %s
    """, (email,))

    tier_list = fetch_all_dict("""
        SELECT id_tier, nama, minimal_frekuensi_terbang, minimal_tier_miles
        FROM tier
        ORDER BY minimal_tier_miles ASC
    """)

    current_tier = tier_list[0] if tier_list else None
    for tier in tier_list:
        if (
            member["total_miles"] >= tier["minimal_tier_miles"]
            and member["flight_frequency"] >= tier["minimal_frekuensi_terbang"]
        ):
            current_tier = tier
        else:
            break

    next_tier = None
    for tier in tier_list:
        if (
            member["total_miles"] < tier["minimal_tier_miles"]
            or member["flight_frequency"] < tier["minimal_frekuensi_terbang"]
        ):
            next_tier = tier
            break

    miles_to_next_tier = 0
    flights_to_next_tier = 0
    if next_tier:
        miles_to_next_tier = max(next_tier["minimal_tier_miles"] - member["total_miles"], 0)
        flights_to_next_tier = max(next_tier["minimal_frekuensi_terbang"] - member["flight_frequency"], 0)

    current_member = {
        "nama": member["user_name"],
        "nomor_member": member["user_code"],
        "current_tier": current_tier["nama"] if current_tier else "-",
        "tier_miles": member["tier_miles"],
        "flight_frequency": member["flight_frequency"],
        "next_tier": next_tier["nama"] if next_tier else "Tier Maksimum",
        "miles_to_next_tier": miles_to_next_tier,
        "flights_to_next_tier": flights_to_next_tier,
    }

    context = base_context("member", "Info Tier", "Informasi Tier & Keuntungan", member)
    context.update({
        "tier_list": tier_list,
        "current_member": current_member,
    })
    return render(request, "member/info_tier.html", context)


# ---------------------------------------------------------------------------
# STAFF VIEWS
# ---------------------------------------------------------------------------

def staff_laporan_transaksi(request):
    email = get_logged_in_email(request)
    if not email:
        return redirect("login")

    staff = get_staff_info(email)
    if not staff:
        return redirect("login")

    transactions = fetch_all_dict("""
        SELECT *
        FROM (
            SELECT
                'Transfer' AS tipe,
                email_member_1 AS member,
                jumlah AS jumlah_miles,
                timestamp,
                true AS dapat_dihapus
            FROM transfer

            UNION ALL

            SELECT
                'Redeem' AS tipe,
                r.email_member AS member,
                h.miles AS jumlah_miles,
                r.timestamp,
                true AS dapat_dihapus
            FROM redeem r
            JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah

            UNION ALL

            SELECT
                'Pembelian Package' AS tipe,
                mamp.email_member AS member,
                amp.jumlah_award_miles AS jumlah_miles,
                mamp.timestamp,
                true AS dapat_dihapus
            FROM member_award_miles_package mamp
            JOIN award_miles_package amp ON amp.id = mamp.id_award_miles_package

            UNION ALL

            SELECT
                'Klaim Disetujui' AS tipe,
                email_member AS member,
                1000 AS jumlah_miles,
                timestamp,
                false AS dapat_dihapus
            FROM claim_missing_miles
            WHERE status_penerimaan = 'Disetujui'
        ) x
        ORDER BY timestamp DESC
    """)

    top_total_miles = fetch_all_dict("""
        SELECT email AS member, total_miles
        FROM member
        ORDER BY total_miles DESC
        LIMIT 5
    """)

    top_activity = fetch_all_dict("""
        SELECT member, aktivitas, jumlah
        FROM (
            SELECT email_member_1 AS member, 'Transfer' AS aktivitas, COUNT(*) AS jumlah
            FROM transfer
            GROUP BY email_member_1

            UNION ALL

            SELECT email_member AS member, 'Redeem' AS aktivitas, COUNT(*) AS jumlah
            FROM redeem
            GROUP BY email_member
        ) x
        ORDER BY jumlah DESC
        LIMIT 5
    """)

    stats = fetch_one_dict("""
        SELECT
            COALESCE((SELECT SUM(total_miles) FROM member), 0) AS total_miles_beredar,
            COALESCE((
                SELECT COUNT(*)
                FROM redeem
                WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)
            ), 0) AS total_redeem_bulan_ini,
            COALESCE((
                SELECT COUNT(*)
                FROM claim_missing_miles
                WHERE status_penerimaan = 'Disetujui'
            ), 0) AS total_klaim_disetujui
    """)

    context = base_context("staff", "Laporan Transaksi", "Laporan & Riwayat Transaksi Miles", staff)
    context.update({
        "transactions": transactions,
        "top_total_miles": top_total_miles,
        "top_activity": top_activity,
        "stats": stats,
        "filters": {
            "date_start": "",
            "date_end": "",
        },
    })
    return render(request, "staff/laporan_transaksi.html", context)

# =====================
# KELOLA HADIAH
# =====================
def kelola_hadiah(request):
    user = get_current_user(request)
    if not user or get_role(user.email) != 'staff':
        return redirect('login')
    return render(request, 'staff/kelola_hadiah.html', {'user': user, 'nav_items':staff_nav_items(), 'role': 'staff'})

# =====================
# KELOLA MITRA
# =====================
def kelola_mitra(request):
    user = get_current_user(request)
    if not user or get_role(user.email) != 'staff':
        return redirect('login')
    return render(request, 'staff/kelola_mitra.html', {'user': user, 'nav_items':staff_nav_items(), 'role': 'staff'})

def fetch_all_dict(query, params=None):
    with connection.cursor() as cur:
        cur.execute(query, params or ())
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]



def fetch_one_dict(query, params=None):
    rows = fetch_all_dict(query, params)
    return rows[0] if rows else None


def get_logged_in_email(request):
    return request.session.get("user_email")

def get_member_info(email):
    return fetch_one_dict("""
        SELECT
            p.first_mid_name || ' ' || p.last_name AS user_name,
            m.nomor_member AS user_code,
            m.award_miles,
            m.total_miles,
            m.id_tier
        FROM pengguna p
        JOIN member m ON m.email = p.email
        WHERE p.email = %s
    """, (email,))


def get_staff_info(email):
    return fetch_one_dict("""
        SELECT
            p.first_mid_name || ' ' || p.last_name AS user_name,
            s.id_staf AS user_code
        FROM pengguna p
        JOIN staf s ON s.email = p.email
        WHERE p.email = %s
    """, (email,))
