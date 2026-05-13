SET search_path TO aeromiles;

-- ============================================================
-- TRIGGER: Sinkronisasi Total Miles Member setelah Klaim
--          Missing Miles Disetujui
--
-- Ketika staf mengubah status_penerimaan menjadi 'Diterima',
-- sistem otomatis menambahkan 1000 miles ke award_miles
-- dan total_miles member yang bersangkutan.
-- ============================================================

-- 1. Buat fungsi trigger dulu
CREATE OR REPLACE FUNCTION sync_miles_on_claim_approved()
RETURNS TRIGGER AS $$
DECLARE
    v_email_member VARCHAR(100);
    v_flight_number VARCHAR(10);
BEGIN
    -- Hanya jalankan jika status berubah MENJADI 'Diterima'
    -- (bukan update lain, dan bukan kalau sudah 'Diterima' sebelumnya)
    IF NEW.status_penerimaan = 'Diterima' AND OLD.status_penerimaan <> 'Diterima' THEN
        v_email_member := NEW.email_member;
        v_flight_number := NEW.flight_number;

        -- Tambah 1000 miles ke award_miles dan total_miles member
        UPDATE member
        SET
            award_miles = award_miles + 1000,
            total_miles = total_miles + 1000
        WHERE email = v_email_member;

        -- Raise notice sebagai pesan sukses (ditangkap di backend)
        RAISE NOTICE 'SUKSES: Total miles Member "%" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "%".',
            v_email_member, v_flight_number;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Buat trigger yang memanggil fungsi di atas
DROP TRIGGER IF EXISTS trigger_sync_miles_on_claim ON claim_missing_miles;

CREATE TRIGGER trigger_sync_miles_on_claim
    AFTER UPDATE OF status_penerimaan
    ON claim_missing_miles
    FOR EACH ROW
    EXECUTE FUNCTION sync_miles_on_claim_approved();


-- ============================================================
-- STORED PROCEDURE: Pemeringkatan Top 5 Member
--                   berdasarkan Total Miles
--
-- Mengembalikan daftar top 5 member dengan total_miles
-- tertinggi, lengkap dengan peringkat dan nama member.
-- ============================================================

CREATE OR REPLACE FUNCTION get_top5_member_by_total_miles()
RETURNS TABLE (
    peringkat   BIGINT,
    email       VARCHAR(100),
    nama_lengkap TEXT,
    total_miles INT
) AS $$
DECLARE
    v_top_email VARCHAR(100);
    v_top_miles INT;
BEGIN
    -- Ambil peringkat 1 untuk pesan sukses
    SELECT m.email, m.total_miles
    INTO v_top_email, v_top_miles
    FROM member m
    ORDER BY m.total_miles DESC
    LIMIT 1;

    -- Raise notice pesan sukses
    RAISE NOTICE 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, dengan peringkat pertama "%" memiliki % miles.',
        v_top_email, v_top_miles;

    -- Return top 5
    RETURN QUERY
        SELECT
            ROW_NUMBER() OVER (ORDER BY m.total_miles DESC) AS peringkat,
            m.email,
            (p.salutation || ' ' || p.first_mid_name || ' ' || p.last_name)::TEXT AS nama_lengkap,
            m.total_miles
        FROM member m
        JOIN pengguna p ON p.email = m.email
        ORDER BY m.total_miles DESC
        LIMIT 5;
END;
$$ LANGUAGE plpgsql;