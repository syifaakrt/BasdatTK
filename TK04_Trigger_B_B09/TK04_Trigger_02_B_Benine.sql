-- Trigger 1: Validasi saldo BEFORE UPDATE member
CREATE OR REPLACE FUNCTION validate_award_miles_transfer()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.award_miles < 0 THEN
        RAISE EXCEPTION 'ERROR: Saldo award miles tidak mencukupi. Saldo Anda saat ini: % miles, jumlah transfer: % miles.',
            OLD.award_miles,
            OLD.award_miles - NEW.award_miles;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trigger_validate_award_miles
BEFORE UPDATE OF award_miles ON aeromiles.member
FOR EACH ROW
EXECUTE FUNCTION validate_award_miles_transfer();


-- Trigger 2: Log transfer AFTER INSERT (sudah ada, update aja)
CREATE OR REPLACE FUNCTION log_transfer_miles()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'SUKSES: Transfer % miles dari "%" ke "%" berhasil dicatat.',
        NEW.jumlah,
        NEW.email_member_1,
        NEW.email_member_2;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trigger_log_transfer_miles
AFTER INSERT ON aeromiles.transfer
FOR EACH ROW
EXECUTE FUNCTION log_transfer_miles();


-- Stored procedure: hapus validasi manual, biarkan trigger yang handle
CREATE OR REPLACE FUNCTION transfer_miles(
    p_email_pengirim VARCHAR,
    p_email_penerima VARCHAR,
    p_jumlah INT,
    p_catatan VARCHAR
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE aeromiles.member
    SET award_miles = award_miles - p_jumlah
    WHERE email = p_email_pengirim;

    UPDATE aeromiles.member
    SET award_miles = award_miles + p_jumlah,
        total_miles = total_miles + p_jumlah
    WHERE email = p_email_penerima;

    INSERT INTO aeromiles.transfer(email_member_1, email_member_2, timestamp, jumlah, catatan)
    VALUES(p_email_pengirim, p_email_penerima, CURRENT_TIMESTAMP, p_jumlah, p_catatan);
END;
$$;