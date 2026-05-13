CREATE OR REPLACE FUNCTION check_duplicate_email()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM aeromiles.pengguna 
        WHERE LOWER(email) = LOWER(NEW.email)
    ) THEN
        RAISE EXCEPTION 'ERROR: Email "%" sudah terdaftar, silakan gunakan email lain.', NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_duplicate_email
BEFORE INSERT ON aeromiles.pengguna
FOR EACH ROW EXECUTE FUNCTION check_duplicate_email();

CREATE OR REPLACE FUNCTION aeromiles.raise_login_error()
RETURNS VOID AS $$
BEGIN
    RAISE EXCEPTION 'Email atau password salah, silakan coba lagi.';
END;
$$ LANGUAGE plpgsql;