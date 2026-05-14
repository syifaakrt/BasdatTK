from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import check_password, make_password
from db import get_connection

import psycopg2

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

def _db_error_message(error):
    if getattr(error, "diag", None) and error.diag.message_primary:
        return error.diag.message_primary
    return str(error)


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


def _base_context(user):
    return {
        "email": user["email"],
        "role": user["role"],
        "user_name": user["full_name"],
        "user_code": user["user_code"],
        "nav_items": member_nav_items() if user["role"] == "member" else staff_nav_items(),
    }

# =====================
# FITUR 8 - CLAIM MISSING MILES (MEMBER)
# =====================

def claim_list(request):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    status_filter = request.GET.get("status", "").strip()

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                c.id,
                c.maskapai,
                c.bandara_asal,
                c.bandara_tujuan,
                c.tanggal_penerbangan,
                c.flight_number,
                c.kelas_kabin,
                CASE
                    WHEN c.status_penerimaan = 'Diterima' THEN 'Disetujui'
                    ELSE c.status_penerimaan
                END AS status_tampilan,
                c.timestamp,
                c.nomor_tiket,
                c.pnr
            FROM aeromiles.claim_missing_miles c
            WHERE c.email_member = %s
              AND (
                    %s = ''
                    OR CASE
                        WHEN c.status_penerimaan = 'Diterima' THEN 'Disetujui'
                        ELSE c.status_penerimaan
                    END = %s
              )
            ORDER BY c.timestamp DESC
            """,
            (user["email"], status_filter, status_filter),
        )
        claims = cur.fetchall()

        cur.execute(
            "SELECT kode_maskapai, nama_maskapai FROM " \
            "aeromiles.maskapai ORDER BY kode_maskapai"
        )
        maskapai_list = cur.fetchall()

        cur.execute(
            "SELECT iata_code, nama, kota FROM aeromiles.bandara ORDER BY iata_code"
        )
        bandara_list = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    context = _base_context(user)
    context.update(
        {
            "claims": claims,
            "maskapai_list": maskapai_list,
            "bandara_list": bandara_list,
            "status_filter": status_filter,
            "current_page": "Klaim Miles",
            "page_title": "Klaim Missing Miles",
        }
    )
    return render(request, "miles/claim_list.html", context)


def claim_create(request):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    if request.method != "POST":
        return redirect("miles:claim_list")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO aeromiles.claim_missing_miles (
                email_member,
                maskapai,
                bandara_asal,
                bandara_tujuan,
                tanggal_penerbangan,
                flight_number,
                nomor_tiket,
                kelas_kabin,
                pnr
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user["email"],
                request.POST.get("maskapai"),
                request.POST.get("bandara_asal"),
                request.POST.get("bandara_tujuan"),
                request.POST.get("tanggal_penerbangan"),
                request.POST.get("flight_number"),
                request.POST.get("nomor_tiket"),
                request.POST.get("kelas_kabin"),
                request.POST.get("pnr"),
            ),
        )
        conn.commit()
        messages.success(request, "Klaim berhasil diajukan.")
    except psycopg2.Error as error:
        conn.rollback()
        messages.error(request, _db_error_message(error))
    finally:
        cur.close()
        conn.close()

    return redirect("miles:claim_list")


def claim_edit(request, id):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    if request.method != "POST":
        return redirect("miles:claim_list")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE aeromiles.claim_missing_miles
            SET
                maskapai = %s,
                bandara_asal = %s,
                bandara_tujuan = %s,
                tanggal_penerbangan = %s,
                flight_number = %s,
                nomor_tiket = %s,
                kelas_kabin = %s,
                pnr = %s
            WHERE id = %s
              AND email_member = %s
              AND status_penerimaan = 'Menunggu'
            """,
            (
                request.POST.get("maskapai"),
                request.POST.get("bandara_asal"),
                request.POST.get("bandara_tujuan"),
                request.POST.get("tanggal_penerbangan"),
                request.POST.get("flight_number"),
                request.POST.get("nomor_tiket"),
                request.POST.get("kelas_kabin"),
                request.POST.get("pnr"),
                id,
                user["email"],
            ),
        )

        if cur.rowcount == 0:
            conn.rollback()
            messages.error(request, "Klaim tidak ditemukan atau sudah tidak bisa diubah.")
        else:
            conn.commit()
            messages.success(request, "Klaim berhasil diperbarui.")
    except psycopg2.Error as error:
        conn.rollback()
        messages.error(request, _db_error_message(error))
    finally:
        cur.close()
        conn.close()

    return redirect("miles:claim_list")


