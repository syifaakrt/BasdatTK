from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.hashers import check_password

from django.db import DatabaseError
from db import get_connection
from rewards.views import base_context

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        salutation = request.POST.get('salutation')
        first_mid_name = request.POST.get('first_mid_name')
        last_name = request.POST.get('last_name')
        country_code = request.POST.get('country_code')
        mobile_number = request.POST.get('mobile_number')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        kewarganegaraan = request.POST.get('kewarganegaraan')

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO pengguna (
                    email,
                    password,
                    salutation,
                    first_mid_name,
                    last_name,
                    country_code,
                    mobile_number,
                    tanggal_lahir,
                    kewarganegaraan
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                email,
                make_password(password),
                salutation,
                first_mid_name,
                last_name,
                country_code,
                mobile_number,
                tanggal_lahir,
                kewarganegaraan
            ))

            conn.commit()

            messages.success(request, "Registrasi berhasil!")
            return redirect('login')

        except Exception as e:
            conn.rollback()

            error_msg = str(e).split('\n')[0]
            messages.error(request, error_msg)

        finally:
            cur.close()
            conn.close()

    return render(request, 'register.html')

def get_session(request):
    email = request.session.get('email', 'alice.smith@email.com')
    role = request.session.get('role', 'member')
    return email, role

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
        id=''

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
            id=row[9]

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
            id=row[11]

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
    
    
    context = base_context(page_title="", current_page="Pengaturan Profil", role="")
    context.update({
        'profil': profil,
        'role': role,
        'maskapai_list': maskapai_list,
        'nav_items': nav_items,
        "user_name": row[2] + " " +row[3],
        "user_code": id,
    })
    return render(request, 'pengaturan_profile.html', context)

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

def get_current_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pengguna WHERE email = %s;", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_role(email):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT 1 FROM member WHERE email = %s;", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return 'member'
    
    cur.execute("SELECT 1 FROM staf WHERE email = %s;", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return 'staff'
    
    cur.close()
    conn.close()
    return None
# =====================
# LOGIN
# =====================
from db import get_connection
from django.contrib.auth.hashers import check_password

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT email, password FROM pengguna WHERE LOWER(email) = LOWER(%s);",
                (email,)
            )
            user = cur.fetchone()

            if user is None or not check_password(password, user[1]):
                cur.execute("SELECT aeromiles.raise_login_error();")
            
            request.session['user_email'] = user[0]
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, str(e).split('\n')[0])

        finally:
            cur.close()
            conn.close()

    return render(request, 'login.html')
# LOGOUT
# =====================
def logout_view(request):
    request.session.flush()
    return redirect('login')

# =====================
# DASHBOARD
# =====================
def dashboard(request):
    from rewards.views import staff_nav_items, member_nav_items
    user = get_current_user(request)
    if not user:
        return redirect('login')

    email = user[0]
    nama_lengkap = f"{user[3]} {user[4]}"
    role = get_role(email)

    context = {
    'user': user,
    'role': role,
    'nama_lengkap': nama_lengkap,
    'user_name': nama_lengkap,
    'current_page': "Dashboard",
    'email': email,
    'country_code': user[5],
    'mobile_number': user[6],
    'tanggal_lahir': user[7],
    'kewarganegaraan': user[8]
    }

    try:
        conn = get_connection()
        cur = conn.cursor()

        if role == 'member':
            # ── Data member + tier ──────────────────────────────────────
            cur.execute("""
                SELECT m.nomor_member, m.tanggal_bergabung, m.award_miles,
                       m.total_miles, t.nama AS tier_nama
                FROM member m
                JOIN tier t ON t.id_tier = m.id_tier
                WHERE m.email = %s
            """, (email,))
            row = cur.fetchone()

            member_data = {
                'nomor_member':      row[0],
                'tanggal_bergabung': row[1],
                'award_miles':       row[2],
                'total_miles':       row[3],
            }
            tier_nama = row[4]

            # ── 5 Transaksi terbaru ─────────────────────────────────────
            cur.execute("""
                SELECT tipe, tanggal, miles FROM (

                    SELECT 'Redeem' AS tipe,
                           r.timestamp AS tanggal,
                           -h.miles AS miles
                    FROM redeem r
                    JOIN hadiah h ON h.kode_hadiah = r.kode_hadiah
                    WHERE r.email_member = %s

                    UNION ALL

                    SELECT 'Transfer' AS tipe,
                           t.timestamp AS tanggal,
                           -t.jumlah AS miles
                    FROM transfer t
                    WHERE t.email_member_1 = %s

                    UNION ALL

                    SELECT 'Package' AS tipe,
                           mamp.timestamp AS tanggal,
                           amp.jumlah_award_miles AS miles
                    FROM member_award_miles_package mamp
                    JOIN award_miles_package amp ON amp.id = mamp.id_award_miles_package
                    WHERE mamp.email_member = %s

                ) AS all_transaksi
                ORDER BY tanggal DESC
                LIMIT 5
            """, (email, email, email))

            transaksi = [
                {
                    'tipe':    r[0],
                    'tanggal': r[1].strftime('%Y-%m-%d %H:%M'),
                    'miles':   r[2],
                }
                for r in cur.fetchall()
            ]

            context.update({
                'member':    member_data,
                'tier_nama': tier_nama,
                'transaksi': transaksi,
                'nav_items': member_nav_items(),
            })

        elif role == 'staff':
            # ── Data staf + maskapai ────────────────────────────────────
            cur.execute("""
                SELECT s.id_staf, m.nama_maskapai
                FROM staf s
                JOIN maskapai m ON m.kode_maskapai = s.kode_maskapai
                WHERE s.email = %s
            """, (email,))
            row = cur.fetchone()
            staf_data = {'id_staf': row[0]}
            maskapai  = row[1]

            # ── Statistik klaim ─────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status_penerimaan = 'Menunggu') AS menunggu,
                    COUNT(*) FILTER (WHERE email_staf = %s AND status_penerimaan = 'Diterima') AS disetujui,
                    COUNT(*) FILTER (WHERE email_staf = %s AND status_penerimaan = 'Ditolak') AS ditolak
                FROM claim_missing_miles
            """, (email, email))
            klaim = cur.fetchone()

            context.update({
                'staf':            staf_data,
                'maskapai':        maskapai,
                'klaim_menunggu':  klaim[0],
                'klaim_disetujui': klaim[1],
                'klaim_ditolak':   klaim[2],
                'nav_items':       staff_nav_items(),
            })

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Dashboard DB error: {e}")

    return render(request, 'dashboard.html', context)
