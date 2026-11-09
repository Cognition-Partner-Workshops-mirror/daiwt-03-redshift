-- SQL UDFs only (Redshift no longer allows Python UDFs).

-- Fiscal year starts Feb 1: Feb-Apr = Q1, May-Jul = Q2, Aug-Oct = Q3, Nov-Jan = Q4.
CREATE OR REPLACE FUNCTION f_fiscal_qtr(d DATE)
RETURNS VARCHAR(8)
IMMUTABLE
AS $$
    SELECT 'Q' || ((((EXTRACT(MONTH FROM $1)::INT + 9) % 12) / 3) + 1)::VARCHAR
$$ LANGUAGE SQL;

-- Strip a phone string down to its digits.
CREATE OR REPLACE FUNCTION f_clean_phone(p VARCHAR)
RETURNS VARCHAR(32)
IMMUTABLE
AS $$
    SELECT REGEXP_REPLACE($1, '[^0-9]', '')
$$ LANGUAGE SQL;