def claim_delete(request, id):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    if request.method != "POST":
        return redirect("miles:claim_list")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM aeromiles.claim_missing_miles
            WHERE id = %s
              AND email_member = %s
              AND status_penerimaan = 'Menunggu'
            """,
            (id, user["email"]),
        )

        if cur.rowcount == 0:
            conn.rollback()
            messages.error(request, "Klaim tidak ditemukan atau sudah tidak bisa dibatalkan.")
        else:
            conn.commit()
            messages.success(request, "Klaim berhasil dibatalkan.")
    except psycopg2.Error as error:
        conn.rollback()
        messages.error(request, _db_error_message(error))
    finally:
        cur.close()
        conn.close()

    return redirect("miles:claim_list")

# =====================
# FITUR 9 - CLAIM MISSING MILES (STAF)
# =====================

def staf_claim_list(request):
    user, redirect_response = _require_role(request, "staff")
    if redirect_response:
        return redirect_response

    status_filter = request.GET.get("status", "").strip()
    maskapai_filter = request.GET.get("maskapai", "").strip()
    tanggal_dari = request.GET.get("tanggal_dari", "").strip()
    tanggal_sampai = request.GET.get("tanggal_sampai", "").strip()

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                c.id,
                m.nomor_member,
                TRIM(p.first_mid_name || ' ' || p.last_name) AS nama_member,
                c.email_member,
                c.maskapai,
                c.bandara_asal || ' -> ' || c.bandara_tujuan AS rute,
                c.tanggal_penerbangan,
                c.flight_number,
                c.kelas_kabin,
                c.timestamp,
                CASE
                    WHEN c.status_penerimaan = 'Diterima' THEN 'Disetujui'
                    ELSE c.status_penerimaan
                END AS status_tampilan,
                c.bandara_asal,
                c.bandara_tujuan
            FROM aeromiles.claim_missing_miles c
            JOIN aeromiles.member m ON m.email = c.email_member
            JOIN aeromiles.pengguna p ON p.email = c.email_member
            WHERE (%s = '' OR (
                    CASE
                        WHEN c.status_penerimaan = 'Diterima' THEN 'Disetujui'
                        ELSE c.status_penerimaan
                    END
                ) = %s)
              AND (%s = '' OR c.maskapai = %s)
              AND (NULLIF(%s, '') IS NULL OR c.tanggal_penerbangan >= NULLIF(%s, '')::date)
              AND (NULLIF(%s, '') IS NULL OR c.tanggal_penerbangan <= NULLIF(%s, '')::date)            
              ORDER BY c.timestamp DESC
            """,
            (
                status_filter,
                status_filter,
                maskapai_filter,
                maskapai_filter,
                tanggal_dari,
                tanggal_dari,
                tanggal_sampai,
                tanggal_sampai,
            ),
        )
        claims = cur.fetchall()

        cur.execute(
            "SELECT kode_maskapai, nama_maskapai FROM aeromiles.maskapai ORDER BY kode_maskapai"
        )
        maskapai_list = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    context = _base_context(user)
    context.update(
        {
            "claims": claims,
            "maskapai_list": maskapai_list,
            "status_filter": status_filter,
            "maskapai_filter": maskapai_filter,
            "tanggal_dari": tanggal_dari,
            "tanggal_sampai": tanggal_sampai,
            "current_page": "Kelola Klaim",
            "page_title": "Kelola Klaim Missing Miles",
        }
    )
    return render(request, "miles/staf_claim_list.html", context)


def staf_claim_update(request, id):
    user, redirect_response = _require_role(request, "staff")
    if redirect_response:
        return redirect_response

    if request.method != "POST":
        return redirect("miles:staf_claim_list")

    status_form = request.POST.get("status", "").strip()
    if status_form not in ("Disetujui", "Ditolak"):
        messages.error(request, "Status klaim tidak valid.")
        return redirect("miles:staf_claim_list")

    status_db = "Diterima" if status_form == "Disetujui" else "Ditolak"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE aeromiles.claim_missing_miles
            SET status_penerimaan = %s,
                email_staf = %s
            WHERE id = %s
            AND status_penerimaan = 'Menunggu'
            """,
            (status_db, user["email"], id),
        )

        if cur.rowcount == 0:
            conn.rollback()
            messages.error(request, "Klaim tidak ditemukan atau sudah diproses.")
        else:
            conn.commit()
            # Tangkap pesan dari trigger
            if conn.notices:
                messages.success(request, conn.notices[-1].strip())

    except psycopg2.Error as error:
        conn.rollback()
        messages.error(request, _db_error_message(error))
    finally:
        cur.close()
        conn.close()
    return redirect("miles:staf_claim_list")

# =====================
# FITUR 10 - TRANSFER MILES (MEMBER)
# =====================

def transfer_list(request):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT award_miles FROM aeromiles.member WHERE email = %s",
            (user["email"],),
        )
        award_miles = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                t.timestamp,
                TRIM(p.first_mid_name || ' ' || p.last_name) AS counterpart_name,
                p.email AS counterpart_email,
                t.jumlah,
                COALESCE(t.catatan, '-') AS catatan,
                CASE
                    WHEN t.email_member_1 = %s THEN 'Kirim'
                    ELSE 'Terima'
                END AS tipe
            FROM aeromiles.transfer t
            JOIN aeromiles.pengguna p
              ON p.email = CASE
                    WHEN t.email_member_1 = %s THEN t.email_member_2
                    ELSE t.email_member_1
                 END
            WHERE t.email_member_1 = %s
               OR t.email_member_2 = %s
            ORDER BY t.timestamp DESC
            """,
            (user["email"], user["email"], user["email"], user["email"]),
        )
        transfers = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    context = _base_context(user)
    context.update(
        {
            "transfers": transfers,
            "award_miles": award_miles,
            "current_page": "Transfer Miles",
            "page_title": "Transfer Miles",
        }
    )
    return render(request, "miles/transfer_list.html", context)


def transfer_create(request):
    user, redirect_response = _require_role(request, "member")
    if redirect_response:
        return redirect_response

    if request.method != "POST":
        return redirect("miles:transfer_list")

    email_penerima = request.POST.get("email_penerima", "").strip()
    catatan = request.POST.get("catatan", "").strip() or None

    try:
        jumlah = int(request.POST.get("jumlah", "0"))
    except ValueError:
        messages.error(request, "Jumlah miles harus berupa angka.")
        return redirect("miles:transfer_list")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT transfer_miles(%s, %s, %s::int, %s);",
            (user["email"], email_penerima, jumlah, catatan)
        )
        conn.commit()
        if conn.notices:
            messages.success(request, conn.notices[-1].strip())

    except Exception as e:
        conn.rollback()
        messages.error(request, str(e).split('\n')[0])

    finally:
        cur.close()
        conn.close()

    return redirect("miles:transfer_list")