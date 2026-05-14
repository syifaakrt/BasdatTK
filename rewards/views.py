import json
from decimal import Decimal
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from db import get_connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

def get_initials(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0][0].upper() + parts[1][0].upper()
    return parts[0][:2].upper() if parts else "?"

def _get_session_email(request):
    return request.session.get("user_email") or request.session.get("email")


def _get_user_context(request):
    email = _get_session_email(request)
    if not email:
        return None

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                p.email,
                p.first_mid_name,
                p.last_name,
                m.nomor_member,
                s.id_staf,
                CASE
                    WHEN m.email IS NOT NULL THEN 'member'
                    WHEN s.email IS NOT NULL THEN 'staff'
                    ELSE NULL
                END AS role
            FROM aeromiles.pengguna p
            LEFT JOIN aeromiles.member m ON m.email = p.email
            LEFT JOIN aeromiles.staf s ON s.email = p.email

            WHERE p.email = %s
            """,
            (email,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        return None

    full_name = f"{row[1] or ''} {row[2] or ''}".strip()
    return {
        "email": row[0],
        "full_name": full_name,
        "nomor_member": row[3],
        "id_staf": row[4],
        "role": row[5],
        "user_code": row[3] if row[5] == "member" else row[4],
    }


def _require_role(request, role):
    user = _get_user_context(request)
    if not user:
        return None, redirect("login")
    if user["role"] != role:
        return user, redirect("dashboard")
    return user, None


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
    context = base_context(role="guest", current_page="Redeem Hadiah", page_title="Guest View", request=request)
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
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                CALL sp_redeem_hadiah(%s, %s, NULL)
            """, (email, kode_hadiah))
            
            # Ambil nilai INOUT p_message
            result = cur.fetchone()
            pesan = result[0] if result else None
            
            conn.commit()
            
            if pesan:
                messages.success(request, pesan)

            cur.close()
            conn.close()
            return redirect("/rewards/member/redeem-hadiah/")

        except Exception as e:
            error_msg = getattr(e, 'diag', None)
            if error_msg:
                messages.error(request, e.diag.message_primary)
            else:
                messages.error(request, str(e).split('\n')[0])
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
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "CALL sp_beli_award_miles_package(%s, %s, NULL)",
                (email, package_id)
            )
            result = cur.fetchone()
            pesan = result[0] if result else None
            conn.commit()

            if pesan:
                messages.success(request, pesan)

            cur.close()
            conn.close()
            return redirect("/rewards/member/beli-package/")

        except Exception as e:
            conn.rollback()
            messages.error(request, str(e).split('\n')[0])
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
        if member["total_miles"] >= tier["minimal_tier_miles"]:
            current_tier = tier
        else:
            break

    next_tier = None
    for tier in tier_list:
        if tier["minimal_tier_miles"] > member["total_miles"]:
            next_tier = tier
            break

    current_member = {
        "nama": member["user_name"],
        "nomor_member": member["user_code"],
        "current_tier": current_tier["nama"] if current_tier else "-",
        "tier_miles": member["tier_miles"],
        "next_tier": next_tier["nama"] if next_tier else "Tier Maksimum",
        "miles_to_next_tier": max(next_tier["minimal_tier_miles"] - member["total_miles"], 0) if next_tier else 0,
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
    transactions = []
    top_total_miles = []
    sp_message = ""
    stats = {"total_miles_beredar": 0, "total_redeem_bulan_ini": 0, "total_klaim_disetujui": 0}

    try:
        conn = get_connection()
        cur = conn.cursor()
            
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
        "top_activity": top_activity,
        "sp_message": sp_message,
        "stats": stats,
        "filters": {"selected_type": "Semua", "selected_member": "Semua Member", "date_start": "", "date_end": ""},
    })
    return render(request, "staff/laporan_transaksi.html", context)

# ---------------------------------------------------------------------------
# KELOLA HADIAH - PAGE
# ---------------------------------------------------------------------------
def kelola_hadiah(request):
    email=get_logged_in_email(request)
    staff=get_staff_info(email)
    if not staff:
        return redirect("login")
    context=base_context("staff", "Kelola Hadiah & Penyedia", "", staff)
    return render(request, 'staff/kelola_hadiah.html', context)


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
    email = get_logged_in_email(request)
    user=get_staff_info(email)
    if not user:
        return redirect("login")
    context=base_context('staff','Kelola Mitra',"",user)    
    return render(request, 'staff/kelola_mitra.html',context)

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
