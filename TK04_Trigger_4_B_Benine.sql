SET search_path TO aeromiles, public;

-- Pemeriksaan status klaim missing miles yang duplikat
CREATE OR REPLACE FUNCTION aeromiles.fn_check_duplicate_claim_missing_miles()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM aeromiles.claim_missing_miles c
        WHERE LOWER(c.email_member) = LOWER(NEW.email_member)
          AND c.flight_number = NEW.flight_number
          AND c.tanggal_penerbangan = NEW.tanggal_penerbangan
          AND c.nomor_tiket = NEW.nomor_tiket
    ) THEN
        RAISE EXCEPTION
            'ERROR: Klaim untuk penerbangan "%" pada tanggal "%" dengan nomor tiket "%" sudah pernah diajukan sebelumnya.',
            NEW.flight_number,
            NEW.tanggal_penerbangan,
            NEW.nomor_tiket;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_duplicate_claim_missing_miles
ON aeromiles.claim_missing_miles;

CREATE TRIGGER trg_check_duplicate_claim_missing_miles
BEFORE INSERT ON aeromiles.claim_missing_miles
FOR EACH ROW
EXECUTE FUNCTION aeromiles.fn_check_duplicate_claim_missing_miles();


-- Pembaruan tier member secara otomatis berdasarkan total miles
CREATE OR REPLACE FUNCTION aeromiles.fn_update_member_tier()
RETURNS TRIGGER AS $$
DECLARE
    old_tier_name VARCHAR(50);
    new_tier_id VARCHAR(10);
    new_tier_name VARCHAR(50);
BEGIN
    SELECT t.nama
    INTO old_tier_name
    FROM aeromiles.tier t
    WHERE t.id_tier = OLD.id_tier;

    SELECT t.id_tier, t.nama
    INTO new_tier_id, new_tier_name
    FROM aeromiles.tier t
    WHERE NEW.total_miles >= t.minimal_tier_miles
    ORDER BY t.minimal_tier_miles DESC, t.minimal_frekuensi_terbang DESC
    LIMIT 1;

    IF new_tier_id IS NOT NULL AND new_tier_id IS DISTINCT FROM NEW.id_tier THEN
        NEW.id_tier := new_tier_id;

        RAISE NOTICE
            'SUKSES: Tier Member "%" telah diperbarui dari "%" menjadi "%" berdasarkan total miles yang dimiliki.',
            NEW.email,
            old_tier_name,
            new_tier_name;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_member_tier
ON aeromiles.member;

CREATE TRIGGER trg_update_member_tier
BEFORE UPDATE OF total_miles ON aeromiles.member
FOR EACH ROW
WHEN (OLD.total_miles IS DISTINCT FROM NEW.total_miles)
EXECUTE FUNCTION aeromiles.fn_update_member_tier();
