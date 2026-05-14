from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .models import Pengguna, Member, Staf, ClaimMissingMiles, Redeem, Transfer, MemberAwardMilesPackage
from django.contrib.auth.hashers import check_password

def register_view(request):
    return render(request, 'register.html')


def get_session(request):
    email = request.session.get('email', 'alice.smith@email.com')
    role = request.session.get('role', 'member')
    return email, role

def get_initials(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0][0].upper() + parts[1][0].upper()
    return parts[0][:2].upper() if parts else "?"

def pengaturan_profile(request):
    from rewards.views import staff_nav_items, member_nav_items

    user = get_current_user(request)
    if not user:
        return redirect('login')

    role = get_role(user.email)

    if role == 'member':
        member = Member.objects.get(email_id=user.email)
        profil = (
            user.email,                   
            user.salutation,              
            user.first_mid_name,          
            user.last_name,               
            user.country_code,            
            user.mobile_number,           
            user.tanggal_lahir,           
            user.kewarganegaraan,         
            member.nomor_member,          
            member.tanggal_bergabung,     
        )
        nav_items = member_nav_items()
        maskapai_list = []

    elif role == 'staff':
        staf = Staf.objects.select_related('kode_maskapai').get(email_id=user.email)
        profil = (
            user.email,                              
            user.salutation,                         
            user.first_mid_name,                     
            user.last_name,                         
            user.country_code,                  
            user.mobile_number,                  
            user.tanggal_lahir,              
            user.kewarganegaraan,                  
            staf.id_staf,                           
            staf.kode_maskapai.kode_maskapai,       
        )
        nav_items = staff_nav_items()
        maskapai_list = list(
            Staf.objects.select_related('kode_maskapai')
            .values_list('kode_maskapai__kode_maskapai', 'kode_maskapai__nama_maskapai')
            .distinct()
        )

    else:
        return redirect('login')

    return render(request, 'pengaturan_profile.html', {
        'profil': profil,
        'role': role,
        'maskapai_list': maskapai_list,
        'nav_items': nav_items,
    })

def update_profile(request):
    email, role = get_session(request)
    if request.method == 'POST':
        messages.success(request, 'Profil berhasil diperbarui!')
    return redirect('pengaturan_profile')


def update_password(request):
    email, role = get_session(request)
    if request.method == 'POST':
        messages.success(request, 'Password berhasil diubah!')
    return redirect('pengaturan_profile')


def get_current_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    try:
        return Pengguna.objects.get(pk=email)
    except Pengguna.DoesNotExist:
        return None

def get_role(email):
    if Member.objects.filter(email_id=email).exists():
        return 'member'
    if Staf.objects.filter(email_id=email).exists():
        return 'staff'
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

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT email, password FROM pengguna WHERE email = %s;",
                (email,)
            )
            user = cur.fetchone()

            cur.close()
            conn.close()

            if user is None:
                messages.error(request, 'Email atau password salah.')
            elif check_password(password, user[1]):
                request.session['user_email'] = user[0]
                return redirect('dashboard')
            else:
                messages.error(request, 'Email atau password salah.')

        except Exception as e:
            print(f"DB error: {e}")
            messages.error(request, 'Terjadi kesalahan server.')

    return render(request, 'login.html')

# =====================
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

    email = user.email
    nama_lengkap = f"{user.first_mid_name} {user.last_name}"
    role = get_role(email)

    context = {
    'user': user,
    'role': role,
    'nama_lengkap': nama_lengkap,
    'user_name': nama_lengkap,
    'user_initials': get_initials(nama_lengkap),
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