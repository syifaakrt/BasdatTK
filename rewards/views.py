import json
from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from main.views import get_current_user, get_role
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection


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


def base_context(role, current_page, page_title):
    if role == "staff":
        nav_items = staff_nav_items()
        user_name = "Yasmin Omar"
        user_code = "S0001"
    elif role == "member":
        nav_items = member_nav_items()
        user_name = "Citra Dewi"
        user_code = "M0003"
    else:
        nav_items = []
        user_name = ""
        user_code = ""

    return {
        "role": role,
        "current_page": current_page,
        "page_title": page_title,
        "nav_items": nav_items,
        "user_name": user_name,
        "user_code": user_code,
    }


# ---------------------------------------------------------------------------
# GUEST VIEWS
# ---------------------------------------------------------------------------
def guest_home(request):
    context = base_context(role="guest", current_page="Redeem Hadiah", page_title="Guest View")
    return render(request, "member/redeem_hadiah.html", context)


# ---------------------------------------------------------------------------
# MEMBER VIEWS
# ---------------------------------------------------------------------------
def member_redeem_hadiah(request):
    hadiah_list = [
        {"kode": "RWD-001", "nama": "Tiket Domestik PP", "penyedia": "Garuda Indonesia", "miles": 15000,
         "deskripsi": "Tiket pulang-pergi rute domestik Indonesia via Garuda Indonesia",
         "valid_start_date": "2024-01-01", "program_end": "2025-12-31", "is_featured": True},
        {"kode": "RWD-002", "nama": "Upgrade ke Business Class", "penyedia": "Garuda Indonesia", "miles": 25000,
         "deskripsi": "Upgrade dari economy class ke business class via Garuda Indonesia",
         "valid_start_date": "2024-01-01", "program_end": "2025-12-31", "is_featured": False},
        {"kode": "RWD-004", "nama": "Akses Lounge 1x", "penyedia": "ShopeeTravel", "miles": 3000,
         "deskripsi": "Akses lounge seluruh bandara partner ShopeeTravel 1 kali masuk",
         "valid_start_date": "2024-01-01", "program_end": "2025-12-31", "is_featured": False},
        {"kode": "RWD-005", "nama": "Diskon Hotel 30%", "penyedia": "TravelokaPartner", "miles": 5000,
         "deskripsi": "Diskon 30% pemesanan hotel melalui Traveloka partner program",
         "valid_start_date": "2024-03-01", "program_end": "2025-12-31", "is_featured": False},
    ]
    redeem_history = [
        {"hadiah": "Akses Lounge 1x", "kode_hadiah": "RWD-004", "timestamp": "2024-02-05 09:15:00", "miles": 3000, "status": "Berhasil"},
        {"hadiah": "Diskon Hotel 30%", "kode_hadiah": "RWD-005", "timestamp": "2024-06-03 10:00:00", "miles": 5000, "status": "Berhasil"},
    ]
    selected_hadiah = hadiah_list[2]
    member_award_miles = 5000
    context = base_context(role="member", current_page="Redeem Hadiah", page_title="Redeem Hadiah")
    context.update({
        "member_award_miles": member_award_miles,
        "hadiah_list": hadiah_list,
        "redeem_history": redeem_history,
        "selected_hadiah": selected_hadiah,
        "remaining_miles_after_redeem": member_award_miles - selected_hadiah["miles"],
    })
    return render(request, "member/redeem_hadiah.html", context)


def member_beli_package(request):
    packages = [
        {"id": "AMP-001", "jumlah_award_miles": 5000,  "harga_paket": Decimal("150000.00")},
        {"id": "AMP-002", "jumlah_award_miles": 10000, "harga_paket": Decimal("280000.00")},
        {"id": "AMP-003", "jumlah_award_miles": 20000, "harga_paket": Decimal("500000.00")},
        {"id": "AMP-004", "jumlah_award_miles": 40000, "harga_paket": Decimal("900000.00")},
        {"id": "AMP-005", "jumlah_award_miles": 75000, "harga_paket": Decimal("1500000.00")},
    ]
    purchase_history = [
        {"id": "AMP-003", "timestamp": "2024-02-01 10:15:00", "jumlah_award_miles": 20000, "harga_paket": Decimal("500000.00")},
    ]
    selected_package = packages[2]
    member_award_miles = 5000
    context = base_context(role="member", current_page="Beli Package", page_title="Beli Award Miles Package")
    context.update({
        "member_award_miles": member_award_miles,
        "packages": packages,
        "purchase_history": purchase_history,
        "selected_package": selected_package,
        "total_after_purchase": member_award_miles + selected_package["jumlah_award_miles"],
    })
    return render(request, "member/beli_package.html", context)


