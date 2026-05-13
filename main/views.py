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
    
    nama_lengkap = f"{user.first_mid_name} {user.last_name}"

    role = get_role(user.email)
    context = {'user': user,
               'role': role,
               'nama_lengkap':nama_lengkap,
               }

    if role == 'member':
        member = Member.objects.select_related('id_tier').get(email_id=user.email)

        transaksi = []

        redeems = Redeem.objects.select_related('kode_hadiah').filter(email_member_id=user.email).order_by('-timestamp')[:5]
        for r in redeems:
            transaksi.append({
                'tipe': 'Redeem',
                'tanggal': r.timestamp.strftime('%Y-%m-%d %H:%M'),
                'miles': -r.kode_hadiah.miles,
            })

        transfers = Transfer.objects.filter(email_member_1_id=user.email).order_by('-timestamp')[:5]
        for t in transfers:
            transaksi.append({
                'tipe': 'Transfer',
                'tanggal': t.timestamp.strftime('%Y-%m-%d %H:%M'),
                'miles': -t.jumlah,
            })

        packages = MemberAwardMilesPackage.objects.select_related('id_award_miles_package').filter(email_member_id=user.email).order_by('-timestamp')[:5]
        for p in packages:
            transaksi.append({
                'tipe': 'Package',
                'tanggal': p.timestamp.strftime('%Y-%m-%d %H:%M'),
                'miles': p.id_award_miles_package.jumlah_award_miles,
            })

        transaksi = sorted(transaksi, key=lambda x: x['tanggal'], reverse=True)[:5]

        context.update({
            'member': member,
            'tier_nama': member.id_tier.nama,
            'transaksi': transaksi,
            'nav_items':member_nav_items()
        })

    elif role == 'staff':
        staf = Staf.objects.select_related('kode_maskapai').get(email_id=user.email)
        klaim_menunggu  = ClaimMissingMiles.objects.filter(status_penerimaan='Menunggu').count()
        klaim_disetujui = ClaimMissingMiles.objects.filter(email_staf_id=user.email, status_penerimaan='Diterima').count()
        klaim_ditolak   = ClaimMissingMiles.objects.filter(email_staf_id=user.email, status_penerimaan='Ditolak').count()

        context.update({
            'staf': staf,
            'maskapai': staf.kode_maskapai.nama_maskapai,
            'klaim_menunggu': klaim_menunggu,
            'klaim_disetujui': klaim_disetujui,
            'klaim_ditolak': klaim_ditolak,
            'nav_items':staff_nav_items()
        })

    return render(request, 'dashboard.html', context)
