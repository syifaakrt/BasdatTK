CREATE OR REPLACE FUNCTION transfer_miles(
    p_email_pengirim VARCHAR,
    p_email_penerima VARCHAR,
    p_jumlah INT,
    p_catatan VARCHAR
)

RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_award_pengirim INT;
BEGIN

    SELECT award_miles
    INTO v_award_pengirim
    FROM aeromiles.member
    WHERE email = p_email_pengirim;

    -- VALIDASI SALDO
    IF v_award_pengirim < p_jumlah THEN

        RETURN
        'ERROR: Saldo award miles tidak mencukupi. '
        || 'Saldo Anda saat ini: '
        || v_award_pengirim
        || ' miles, jumlah transfer: '
        || p_jumlah
        || ' miles.';

    END IF;

    -- Kurangi saldo pengirim
    UPDATE aeromiles.member
    SET award_miles = award_miles - p_jumlah
    WHERE email = p_email_pengirim;

    -- Tambah saldo penerima
    UPDATE aeromiles.member
    SET
        award_miles = award_miles + p_jumlah,
        total_miles = total_miles + p_jumlah
    WHERE email = p_email_penerima;

    -- Insert log transfer
    INSERT INTO aeromiles.transfer(
        email_member_1,
        email_member_2,
        timestamp,
        jumlah,
        catatan
    )
    VALUES(
        p_email_pengirim,
        p_email_penerima,
        CURRENT_TIMESTAMP,
        p_jumlah,
        p_catatan
    );

    -- Return sukses
    RETURN
    'SUKSES: Transfer '
    || p_jumlah
    || ' miles dari "'
    || p_email_pengirim
    || '" ke "'
    || p_email_penerima
    || '" berhasil dicatat.';

END;
$$;

CREATE OR REPLACE FUNCTION log_transfer_miles()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    RAISE NOTICE
    'SUKSES: Transfer % miles dari "%" ke "%" berhasil dicatat.',
    NEW.jumlah,
    NEW.email_member_1,
    NEW.email_member_2;

    RETURN NEW;

END;
$$;

CREATE TRIGGER trigger_log_transfer_miles
AFTER INSERT ON aeromiles.transfer
FOR EACH ROW
EXECUTE FUNCTION log_transfer_miles();