def member_info_tier(request):
    tier_list = [
        {"id_tier": "T001", "nama": "Blue",     "minimal_frekuensi_terbang": 0,  "minimal_tier_miles": 0},
        {"id_tier": "T002", "nama": "Silver",   "minimal_frekuensi_terbang": 10, "minimal_tier_miles": 25000},
        {"id_tier": "T003", "nama": "Gold",     "minimal_frekuensi_terbang": 25, "minimal_tier_miles": 50000},
        {"id_tier": "T004", "nama": "Platinum", "minimal_frekuensi_terbang": 50, "minimal_tier_miles": 100000},
    ]
    current_member = {
        "nama": "Citra Dewi", "nomor_member": "M0003", "current_tier": "Silver",
        "tier_miles": 30000, "flight_frequency": 14, "next_tier": "Gold", "miles_to_next_tier": 20000,
    }
    context = base_context(role="member", current_page="Info Tier", page_title="Informasi Tier & Keuntungan")
    context.update({"tier_list": tier_list, "current_member": current_member})
    return render(request, "member/info_tier.html", context)


# ---------------------------------------------------------------------------
# STAFF VIEWS
# ---------------------------------------------------------------------------
def staff_laporan_transaksi(request):
    transactions = []
    top_total_miles = []
    sp_message = ""
    stats = {"total_miles_beredar": 0, "total_redeem_bulan_ini": 0, "total_klaim_disetujui": 0}

    try:
        conn = get_connection()
        cur = conn.cursor()

        # ── 1. Gabungan transaksi dari 3 tabel ──────────────────────────
        cur.execute("""
            SELECT 'Transfer' AS tipe, email_member_1 AS member,
                   jumlah AS jumlah_miles, timestamp, TRUE AS dapat_dihapus
            FROM transfer

            UNION ALL

            SELECT 'Redeem' AS tipe, r.email_member AS member,
                   h.miles AS jumlah_miles, r.timestamp, TRUE AS dapat_dihapus
            FROM redeem r
            JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah

            UNION ALL

            SELECT 'Pembelian Package' AS tipe, mamp.email_member AS member,
                   amp.jumlah_award_miles AS jumlah_miles, mamp.timestamp, TRUE AS dapat_dihapus
            FROM member_award_miles_package mamp
            JOIN award_miles_package amp ON amp.id = mamp.id_award_miles_package

            UNION ALL

            SELECT 'Klaim Disetujui' AS tipe, email_member AS member,
                   1000 AS jumlah_miles, timestamp, FALSE AS dapat_dihapus
            FROM claim_missing_miles
            WHERE status_penerimaan = 'Diterima'

            ORDER BY timestamp DESC
        """)
        rows = cur.fetchall()
        transactions = [
            {
                "tipe": r[0],
                "member": r[1],
                "jumlah_miles": r[2],
                "timestamp": str(r[3]),
                "dapat_dihapus": r[4],
            }
            for r in rows
        ]

        # ── 2. Stats ─────────────────────────────────────────────────────
        cur.execute("SELECT COALESCE(SUM(total_miles), 0) FROM member")
        stats["total_miles_beredar"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM redeem WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)")
        stats["total_redeem_bulan_ini"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM claim_missing_miles WHERE status_penerimaan = 'Diterima'")
        stats["total_klaim_disetujui"] = cur.fetchone()[0]

        # ── 3. Stored Procedure: Top 5 Member by Total Miles ─────────────
        cur.execute("SELECT * FROM get_top5_member_by_total_miles()")
        top_rows = cur.fetchall()
        top_total_miles = [
            {
                "peringkat": r[0],
                "member": r[1],
                "nama_lengkap": r[2],
                "total_miles": r[3],
            }
            for r in top_rows
        ]

        # Ambil pesan RAISE NOTICE dari stored procedure
        if conn.notices:
            sp_message = conn.notices[-1].replace("NOTICE:  ", "").strip()

        cur.close()
        conn.close()

    except Exception as e:
        sp_message = f"Error: {str(e)}"

    context = base_context(role="staff", current_page="Laporan Transaksi", page_title="Laporan & Riwayat Transaksi Miles")
    context.update({
        "transactions": transactions,
        "top_total_miles": top_total_miles,
        "sp_message": sp_message,
        "stats": stats,
        "filters": {"selected_type": "Semua", "selected_member": "Semua Member", "date_start": "", "date_end": ""},
    })
    return render(request, "staff/laporan_transaksi.html", context)


# ---------------------------------------------------------------------------
# KELOLA HADIAH - PAGE
# ---------------------------------------------------------------------------
def kelola_hadiah(request):
    user = get_current_user(request)
    if not user or get_role(user.email) != 'staff':
        return redirect('login')
    return render(request, 'staff/kelola_hadiah.html', {
        'user': user,
        'nav_items': staff_nav_items(),
        'role': 'staff'
    })


# ---------------------------------------------------------------------------
# KELOLA HADIAH - API
# ---------------------------------------------------------------------------
def api_hadiah_list(request):
    """GET /rewards/api/hadiah/ → list semua hadiah"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end
            FROM hadiah
            ORDER BY kode_hadiah
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = [
            {
                "kode": r[0],
                "nama": r[1],
                "miles": r[2],
                "deskripsi": r[3],
                "mulai": str(r[4]),
                "akhir": str(r[5]),
            }
            for r in rows
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_hadiah_create(request):
    """POST /rewards/api/hadiah/create/ → tambah hadiah baru"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body)
        nama     = body.get("nama")
        miles    = body.get("miles")
        deskripsi = body.get("deskripsi")
        mulai    = body.get("mulai")
        akhir    = body.get("akhir")

        if not all([nama, miles, deskripsi, mulai, akhir]):
            return JsonResponse({"error": "Semua field wajib diisi"}, status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Generate kode otomatis: ambil max kode, increment
        cur.execute("SELECT kode_hadiah FROM hadiah ORDER BY kode_hadiah DESC LIMIT 1")
        last = cur.fetchone()
        if last:
            num = int(last[0].replace("RWD-", "")) + 1
        else:
            num = 1
        kode = f"RWD-{str(num).zfill(3)}"

        cur.execute("""
            INSERT INTO hadiah (kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (kode, nama, miles, deskripsi, mulai, akhir, body.get("idPenyedia")))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True, "kode": kode})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_hadiah_update(request, kode):
    """POST /rewards/api/hadiah/update/<kode>/ → edit hadiah"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body)
        nama     = body.get("nama")
        miles    = body.get("miles")
        deskripsi = body.get("deskripsi")
        mulai    = body.get("mulai")
        akhir    = body.get("akhir")

        if not all([nama, miles, deskripsi, mulai, akhir]):
            return JsonResponse({"error": "Semua field wajib diisi"}, status=400)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE hadiah
            SET nama=%s, miles=%s, deskripsi=%s, valid_start_date=%s, program_end=%s
            WHERE kode_hadiah=%s
        """, (nama, miles, deskripsi, mulai, akhir, kode))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_hadiah_delete(request, kode):
    """POST /rewards/api/hadiah/delete/<kode>/ → hapus hadiah"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM hadiah WHERE kode_hadiah=%s", (kode,))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# KELOLA MITRA - PAGE
# ---------------------------------------------------------------------------
def kelola_mitra(request):
    user = get_current_user(request)
    if not user or get_role(user.email) != 'staff':
        return redirect('login')
    return render(request, 'staff/kelola_mitra.html', {
        'user': user,
        'nav_items': staff_nav_items(),
        'role': 'staff'
    })


# ---------------------------------------------------------------------------
# KELOLA MITRA - API
# ---------------------------------------------------------------------------
def api_mitra_list(request):
    """GET /rewards/api/mitra/ → list semua mitra"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT m.email_mitra, m.id_penyedia, m.nama_mitra, m.tanggal_kerja_sama
            FROM mitra m
            ORDER BY m.id_penyedia
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = [
            {
                "emailMitra": r[0],
                "idPenyedia": r[1],
                "namaMitra": r[2],
                "tanggalKerjaSama": str(r[3]),
            }
            for r in rows
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_mitra_create(request):
    """POST /rewards/api/mitra/create/ → tambah mitra"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body)
        email_mitra       = body.get("emailMitra")
        id_penyedia       = body.get("idPenyedia")
        nama_mitra        = body.get("namaMitra")
        tanggal_kerja_sama = body.get("tanggalKerjaSama")

        if not all([email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama]):
            return JsonResponse({"error": "Semua field wajib diisi"}, status=400)

        conn = get_connection()
        cur = conn.cursor()

        # Cek apakah id_penyedia sudah dipakai mitra lain (UNIQUE constraint)
        cur.execute("SELECT email_mitra FROM mitra WHERE id_penyedia=%s", (id_penyedia,))
        if cur.fetchone():
            return JsonResponse({"error": f"Penyedia ID {id_penyedia} sudah terdaftar sebagai mitra lain"}, status=400)

        # Cek apakah penyedia ada, kalau belum insert baru dengan DEFAULT VALUES
        cur.execute("SELECT id FROM penyedia WHERE id=%s", (id_penyedia,))
        if not cur.fetchone():
            cur.execute("INSERT INTO penyedia DEFAULT VALUES RETURNING id")
            generated_id = cur.fetchone()[0]
            id_penyedia = generated_id  # pakai id yang di-generate DB

        cur.execute("""
            INSERT INTO mitra (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama)
            VALUES (%s, %s, %s, %s)
        """, (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_mitra_update(request, email):
    """POST /rewards/api/mitra/update/<email>/ → edit mitra"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body)
        nama_mitra        = body.get("namaMitra")
        tanggal_kerja_sama = body.get("tanggalKerjaSama")
        id_penyedia       = body.get("idPenyedia")

        if not all([nama_mitra, tanggal_kerja_sama, id_penyedia]):
            return JsonResponse({"error": "Semua field wajib diisi"}, status=400)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE mitra
            SET nama_mitra=%s, tanggal_kerja_sama=%s, id_penyedia=%s
            WHERE email_mitra=%s
        """, (nama_mitra, tanggal_kerja_sama, id_penyedia, email))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_mitra_delete(request, email):
    """POST /rewards/api/mitra/delete/<email>/ → hapus mitra"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM mitra WHERE email_mitra=%s", (email,))
        conn.commit()
        cur.close()
        conn.close()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)