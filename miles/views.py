from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import check_password, make_password
from db import get_connection

import psycopg2

from db import get_connection
from rewards.views import member_nav_items, staff_nav_items

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
              AND (%s = '' OR c.tanggal_penerbangan >= %s::date)
              AND (%s = '' OR c.tanggal_penerbangan <= %s::date)
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
            messages.success(request, f"Status klaim berhasil diubah menjadi {status_form}.")
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

    if jumlah <= 0:
        messages.error(request, "Jumlah miles harus lebih dari 0.")
        return redirect("miles:transfer_list")

    if email_penerima == user["email"]:
        messages.error(request, "Anda tidak bisa transfer miles ke akun sendiri.")
        return redirect("miles:transfer_list")

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT award_miles FROM aeromiles.member WHERE email = %s FOR UPDATE",
            (user["email"],),
        )
        sender_row = cur.fetchone()

        cur.execute(
            "SELECT award_miles FROM aeromiles.member WHERE email = %s FOR UPDATE",
            (email_penerima,),
        )
        recipient_row = cur.fetchone()

        if recipient_row is None:
            raise ValueError("Member penerima tidak ditemukan.")

        sender_award_miles = sender_row[0]
        if sender_award_miles < jumlah:
            raise ValueError(
                f"Saldo award miles tidak mencukupi. Saldo Anda saat ini {sender_award_miles} miles."
            )

        cur.execute(
            """
            INSERT INTO aeromiles.transfer (email_member_1, email_member_2, jumlah, catatan)
            VALUES (%s, %s, %s, %s)
            """,
            (user["email"], email_penerima, jumlah, catatan),
        )

        cur.execute(
            "UPDATE aeromiles.member SET award_miles = award_miles - %s WHERE email = %s",
            (jumlah, user["email"]),
        )
        cur.execute(
            "UPDATE member SET award_miles = award_miles + %s WHERE email = %s",
            (jumlah, email_penerima),
        )

        conn.commit()
        messages.success(request, f"Transfer {jumlah} miles berhasil.")
    except ValueError as error:
        conn.rollback()
        messages.error(request, str(error))
    except psycopg2.Error as error:
        conn.rollback()
        messages.error(request, _db_error_message(error))
    finally:
        cur.close()
        conn.close()

    return redirect("miles:transfer_list")

# =====================
# PENGATURAN PROFIL
# =====================

def pengaturan_profile(request):
    from rewards.views import staff_nav_items, member_nav_items

    email = request.session.get('user_email') or request.session.get('email')
    if not email:
        return redirect('login')

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                p.email,
                p.salutation,
                p.first_mid_name,
                p.last_name,
                p.country_code,
                p.mobile_number,
                p.tanggal_lahir,
                p.kewarganegaraan,
                CASE
                    WHEN m.email IS NOT NULL THEN 'member'
                    WHEN s.email IS NOT NULL THEN 'staff'
                    ELSE NULL
                END AS role,
                m.nomor_member,
                m.tanggal_bergabung,
                s.id_staf,
                s.kode_maskapai
            FROM pengguna p
            LEFT JOIN member m ON p.email = m.email
            LEFT JOIN staf s ON p.email = s.email
            WHERE p.email = %s
        """, (email,))
        row = cur.fetchone()

        if not row:
            return redirect('login')

        role = row[8]

        if role == 'member':
            profil = (
                row[0],   # email
                row[1],   # salutation
                row[2],   # first_mid_name
                row[3],   # last_name
                row[4],   # country_code
                row[5],   # mobile_number
                row[6],   # tanggal_lahir
                row[7],   # kewarganegaraan
                row[9],   # nomor_member
                row[10],  # tanggal_bergabung
            )
            nav_items = member_nav_items()
            maskapai_list = []

        elif role == 'staff':
            profil = (
                row[0],   # email
                row[1],   # salutation
                row[2],   # first_mid_name
                row[3],   # last_name
                row[4],   # country_code
                row[5],   # mobile_number
                row[6],   # tanggal_lahir
                row[7],   # kewarganegaraan
                row[11],  # id_staf
                row[12],  # kode_maskapai
            )
            nav_items = staff_nav_items()

            cur.execute("""
                SELECT kode_maskapai, nama_maskapai
                FROM maskapai
                ORDER BY kode_maskapai
            """)
            maskapai_list = cur.fetchall()

        else:
            return redirect('login')

    finally:
        cur.close()
        conn.close()

    return render(request, 'pengaturan_profile.html', {
        'profil': profil,
        'role': role,
        'maskapai_list': maskapai_list,
        'nav_items': nav_items,
    })

def update_profile(request):
    if request.method != 'POST':
        return redirect('pengaturan_profile')

    email = request.session.get('user_email') or request.session.get('email')
    if not email:
        return redirect('login')

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                CASE
                    WHEN EXISTS (SELECT 1 FROM member WHERE email = %s) THEN 'member'
                    WHEN EXISTS (SELECT 1 FROM staf WHERE email = %s) THEN 'staff'
                    ELSE NULL
                END
        """, (email, email))
        role_row = cur.fetchone()
        role = role_row[0] if role_row else None

        cur.execute("""
            UPDATE pengguna
            SET
                salutation = %s,
                first_mid_name = %s,
                last_name = %s,
                country_code = %s,
                mobile_number = %s,
                tanggal_lahir = %s,
                kewarganegaraan = %s
            WHERE email = %s
        """, (
            request.POST.get('salutation'),
            request.POST.get('first_mid_name'),
            request.POST.get('last_name'),
            request.POST.get('country_code'),
            request.POST.get('mobile_number'),
            request.POST.get('tanggal_lahir'),
            request.POST.get('kewarganegaraan'),
            email,
        ))

        if role == 'staff':
            cur.execute("""
                UPDATE staf
                SET kode_maskapai = %s
                WHERE email = %s
            """, (
                request.POST.get('kode_maskapai'),
                email,
            ))

        conn.commit()
        messages.success(request, 'Profil berhasil diperbarui!')
    except Exception as e:
        conn.rollback()
        messages.error(request, f'Gagal memperbarui profil: {e}')
    finally:
        cur.close()
        conn.close()

    return redirect('pengaturan_profile')

def update_password(request):
    if request.method != 'POST':
        return redirect('pengaturan_profile')

    email = request.session.get('user_email') or request.session.get('email')
    if not email:
        return redirect('login')

    password_lama = request.POST.get('password_lama')
    password_baru = request.POST.get('password_baru')
    konfirmasi_password = request.POST.get('konfirmasi_password')

    if password_baru != konfirmasi_password:
        messages.error(request, 'Konfirmasi password baru tidak cocok.')
        return redirect('pengaturan_profile')

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT password
            FROM pengguna
            WHERE email = %s
        """, (email,))
        row = cur.fetchone()

        if not row or not check_password(password_lama, row[0]):
            messages.error(request, 'Password lama salah.')
            return redirect('pengaturan_profile')

        hashed_password = make_password(password_baru)
        cur.execute("""
            UPDATE pengguna
            SET password = %s
            WHERE email = %s
        """, (hashed_password, email))

        conn.commit()
        messages.success(request, 'Password berhasil diubah!')
    except Exception as e:
        conn.rollback()
        messages.error(request, f'Gagal mengubah password: {e}')
    finally:
        cur.close()
        conn.close()

    return redirect('pengaturan_profile')
