from pyexpat.errors import messages
from django.contrib import messages as django_messages
from django.shortcuts import redirect, render
from db import get_connection
from miles.views import _require_role
from rewards.views import staff_nav_items, member_nav_items, base_context
from django.contrib.auth.hashers import make_password
from db import get_connection

def kelola_member(request):
    user, redirect_response = _require_role(request, "staff")
    nav_items = staff_nav_items()
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST' and request.POST.get('action') == 'tambah':
        try:
            email = request.POST.get('email')
            password = make_password(request.POST.get('password'))
            salutation = request.POST.get('salutation')
            first_mid_name = request.POST.get('first_mid_name')
            last_name = request.POST.get('last_name')
            country_code = request.POST.get('country_code')
            mobile_number = request.POST.get('mobile_number')
            tanggal_lahir = request.POST.get('tanggal_lahir')
            kewarganegaraan = request.POST.get('kewarganegaraan')

            cur.execute("""
                INSERT INTO pengguna (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan))

            cur.execute("""
                INSERT INTO member (email, tanggal_bergabung, id_tier, award_miles, total_miles)
                VALUES (%s, CURRENT_DATE, 'T001', 0, 0);
            """, (email,))

            conn.commit()
            django_messages.success(request, 'Member berhasil ditambahkan.')

        except Exception as e:
            conn.rollback()
            django_messages.error(request, str(e).split('\n')[0])

    elif request.method == 'POST' and request.POST.get('action') == 'edit':
        try:
            email = request.POST.get('email')
            salutation = request.POST.get('salutation')
            first_mid_name = request.POST.get('first_mid_name')
            last_name = request.POST.get('last_name')
            country_code = request.POST.get('country_code')
            mobile_number = request.POST.get('mobile_number')
            tanggal_lahir = request.POST.get('tanggal_lahir')
            kewarganegaraan = request.POST.get('kewarganegaraan')
            id_tier = request.POST.get('tier')

            cur.execute("""
                UPDATE pengguna SET salutation=%s, first_mid_name=%s, last_name=%s,
                country_code=%s, mobile_number=%s, tanggal_lahir=%s, kewarganegaraan=%s
                WHERE email=%s;
            """, (salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan, email))

            cur.execute("""
                UPDATE member SET id_tier=%s WHERE email=%s;
            """, (id_tier, email))

            conn.commit()
            django_messages.success(request, 'Member berhasil diupdate.')

        except Exception as e:
            conn.rollback()
            django_messages.error(request, str(e).split('\n')[0])

    # HAPUS MEMBER
    elif request.method == 'POST' and request.POST.get('action') == 'hapus':
        try:
            email = request.POST.get('email')
            cur.execute("DELETE FROM pengguna WHERE email=%s;", (email,))
            conn.commit()
            django_messages.success(request, 'Member berhasil dihapus.')

        except Exception as e:
            conn.rollback()
            django_messages.error(request, str(e).split('\n')[0])

    # AMBIL DATA MEMBER
    cur.execute("""
        SELECT m.nomor_member, p.salutation, p.first_mid_name, p.last_name,
               p.email, m.id_tier, m.total_miles, m.award_miles, m.tanggal_bergabung
        FROM member m
        JOIN pengguna p ON m.email = p.email
        ORDER BY m.nomor_member;
    """)
    members = cur.fetchall()
    print(members)

    cur.close()
    conn.close()
    context=base_context("staff","","",user)


    return render(request, 'member/kelola_member.html', {
        "nav_items": nav_items,
        "role": "member",
        "user_name": user["full_name"],
        "user_code": user["user_code"],
        "current_page": "Kelola Member",
        "members": members
    })


def identitas(request):
    user, redirect_response = _require_role(request, "member")

    nav_items = member_nav_items()
    user_email = request.session.get('user_email')

    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'tambah':
                cur.execute("""
                    INSERT INTO identitas (nomor, email_member, jenis, negara_penerbit, tanggal_terbit, tanggal_habis)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    request.POST.get('nomor_dokumen'),
                    user_email,
                    request.POST.get('jenis_dokumen'),
                    request.POST.get('negara_penerbit'),
                    request.POST.get('tanggal_terbit'),
                    request.POST.get('tanggal_habis'),
                ))
                conn.commit()
                django_messages.success(request, 'Identitas berhasil ditambahkan.')

            elif action == 'edit':
                cur.execute("""
                    UPDATE identitas
                    SET nomor = %s, jenis = %s, negara_penerbit = %s,
                        tanggal_terbit = %s, tanggal_habis = %s
                    WHERE nomor = %s AND email_member = %s
                """, (
                    request.POST.get('nomor_dokumen'),
                    request.POST.get('jenis_dokumen'),
                    request.POST.get('negara_penerbit'),
                    request.POST.get('tanggal_terbit'),
                    request.POST.get('tanggal_habis'),
                    request.POST.get('identitas_id'),
                    user_email,
                ))
                conn.commit()
                django_messages.success(request, 'Identitas berhasil diperbarui.')
            elif action == 'hapus':
                cur.execute("""
                    DELETE FROM identitas
                    WHERE nomor = %s AND email_member = %s
                """, (request.POST.get('identitas_id'), user_email))
                conn.commit()
                django_messages.success(request, 'Identitas berhasil dihapus.')

        except Exception as e:
            conn.rollback()
            django_messages.error(request, str(e).split('\n')[0])

        finally:
            cur.close()
            conn.close()

        return redirect('member:identitas')  # ← selalu redirect setelah POST
    try:
        cur.execute("""
            SELECT nomor, jenis, negara_penerbit, tanggal_terbit, tanggal_habis,
                CASE WHEN tanggal_habis >= CURRENT_DATE THEN 'Aktif' ELSE 'Kedaluwarsa' END AS status
            FROM identitas
            WHERE email_member = %s
            ORDER BY tanggal_terbit DESC
        """, (user_email,))
        identitas_list = cur.fetchall()
    except Exception as e:
        identitas_list = []

    context=base_context("member","","",user)

    return render(request, 'member/identitas.html', {
        "nav_items": nav_items,
        "role": "member",
        "identitas_list": identitas_list,
        "user_name": user["full_name"],
        "user_code": user["user_code"],
        "current_page": "Identitas Saya",
    })