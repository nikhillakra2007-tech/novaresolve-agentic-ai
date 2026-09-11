-- Migration 002: Add quantity column to replacements table
-- Preserves existing replacements with default quantity of 1
-- Enforces quantity > 0

ALTER TABLE replacements
ADD COLUMN IF NOT EXISTS quantity INTEGER NOT NULL DEFAULT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_replacement_quantity_positive'
    ) THEN
        ALTER TABLE replacements
        ADD CONSTRAINT chk_replacement_quantity_positive CHECK (quantity > 0);
    END IF;
END $$;
