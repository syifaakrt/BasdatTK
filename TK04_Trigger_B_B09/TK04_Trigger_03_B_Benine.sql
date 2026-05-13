SET search_path TO aeromiles, public;

CREATE OR REPLACE FUNCTION trg_validate_redeem_before_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_award_miles INT;
    v_miles_hadiah INT;
    v_nama_hadiah VARCHAR(100);
    v_valid_start DATE;
    v_program_end DATE;
BEGIN
    SELECT award_miles
    INTO v_award_miles
    FROM member
    WHERE email = NEW.email_member
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION USING MESSAGE = 'ERROR: Member tidak ditemukan.';
    END IF;

    SELECT nama, miles, valid_start_date, program_end
    INTO v_nama_hadiah, v_miles_hadiah, v_valid_start, v_program_end
    FROM hadiah
    WHERE kode_hadiah = NEW.kode_hadiah;

    IF NOT FOUND THEN
        RAISE EXCEPTION USING MESSAGE = 'ERROR: Hadiah tidak ditemukan.';
    END IF;

    IF CURRENT_DATE < v_valid_start OR CURRENT_DATE > v_program_end THEN
        RAISE EXCEPTION USING MESSAGE = FORMAT(
            'ERROR: Hadiah "%s" tidak tersedia pada periode ini.',
            v_nama_hadiah
        );
    END IF;

    IF v_award_miles < v_miles_hadiah THEN
        RAISE EXCEPTION USING MESSAGE = FORMAT(
            'ERROR: Saldo award miles tidak mencukupi. Dibutuhkan %s miles, saldo Anda: %s miles.',
            v_miles_hadiah,
            v_award_miles
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS before_insert_redeem_validation ON redeem;
CREATE TRIGGER before_insert_redeem_validation
BEFORE INSERT ON redeem
FOR EACH ROW
EXECUTE FUNCTION trg_validate_redeem_before_insert();


CREATE OR REPLACE FUNCTION trg_reduce_award_miles_after_redeem()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE member AS m
    SET award_miles = m.award_miles - h.miles
    FROM hadiah AS h
    WHERE m.email = NEW.email_member
      AND h.kode_hadiah = NEW.kode_hadiah;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_insert_redeem_reduce_award_miles ON redeem;
CREATE TRIGGER after_insert_redeem_reduce_award_miles
AFTER INSERT ON redeem
FOR EACH ROW
EXECUTE FUNCTION trg_reduce_award_miles_after_redeem();


CREATE OR REPLACE FUNCTION trg_sync_miles_after_package_purchase()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE member AS m
    SET
        award_miles = m.award_miles + amp.jumlah_award_miles,
        total_miles = m.total_miles + amp.jumlah_award_miles
    FROM award_miles_package AS amp
    WHERE m.email = NEW.email_member
      AND amp.id = NEW.id_award_miles_package;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_insert_member_award_miles_package_sync ON member_award_miles_package;
CREATE TRIGGER after_insert_member_award_miles_package_sync
AFTER INSERT ON member_award_miles_package
FOR EACH ROW
EXECUTE FUNCTION trg_sync_miles_after_package_purchase();


CREATE OR REPLACE PROCEDURE sp_redeem_hadiah(
    IN p_email_member VARCHAR(100),
    IN p_kode_hadiah VARCHAR(20),
    INOUT p_message TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_nama_hadiah VARCHAR(100);
    v_miles_hadiah INT;
BEGIN
    SELECT nama, miles
    INTO v_nama_hadiah, v_miles_hadiah
    FROM hadiah
    WHERE kode_hadiah = p_kode_hadiah;

    IF NOT FOUND THEN
        RAISE EXCEPTION USING MESSAGE = 'ERROR: Hadiah tidak ditemukan.';
    END IF;

    INSERT INTO redeem (email_member, kode_hadiah)
    VALUES (p_email_member, p_kode_hadiah);

    p_message := FORMAT(
        'SUKSES: Redeem hadiah "%s" berhasil. Award miles Anda berkurang %s miles.',
        v_nama_hadiah,
        v_miles_hadiah
    );
END;
$$;


CREATE OR REPLACE PROCEDURE sp_beli_award_miles_package(
    IN p_email_member VARCHAR(100),
    IN p_id_award_miles_package VARCHAR(20),
    INOUT p_message TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_jumlah_award_miles INT;
BEGIN
    SELECT jumlah_award_miles
    INTO v_jumlah_award_miles
    FROM award_miles_package
    WHERE id = p_id_award_miles_package;

    IF NOT FOUND THEN
        RAISE EXCEPTION USING MESSAGE = 'ERROR: Package award miles tidak ditemukan.';
    END IF;

    INSERT INTO member_award_miles_package (id_award_miles_package, email_member)
    VALUES (p_id_award_miles_package, p_email_member);

    p_message := FORMAT(
        'SUKSES: Pembelian package berhasil. Award miles dan total miles Anda bertambah %s miles.',
        v_jumlah_award_miles
    );
END;
$$;